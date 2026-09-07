from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4


CLASSIFICATIONS = frozenset({"public", "internal", "restricted"})
INTENTS = frozenset({"enterprise_sync", "kem_analysis", "local"})


@dataclass(frozen=True)
class CryptoContext:
    """Crypto-agile identifiers; classical→hybrid is a config change."""

    policy_version: int = 1
    alg_id: str = "classical-2026"
    kem_id: str = "x25519"
    sig_id: str = "ed25519"
    key_id: str = "desk-key-2026q3"
    hybrid: bool = False
    classical_fallback: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SecurityContext:
    classification: str
    crypto: CryptoContext = field(default_factory=CryptoContext)

    def __post_init__(self) -> None:
        if self.classification not in CLASSIFICATIONS:
            raise ValueError(f"invalid classification: {self.classification}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification": self.classification,
            "crypto": self.crypto.to_dict(),
        }


def default_security_context(classification: str = "internal") -> SecurityContext:
    return SecurityContext(classification=classification, crypto=CryptoContext())


@dataclass
class CryptexEnvelope:
    """RFQ wrapped in a Cryptex envelope."""

    artifact_id: str
    security_context: SecurityContext
    intent: str
    instrument: str
    price_print_usd_mt: float | None = None
    price_print_ts: str | None = None
    incoterms: str | None = None
    payment_escrow: bool | None = None
    origin_source_hash: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.intent not in INTENTS:
            raise ValueError(f"invalid intent: {self.intent}")
        if not self.artifact_id:
            raise ValueError("artifact_id required")

    @classmethod
    def wrap(
        cls,
        *,
        intent: str,
        instrument: str,
        classification: str | None = None,
        security_context: SecurityContext | None = None,
        artifact_id: str | None = None,
        **rfq_fields: Any,
    ) -> CryptexEnvelope:
        if security_context is None:
            if classification is None:
                classification = (
                    "restricted" if intent == "kem_analysis" else "internal"
                )
            security_context = default_security_context(classification)
        return cls(
            artifact_id=artifact_id or str(uuid4()),
            security_context=security_context,
            intent=intent,
            instrument=instrument,
            price_print_usd_mt=rfq_fields.pop("price_print_usd_mt", None),
            price_print_ts=rfq_fields.pop("price_print_ts", None),
            incoterms=rfq_fields.pop("incoterms", None),
            payment_escrow=rfq_fields.pop("payment_escrow", None),
            origin_source_hash=rfq_fields.pop("origin_source_hash", None),
            extra=rfq_fields,
        )

    def to_dict(self) -> dict[str, Any]:
        rfq: dict[str, Any] = {
            "intent": self.intent,
            "instrument": self.instrument,
        }
        if self.price_print_usd_mt is not None:
            rfq["price_print_usd_mt"] = self.price_print_usd_mt
        if self.price_print_ts is not None:
            rfq["price_print_ts"] = self.price_print_ts
        if self.incoterms is not None:
            rfq["incoterms"] = self.incoterms
        if self.payment_escrow is not None:
            rfq["payment_escrow"] = self.payment_escrow
        if self.origin_source_hash is not None:
            rfq["origin_source_hash"] = self.origin_source_hash
        rfq.update(self.extra)
        return {
            "$meta": {
                "artifact_id": self.artifact_id,
                "security_context": self.security_context.to_dict(),
            },
            "rfq": rfq,
        }
