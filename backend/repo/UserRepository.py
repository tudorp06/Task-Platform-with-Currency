from __future__ import annotations

from typing import Dict, List, Optional

from backend.entities.user import User


class UserRepository:
    def __init__(self) -> None:
        self._users: Dict[int, User] = {}

    def save(self, user: User) -> User:
        self._users[user.user_id] = user
        return user

    def get(self, user_id: int) -> Optional[User]:
        return self._users.get(user_id)

    def list_all(self) -> List[User]:
        return list(self._users.values())
