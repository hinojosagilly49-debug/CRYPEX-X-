"""Master-record acceptance tests (pilot SOW hop-log criteria A1–A8)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from cryptex_x import (
    Connector395,
    CryptexEnvelope,
    IntentRouter,
    Pipeline,
    PreFlectGuardrail,
    default_security_context,
)
from cryptex_x.connector_395 import GOVERNED_BUFFER_USD_MT, STALE_LME_PRINT_USD_MT
from cryptex_x.envelope import CryptoContext, SecurityContext


FIXTURES = Path(__file__).parent / "fixtures" / "hop_logs.json"


def _load_cases() -> list[dict]:
    data = json.loads(FIXTURES.read_text(encoding="utf-8"))
    return data["cases"]


def _envelope_from_rfq(rfq: dict) -> CryptexEnvelope:
    classification = rfq.get("classification")
    kwargs = {
        k: v
        for k, v in rfq.items()
        if k
        in {
            "intent",
            "instrument",
            "price_print_usd_mt",
            "price_print_ts",
            "incoterms",
            "payment_escrow",
            "origin_source_hash",
        }
    }
    if classification:
        kwargs["security_context"] = default_security_context(classification)
    return CryptexEnvelope.wrap(**kwargs)


def test_a1_desk_window_thirty_minutes():
    connector = Connector395()
    assert connector.desk_window == timedelta(minutes=30)


def test_a2_a3_a4_quarantine_substitute_immutable():
    """Stale $2,412/mt quarantined; $2,286/mt buffer; origin immutable."""
    connector = Connector395()
    origin_hash = "lme-al3105-print-2412-immutable"
    origin_price = STALE_LME_PRINT_USD_MT
    now = datetime(2026, 9, 1, 11, 0, tzinfo=timezone.utc)
    print_ts = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)

    view = connector.apply(
        price_print_usd_mt=origin_price,
        price_print_ts=print_ts,
        origin_source_hash=origin_hash,
        instrument="Al 3105",
        now=now,
    )

    assert view.quarantined is True
    assert view.stale_print_usd_mt == 2412.0
    assert view.agent_price_usd_mt == GOVERNED_BUFFER_USD_MT == 2286.0
    assert view.origin_price_usd_mt == 2412.0
    assert view.origin_source_hash == origin_hash
    assert view.origin_immutable is True
    # Downstream-only: applying again must not mutate prior origin fields
    assert view.hop["mode"] == "downstream_only"
    assert view.hop["origin_immutable"] is True


def test_quarantine_without_configured_buffer_keeps_origin_price():
    connector = Connector395()
    now = datetime(2026, 9, 1, 11, 0, tzinfo=timezone.utc)
    print_ts = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)

    view = connector.apply(
        instrument="Cu cathode",
        price_print_usd_mt=2412.0,
        price_print_ts=print_ts,
        origin_source_hash="cu-cathode-print-2412",
        now=now,
    )

    assert view.quarantined is True
    assert view.agent_price_usd_mt == 2412.0
    assert view.hop["substitution_permitted"] is False
    assert view.hop["governed_buffer_usd_mt"] is None


def test_a5_kem_analysis_restricted_route():
    env = CryptexEnvelope.wrap(
        intent="kem_analysis",
        instrument="NMC 811 / Cu cathode",
        classification="restricted",
        incoterms="CIF",
        payment_escrow=True,
    )
    decision = IntentRouter().dispatch(env)
    assert decision.allowed is True
    assert decision.engine == "agent-gpt-4o-secure"
    assert decision.classification == "restricted"
    assert "agent-gpt-4o-secure" in decision.dispatch


def test_a5_kem_analysis_rejects_non_restricted():
    env = CryptexEnvelope.wrap(
        intent="kem_analysis",
        instrument="NMC 811",
        security_context=SecurityContext(
            classification="internal",
            crypto=CryptoContext(),
        ),
    )
    decision = IntentRouter().dispatch(env)
    assert decision.allowed is False


def test_a5_kem_analysis_rejects_missing_crypto_agility_fields():
    env = CryptexEnvelope.wrap(
        intent="kem_analysis",
        instrument="NMC 811 / Cu cathode",
        security_context=SecurityContext(
            classification="restricted",
            crypto=CryptoContext(
                alg_id="classical-2026",
                kem_id="",
                sig_id="ed25519",
                key_id="desk-key-2026q3",
            ),
        ),
    )
    decision = IntentRouter().dispatch(env)
    assert decision.allowed is False
    assert "kem_id" in decision.reason


def test_missing_price_timestamp_is_not_within_window():
    connector = Connector395()
    view = connector.apply(
        price_print_usd_mt=1500.0,
        price_print_ts=None,
        origin_source_hash="hash-with-no-ts",
        now=datetime(2026, 9, 1, 11, 0, tzinfo=timezone.utc),
    )
    assert view.quarantined is True
    assert view.within_desk_window is False


def test_a6_preflect_hold_missing_incoterms():
    env = CryptexEnvelope.wrap(
        intent="kem_analysis",
        instrument="Cu cathode",
        classification="restricted",
        incoterms=None,
        payment_escrow=True,
    )
    hold = PreFlectGuardrail().evaluate(env)
    assert hold.held is True
    assert hold.can_execute is False
    assert "incoterms" in hold.missing_constraints
    assert hold.silent_execute_prevented is True


def test_a7_preflect_hold_missing_payment_escrow():
    env = CryptexEnvelope.wrap(
        intent="kem_analysis",
        instrument="Cu cathode",
        classification="restricted",
        incoterms="FOB",
        payment_escrow=None,
    )
    hold = PreFlectGuardrail().evaluate(env)
    assert hold.held is True
    assert "payment_escrow" in hold.missing_constraints
    assert hold.silent_execute_prevented is True


def test_a8_local_freight_llama_path():
    env = CryptexEnvelope.wrap(
        intent="local",
        instrument="SHA-RTM freight",
        incoterms="FOB",
        payment_escrow=True,
    )
    decision = IntentRouter().dispatch(env)
    assert decision.engine == "llama-3-8b-instruct"
    assert "llama-3-8b-instruct" in decision.dispatch


def test_security_context_crypto_agility_fields_present():
    ctx = default_security_context("restricted")
    d = ctx.to_dict()
    crypto = d["crypto"]
    for key in ("policy_version", "alg_id", "kem_id", "sig_id", "key_id", "hybrid"):
        assert key in crypto
    assert crypto["hybrid"] is False
    assert crypto["policy_version"] >= 1


def test_pipeline_hold_to_execute_not_autonomous_settle():
    env = CryptexEnvelope.wrap(
        intent="enterprise_sync",
        instrument="Al 3105",
        price_print_usd_mt=2412.0,
        price_print_ts="2026-09-01T10:00:00+00:00",
        origin_source_hash="hash-1",
        incoterms=None,
        payment_escrow=None,
    )
    result = Pipeline().run(
        env, now=datetime(2026, 9, 1, 11, 0, tzinfo=timezone.utc)
    )
    assert result.action == "hold"
    assert result.learning["autonomous_settle"] is False
    assert result.learning["decision_engine"] == "PreFlect"
    assert result.price_view is not None
    assert result.price_view.quarantined is True
    assert result.stages == [
        "ingest",
        "rag_context",
        "llm",
        "preflect_sarc_dq",
        "action",
        "learning",
    ]


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["id"])
def test_fixture_hop_log_cases(case: dict):
    rfq = case["rfq"]
    expect = case["expect"]
    env = _envelope_from_rfq(rfq)
    now = case.get("now")
    now_dt = datetime.fromisoformat(now) if now else None

    result = Pipeline().run(env, now=now_dt)

    if "engine" in expect:
        assert result.dispatch is not None
        assert result.dispatch.engine == expect["engine"]
    if "classification" in expect:
        assert result.dispatch is not None
        assert result.dispatch.classification == expect["classification"]
    if "dispatch_contains" in expect:
        assert result.dispatch is not None
        assert expect["dispatch_contains"] in result.dispatch.dispatch
    if "allowed" in expect:
        assert result.dispatch is not None
        assert result.dispatch.allowed is expect["allowed"]
    if "quarantined" in expect:
        assert result.price_view is not None
        assert result.price_view.quarantined is expect["quarantined"]
    if "agent_price_usd_mt" in expect:
        assert result.price_view is not None
        assert result.price_view.agent_price_usd_mt == expect["agent_price_usd_mt"]
    if "origin_price_usd_mt" in expect:
        assert result.price_view is not None
        assert result.price_view.origin_price_usd_mt == expect["origin_price_usd_mt"]
    if "origin_immutable" in expect:
        assert result.price_view is not None
        assert result.price_view.origin_immutable is expect["origin_immutable"]
    if "within_desk_window" in expect:
        assert result.price_view is not None
        assert result.price_view.within_desk_window is expect["within_desk_window"]
    if "action" in expect:
        assert result.action == expect["action"]
    if "missing_constraints" in expect:
        assert result.hold is not None
        assert list(result.hold.missing_constraints) == expect["missing_constraints"]
    if "silent_execute_prevented" in expect:
        assert result.hold is not None
        assert (
            result.hold.silent_execute_prevented
            is expect["silent_execute_prevented"]
        )


def test_pipeline_execute_when_constraints_present():
    env = CryptexEnvelope.wrap(
        intent="local",
        instrument="SHA-RTM freight",
        incoterms="FOB",
        payment_escrow=True,
    )
    result = Pipeline().run(env)
    assert result.action == "execute"
    assert result.hold is not None
    assert result.hold.can_execute is True
