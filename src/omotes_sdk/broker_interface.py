import asyncio
import logging
from asyncio import Task
from concurrent.futures import Future
from dataclasses import dataclass
from functools import partial
import threading
from typing import Callable, Optional, Set, Dict

from aio_pika import connect_robust, Message
from aio_pika.abc import AbstractRobustConnection, AbstractChannel, AbstractQueue

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
        async with self.queue.iterator() as queue_iter:
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

    Will only work if a single message is expected to publish to the queue. Otherwise, the
    consumer subscription may receive multiple messages and a number of messages will be lost.
    Only the first message will be accepted and
    processed.
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
        logger.debug(
            "Waiting for next message on queue %s with timeout %s", self.queue.name, self.timeout
        )
        async with self.queue.iterator() as queue_iter:
            try:
                message = await asyncio.wait_for(anext(queue_iter), timeout=self.timeout)  # noqa
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
    TIMEOUT_ON_STOP_SECONDS: int = 5
    """How long to wait till the broker connection has stopped before killing it non-gracefully."""

    config: RabbitMQConfig

    _loop: asyncio.AbstractEventLoop
    """The eventloop in which all broker-related async traffic is run."""
    _connection: AbstractRobustConnection
    """AMQP connection."""
    _channel: AbstractChannel
    """AMQP channel."""
    _queue_subscription_consumer_by_name: Dict[str, QueueSubscriptionConsumer]
    """Task to consume messages when they are received ordered by queue name."""
    _queue_subscription_tasks: Set[Task]
    """Reference to the queue subscription task """
    _queue_retrieve_next_message_tasks: Set[Task]
    """Reference to the queue next message task """
    _ready_for_processing: threading.Event
    """Thread-safe check which is set once the AMQP connection is up and running."""
    _stopping_lock: threading.Lock
    _stopping: bool
    _stopped: bool

    def __init__(self, config: RabbitMQConfig):
        super().__init__()
        self.config = config

        self._queue_subscription_consumer_by_name = {}
        self._queue_subscription_tasks = set()
        self._queue_retrieve_next_message_tasks = set()
        self._ready_for_processing = threading.Event()
        self._stopping_lock = threading.Lock()
        self._stopping = False
        self._stopped = False

    async def _send_message_to(self, queue_name: str, message: bytes) -> None:
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
        queue = await self._channel.declare_queue(queue_name)
        queue_consumer = QueueSubscriptionConsumer(queue, callback_on_message)
        self._queue_subscription_consumer_by_name[queue_name] = queue_consumer

        queue_subscription_task = asyncio.create_task(queue_consumer.run())
        queue_subscription_task.add_done_callback(
            partial(self._remove_queue_subscription_task, queue_name, queue_subscription_task)
        )
        self._queue_subscription_tasks.add(queue_subscription_task)

    async def _receive_next_message(
        self,
        queue_name: str,
        timeout: Optional[float],
        callback_on_message: Callable[[bytes], None],
        callback_on_no_message: Optional[Callable[[], None]],
    ) -> None:
        logger.info("Declaring queue and retrieving the next message to %s", queue_name)
        queue = await self._channel.declare_queue(queue_name)
        queue_retriever = QueueSingleMessageConsumer(
            queue, timeout, callback_on_message, callback_on_no_message
        )

        queue_retriever_task = asyncio.create_task(queue_retriever.run())
        queue_retriever_task.add_done_callback(
            partial(self._remove_queue_next_message_task, queue_name, queue_retriever_task)
        )
        self._queue_retrieve_next_message_tasks.add(queue_retriever_task)

    def _remove_queue_subscription_task(
        self, queue_name: str, queue_subscription_task: Task, future: Future
    ) -> None:
        """Remove the queue from the internal cache.

        :param queue_name:
        :param queue_subscription_task:
        """
        if queue_subscription_task in self._queue_subscription_tasks:
            logger.debug("Queue subscription %s is done. Calling termination callback", queue_name)
            # TODO Remove / delete queue if unused?
            del self._queue_subscription_consumer_by_name[queue_name]
            self._queue_subscription_tasks.remove(queue_subscription_task)

    def _remove_queue_next_message_task(
        self, queue_name: str, queue_retriever_task: Task, future: Future
    ) -> None:
        if queue_retriever_task in self._queue_retrieve_next_message_tasks:
            logger.debug(
                "Waiting for single message on %s is done. Calling termination callback", queue_name
            )
            self._queue_retrieve_next_message_tasks.remove(queue_retriever_task)

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
        )
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=1)
        self._ready_for_processing.set()

    async def _stop_broker_interface(self) -> None:
        """Cancel all subscriptions, close the channel and the connection."""
        logger.info("Stopping broker interface")
        tasks_to_cancel = list(self._queue_subscription_tasks) + list(
            self._queue_retrieve_next_message_tasks
        )
        for queue_task in tasks_to_cancel:
            queue_task.cancel()

        await self._channel.close()
        await self._connection.close()

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
        """Add AMQP subscription to a queue and register callback to be called on each new
        message."""
        asyncio.run_coroutine_threadsafe(
            self._add_queue_subscription(queue_name, callback_on_message), self._loop
        ).result()

    def receive_next_message(
        self,
        queue_name: str,
        timeout: Optional[float],
        callback_on_message: Callable[[bytes], None],
        callback_on_no_message: Optional[Callable[[], None]],
    ) -> None:
        """
        :param queue_name: Name of the queue to retrieve a message from.
        :param timeout: Time to wait for message to arrive in seconds. If None is used, the timeout
            is infinite.
        :param callback_on_message: Callback which is called when the message is received.
        :param callback_on_no_message: Callback which is called when no message is received in the
            alloted time.
        """
        asyncio.run_coroutine_threadsafe(
            self._receive_next_message(
                queue_name, timeout, callback_on_message, callback_on_no_message
            ),
            self._loop,
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
