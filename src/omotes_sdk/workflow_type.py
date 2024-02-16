from dataclasses import dataclass
from typing import List


@dataclass
class WorkflowType:
    """Define a type of workflow this SDK supports."""

    workflow_type_name: str
    """Technical name for the workflow."""
    workflow_type_description_name: str
    """Human-readable name for the workflow."""


@dataclass
class WorkflowTypeManager:
    """Container for all possible workflows."""

    possible_workflows: List[WorkflowType]
    """The possible workflows this SDK supports."""
