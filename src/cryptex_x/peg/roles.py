from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FunctionaryHat(str, Enum):
    """Two jobs on the same machines — do not mix in diagrams or policy."""

    BLOCKSIGNER = "blocksigner"  # sidechain consensus
    WATCHMAN = "watchman"  # Bitcoin reserve custody / peg-out


@dataclass(frozen=True)
class Blocksigner:
    """Proposes and threshold-signs sidechain blocks. Does not spend BTC reserve."""

    member_id: str
    hat: FunctionaryHat = FunctionaryHat.BLOCKSIGNER

    def touches_chain(self) -> str:
        return "sidechain"

    def may_spend_bitcoin_reserve(self) -> bool:
        return False

    def may_sign_sidechain_block(self) -> bool:
        return True


@dataclass(frozen=True)
class Watchman:
    """Holds k-of-n BTC reserve and signs peg-outs. Does not mint L-BTC."""

    member_id: str
    hat: FunctionaryHat = FunctionaryHat.WATCHMAN

    def touches_chain(self) -> str:
        return "bitcoin"

    def may_spend_bitcoin_reserve(self) -> bool:
        return True

    def may_sign_sidechain_block(self) -> bool:
        return False


@dataclass(frozen=True)
class Functionary:
    """
    Same physical HSM can host both hats; policy still treats jobs as separate.

    Collapsing hats is how hybrid SPV+federation diagrams go wrong.
    """

    member_id: str
    blocksigner: Blocksigner
    watchman: Watchman

    @classmethod
    def create(cls, member_id: str) -> Functionary:
        return cls(
            member_id=member_id,
            blocksigner=Blocksigner(member_id=member_id),
            watchman=Watchman(member_id=member_id),
        )
