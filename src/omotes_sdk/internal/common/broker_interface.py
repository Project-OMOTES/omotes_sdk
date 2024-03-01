import asyncio
import logging
from asyncio import Task
from concurrent.futures import Future
from dataclasses import dataclass
from functools import partial
import threading
from types import TracebackType
from typing import Callable, Optional, Dict, Type

from aio_pika import connect_robust, Message
from aio_pika.abc import (
    AbstractRobustConnection,
    AbstractChannel,
    AbstractQueue,
    AbstractIncomingMessage,
)

from omotes_sdk.config import RabbitMQConfig

logger = logging.getLogger("omotes_sdk")


@dataclass
class QueueSubscriptionConsumer:
    """Consumes a queue until stopped and forwards received messages using a callback."""

    queue: AbstractQueue
    """The queue to which is subscribed."""
    callback_on_message: Callable[[bytes], None]
    """Callback which is called on each message."""

    async def run(self) -> None:
        """Retrieve messages from the AMQP queue and run callback on each message.

        Requeue in case the handler generates an exception. Callback is a synchronous
        function which is executed from the executor threadpool.
        """
        async with self.queue.iterator() as queue_iter:
            message: AbstractIncomingMessage
            async for message in queue_iter:
                async with message.process(requeue=True):
                    logger.debug(
                        "Received with queue subscription on queue %s: %s",
                        self.queue.name,
                        message.body,
                    )
                    await asyncio.get_running_loop().run_in_executor(
                        None, partial(self.callback_on_message, message.body)
                    )


@dataclass
class QueueSingleMessageConsumer:
    """Retrieves a single message from a queue and processes the message using a callback.

    NOTE: Will only work if a single message is expected to publish to the queue. Otherwise, the
    consumer subscription may receive multiple messages and a number of messages will be lost.
    Only the first message will be accepted and processed.
    """

    queue: AbstractQueue
    """The queue to which is subscribed."""
    timeout: Optional[float]
    """Time to wait for message to arrive in seconds."""
    callback_on_message: Callable[[bytes], None]
    """Callback which is called when the message is received."""
    callback_on_no_message: Optional[Callable[[], None]]
    """Callback which is called when no message is received in the alloted time."""

    async def run(self) -> None:
        """Retrieve a single message from the AMQP queue and run the callback on the message.

        Requeue in case the handler generates an exception. Callback is a synchronous
        function which is executed from the executor threadpool.

        As a `queue.iterator()` is used, an AMQP Consumption subscription is created rather than
        an AMQP Get request. This allows this consumer to wait until a message is received instead
        of working on a polling basis.
        """
        logger.debug(
            "Waiting for next message on queue %s with timeout %s", self.queue.name, self.timeout
        )
        async with self.queue.iterator() as queue_iter:
            try:
                message = await asyncio.wait_for(queue_iter.__anext__(), timeout=self.timeout)
            except TimeoutError:
                if self.callback_on_no_message:
                    asyncio.get_running_loop().run_in_executor(None, self.callback_on_no_message)
            else:
                async with message.process(requeue=True):
                    logger.debug(
                        "Received next message on queue %s: %s", self.queue.name, message.body
                    )
                    await asyncio.get_running_loop().run_in_executor(
                        None, partial(self.callback_on_message, message.body)
                    )


class BrokerInterface(threading.Thread):
    """Interface to RabbitMQ using aiopika."""

    TIMEOUT_ON_STOP_SECONDS: int = 5
    """How long to wait till the broker connection has stopped before killing it non-gracefully."""

    config: RabbitMQConfig
    """The broker configuration."""

    _loop: asyncio.AbstractEventLoop
    """The eventloop in which all broker-related async traffic is run."""
    _connection: AbstractRobustConnection
    """AMQP connection."""
    _channel: AbstractChannel
    """AMQP channel."""
    _queue_subscription_consumer_by_name: Dict[str, QueueSubscriptionConsumer]
    """Task to consume messages when they are received ordered by queue name."""
    _queue_subscription_tasks: Dict[str, Task]
    """Reference to the queue subscription task by queue name."""
    _queue_retrieve_next_message_tasks: Dict[str, Task]
    """Reference to the queue next message task by queue name."""
    _ready_for_processing: threading.Event
    """Thread-safe check which is set once the AMQP connection is up and running."""
    _stopping_lock: threading.Lock
    """Lock to make sure only a single thread is stopping this interface."""
    _stopping: bool
    """Value to check if a thread is stopping this interface."""
    _stopped: bool
    """Value to check if this interface has successfully stopped."""

    def __init__(self, config: RabbitMQConfig):
        """Create the BrokerInterface.

        :param config: Configuration to connect to RabbitMQ.
        """
        super().__init__()
        self.config = config

        self._queue_subscription_consumer_by_name = {}
        self._queue_subscription_tasks = {}
        self._queue_retrieve_next_message_tasks = {}
        self._ready_for_processing = threading.Event()
        self._stopping_lock = threading.Lock()
        self._stopping = False
        self._stopped = False

    def __enter__(self) -> "BrokerInterface":
        """Start the interface when it is called as a context manager."""
        self.start()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Stop the interface when it is called as a context manager."""
        self.stop()

    async def _send_message_to(self, queue_name: str, message: bytes) -> None:
        """Publish a message to a specific queue assuming the routing key equals the queue name."""
        logger.debug("Sending a message to %s containing: %s", queue_name, message)
        await self._channel.default_exchange.publish(Message(body=message), routing_key=queue_name)

    async def _add_queue_subscription(
        self, queue_name: str, callback_on_message: Callable[[bytes], None]
    ) -> None:
        """Declare an AMQP queue and subscribe to the messages.

        :param queue_name: Name of the queue to declare.
        :param callback_on_message: Callback which is called from a separate thread to process the
            message body.
        """
        if queue_name in self._queue_subscription_consumer_by_name:
            logger.error(
                "Attempting to declare a subscription on %s but a "
                "subscription on this queue already exists."
            )
            raise RuntimeError(f"Queue subscription for {queue_name} already exists.")
        logger.info("Declaring queue and adding subscription to %s", queue_name)
        queue = await self._channel.declare_queue(queue_name, durable=True, auto_delete=False)
        queue_consumer = QueueSubscriptionConsumer(queue, callback_on_message)
        self._queue_subscription_consumer_by_name[queue_name] = queue_consumer

        queue_subscription_task = asyncio.create_task(queue_consumer.run())
        queue_subscription_task.add_done_callback(
            partial(self._remove_queue_subscription_task, queue_name)
        )
        self._queue_subscription_tasks[queue_name] = queue_subscription_task

    async def _remove_queue_subscription(self, queue_name: str) -> None:
        """Remove subscription from queue and delete the queue if one exists.

        :param queue_name: Name of the queue to unsubscribe from.
        """
        if queue_name in self._queue_subscription_tasks:
            logger.info("Stopping subscription to %s and remove queue", queue_name)
            self._queue_subscription_tasks[queue_name].cancel()
            await self._channel.queue_delete(queue_name)

    async def _receive_next_message(
        self,
        queue_name: str,
        timeout: Optional[float],
        callback_on_message: Callable[[bytes], None],
        callback_on_no_message: Optional[Callable[[], None]],
    ) -> None:
        """Declare an AMQP queue and wait for the next message on it to arrive.

        :param queue_name: Name of the queue and routing key.
        :param timeout: How long to wait until the next message arrives.
        :param callback_on_message: Callback which is executed when the message arrives.
        :param callback_on_no_message: Callback which is called when the message does not arrive
            within the timeout.
        """
        logger.info("Declaring queue and retrieving the next message to %s", queue_name)
        queue = await self._channel.declare_queue(queue_name, durable=True, auto_delete=False)
        queue_retriever = QueueSingleMessageConsumer(
            queue, timeout, callback_on_message, callback_on_no_message
        )

        queue_retriever_task = asyncio.create_task(queue_retriever.run())
        queue_retriever_task.add_done_callback(
            partial(self._remove_queue_next_message_task, queue_name)
        )
        self._queue_retrieve_next_message_tasks[queue_name] = queue_retriever_task

    async def _remove_queue_next_message_subscription(self, queue_name: str) -> None:
        """Remove subscription from queue and delete the queue if one exists.

        :param queue_name: Name of the queue to unsubscribe from.
        """
        if queue_name in self._queue_retrieve_next_message_tasks:
            logger.info("Stop waiting for next message on %s and remove queue", queue_name)
            self._queue_retrieve_next_message_tasks[queue_name].cancel()
            await self._channel.queue_delete(queue_name)

    def _remove_queue_subscription_task(self, queue_name: str, future: Future) -> None:
        """Remove the queue subscription from the internal cache.

        :param queue_name: Name of the queue to which is subscribed.
        :param future: Required argument from Task.add_done_callback which also refers to the
            task running the subscription but as a `Future`.
        """
        if queue_name in self._queue_subscription_tasks:
            logger.debug("Queue subscription %s is done. Calling termination callback", queue_name)
            del self._queue_subscription_consumer_by_name[queue_name]
            del self._queue_subscription_tasks[queue_name]

    def _remove_queue_next_message_task(self, queue_name: str, future: Future) -> None:
        """Remove the task waiting for next message from queue from the internal cache.

        :param queue_name: Name of the queue which is awaiting an new message.
        :param future: Required argument from Task.add_done_callback which also refers to the
            task running the subscription but as a `Future`.
        """
        if queue_name in self._queue_retrieve_next_message_tasks:
            logger.debug(
                "Waiting for single message on %s is done. Calling termination callback", queue_name
            )
            del self._queue_retrieve_next_message_tasks[queue_name]

    async def _setup_broker_interface(self) -> None:
        """Start the AMQP connection and channel."""
        logger.info(
            "Broker interface connecting to %s:%s as %s at %s",
            self.config.host,
            self.config.port,
            self.config.username,
            self.config.virtual_host,
        )

        self._connection = await connect_robust(
            host=self.config.host,
            port=self.config.port,
            login=self.config.username,
            password=self.config.password,
            virtualhost=self.config.virtual_host,
            loop=self._loop,
            fail_fast="false",  # aiormq requires this to be str and not bool
        )
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=1)
        self._ready_for_processing.set()

    async def _stop_broker_interface(self) -> None:
        """Cancel all subscriptions, close the channel and the connection."""
        logger.info("Stopping broker interface")
        tasks_to_cancel = list(self._queue_subscription_tasks.values()) + list(
            self._queue_retrieve_next_message_tasks.values()
        )
        for queue_task in tasks_to_cancel:
            queue_task.cancel()
        if self._channel:
            await self._channel.close()
        if self._connection:
            await self._connection.close()
        logger.info("Stopped broker interface")

    def start(self) -> None:
        """Start the broker interface."""
        super().start()
        self._ready_for_processing.wait()

    def run(self) -> None:
        """Run the broker interface and start the AMQP connection.

        In a separate thread and starting a new, isolated eventloop. The AMQP connection and
        channel are started as its first task.
        """
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            self._loop.create_task(self._setup_broker_interface())
            self._loop.run_forever()
        finally:
            self._loop.close()

    def add_queue_subscription(
        self, queue_name: str, callback_on_message: Callable[[bytes], None]
    ) -> None:
        """Declare an AMQP queue and subscribe to the messages.

        :param queue_name: Name of the queue to declare.
        :param callback_on_message: Callback which is called from a separate thread to process the
            message body.
        """
        asyncio.run_coroutine_threadsafe(
            self._add_queue_subscription(queue_name, callback_on_message), self._loop
        ).result()

    def remove_queue_subscription(self, queue_name: str) -> None:
        """Remove subscription from queue and delete the queue if one exists.

        :param queue_name: Name of the queue to unsubscribe from.
        """
        asyncio.run_coroutine_threadsafe(
            self._remove_queue_subscription(queue_name), self._loop
        ).result()

    def receive_next_message(
        self,
        queue_name: str,
        timeout: Optional[float],
        callback_on_message: Callable[[bytes], None],
        callback_on_no_message: Optional[Callable[[], None]],
    ) -> None:
        """Declare an AMQP queue and wait for the next message on it to arrive.

        :param queue_name: Name of the queue to retrieve a message from.
        :param timeout: Time to wait for message to arrive in seconds. If None is used, the timeout
            is infinite.
        :param callback_on_message: Callback which is called when the message is received.
        :param callback_on_no_message: Callback which is called when no message is received in the
            allotted time.
        """
        asyncio.run_coroutine_threadsafe(
            self._receive_next_message(
                queue_name, timeout, callback_on_message, callback_on_no_message
            ),
            self._loop,
        ).result()

    def remove_queue_next_message_subscription(self, queue_name: str) -> None:
        """Remove subscription from queue and delete the queue if one exists.

        :param queue_name: Name of the queue to unsubscribe from.
        """
        asyncio.run_coroutine_threadsafe(
            self._remove_queue_next_message_subscription(queue_name), self._loop
        ).result()

    def send_message_to(self, queue_name: str, message: bytes) -> None:
        """Publish a single message to the queue.

        :param queue_name: Name of the queue to publish the message to.
        :param message: The message to send.
        """
        asyncio.run_coroutine_threadsafe(
            self._send_message_to(queue_name, message), self._loop
        ).result()

    def stop(self) -> None:
        """Stop the broker interface.

        By shutting down the AMQP connection and stopping the eventloop.
        """
        will_stop = False
        with self._stopping_lock:
            if not self._stopping:
                self._stopping = True
                will_stop = True

        if will_stop:
            future = asyncio.run_coroutine_threadsafe(self._stop_broker_interface(), self._loop)
            try:
                future.result(timeout=BrokerInterface.TIMEOUT_ON_STOP_SECONDS)
            except Exception:
                logger.exception("Could not stop the broker interface during shutdown.")
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._stopped = True
