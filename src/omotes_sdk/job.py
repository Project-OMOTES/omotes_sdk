import uuid
from dataclasses import dataclass

from omotes_sdk.workflow_type import WorkflowType


@dataclass
class Job:
    id: uuid.UUID
    workflow_type: WorkflowType
