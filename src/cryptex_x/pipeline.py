from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .connector_395 import Connector395, DeskPriceView
from .envelope import CryptexEnvelope
from .preflect import HoldDecision, PreFlectGuardrail
from .router import DispatchDecision, IntentRouter


@dataclass
class PipelineResult:
    """
    GENIUS+ map result with Cryptex stage-4 orchestration.

    action is only 'execute' when PreFlect clears; otherwise 'hold'.
    learning hooks capture hop evidence for audit export.
    """

    stages: list[str]
    envelope_id: str
    dispatch: DispatchDecision | None
    price_view: DeskPriceView | None
    hold: HoldDecision | None
    action: str
    learning: dict[str, Any] = field(default_factory=dict)
    hops: list[dict[str, Any]] = field(default_factory=list)


class Pipeline:
    """ingest → RAG context → LLM → PreFlect/SARC-DQ → action → learning."""

    STAGES = (
        "ingest",
        "rag_context",
        "llm",
        "preflect_sarc_dq",
        "action",
        "learning",
    )

    def __init__(
        self,
        *,
        router: IntentRouter | None = None,
        connector: Connector395 | None = None,
        preflect: PreFlectGuardrail | None = None,
    ) -> None:
        self.router = router or IntentRouter()
        self.connector = connector or Connector395()
        self.preflect = preflect or PreFlectGuardrail()

    def run(
        self,
        envelope: CryptexEnvelope,
        *,
        now: datetime | None = None,
    ) -> PipelineResult:
        now = now or datetime.now(timezone.utc)
        hops: list[dict[str, Any]] = []
        stages_hit = ["ingest", "rag_context", "llm"]

        dispatch = self.router.dispatch(envelope)
        hops.append(
            {
                "stage": "cryptex_router",
                "dispatch": dispatch.dispatch,
                "engine": dispatch.engine,
                "allowed": dispatch.allowed,
                "reason": dispatch.reason,
            }
        )

        price_view: DeskPriceView | None = None
        if dispatch.allowed and envelope.intent == "enterprise_sync":
            if envelope.price_print_usd_mt is None:
                raise ValueError("enterprise_sync requires price_print_usd_mt")
            if not envelope.origin_source_hash:
                raise ValueError("enterprise_sync requires origin_source_hash")
            price_view = self.connector.apply(
                price_print_usd_mt=envelope.price_print_usd_mt,
                price_print_ts=envelope.price_print_ts,
                origin_source_hash=envelope.origin_source_hash,
                now=now,
            )
            hops.append(price_view.hop)

        stages_hit.append("preflect_sarc_dq")
        hold: HoldDecision | None = None
        action = "blocked_route"

        if not dispatch.allowed:
            action = "blocked_route"
        else:
            hold = self.preflect.evaluate(envelope)
            hops.append(
                {
                    "stage": "preflect",
                    "held": hold.held,
                    "can_execute": hold.can_execute,
                    "missing_constraints": list(hold.missing_constraints),
                    "reason_codes": list(hold.reason_codes),
                }
            )
            action = "execute" if hold.can_execute else "hold"

        stages_hit.append("action")
        learning = {
            "artifact_id": envelope.artifact_id,
            "action": action,
            "engine": dispatch.engine if dispatch else None,
            "quarantined": price_view.quarantined if price_view else None,
            "decision_engine": "PreFlect",
            "autonomous_settle": False,
            "note": "hold-to-execute is the supported path; wire does not auto-compile settle",
        }
        stages_hit.append("learning")
        hops.append({"stage": "learning", "record": learning})

        return PipelineResult(
            stages=stages_hit,
            envelope_id=envelope.artifact_id,
            dispatch=dispatch,
            price_view=price_view,
            hold=hold,
            action=action,
            learning=learning,
            hops=hops,
        )
