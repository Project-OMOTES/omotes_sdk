import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class TaskStatus(Enum):
    CREATED = 'created'
    STARTED = 'started'
    SUCCEEDED = 'succeeded'


@dataclass
class CalculationResult:
    job_id: uuid.uuid4
    exit_code: int
    logs: str
    input_esdl: str
    output_esdl: Optional[str]


@dataclass
class StatusUpdateMessage:
    omotes_job_id: uuid.UUID
    celery_task_id: str
    status: TaskStatus
    task_type: str

    def to_dict(self):
        return {'omotes_job_id': str(self.omotes_job_id), 'celery_task_id': self.celery_task_id, 'status': self.status.value,
        'task_type': self.task_type}

    @staticmethod
    def from_dict(value: Dict):
        return StatusUpdateMessage(uuid.UUID(value['omotes_job_id']),
                                   value['celery_task_id'],
                                   TaskStatus(value['status']),
                                   value['task_type'])
