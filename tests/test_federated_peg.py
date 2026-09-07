"""Federated peg invariants — shipped architecture (not SPV)."""

from __future__ import annotations

import pytest

from cryptex_x.peg import (
    FederatedPeg,
    Functionary,
    PegInDeposit,
    PegOutRequest,
)
from cryptex_x.peg.federated import PegInProofLocus, PegOutProofLocus
from cryptex_x.peg.roles import FunctionaryHat


def test_functionary_hats_are_split():
    fn = Functionary.create("fn-0")
    assert fn.blocksigner.hat is FunctionaryHat.BLOCKSIGNER
    assert fn.watchman.hat is FunctionaryHat.WATCHMAN
    assert fn.blocksigner.touches_chain() == "sidechain"
    assert fn.watchman.touches_chain() == "bitcoin"
    assert fn.blocksigner.may_spend_bitcoin_reserve() is False
    assert fn.watchman.may_sign_sidechain_block() is False
    assert fn.watchman.may_spend_bitcoin_reserve() is True
    assert fn.blocksigner.may_sign_sidechain_block() is True


def test_rule1_pegin_proof_on_sidechain_not_bitcoin():
    peg = FederatedPeg.liquid_like(n=5, k=3)
    assert peg.pegin_proof_locus is PegInProofLocus.SIDECHAIN
    assert peg.bitcoin_verifies_sidechain_headers is False


def test_rule2_pegout_proof_in_federation_multisig():
    peg = FederatedPeg.liquid_like(n=5, k=3)
    assert peg.pegout_proof_locus is PegOutProofLocus.FEDERATION_MULTISIG
    assert peg.requires_bitcoin_spv_softfork is False


def test_rule3_consensus_and_custody_separated():
    peg = FederatedPeg.liquid_like(n=5, k=3)
    assert peg.consensus_and_custody_separated() is True


def test_pegin_user_driven_watchmen_do_not_vote():
    peg = FederatedPeg.liquid_like(n=5, k=3)
    assert peg.watchmen_vote_required_for_pegin() is False

    peg.record_deposit(
        PegInDeposit(
            txid="btc-tx-1",
            amount_sats=100_000,
            tweaked_script="twk-msig",
            sidechain_claim_address="lq1-claim",
            bitcoin_confirmations=100,
            tweak_revealed=False,
        )
    )
    # Before claim, tweak need not be revealed (pay-to-contract privacy)
    assert peg._deposits["btc-tx-1"].tweak_revealed is False

    claim = peg.claim_pegin(
        deposit_txid="btc-tx-1",
        merkle_proof_valid=True,
        controls_tweak_address=True,
    )
    assert claim.accepted is True
    assert claim.minted_lbtc_sats == 100_000
    assert peg.sidechain_lbtc_sats == 100_000
    assert peg.reserve_sats == 100_000
    assert peg._deposits["btc-tx-1"].tweak_revealed is True


def test_pegin_requires_confirmations_and_merkle_proof():
    peg = FederatedPeg.liquid_like(n=3, k=2)
    peg.record_deposit(
        PegInDeposit(
            txid="btc-tx-2",
            amount_sats=50_000,
            tweaked_script="twk",
            sidechain_claim_address="lq1",
            bitcoin_confirmations=20,
        )
    )
    low = peg.claim_pegin(
        deposit_txid="btc-tx-2",
        merkle_proof_valid=True,
        controls_tweak_address=True,
    )
    assert low.accepted is False
    assert low.reason == "insufficient_bitcoin_confirmations"

    peg._deposits["btc-tx-2"] = PegInDeposit(
        txid="btc-tx-2",
        amount_sats=50_000,
        tweaked_script="twk",
        sidechain_claim_address="lq1",
        bitcoin_confirmations=100,
    )
    bad_proof = peg.claim_pegin(
        deposit_txid="btc-tx-2",
        merkle_proof_valid=False,
        controls_tweak_address=True,
    )
    assert bad_proof.accepted is False
    assert bad_proof.reason == "invalid_merkle_proof"


def test_pegout_k_of_n_watchmen_bitcoin_never_checks_sidechain_header():
    peg = FederatedPeg.liquid_like(n=5, k=3)
    peg.record_deposit(
        PegInDeposit(
            txid="btc-tx-3",
            amount_sats=80_000,
            tweaked_script="twk",
            sidechain_claim_address="lq1",
            bitcoin_confirmations=100,
        )
    )
    assert peg.claim_pegin(
        deposit_txid="btc-tx-3",
        merkle_proof_valid=True,
        controls_tweak_address=True,
    ).accepted

    req = PegOutRequest(
        burn_txid="sc-burn-1",
        amount_sats=30_000,
        btc_destination="bc1q-user",
        blocksigner_quorum_included_burn=True,
    )
    below = peg.release_pegout(req, watchmen_signature_ids=["fn-0", "fn-1"])
    assert below.released is False
    assert below.reason == "below_k_of_n"
    assert below.bitcoin_verified_sidechain_header is False

    ok = peg.release_pegout(
        req, watchmen_signature_ids=["fn-0", "fn-1", "fn-2"]
    )
    assert ok.released is True
    assert ok.reason == "k_of_n_reserve_spend"
    assert ok.bitcoin_verified_sidechain_header is False
    assert peg.reserve_sats == 50_000
    assert peg.sidechain_lbtc_sats == 50_000


def test_pegout_requires_blocksigner_burn_inclusion():
    peg = FederatedPeg.liquid_like(n=3, k=2)
    peg.reserve_sats = 10_000
    peg.sidechain_lbtc_sats = 10_000
    req = PegOutRequest(
        burn_txid="sc-burn-2",
        amount_sats=1_000,
        btc_destination="bc1q-x",
        blocksigner_quorum_included_burn=False,
    )
    out = peg.release_pegout(req, watchmen_signature_ids=["fn-0", "fn-1"])
    assert out.released is False
    assert out.reason == "burn_not_in_sidechain_quorum"


def test_no_spv_locus_on_federated_path():
    """Hybrid paper line stayed theoretical — federated path has no SPV peg-out locus."""
    peg = FederatedPeg.liquid_like()
    assert peg.pegout_proof_locus is not PegOutProofLocus.BITCOIN_SPV_SCRIPT
    assert PegOutProofLocus.BITCOIN_SPV_SCRIPT.value == "bitcoin_spv_script"


def test_k_bounds():
    with pytest.raises(ValueError):
        FederatedPeg.liquid_like(n=3, k=0)
    with pytest.raises(ValueError):
        FederatedPeg.liquid_like(n=3, k=4)
