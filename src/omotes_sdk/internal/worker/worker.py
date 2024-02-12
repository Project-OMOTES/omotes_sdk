import io
import logging
import pickle
import socket
from typing import Callable
from uuid import uuid4

from celery import Task as CeleryTask, Celery
from celery.apps.worker import Worker as CeleryWorker
from kombu import Queue as KombuQueue
import jsonpickle

from omotes_sdk.internal.worker.configs import WorkerConfig
from omotes_sdk.internal.common.broker_interface import BrokerInterface
from omotes_sdk.internal.orchestrator_worker_events.messages import (
    StatusUpdateMessage,
    TaskStatus,
    CalculationResult,
)

logger = logging.getLogger("omotes_sdk_internal")


class TaskUtil:
    def __init__(self, task: CeleryTask):
        self.task = task

    def update_progress(self, fraction: float, message: str) -> None:
        # TODO Needs to be fixed to not use Celery event system, but Broker Interface &
        #  omotes_task_events queue
        self.task.send_event(
            "task-progress-update", progress={"fraction": fraction, "message": message}
        )


class WorkerTask(CeleryTask):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        super().on_failure(exc, task_id, args, kwargs, einfo)
        logger.error("Failure detected for celery task %s", task_id)
        # TODO Entrypoint to notify orchestrator & sdk of failure of task. At least in case where
        #  Celery itself or the task triggers an error. This is necessary as task is dropped but an
        #  error is published to logs. SDK wouldn't be notified otherwise.


def wrapped_worker_task(task: WorkerTask, job_id: uuid4, esdl_string: bytes):
    """Task performed by Celery.

    Note: Be careful! This spawns within a subprocess and gains a copy of memory from parent
    process. You cannot open sockets and other resources in the main process and expect
    it to be copied to subprocess. Any resources e.g. connections/sockets need to be opened
    in this task by the subprocess.

    :param task:
    :param job_id:
    :param esdl_string:
    :return: Pickled Calculation result
    """
    with BrokerInterface(config=WORKER.config.rabbitmq) as broker_if:
        # global logging_string
        # logging_string = io.StringIO()
        logger.info("GROW worker started new task %s", job_id)
        broker_if.send_message_to(
            WORKER.config.task_event_queue_name,
            pickle.dumps(
                StatusUpdateMessage(
                    omotes_job_id=job_id,
                    celery_task_id=task.request.id,
                    status=TaskStatus.STARTED,
                    task_type=task.name,
                ).to_dict()
            ),
        )

        result = WORKER_TASK_FUNCTION(task, job_id, esdl_string, TaskUtil(task).update_progress)

        broker_if.send_message_to(
            WORKER.config.task_event_queue_name,
            pickle.dumps(
                StatusUpdateMessage(
                    omotes_job_id=job_id,
                    celery_task_id=task.request.id,
                    status=TaskStatus.SUCCEEDED,
                    task_type=task.name,
                ).to_dict()
            ),
        )
    return jsonpickle.encode(result)


class Worker:
    config = WorkerConfig()
    captured_logging_string = io.StringIO()

    celery_app: Celery
    celery_worker: CeleryWorker

    def start(self):
        config = self.config
        self.celery_app = Celery(
            "omotes",
            broker=f"amqp://{config.rabbitmq.username}:{config.rabbitmq.password}@{config.rabbitmq.host}:{config.rabbitmq.port}/{config.rabbitmq.virtual_host}",
            backend=f"db+postgresql://{config.postgresql.username}:{config.postgresql.password}@{config.postgresql.host}:{config.postgresql.port}/{config.postgresql.database}",
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

        logger.info("Starting GROW worker to work on task %s", WORKER_TASK_TYPE)
        logger.info(
            "Connected to broker rabbitmq (%s:%s/%s) as %s",
            config.rabbitmq.host,
            config.rabbitmq.port,
            config.rabbitmq.virtual_host,
            config.rabbitmq.username,
        )

        self.celery_worker = self.celery_app.Worker(
            hostname=f"worker-{WORKER_TASK_TYPE}@{socket.gethostname()}",
            log_level=logging.getLevelName(config.log_level),
            autoscale=(1, 1),
        )

        self.celery_worker.start()

        logger.info(
            "Connected to backend postgresql (%s:%s/%s) as %s",
            config.postgresql.host,
            config.postgresql.port,
            config.postgresql.database,
            config.postgresql.username,
        )


UpdateProgressHandler = Callable[[float, str], None]
WorkerTaskF = Callable[[WorkerTask, uuid4, bytes, UpdateProgressHandler], CalculationResult]

WORKER: Worker = None  # noqa
WORKER_TASK_FUNCTION: WorkerTaskF = None  # noqa
WORKER_TASK_TYPE: str = None  # noqa


def initialize_worker(
    task_type: str,
    task_function: WorkerTaskF,
) -> None:
    global WORKER_TASK_FUNCTION, WORKER_TASK_TYPE, WORKER
    WORKER_TASK_TYPE = task_type
    WORKER_TASK_FUNCTION = task_function
    WORKER = Worker()
    WORKER.start()
