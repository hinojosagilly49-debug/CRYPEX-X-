from __future__ import annotations

from dataclasses import dataclass, field

from .envelope import CryptexEnvelope


@dataclass(frozen=True)
class HoldDecision:
    """PreFlect hold-to-execute outcome. Hold is success for incomplete RFQs."""

    held: bool
    can_execute: bool
    missing_constraints: tuple[str, ...] = field(default_factory=tuple)
    reason_codes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def silent_execute_prevented(self) -> bool:
        return self.held and not self.can_execute


class PreFlectGuardrail:
    """
    Decision Engine guardrail (supported pilot path: hold-to-execute).

    Catches missing Incoterms and payment escrow. Does not claim compiled
    autonomous settle — the wire remains hold-gated.
    """

    REQUIRED_FOR_EXECUTE = ("incoterms", "payment_escrow")

    def evaluate(self, envelope: CryptexEnvelope) -> HoldDecision:
        missing: list[str] = []
        reasons: list[str] = []
        reason_by_field = {
            "incoterms": "HOLD_MISSING_INCOTERMS",
            "payment_escrow": "HOLD_MISSING_PAYMENT_ESCROW",
        }

        for field_name in self.REQUIRED_FOR_EXECUTE:
            value = getattr(envelope, field_name)
            if field_name == "payment_escrow":
                missing_value = value is not True
            else:
                missing_value = not value
            if missing_value:
                missing.append(field_name)
                reasons.append(reason_by_field[field_name])

        if missing:
            return HoldDecision(
                held=True,
                can_execute=False,
                missing_constraints=tuple(missing),
                reason_codes=tuple(reasons),
            )

        return HoldDecision(
            held=False,
            can_execute=True,
            missing_constraints=(),
            reason_codes=("CLEARED_FOR_EXECUTE",),
        )
