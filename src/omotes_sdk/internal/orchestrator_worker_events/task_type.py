from dataclasses import dataclass
from typing import List


@dataclass
class TaskType:
    """Celery task type which may belong to a workflow."""

    task_type_name: str
    """Technical name for the task."""
    task_type_description_name: str
    """Human-readable name for the task."""


@dataclass
class TaskTypeManager:
    """Container for all possible Celery tasks."""

    possible_tasks: List[TaskType]
    """All possible Celery tasks."""
