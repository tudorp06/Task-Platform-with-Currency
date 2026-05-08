from __future__ import annotations

from backend.entities.task import Task
from backend.repo.TaskRepository import TaskRepository


class TaskService:
    def __init__(self, task_repo: TaskRepository) -> None:
        self.task_repo = task_repo

    def create_task(
        self,
        task_id: str,
        title: str,
        prompt: str,
        description: str,
        reward_usd: float,
        slots_total: int = 1,
    ) -> Task:
        task = Task(
            task_id=task_id,
            title=title,
            prompt=prompt,
            description=description,
            reward_usd=reward_usd,
            slots_total=slots_total,
        )
        return self.task_repo.save(task)

    def reserve_task_slot(self, task_id: str) -> Task:
        task = self._require_task(task_id)
        task.reserve_slot()
        return self.task_repo.save(task)

    def submit_task_result(self, task_id: str, result_text: str) -> Task:
        task = self._require_task(task_id)
        task.submit(result_text)
        return self.task_repo.save(task)

    def approve_task(self, task_id: str) -> Task:
        task = self._require_task(task_id)
        task.approve()
        return self.task_repo.save(task)

    def reject_task(self, task_id: str) -> Task:
        task = self._require_task(task_id)
        task.reject()
        return self.task_repo.save(task)

    def open_dispute(self, task_id: str) -> Task:
        task = self._require_task(task_id)
        task.open_dispute()
        return self.task_repo.save(task)

    def _require_task(self, task_id: str) -> Task:
        task = self.task_repo.get(task_id)
        if task is None:
            raise ValueError(f"Task '{task_id}' not found")
        return task
