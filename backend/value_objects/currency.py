from __future__ import annotations


class Currency:
    def __init__(self, code: str, symbol: str, exchange_rate_to_usd: float = 1.0) -> None:
        self.code = code
        self.symbol = symbol
        self.exchange_rate_to_usd = exchange_rate_to_usd

    @property
    def code(self) -> str:
        return self._code

    @code.setter
    def code(self, value: str) -> None:
        cleaned = value.strip().upper()
        if len(cleaned) != 3 or not cleaned.isalpha():
            raise ValueError("code must be a 3-letter currency code")
        self._code = cleaned

    @property
    def symbol(self) -> str:
        return self._symbol

    @symbol.setter
    def symbol(self, value: str) -> None:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("symbol cannot be empty")
        self._symbol = cleaned

    @property
    def exchange_rate_to_usd(self) -> float:
        return self._exchange_rate_to_usd

    @exchange_rate_to_usd.setter
    def exchange_rate_to_usd(self, value: float) -> None:
        if value <= 0:
            raise ValueError("exchange_rate_to_usd must be positive")
        self._exchange_rate_to_usd = float(value)

    def __repr__(self) -> str:
        return (
            f"Currency(code={self.code!r}, symbol={self.symbol!r}, "
            f"exchange_rate_to_usd={self.exchange_rate_to_usd!r})"
        )
