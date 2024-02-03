import uuid
from dataclasses import dataclass

from omotes_sdk.workflow_type import WorkflowType


@dataclass
class Job:
    """Reference to a submitted job."""

    id: uuid.UUID
    """ID used to reference to job in OMOTES system."""
    workflow_type: WorkflowType
    """Describes the type of job / workflow has been submitted."""
