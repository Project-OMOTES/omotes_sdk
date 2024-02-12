import uuid
from dataclasses import dataclass

from omotes_job_tools.workflow_type import TaskType


@dataclass
class Job:
    id: uuid.UUID
    task_type: TaskType
