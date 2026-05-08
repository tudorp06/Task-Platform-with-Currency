from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class DisputeStatus(Enum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class DisputeResult(Enum):
    PAY_CONTRIBUTOR = "pay_contributor"
    KEEP_REJECTION = "keep_rejection"
    REQUIRE_REVISION = "require_revision"


class Dispute:
    def __init__(
        self,
        dispute_id: str,
        task_id: str,
        opened_by_user_id: int,
        reason: str,
    ) -> None:
        self.dispute_id = dispute_id
        self.task_id = task_id
        self.opened_by_user_id = opened_by_user_id
        self.reason = reason
        self.status = DisputeStatus.OPEN
        self.result: Optional[DisputeResult] = None
        self.resolution_note: Optional[str] = None
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = self.created_at

    def mark_under_review(self) -> None:
        self.status = DisputeStatus.UNDER_REVIEW
        self.updated_at = datetime.now(timezone.utc)

    def resolve(self, result: DisputeResult, note: str) -> None:
        cleaned = note.strip()
        if len(cleaned) < 5:
            raise ValueError("resolution note must be meaningful")
        self.status = DisputeStatus.RESOLVED
        self.result = result
        self.resolution_note = cleaned
        self.updated_at = datetime.now(timezone.utc)

    def reject(self, note: str) -> None:
        cleaned = note.strip()
        if len(cleaned) < 5:
            raise ValueError("rejection note must be meaningful")
        self.status = DisputeStatus.REJECTED
        self.result = DisputeResult.KEEP_REJECTION
        self.resolution_note = cleaned
        self.updated_at = datetime.now(timezone.utc)
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class DisputeStatus(Enum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class DisputeResult(Enum):
    PAY_CONTRIBUTOR = "pay_contributor"
    KEEP_REJECTION = "keep_rejection"
    REQUIRE_REVISION = "require_revision"


class Dispute:
    def __init__(
        self,
        dispute_id: str,
        task_id: str,
        opened_by_user_id: int,
        reason: str,
    ) -> None:
        self.dispute_id = dispute_id
        self.task_id = task_id
        self.opened_by_user_id = opened_by_user_id
        self.reason = reason
        self.status = DisputeStatus.OPEN
        self.result: Optional[DisputeResult] = None
        self.resolution_note: Optional[str] = None
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = self.created_at

    def mark_under_review(self) -> None:
        self.status = DisputeStatus.UNDER_REVIEW
        self.updated_at = datetime.now(timezone.utc)

    def resolve(self, result: DisputeResult, note: str) -> None:
        cleaned = note.strip()
        if len(cleaned) < 5:
            raise ValueError("resolution note must be meaningful")
        self.status = DisputeStatus.RESOLVED
        self.result = result
        self.resolution_note = cleaned
        self.updated_at = datetime.now(timezone.utc)

    def reject(self, note: str) -> None:
        cleaned = note.strip()
        if len(cleaned) < 5:
            raise ValueError("rejection note must be meaningful")
        self.status = DisputeStatus.REJECTED
        self.result = DisputeResult.KEEP_REJECTION
        self.resolution_note = cleaned
        self.updated_at = datetime.now(timezone.utc)
