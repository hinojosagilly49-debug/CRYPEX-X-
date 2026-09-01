from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


# Master-record audit constants
STALE_LME_PRINT_USD_MT = 2412.0
GOVERNED_BUFFER_USD_MT = 2286.0
DESK_WINDOW = timedelta(minutes=30)


def _parse_ts(ts: str | datetime | None, _now: datetime) -> datetime | None:
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


@dataclass(frozen=True)
class DeskPriceView:
    """Agent-facing price after SARC-DQ downstream-only remediation."""

    agent_price_usd_mt: float
    quarantined: bool
    stale_print_usd_mt: float | None
    origin_price_usd_mt: float
    origin_source_hash: str
    origin_immutable: bool
    within_desk_window: bool
    hop: dict[str, Any]


class Connector395:
    """
    Enterprise sync connector.

    Four invariants:
    1. 30-minute desk window enforcement
    2. Quarantine stale prints (e.g. $2,412/mt)
    3. Substitute governed buffer for agent view (e.g. $2,286/mt)
    4. Keep original source immutable
    """

    def __init__(
        self,
        *,
        desk_window: timedelta = DESK_WINDOW,
        governed_buffer_usd_mt: float = GOVERNED_BUFFER_USD_MT,
        stale_marks_usd_mt: frozenset[float] | None = None,
    ) -> None:
        self.desk_window = desk_window
        self.governed_buffer_usd_mt = governed_buffer_usd_mt
        self.stale_marks_usd_mt = stale_marks_usd_mt or frozenset(
            {STALE_LME_PRINT_USD_MT}
        )

    def apply(
        self,
        *,
        price_print_usd_mt: float,
        price_print_ts: str | datetime | None,
        origin_source_hash: str,
        now: datetime | None = None,
    ) -> DeskPriceView:
        if not origin_source_hash:
            raise ValueError("origin_source_hash required for immutability chain")

        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        print_ts = _parse_ts(price_print_ts, now)
        within_window = print_ts is not None and (now - print_ts) <= self.desk_window

        # Explicit stale mark or anything outside the desk window is quarantined.
        marked_stale = price_print_usd_mt in self.stale_marks_usd_mt
        quarantine = marked_stale or not within_window

        # Downstream-only: never mutate caller-held origin; return separate view.
        origin_price = price_print_usd_mt
        origin_hash = origin_source_hash

        if quarantine:
            agent_price = self.governed_buffer_usd_mt
            hop = {
                "protocol": "SARC-DQ",
                "mode": "downstream_only",
                "action": "quarantine_and_substitute",
                "quarantined_print_usd_mt": origin_price,
                "governed_buffer_usd_mt": agent_price,
                "origin_source_hash": origin_hash,
                "origin_immutable": True,
                "desk_window_minutes": int(self.desk_window.total_seconds() // 60),
                "within_desk_window": within_window,
            }
        else:
            agent_price = origin_price
            hop = {
                "protocol": "SARC-DQ",
                "mode": "downstream_only",
                "action": "pass_through",
                "origin_source_hash": origin_hash,
                "origin_immutable": True,
                "within_desk_window": within_window,
            }

        return DeskPriceView(
            agent_price_usd_mt=agent_price,
            quarantined=quarantine,
            stale_print_usd_mt=origin_price if quarantine else None,
            origin_price_usd_mt=origin_price,
            origin_source_hash=origin_hash,
            origin_immutable=True,
            within_desk_window=within_window,
            hop=hop,
        )
