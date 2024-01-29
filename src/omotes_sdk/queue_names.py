from omotes_sdk.job import Job
from omotes_sdk.workflow_type import WorkflowType


class OmotesQueueNames:
    @staticmethod
    def job_submission_queue_name(workflow_type: WorkflowType) -> str:
        return f"job_submissions.{workflow_type.workflow_type_name}"

    @staticmethod
    def job_submission_response_queue_name(job: Job) -> str:
        return f"jobs.{job.id}.submission_response"

    @staticmethod
    def job_results_queue_name(job: Job) -> str:
        return f"jobs.{job.id}.result"

    @staticmethod
    def job_progress_queue_name(job: Job) -> str:
        return f"jobs.{job.id}.progress"

    @staticmethod
    def job_status_queue_name(job: Job) -> str:
        return f"jobs.{job.id}.status"

    @staticmethod
    def job_cancel_queue_name(job: Job) -> str:
        return f"jobs.{job.id}.cancel"

    @staticmethod
    def job_cancel_response_queue_name(job: Job) -> str:
        return f"jobs.{job.id}.cancel_response"
