from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

from .roles import Blocksigner, Watchman


# Liquid-style default confirmation depth for peg-in claims
DEFAULT_PEGIN_CONFIRMATIONS = 100


class PegInProofLocus(str, Enum):
    """Rule 1: peg-in proof lives on the sidechain."""

    SIDECHAIN = "sidechain"
    BITCOIN = "bitcoin"


class PegOutProofLocus(str, Enum):
    """Rule 2: peg-out proof lives in the federation (Bitcoin multisig)."""

    FEDERATION_MULTISIG = "federation_multisig"
    BITCOIN_SPV_SCRIPT = "bitcoin_spv_script"


@dataclass(frozen=True)
class PegInDeposit:
    """User sends BTC to pay-to-contract tweaked federation multisig."""

    txid: str
    amount_sats: int
    tweaked_script: str
    sidechain_claim_address: str
    bitcoin_confirmations: int
    # Until claim address is revealed, federation cannot label the payment a peg-in
    tweak_revealed: bool = False


@dataclass(frozen=True)
class PegInClaim:
    """Sidechain checks Bitcoin Merkle proof + tweak control; mints L-BTC 1:1."""

    deposit_txid: str
    amount_sats: int
    merkle_proof_valid: bool
    controls_tweak_address: bool
    minted_lbtc_sats: int | None = None
    accepted: bool = False
    reason: str = ""


@dataclass(frozen=True)
class PegOutRequest:
    """User burns L-BTC on sidechain; watchmen release BTC (not Bitcoin SPV)."""

    burn_txid: str
    amount_sats: int
    btc_destination: str
    blocksigner_quorum_included_burn: bool


@dataclass(frozen=True)
class PegOutRelease:
    burn_txid: str
    amount_sats: int
    btc_destination: str
    watchmen_signatures: tuple[str, ...]
    released: bool
    reason: str
    bitcoin_verified_sidechain_header: bool = False


@dataclass
class FederatedPeg:
    """
    Production federated peg: Bitcoin never verifies sidechain headers.

    - Peg-in: user-driven; watchmen do not vote to accept deposits.
    - Peg-out: watchmen k-of-n sign mainchain spend after verifying burn + policy.
    """

    n_watchmen: int
    k_watchmen: int
    blocksigners: tuple[Blocksigner, ...] = ()
    watchmen: tuple[Watchman, ...] = ()
    pegin_confirmations_required: int = DEFAULT_PEGIN_CONFIRMATIONS
    reserve_sats: int = 0
    sidechain_lbtc_sats: int = 0
    _deposits: dict[str, PegInDeposit] = field(default_factory=dict)
    _seen_burns: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        if self.k_watchmen < 1 or self.k_watchmen > self.n_watchmen:
            raise ValueError("k_watchmen must satisfy 1 <= k <= n")
        if len(self.watchmen) != self.n_watchmen:
            raise ValueError("watchmen count must equal n_watchmen")

    @classmethod
    def liquid_like(
        cls,
        *,
        n: int = 5,
        k: int = 3,
        member_ids: Iterable[str] | None = None,
    ) -> FederatedPeg:
        ids = list(member_ids) if member_ids is not None else [f"fn-{i}" for i in range(n)]
        if len(ids) != n:
            raise ValueError("member_ids length must equal n")
        return cls(
            n_watchmen=n,
            k_watchmen=k,
            blocksigners=tuple(Blocksigner(member_id=i) for i in ids),
            watchmen=tuple(Watchman(member_id=i) for i in ids),
        )

    # --- architectural loci (the three rules) ---

    @property
    def pegin_proof_locus(self) -> PegInProofLocus:
        return PegInProofLocus.SIDECHAIN

    @property
    def pegout_proof_locus(self) -> PegOutProofLocus:
        return PegOutProofLocus.FEDERATION_MULTISIG

    @property
    def bitcoin_verifies_sidechain_headers(self) -> bool:
        return False

    @property
    def requires_bitcoin_spv_softfork(self) -> bool:
        return False

    def consensus_and_custody_separated(self) -> bool:
        """Rule 3: blocksigner halt ≠ watchman steal/freeze."""
        bs_ids = {b.member_id for b in self.blocksigners}
        w_ids = {w.member_id for w in self.watchmen}
        # Same member_ids allowed (same machines); hats must still differ by capability
        hats_ok = all(not b.may_spend_bitcoin_reserve() for b in self.blocksigners)
        hats_ok = hats_ok and all(not w.may_sign_sidechain_block() for w in self.watchmen)
        return hats_ok and bs_ids == w_ids

    # --- peg-in (user-driven) ---

    def record_deposit(self, deposit: PegInDeposit) -> None:
        if deposit.amount_sats <= 0:
            raise ValueError("deposit amount must be positive")
        self._deposits[deposit.txid] = deposit
        # Coins sit in reserve regardless of tweak reveal
        self.reserve_sats += deposit.amount_sats

    def watchmen_vote_required_for_pegin(self) -> bool:
        return False

    def claim_pegin(self, *, deposit_txid: str, merkle_proof_valid: bool, controls_tweak_address: bool) -> PegInClaim:
        """
        Sidechain validates Bitcoin Merkle proof + tweak control.
        Watchmen do not vote. Bitcoin does not check the sidechain.
        """
        dep = self._deposits.get(deposit_txid)
        if dep is None:
            return PegInClaim(
                deposit_txid=deposit_txid,
                amount_sats=0,
                merkle_proof_valid=merkle_proof_valid,
                controls_tweak_address=controls_tweak_address,
                accepted=False,
                reason="unknown_deposit",
            )

        if dep.bitcoin_confirmations < self.pegin_confirmations_required:
            return PegInClaim(
                deposit_txid=deposit_txid,
                amount_sats=dep.amount_sats,
                merkle_proof_valid=merkle_proof_valid,
                controls_tweak_address=controls_tweak_address,
                accepted=False,
                reason="insufficient_bitcoin_confirmations",
            )

        if not merkle_proof_valid:
            return PegInClaim(
                deposit_txid=deposit_txid,
                amount_sats=dep.amount_sats,
                merkle_proof_valid=False,
                controls_tweak_address=controls_tweak_address,
                accepted=False,
                reason="invalid_merkle_proof",
            )

        if not controls_tweak_address:
            return PegInClaim(
                deposit_txid=deposit_txid,
                amount_sats=dep.amount_sats,
                merkle_proof_valid=True,
                controls_tweak_address=False,
                accepted=False,
                reason="missing_tweak_control",
            )

        # Pay-to-contract: claim reveals the sidechain address binding
        dep_revealed = PegInDeposit(
            txid=dep.txid,
            amount_sats=dep.amount_sats,
            tweaked_script=dep.tweaked_script,
            sidechain_claim_address=dep.sidechain_claim_address,
            bitcoin_confirmations=dep.bitcoin_confirmations,
            tweak_revealed=True,
        )
        self._deposits[deposit_txid] = dep_revealed

        self.sidechain_lbtc_sats += dep.amount_sats
        return PegInClaim(
            deposit_txid=deposit_txid,
            amount_sats=dep.amount_sats,
            merkle_proof_valid=True,
            controls_tweak_address=True,
            minted_lbtc_sats=dep.amount_sats,
            accepted=True,
            reason="minted_1to1",
        )

    # --- peg-out (federated surface) ---

    def request_pegout(self, request: PegOutRequest) -> PegOutRequest:
        if request.amount_sats <= 0:
            raise ValueError("burn amount must be positive")
        if request.burn_txid in self._seen_burns:
            raise ValueError("burn already processed")
        return request

    def release_pegout(
        self,
        request: PegOutRequest,
        *,
        watchmen_signature_ids: Iterable[str],
        burn_policy_ok: bool = True,
    ) -> PegOutRelease:
        """
        Watchmen verify burn + policy and k-of-n sign Bitcoin reserve spend.
        Bitcoin checks multisig only — not a sidechain header chain.
        """
        sigs = tuple(watchmen_signature_ids)
        valid_ids = {w.member_id for w in self.watchmen}
        if any(s not in valid_ids for s in sigs):
            return PegOutRelease(
                burn_txid=request.burn_txid,
                amount_sats=request.amount_sats,
                btc_destination=request.btc_destination,
                watchmen_signatures=sigs,
                released=False,
                reason="unknown_watchman_signer",
                bitcoin_verified_sidechain_header=False,
            )

        if not request.blocksigner_quorum_included_burn:
            return PegOutRelease(
                burn_txid=request.burn_txid,
                amount_sats=request.amount_sats,
                btc_destination=request.btc_destination,
                watchmen_signatures=sigs,
                released=False,
                reason="burn_not_in_sidechain_quorum",
                bitcoin_verified_sidechain_header=False,
            )

        if not burn_policy_ok:
            return PegOutRelease(
                burn_txid=request.burn_txid,
                amount_sats=request.amount_sats,
                btc_destination=request.btc_destination,
                watchmen_signatures=sigs,
                released=False,
                reason="policy_rejected",
                bitcoin_verified_sidechain_header=False,
            )

        if len(set(sigs)) < self.k_watchmen:
            return PegOutRelease(
                burn_txid=request.burn_txid,
                amount_sats=request.amount_sats,
                btc_destination=request.btc_destination,
                watchmen_signatures=sigs,
                released=False,
                reason="below_k_of_n",
                bitcoin_verified_sidechain_header=False,
            )

        if request.amount_sats > self.sidechain_lbtc_sats:
            return PegOutRelease(
                burn_txid=request.burn_txid,
                amount_sats=request.amount_sats,
                btc_destination=request.btc_destination,
                watchmen_signatures=sigs,
                released=False,
                reason="insufficient_sidechain_inventory",
                bitcoin_verified_sidechain_header=False,
            )

        if request.amount_sats > self.reserve_sats:
            return PegOutRelease(
                burn_txid=request.burn_txid,
                amount_sats=request.amount_sats,
                btc_destination=request.btc_destination,
                watchmen_signatures=sigs,
                released=False,
                reason="insufficient_bitcoin_reserve",
                bitcoin_verified_sidechain_header=False,
            )

        self.sidechain_lbtc_sats -= request.amount_sats
        self.reserve_sats -= request.amount_sats
        self._seen_burns.add(request.burn_txid)

        return PegOutRelease(
            burn_txid=request.burn_txid,
            amount_sats=request.amount_sats,
            btc_destination=request.btc_destination,
            watchmen_signatures=tuple(dict.fromkeys(sigs)),  # preserve order, uniq
            released=True,
            reason="k_of_n_reserve_spend",
            bitcoin_verified_sidechain_header=False,
        )
