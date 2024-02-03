from dataclasses import dataclass
from typing import List


@dataclass
class WorkflowType:
    workflow_type_name: str
    """Technical name for the workflow."""
    workflow_type_description_name: str
    """Human-readable name for the workflow."""


@dataclass
class WorkflowTypeManager:
    possible_workflows: List[WorkflowType]
