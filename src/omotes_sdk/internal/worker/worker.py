import io
import logging
import socket
from typing import Callable, Dict, List, Any
from uuid import UUID

from billiard.einfo import ExceptionInfo
from celery import Task as CeleryTask, Celery
from celery.apps.worker import Worker as CeleryWorker
from kombu import Queue as KombuQueue

from omotes_sdk.internal.worker.configs import WorkerConfig
from omotes_sdk.internal.common.broker_interface import BrokerInterface
from omotes_sdk.internal.orchestrator_worker_events.messages.task_pb2 import (
    TaskResult,
    TaskProgressUpdate,
)

logger = logging.getLogger("omotes_sdk_internal")


class TaskUtil:
    """Utilities for a Celery task."""

    job_id: UUID
    """The id of the job this task belongs to."""
    task: CeleryTask
    """Reference to the Celery task which is executed."""
    broker_if: BrokerInterface
    """Interface to the OMOTES Celery RabbitMQ."""

    def __init__(self, job_id: UUID, task: CeleryTask, broker_if: BrokerInterface):
        """Create the task utilities.

        :param job_id: The id of the job this task belongs to.
        :param task: Reference to the Celery task which is executed.
        :param broker_if: Interface to the OMOTES Celery RabbitMQ.
        """
        self.job_id = job_id
        self.task = task
        self.broker_if = broker_if

    def update_progress(self, fraction: float, message: str) -> None:
        """Send a progress update to the orchestrator.

        :param fraction: Value between 0.0 and 1.0 to denote the progress.
        :param message: Message which explains the current progress of the task.
        """
        logger.debug(
            "Sending progress update. Progress %s for job %s (celery id %s) with message %s",
            fraction,
            self.job_id,
            self.task.request.id,
            message,
        )
        self.broker_if.send_message_to(
            WORKER.config.task_progress_queue_name,
            TaskProgressUpdate(
                job_id=str(self.job_id),
                celery_task_id=self.task.request.id,
                celery_task_type=WORKER_TASK_TYPE,
                progress=float(fraction),
                message=message,
            ).SerializeToString(),
        )


class WorkerTask(CeleryTask):
    """Wrapped CeleryTask to connect to a number of CeleryTask events."""

    def on_failure(
        self,
        exc: Exception,
        task_id: str,
        args: List[Any],
        kwargs: Dict[str, Any],
        einfo: ExceptionInfo,
    ) -> None:
        """Runs when the CeleryTask fails on an exception.

        :param exc: The exception triggered by the task.
        :param task_id: Celery task id of the task.
        :param args: Unnamed arguments passed to the CeleryTask.
        :param kwargs: Named arguments passed to the CeleryTask.
        :param einfo: Context information regarding the exception triggered.
        """
        super().on_failure(exc, task_id, args, kwargs, einfo)
        logger.error("Failure detected for celery task %s", task_id)
        # TODO Entrypoint to notify orchestrator & sdk of failure of task. At least in case where
        #  Celery itself or the task triggers an error. This is necessary as task is dropped but an
        #  error is published to logs. SDK wouldn't be notified otherwise.


def wrapped_worker_task(task: WorkerTask, job_id: UUID, encoded_input_esdl: bytes) -> None:
    """Task performed by Celery.

    Note: Be careful! This spawns within a subprocess and gains a copy of memory from parent
    process. You cannot open sockets and other resources in the main process and expect
    it to be copied to subprocess. Any resources e.g. connections/sockets need to be opened
    in this task by the subprocess.

    :param task: Reference to the CeleryTask.
    :param job_id: Id of the job this task belongs to.
    :param encoded_input_esdl: UTF-8 encoded ESDL description which needs to be processed.
    """
    with BrokerInterface(config=WORKER.config.rabbitmq_config) as broker_if:
        # captured_logging_string = io.StringIO()
        logger.info("Worker started new task %s", job_id)

        task_util = TaskUtil(job_id, task, broker_if)
        task_util.update_progress(0, "Job calculation started")
        input_esdl = encoded_input_esdl.decode()
        # TODO retrieve config as an input argument from Celery.
        #  See https://github.com/Project-OMOTES/omotes-sdk-python/issues/3
        workflow_config: Dict[str, str] = {}
        output_esdl = WORKER_TASK_FUNCTION(input_esdl, workflow_config, task_util.update_progress)

        task_util.update_progress(1.0, "Calculation finished.")
        result_message = TaskResult(
            job_id=str(job_id),
            celery_task_id=task.request.id,
            celery_task_type=WORKER_TASK_TYPE,
            result_type=TaskResult.ResultType.SUCCEEDED,
            output_esdl=output_esdl,
            logs="",  # TODO captured_logging_string.getvalue(),
        )
        broker_if.send_message_to(
            WORKER.config.task_result_queue_name,
            result_message.SerializeToString(),
        )


class Worker:
    """Worker which works as an Celery Worker application and runs a single type of task."""

    config = WorkerConfig()
    """Configuration for the worker."""
    captured_logging_string = io.StringIO()
    """Captured logging while performing the task."""

    celery_app: Celery
    """Contains the Celery app configuration."""
    celery_worker: CeleryWorker
    """The Celery Worker app."""

    def start(self) -> None:
        """Start the `Worker`.

        Creates the Celery application, Celery Worker application and connects to RabbitMQ.
        """
        rabbitmq_config = self.config.rabbitmq_config
        self.celery_app = Celery(
            broker=f"amqp://{rabbitmq_config.username}:{rabbitmq_config.password}@"
            f"{rabbitmq_config.host}:{rabbitmq_config.port}/{rabbitmq_config.virtual_host}",
        )

        # Config of celery app
        self.celery_app.conf.task_queues = (
            KombuQueue(WORKER_TASK_TYPE, routing_key=WORKER_TASK_TYPE),
        )  # Tell the worker to listen to a specific queue for 1 workflow type.
        self.celery_app.conf.task_acks_late = True
        self.celery_app.conf.task_reject_on_worker_lost = True
        self.celery_app.conf.task_acks_on_failure_or_timeout = False
        self.celery_app.conf.worker_prefetch_multiplier = 1
        self.celery_app.conf.broker_connection_retry_on_startup = True
        # app.conf.worker_send_task_events = True  # Tell the worker to send task events.

        self.celery_app.task(wrapped_worker_task, base=WorkerTask, name=WORKER_TASK_TYPE, bind=True)

        logger.info("Starting Worker to work on task %s", WORKER_TASK_TYPE)
        logger.info(
            "Connected to broker rabbitmq (%s:%s/%s) as %s",
            rabbitmq_config.host,
            rabbitmq_config.port,
            rabbitmq_config.virtual_host,
            rabbitmq_config.username,
        )

        self.celery_worker = self.celery_app.Worker(
            hostname=f"worker-{WORKER_TASK_TYPE}@{socket.gethostname()}",
            log_level=logging.getLevelName(self.config.log_level),
            autoscale=(1, 1),
        )

        self.celery_worker.start()


UpdateProgressHandler = Callable[[float, str], None]
WorkerTaskF = Callable[[str, Dict[str, str], UpdateProgressHandler], str]

WORKER: Worker = None  # type: ignore [assignment]  # noqa
WORKER_TASK_FUNCTION: WorkerTaskF = None  # type: ignore [assignment]  # noqa
WORKER_TASK_TYPE: str = None  # type: ignore [assignment]  # noqa


def initialize_worker(
    task_type: str,
    task_function: WorkerTaskF,
) -> None:
    """Initialize and run the `Worker`.

    :param task_type: Technical name of the task. Needs to be equal to the name of the celery task
      to which the orchestrator forwards the task.
    :param task_function: Function which performs the Celery task.
    """
    global WORKER_TASK_FUNCTION, WORKER_TASK_TYPE, WORKER
    WORKER_TASK_TYPE = task_type
    WORKER_TASK_FUNCTION = task_function
    WORKER = Worker()
    WORKER.start()
