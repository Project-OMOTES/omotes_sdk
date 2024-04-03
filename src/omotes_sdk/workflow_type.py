from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class WorkflowType:
    """Define a type of workflow this SDK supports."""

    workflow_type_name: str
    """Technical name for the workflow."""
    workflow_type_description_name: str
    """Human-readable name for the workflow."""

    def __hash__(self) -> int:
        """Hash the `WorkflowType`.

        :return: A hash identifying this workflow type.
        """
        return hash(self.workflow_type_name)

    def __eq__(self, other: Any) -> bool:
        """Check if this `WorkflowType` is equal to another.

        :param other: The other `WorkflowType` (or other object).
        :return: True of the 2 objects are considered equal based on the `workflow_type_name`,
            otherwise False.
        """
        if isinstance(other, WorkflowType):
            return self.workflow_type_name == other.workflow_type_name
        else:
            return False


class WorkflowTypeManager:
    """Container for all possible workflows."""

    _workflows: Dict[str, WorkflowType]
    """The possible workflows this SDK supports."""

    def __init__(self, possible_workflows: List[WorkflowType]):
        """Create the workflow type manager.

        :param possible_workflows: The workflows to manage.
        """
        self._workflows = {workflow.workflow_type_name: workflow for workflow in possible_workflows}

    def get_workflow_by_name(self, name: str) -> Optional[WorkflowType]:
        """Find the workflow type using the name.

        :param name: Name of the workflow type to find.
        :return: The workflow type if it exists.
        """
        return self._workflows.get(name)

    def get_all_workflows(self) -> List[WorkflowType]:
        """List all workflows.

        :return: The workflows.
        """
        return list(self._workflows.values())

    def workflow_exists(self, workflow: WorkflowType) -> bool:
        """Check if the workflow exists within this manager.

        :param workflow: Check if this workflow exists within the manager.
        :return: If the workflow exists.
        """
        return workflow.workflow_type_name in self._workflows
