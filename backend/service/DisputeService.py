from __future__ import annotations

from backend.entities.dispute import Dispute, DisputeResult
from backend.entities.task import TaskStatus
from backend.repo.DisputeRepository import DisputeRepository
from backend.repo.TaskRepository import TaskRepository


class DisputeService:
    def __init__(self, dispute_repo: DisputeRepository, task_repo: TaskRepository) -> None:
        self.dispute_repo = dispute_repo
        self.task_repo = task_repo

    def open_dispute(
        self,
        dispute_id: str,
        task_id: str,
        opened_by_user_id: int,
        reason: str,
    ) -> Dispute:
        task = self.task_repo.get(task_id)
        if task is None:
            raise ValueError(f"Task '{task_id}' not found")
        if task.status != TaskStatus.REJECTED:
            raise ValueError("only rejected tasks can be disputed")

        task.open_dispute()
        self.task_repo.save(task)

        dispute = Dispute(
            dispute_id=dispute_id,
            task_id=task_id,
            opened_by_user_id=opened_by_user_id,
            reason=reason,
        )
        return self.dispute_repo.save(dispute)

    def resolve_in_favor_of_contributor(self, dispute_id: str, note: str) -> Dispute:
        dispute = self._require_dispute(dispute_id)
        dispute.mark_under_review()
        dispute.resolve(DisputeResult.PAY_CONTRIBUTOR, note)

        task = self._require_task(dispute.task_id)
        task.approve()
        self.task_repo.save(task)
        return self.dispute_repo.save(dispute)

    def resolve_keep_rejection(self, dispute_id: str, note: str) -> Dispute:
        dispute = self._require_dispute(dispute_id)
        dispute.mark_under_review()
        dispute.reject(note)
        return self.dispute_repo.save(dispute)

    def _require_dispute(self, dispute_id: str) -> Dispute:
        dispute = self.dispute_repo.get(dispute_id)
        if dispute is None:
            raise ValueError(f"Dispute '{dispute_id}' not found")
        return dispute

    def _require_task(self, task_id: str):
        task = self.task_repo.get(task_id)
        if task is None:
            raise ValueError(f"Task '{task_id}' not found")
        return task