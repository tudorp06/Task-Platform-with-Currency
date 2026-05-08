from __future__ import annotations

from backend.value_objects.currency import Currency


class Money:
    def __init__(self, amount: float, currency: Currency) -> None:
        self.amount = amount
        self.currency = currency

    @property
    def amount(self) -> float:
        return self._amount

    @amount.setter
    def amount(self, value: float) -> None:
        if value < 0:
            raise ValueError("amount cannot be negative")
        self._amount = round(float(value), 2)

    @property
    def currency(self) -> Currency:
        return self._currency

    @currency.setter
    def currency(self, value: Currency) -> None:
        if not isinstance(value, Currency):
            raise TypeError("currency must be Currency")
        self._currency = value

    def add(self, amount: float) -> None:
        self.amount = self.amount + amount

    def subtract(self, amount: float) -> None:
        if amount > self.amount:
            raise ValueError("insufficient funds")
        self.amount = self.amount - amount

    def __repr__(self) -> str:
        return f"Money(amount={self.amount!r}, currency={self.currency.code!r})"
