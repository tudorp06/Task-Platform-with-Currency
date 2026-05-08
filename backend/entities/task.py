from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class TaskStatus(Enum):
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISPUTED = "disputed"


class Task:
    def __init__(
        self,
        task_id: str,
        title: str,
        prompt: str,
        description: str,
        reward_usd: float,
        slots_total: int = 1,
    ) -> None:
        self.task_id = task_id
        self.title = title
        self.prompt = prompt
        self.description = description
        self.reward_usd = reward_usd
        self.slots_total = slots_total
        self.slots_used = 0
        self.status = TaskStatus.AVAILABLE
        self.result: Optional[str] = None
        self.created_at = datetime.now(timezone.utc)
        self.completed_at: Optional[datetime] = None

    @property
    def task_id(self) -> str:
        return self._task_id

    @task_id.setter
    def task_id(self, value: str) -> None:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("task_id cannot be empty")
        self._task_id = cleaned

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        cleaned = value.strip()
        if len(cleaned) < 4:
            raise ValueError("title must be at least 4 characters")
        self._title = cleaned

    @property
    def prompt(self) -> str:
        return self._prompt

    @prompt.setter
    def prompt(self, value: str) -> None:
        cleaned = value.strip()
        if len(cleaned) < 10:
            raise ValueError("prompt must be at least 10 characters")
        self._prompt = cleaned

    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, value: str) -> None:
        cleaned = value.strip()
        if len(cleaned) < 10:
            raise ValueError("description must be at least 10 characters")
        self._description = cleaned

    @property
    def reward_usd(self) -> float:
        return self._reward_usd

    @reward_usd.setter
    def reward_usd(self, value: float) -> None:
        if value <= 0:
            raise ValueError("reward_usd must be positive")
        self._reward_usd = round(float(value), 2)

    @property
    def slots_total(self) -> int:
        return self._slots_total

    @slots_total.setter
    def slots_total(self, value: int) -> None:
        if value <= 0:
            raise ValueError("slots_total must be positive")
        self._slots_total = value

    def reserve_slot(self) -> None:
        if self.slots_used >= self.slots_total:
            raise ValueError("no slots left")
        self.slots_used += 1
        self.status = TaskStatus.IN_PROGRESS

    def submit(self, result: str) -> None:
        cleaned = result.strip()
        if not cleaned:
            raise ValueError("result cannot be empty")
        self.result = cleaned
        self.status = TaskStatus.SUBMITTED

    def approve(self) -> None:
        if self.status not in (TaskStatus.SUBMITTED, TaskStatus.DISPUTED):
            raise ValueError("task can only be approved after submit/dispute")
        self.status = TaskStatus.APPROVED
        self.completed_at = datetime.now(timezone.utc)

    def reject(self) -> None:
        if self.status not in (TaskStatus.SUBMITTED, TaskStatus.DISPUTED):
            raise ValueError("task can only be rejected after submit/dispute")
        self.status = TaskStatus.REJECTED
        self.completed_at = datetime.now(timezone.utc)

    def open_dispute(self) -> None:
        if self.status != TaskStatus.REJECTED:
            raise ValueError("only rejected tasks can be disputed")
        self.status = TaskStatus.DISPUTED
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class TaskStatus(Enum):
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISPUTED = "disputed"


class Task:
    def __init__(
        self,
        task_id: str,
        title: str,
        prompt: str,
        description: str,
        reward_usd: float,
        slots_total: int = 1,
    ) -> None:
        self.task_id = task_id
        self.title = title
        self.prompt = prompt
        self.description = description
        self.reward_usd = reward_usd
        self.slots_total = slots_total
        self.slots_used = 0
        self.status = TaskStatus.AVAILABLE
        self.result: Optional[str] = None
        self.created_at = datetime.now(timezone.utc)
        self.completed_at: Optional[datetime] = None

    @property
    def task_id(self) -> str:
        return self._task_id

    @task_id.setter
    def task_id(self, value: str) -> None:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("task_id cannot be empty")
        self._task_id = cleaned

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        cleaned = value.strip()
        if len(cleaned) < 4:
            raise ValueError("title must be at least 4 characters")
        self._title = cleaned

    @property
    def prompt(self) -> str:
        return self._prompt

    @prompt.setter
    def prompt(self, value: str) -> None:
        cleaned = value.strip()
        if len(cleaned) < 10:
            raise ValueError("prompt must be at least 10 characters")
        self._prompt = cleaned

    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, value: str) -> None:
        cleaned = value.strip()
        if len(cleaned) < 10:
            raise ValueError("description must be at least 10 characters")
        self._description = cleaned

    @property
    def reward_usd(self) -> float:
        return self._reward_usd

    @reward_usd.setter
    def reward_usd(self, value: float) -> None:
        if value <= 0:
            raise ValueError("reward_usd must be positive")
        self._reward_usd = round(float(value), 2)

    @property
    def slots_total(self) -> int:
        return self._slots_total

    @slots_total.setter
    def slots_total(self, value: int) -> None:
        if value <= 0:
            raise ValueError("slots_total must be positive")
        self._slots_total = value

    def reserve_slot(self) -> None:
        if self.slots_used >= self.slots_total:
            raise ValueError("no slots left")
        self.slots_used += 1
        self.status = TaskStatus.IN_PROGRESS

    def submit(self, result: str) -> None:
        cleaned = result.strip()
        if not cleaned:
            raise ValueError("result cannot be empty")
        self.result = cleaned
        self.status = TaskStatus.SUBMITTED

    def approve(self) -> None:
        if self.status not in (TaskStatus.SUBMITTED, TaskStatus.DISPUTED):
            raise ValueError("task can only be approved after submit/dispute")
        self.status = TaskStatus.APPROVED
        self.completed_at = datetime.now(timezone.utc)

    def reject(self) -> None:
        if self.status not in (TaskStatus.SUBMITTED, TaskStatus.DISPUTED):
            raise ValueError("task can only be rejected after submit/dispute")
        self.status = TaskStatus.REJECTED
        self.completed_at = datetime.now(timezone.utc)

    def open_dispute(self) -> None:
        if self.status != TaskStatus.REJECTED:
            raise ValueError("only rejected tasks can be disputed")
        self.status = TaskStatus.DISPUTED

    def __repr__(self) -> str:
        return (
            f"Task(task_id={self.task_id!r}, title={self.title!r}, "
            f"status={self.status.value!r}, reward_usd={self.reward_usd!r})"
        )
