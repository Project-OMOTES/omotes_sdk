from dataclasses import dataclass
from typing import List


@dataclass
class TaskType:
    task_type_name: str
    """Technical name for the task."""
    task_type_description_name: str
    """Human-readable name for the task."""


@dataclass
class TaskTypeManager:
    possible_tasks: List[TaskType]
