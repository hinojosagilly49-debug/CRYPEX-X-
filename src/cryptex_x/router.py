from __future__ import annotations

from dataclasses import dataclass

from .envelope import CryptexEnvelope


ENGINE_BY_INTENT = {
    "enterprise_sync": "395-connector",
    "kem_analysis": "agent-gpt-4o-secure",
    "local": "llama-3-8b-instruct",
}


@dataclass(frozen=True)
class DispatchDecision:
    intent: str
    engine: str
    classification: str
    dispatch: str
    allowed: bool
    reason: str


class IntentRouter:
    """Cryptex stage-4 intent → engine router."""

    def dispatch(self, envelope: CryptexEnvelope) -> DispatchDecision:
        intent = envelope.intent
        engine = ENGINE_BY_INTENT[intent]
        classification = envelope.security_context.classification

        if intent == "kem_analysis":
            if classification != "restricted":
                return DispatchDecision(
                    intent=intent,
                    engine=engine,
                    classification=classification,
                    dispatch="blocked",
                    allowed=False,
                    reason="kem_analysis requires restricted security_context",
                )
            # Crypto agility fields must be present before secure dispatch.
            crypto = envelope.security_context.crypto
            if not crypto.alg_id or not crypto.key_id:
                return DispatchDecision(
                    intent=intent,
                    engine=engine,
                    classification=classification,
                    dispatch="blocked",
                    allowed=False,
                    reason="security_context.crypto alg_id/key_id required",
                )
            return DispatchDecision(
                intent=intent,
                engine=engine,
                classification=classification,
                dispatch="dispatch_to_model → agent-gpt-4o-secure",
                allowed=True,
                reason="restricted kem_analysis route",
            )

        if intent == "local":
            return DispatchDecision(
                intent=intent,
                engine=engine,
                classification=classification,
                dispatch="dispatch_to_local → llama-3-8b-instruct",
                allowed=True,
                reason="local freight path (data residency companion)",
            )

        return DispatchDecision(
            intent=intent,
            engine=engine,
            classification=classification,
            dispatch="dispatch_to_connector → 395-connector",
            allowed=True,
            reason="enterprise_sync",
        )
