from __future__ import annotations

from typing import Dict, List, Optional

from backend.entities.dispute import Dispute


class DisputeRepository:
    def __init__(self) -> None:
        self._disputes: Dict[str, Dispute] = {}

    def save(self, dispute: Dispute) -> Dispute:
        self._disputes[dispute.dispute_id] = dispute
        return dispute

    def get(self, dispute_id: str) -> Optional[Dispute]:
        return self._disputes.get(dispute_id)

    def list_by_task(self, task_id: str) -> List[Dispute]:
        return [d for d in self._disputes.values() if d.task_id == task_id]
