from __future__ import annotations

from enum import Enum
from typing import Optional


class UserRole(Enum):
    CONTRIBUTOR = "contributor"
    FOUNDER = "founder"
    MODERATOR = "moderator"


class User:
    def __init__(
        self,
        user_id: int,
        full_name: str,
        email: str,
        password_hash: str,
        role: UserRole = UserRole.CONTRIBUTOR,
        years_of_experience: int = 0,
        github_url: Optional[str] = None,
        paypal_id: Optional[str] = None,
    ) -> None:
        self.user_id = user_id
        self.full_name = full_name
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.years_of_experience = years_of_experience
        self.github_url = github_url
        self.paypal_id = paypal_id
        self.skills: list[str] = []
        self.completed_task_ids: list[str] = []

    @property
    def user_id(self) -> int:
        return self._user_id

    @user_id.setter
    def user_id(self, value: int) -> None:
        if value <= 0:
            raise ValueError("user_id must be positive")
        self._user_id = value

    @property
    def full_name(self) -> str:
        return self._full_name

    @full_name.setter
    def full_name(self, value: str) -> None:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("full_name cannot be empty")
        self._full_name = cleaned

    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, value: str) -> None:
        cleaned = value.strip().lower()
        if "@" not in cleaned:
            raise ValueError("email must contain '@'")
        self._email = cleaned

    @property
    def password_hash(self) -> str:
        return self._password_hash

    @password_hash.setter
    def password_hash(self, value: str) -> None:
        cleaned = value.strip()
        if len(cleaned) < 8:
            raise ValueError("password_hash looks too short")
        self._password_hash = cleaned

    @property
    def role(self) -> UserRole:
        return self._role

    @role.setter
    def role(self, value: UserRole) -> None:
        if not isinstance(value, UserRole):
            raise TypeError("role must be UserRole")
        self._role = value

    @property
    def years_of_experience(self) -> int:
        return self._years_of_experience

    @years_of_experience.setter
    def years_of_experience(self, value: int) -> None:
        if value < 0:
            raise ValueError("years_of_experience cannot be negative")
        self._years_of_experience = value

    @property
    def github_url(self) -> Optional[str]:
        return self._github_url

    @github_url.setter
    def github_url(self, value: Optional[str]) -> None:
        if value is None:
            self._github_url = None
            return
        cleaned = value.strip()
        if cleaned and not cleaned.startswith(("http://", "https://")):
            raise ValueError("github_url must start with http:// or https://")
        self._github_url = cleaned

    @property
    def paypal_id(self) -> Optional[str]:
        return self._paypal_id

    @paypal_id.setter
    def paypal_id(self, value: Optional[str]) -> None:
        self._paypal_id = value.strip() if value else None

    def add_skill(self, skill: str) -> None:
        cleaned = skill.strip().lower()
        if cleaned and cleaned not in self.skills:
            self.skills.append(cleaned)

    def mark_task_completed(self, task_id: str) -> None:
        cleaned = task_id.strip()
        if cleaned and cleaned not in self.completed_task_ids:
            self.completed_task_ids.append(cleaned)
from __future__ import annotations

from enum import Enum
from typing import Optional


class UserRole(Enum):
    CONTRIBUTOR = "contributor"
    FOUNDER = "founder"
    MODERATOR = "moderator"


class User:
    def __init__(
        self,
        user_id: int,
        full_name: str,
        email: str,
        password_hash: str,
        role: UserRole = UserRole.CONTRIBUTOR,
        years_of_experience: int = 0,
        github_url: Optional[str] = None,
        paypal_id: Optional[str] = None,
    ) -> None:
        self.user_id = user_id
        self.full_name = full_name
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.years_of_experience = years_of_experience
        self.github_url = github_url
        self.paypal_id = paypal_id
        self.skills: list[str] = []
        self.completed_task_ids: list[str] = []

    @property
    def user_id(self) -> int:
        return self._user_id

    @user_id.setter
    def user_id(self, value: int) -> None:
        if value <= 0:
            raise ValueError("user_id must be positive")
        self._user_id = value

    @property
    def full_name(self) -> str:
        return self._full_name

    @full_name.setter
    def full_name(self, value: str) -> None:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("full_name cannot be empty")
        self._full_name = cleaned

    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, value: str) -> None:
        cleaned = value.strip().lower()
        if "@" not in cleaned:
            raise ValueError("email must contain '@'")
        self._email = cleaned

    @property
    def password_hash(self) -> str:
        return self._password_hash

    @password_hash.setter
    def password_hash(self, value: str) -> None:
        cleaned = value.strip()
        if len(cleaned) < 8:
            raise ValueError("password_hash looks too short")
        self._password_hash = cleaned

    @property
    def role(self) -> UserRole:
        return self._role

    @role.setter
    def role(self, value: UserRole) -> None:
        if not isinstance(value, UserRole):
            raise TypeError("role must be UserRole")
        self._role = value

    @property
    def years_of_experience(self) -> int:
        return self._years_of_experience

    @years_of_experience.setter
    def years_of_experience(self, value: int) -> None:
        if value < 0:
            raise ValueError("years_of_experience cannot be negative")
        self._years_of_experience = value

    @property
    def github_url(self) -> Optional[str]:
        return self._github_url

    @github_url.setter
    def github_url(self, value: Optional[str]) -> None:
        if value is None:
            self._github_url = None
            return
        cleaned = value.strip()
        if cleaned and not cleaned.startswith(("http://", "https://")):
            raise ValueError("github_url must start with http:// or https://")
        self._github_url = cleaned

    @property
    def paypal_id(self) -> Optional[str]:
        return self._paypal_id

    @paypal_id.setter
    def paypal_id(self, value: Optional[str]) -> None:
        self._paypal_id = value.strip() if value else None

    def add_skill(self, skill: str) -> None:
        cleaned = skill.strip().lower()
        if cleaned and cleaned not in self.skills:
            self.skills.append(cleaned)

    def mark_task_completed(self, task_id: str) -> None:
        cleaned = task_id.strip()
        if cleaned and cleaned not in self.completed_task_ids:
            self.completed_task_ids.append(cleaned)
