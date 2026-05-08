from __future__ import annotations

from backend.value_objects.money import Money


class Wallet:
    def __init__(self, wallet_id: int, user_id: int, balance: Money) -> None:
        self.wallet_id = wallet_id
        self.user_id = user_id
        self.balance = balance
        self.escrow_locked = 0.0

    @property
    def wallet_id(self) -> int:
        return self._wallet_id

    @wallet_id.setter
    def wallet_id(self, value: int) -> None:
        if value <= 0:
            raise ValueError("wallet_id must be positive")
        self._wallet_id = value

    @property
    def user_id(self) -> int:
        return self._user_id

    @user_id.setter
    def user_id(self, value: int) -> None:
        if value <= 0:
            raise ValueError("user_id must be positive")
        self._user_id = value

    @property
    def balance(self) -> Money:
        return self._balance

    @balance.setter
    def balance(self, value: Money) -> None:
        if not isinstance(value, Money):
            raise TypeError("balance must be Money")
        self._balance = value

    def lock_escrow(self, amount: float) -> None:
        self.balance.subtract(amount)
        self.escrow_locked = round(self.escrow_locked + amount, 2)

    def release_escrow(self, amount: float) -> None:
        if amount > self.escrow_locked:
            raise ValueError("cannot release more escrow than locked")
        self.escrow_locked = round(self.escrow_locked - amount, 2)

    def credit(self, amount: float) -> None:
        self.balance.add(amount)
from __future__ import annotations

from backend.value_objects.money import Money


class Wallet:
    def __init__(self, wallet_id: int, user_id: int, balance: Money) -> None:
        self.wallet_id = wallet_id
        self.user_id = user_id
        self.balance = balance
        self.escrow_locked = 0.0

    @property
    def wallet_id(self) -> int:
        return self._wallet_id

    @wallet_id.setter
    def wallet_id(self, value: int) -> None:
        if value <= 0:
            raise ValueError("wallet_id must be positive")
        self._wallet_id = value

    @property
    def user_id(self) -> int:
        return self._user_id

    @user_id.setter
    def user_id(self, value: int) -> None:
        if value <= 0:
            raise ValueError("user_id must be positive")
        self._user_id = value

    @property
    def balance(self) -> Money:
        return self._balance

    @balance.setter
    def balance(self, value: Money) -> None:
        if not isinstance(value, Money):
            raise TypeError("balance must be Money")
        self._balance = value

    def lock_escrow(self, amount: float) -> None:
        self.balance.subtract(amount)
        self.escrow_locked = round(self.escrow_locked + amount, 2)

    def release_escrow(self, amount: float) -> None:
        if amount > self.escrow_locked:
            raise ValueError("cannot release more escrow than locked")
        self.escrow_locked = round(self.escrow_locked - amount, 2)

    def credit(self, amount: float) -> None:
        self.balance.add(amount)
