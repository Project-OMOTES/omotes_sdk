import logging
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Callable, Optional

from omotes_sdk.internal.common.broker_interface import BrokerInterface
from omotes_sdk.config import RabbitMQConfig
from omotes_sdk_protocol.job_pb2 import (
    JobResult,
    JobProgressUpdate,
    JobStatusUpdate,
    JobSubmission,
    JobCancel,
)
from omotes_sdk.job import Job
from omotes_sdk.queue_names import OmotesQueueNames
from omotes_sdk.workflow_type import WorkflowType

logger = logging.getLogger("omotes_sdk")


@dataclass
class JobSubmissionCallbackHandler:
    """Handler for updates on a submitted job."""

    job: Job
    """The job to listen to."""
    callback_on_finished: Callable[[Job, JobResult], None]
    """Handler which is called when a job finishes."""
    callback_on_progress_update: Optional[Callable[[Job, JobProgressUpdate], None]]
    """Handler which is called on a job progress update."""
    callback_on_status_update: Optional[Callable[[Job, JobStatusUpdate], None]]
    """Handler which is called on a job status update."""
    auto_disconnect_on_result_handler: Optional[Callable[[Job], None]]
    """Handler to remove/disconnect from all queues pertaining to this job once the result is 
    received and handled without exceptions through `callback_on_finished`."""

    def callback_on_finished_wrapped(self, message: bytes) -> None:
        """Parse a serialized JobResult message and call handler.

        :param message: Serialized message.
        """
        job_result = JobResult()
        job_result.ParseFromString(message)
        self.callback_on_finished(self.job, job_result)

        if self.auto_disconnect_on_result_handler:
            self.auto_disconnect_on_result_handler(self.job)

    def callback_on_progress_update_wrapped(self, message: bytes) -> None:
        """Parse a serialized JobProgressUpdate message and call handler.

        :param message: Serialized message.
        """
        progress_update = JobProgressUpdate()
        progress_update.ParseFromString(message)
        if self.callback_on_progress_update:
            self.callback_on_progress_update(self.job, progress_update)

    def callback_on_status_update_wrapped(self, message: bytes) -> None:
        """Parse a serialized JobStatusUpdate message and call handler.

        :param message: Serialized message.
        """
        status_update = JobStatusUpdate()
        status_update.ParseFromString(message)
        if self.callback_on_status_update:
            self.callback_on_status_update(self.job, status_update)


class OmotesInterface:
    """SDK interface for other applications to communicate with OMOTES."""

    broker_if: BrokerInterface
    """Interface to RabbitMQ broker."""

    def __init__(self, rabbitmq_config: RabbitMQConfig):
        """Create the OMOTES interface.

        NOTE: Needs to be started separately.

        :param rabbitmq_config: RabbitMQ configuration how to connect to OMOTES.
        """
        self.broker_if = BrokerInterface(rabbitmq_config)

    def start(self) -> None:
        """Start any other interfaces."""
        self.broker_if.start()

    def stop(self) -> None:
        """Stop any other interfaces."""
        self.broker_if.stop()

    def disconnect_from_submitted_job(self, job: Job) -> None:
        """Disconnect from the submitted job and delete all queues on the broker.

        :param job: Job to disconnect from.
        """

        self.broker_if.remove_queue_next_message_subscription(
            OmotesQueueNames.job_results_queue_name(job)
        )
        self.broker_if.remove_queue_subscription(OmotesQueueNames.job_progress_queue_name(job))
        self.broker_if.remove_queue_subscription(OmotesQueueNames.job_status_queue_name(job))

    def connect_to_submitted_job(
        self,
        job: Job,
        callback_on_finished: Callable[[Job, JobResult], None],
        callback_on_progress_update: Optional[Callable[[Job, JobProgressUpdate], None]],
        callback_on_status_update: Optional[Callable[[Job, JobStatusUpdate], None]],
        auto_disconnect_on_result: bool,
    ) -> None:
        """(Re)connect to the running job.

        Useful when the application using this SDK restarts and needs to reconnect to already
        running jobs. Assumes that the job exists otherwise the callbacks will never be called.

        :param job: The job to reconnect to.
        :param callback_on_finished: Called when the job has a result.
        :param callback_on_progress_update: Called when there is a progress update for the job.
        :param callback_on_status_update: Called when there is a status update for the job.
        :param auto_disconnect_on_result: Remove/disconnect from all queues pertaining to this job
        once the result is received and handled without exceptions through `callback_on_finished`.
        """
        if auto_disconnect_on_result:
            auto_disconnect_handler = self.disconnect_from_submitted_job
        else:
            auto_disconnect_handler = None

        callback_handler = JobSubmissionCallbackHandler(
            job,
            callback_on_finished,
            callback_on_progress_update,
            callback_on_status_update,
            auto_disconnect_handler,
        )

        self.broker_if.receive_next_message(
            queue_name=OmotesQueueNames.job_results_queue_name(job),
            timeout=None,
            callback_on_message=callback_handler.callback_on_finished_wrapped,
            callback_on_no_message=None,
        )
        if callback_on_progress_update:
            self.broker_if.add_queue_subscription(
                queue_name=OmotesQueueNames.job_progress_queue_name(job),
                callback_on_message=callback_handler.callback_on_progress_update_wrapped,
            )
        if callback_on_status_update:
            self.broker_if.add_queue_subscription(
                queue_name=OmotesQueueNames.job_status_queue_name(job),
                callback_on_message=callback_handler.callback_on_status_update_wrapped,
            )

    def submit_job(
        self,
        esdl: str,
        job_config: dict,
        workflow_type: WorkflowType,
        job_timeout: Optional[timedelta],
        callback_on_finished: Callable[[Job, JobResult], None],
        callback_on_progress_update: Optional[Callable[[Job, JobProgressUpdate], None]],
        callback_on_status_update: Optional[Callable[[Job, JobStatusUpdate], None]],
        auto_disconnect_on_result: bool,
    ) -> Job:
        """Submit a new job and connect to progress and status updates and the job result.

        :param esdl: String containing the XML that make up the ESDL.
        :param job_config: Any job-specific configuration parameters.
        :param workflow_type: Type of the workflow to start.
        :param job_timeout: How long the job may take before it is considered to be timeout.
        :param callback_on_finished: Callback which is called with the job result once the job is
            done.
        :param callback_on_progress_update: Callback which is called with any progress updates.
        :param callback_on_status_update: Callback which is called with any status updates.
        :param auto_disconnect_on_result: Remove/disconnect from all queues pertaining to this job
        once the result is received and handled without exceptions through `callback_on_finished`.
        :return: The job handle which is created. This object needs to be saved persistently by the
            program using this SDK in order to resume listening to jobs in progress after a restart.
        """
        job = Job(id=uuid.uuid4(), workflow_type=workflow_type)

        self.connect_to_submitted_job(
            job,
            callback_on_finished,
            callback_on_progress_update,
            callback_on_status_update,
            auto_disconnect_on_result,
        )

        timeout_ms = round(job_timeout.total_seconds() * 1000) if job_timeout else None
        job_submission_msg = JobSubmission(
            uuid=str(job.id),
            timeout_ms=timeout_ms,
            workflow_type=workflow_type.workflow_type_name,
            esdl=esdl.encode(),
        )
        self.broker_if.send_message_to(
            OmotesQueueNames.job_submission_queue_name(workflow_type),
            message=job_submission_msg.SerializeToString(),
        )

        return job

    def cancel_job(self, job: Job) -> None:
        """Cancel a job.

        If this succeeds or not will be send as a job status update through the
        `callback_on_status_update` handler. This method will not disconnect from the submitted job
        events. This will need to be done separately using `disconnect_from_submitted_job`.

        :param job: The job to cancel.
        """
        cancel_msg = JobCancel(uuid=str(job.id))
        self.broker_if.send_message_to(
            OmotesQueueNames.job_cancel_queue_name(job), message=cancel_msg.SerializeToString()
        )
