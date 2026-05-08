from __future__ import annotations

from typing import Dict, Optional

from backend.entities.wallet import Wallet


class WalletRepository:
    def __init__(self) -> None:
        self._wallets_by_user_id: Dict[int, Wallet] = {}

    def save(self, wallet: Wallet) -> Wallet:
        self._wallets_by_user_id[wallet.user_id] = wallet
        return wallet

    def get_by_user_id(self, user_id: int) -> Optional[Wallet]:
        return self._wallets_by_user_id.get(user_id)
