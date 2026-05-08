from __future__ import annotations

from backend.entities.task import TaskStatus
from backend.entities.user import User
from backend.repo.TaskRepository import TaskRepository
from backend.repo.UserRepository import UserRepository
from backend.repo.WalletRepository import WalletRepository


class PaymentService:
    def __init__(
        self,
        user_repo: UserRepository,
        task_repo: TaskRepository,
        wallet_repo: WalletRepository,
    ) -> None:
        self.user_repo = user_repo
        self.task_repo = task_repo
        self.wallet_repo = wallet_repo

    def payout_for_approved_task(
        self,
        task_id: str,
        contributor_user_id: int,
        bonus_usd: float = 0.0,
    ) -> float:
        task = self.task_repo.get(task_id)
        if task is None:
            raise ValueError(f"Task '{task_id}' not found")
        if task.status != TaskStatus.APPROVED:
            raise ValueError("task must be approved before payout")

        user = self._require_user(contributor_user_id)
        wallet = self.wallet_repo.get_by_user_id(contributor_user_id)
        if wallet is None:
            raise ValueError("user wallet not found")

        total = round(task.reward_usd + max(0.0, bonus_usd), 2)
        wallet.credit(total)
        user.mark_task_completed(task_id)
        self.wallet_repo.save(wallet)
        self.user_repo.save(user)
        return total

    def can_withdraw_to_paypal(self, user_id: int, min_balance: float = 10.0) -> bool:
        user = self._require_user(user_id)
        wallet = self.wallet_repo.get_by_user_id(user_id)
        if wallet is None:
            return False
        return bool(user.paypal_id) and wallet.balance.amount >= min_balance

    def _require_user(self, user_id: int) -> User:
        user = self.user_repo.get(user_id)
        if user is None:
            raise ValueError(f"User '{user_id}' not found")
        return user
