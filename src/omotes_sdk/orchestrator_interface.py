import logging
import uuid
from dataclasses import dataclass
from typing import Callable

from omotes_sdk_protocol.job_pb2 import JobSubmission, JobProgressUpdate, JobStatusUpdate, JobResult
from omotes_sdk.broker_interface import BrokerInterface
from omotes_sdk.config import RabbitMQConfig
from omotes_sdk.job import Job
from omotes_sdk.queue_names import OmotesQueueNames
from omotes_sdk.workflow_type import WorkflowType, WorkflowTypeManager

logger = logging.getLogger("omotes_sdk")


@dataclass
class JobSubmissionCallbackHandler:
    workflow_type: WorkflowType
    callback_on_new_job: Callable[[JobSubmission, Job], None]

    def callback_on_new_job_wrapped(self, message: bytes):
        submitted_job = JobSubmission()
        submitted_job.ParseFromString(message)

        if self.workflow_type.workflow_type_name == submitted_job.workflow_type:
            job = Job(uuid.UUID(submitted_job.uuid), self.workflow_type)
            self.callback_on_new_job(submitted_job, job)
        else:
            logger.error(
                "Received a job submission (id: %s) that was meant for workflow type %s but found "
                "it on queue %s. Dropping message.",
                submitted_job.uuid,
                submitted_job.workflow_type,
                self.workflow_type,
            )


class OrchestratorInterface:
    broker_if: BrokerInterface
    workflow_type_manager: WorkflowTypeManager

    def __init__(
        self, omotes_rabbitmq_config: RabbitMQConfig, workflow_type_manager: WorkflowTypeManager
    ):
        self.broker_if = BrokerInterface(omotes_rabbitmq_config)
        self.workflow_type_manager = workflow_type_manager

    def start(self):
        self.broker_if.start()

    def stop(self):
        self.broker_if.stop()

    def connect_to_job_submissions(
        self, callback_on_new_job: Callable[[JobSubmission, Job], None]
    ) -> None:
        for workflow_type in self.workflow_type_manager.possible_workflows:
            callback_handler = JobSubmissionCallbackHandler(workflow_type, callback_on_new_job)
            self.broker_if.add_queue_subscription(
                OmotesQueueNames.job_submission_queue_name(workflow_type),
                callback_on_message=callback_handler.callback_on_new_job_wrapped,
            )

    def send_job_progress_update(self, job: Job, progress_update: JobProgressUpdate) -> None:
        self.broker_if.send_message_to(
            OmotesQueueNames.job_progress_queue_name(job), progress_update.SerializeToString()
        )

    def send_job_status_update(self, job: Job, status_update: JobStatusUpdate) -> None:
        self.broker_if.send_message_to(
            OmotesQueueNames.job_status_queue_name(job), status_update.SerializeToString()
        )

    def send_job_result(self, job: Job, result: JobResult) -> None:
        self.broker_if.send_message_to(
            OmotesQueueNames.job_results_queue_name(job), result.SerializeToString()
        )
