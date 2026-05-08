from __future__ import annotations

from typing import Dict, List, Optional

from backend.entities.task import Task


class TaskRepository:
    def __init__(self) -> None:
        self._tasks: Dict[str, Task] = {}

    def save(self, task: Task) -> Task:
        self._tasks[task.task_id] = task
        return task

    def get(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def list_all(self) -> List[Task]:
        return list(self._tasks.values())

    def list_available(self) -> List[Task]:
        return [task for task in self._tasks.values() if task.status.value == "available"]
