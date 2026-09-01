# CRYPEX-X-

Metals RFQ desk on **COGNITIVE SILICONE** — silicon-to-semantics stack — with **GENIUS+** Pipeline and **Cryptex X+** stage-4 orchestration.

## Status (post-audit)

Master-record double-check verified:

- **395-connector** — 30-minute desk window; four invariants; quarantine stale **$2,412/mt** LME print; substitute governed **$2,286/mt** buffer; **origin immutable**
- **Cryptex routing** — `kem_analysis` + restricted `security_context` → `agent-gpt-4o-secure`
- **PreFlect** — holds on missing Incoterms / payment escrow (**no silent execute**)

**Supported path:** PreFlect **hold-to-execute**. Autonomous settle is out of scope until action→learning is contractually scoped (“wire never compiles” remains a product seam).

**Next focus:** 2026 GTM on one desk wedge; PQC as crypto-agility (not a blocker).

## Pipeline

`ingest → RAG context → LLM → PreFlect/SARC-DQ → action → learning`

Every RFQ is a Cryptex envelope (`$meta.artifact_id`, versioned `security_context`).

| RFQ | Intent | Engine |
|-----|--------|--------|
| Al 3105 (stale ticker) | `enterprise_sync` | 395-connector |
| NMC 811 / Cu cathode | `kem_analysis` | agent-gpt-4o-secure |
| SHA–RTM freight | `local` | llama-3-8b-instruct |

## Repository map

| Path | Purpose |
|------|---------|
| [docs/gtm/](docs/gtm/) | One-pager, pilot SOW, runbook, demo script, security questionnaire, SKUs |
| [docs/security/](docs/security/) | Crypto agility + threat model (PQC secondary) |
| [schemas/](schemas/) | `security_context` + Cryptex envelope JSON Schemas |
| [src/cryptex_x/](src/cryptex_x/) | Envelope, router, 395-connector, PreFlect, pipeline |
| [tests/test_acceptance_audit.py](tests/test_acceptance_audit.py) | Hop-log acceptance criteria A1–A8 |

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

## GTM packaging

- [One-pager](docs/gtm/one-pager.md)
- [Pilot SOW](docs/gtm/pilot-sow.md)
- [Pilot runbook](docs/gtm/pilot-runbook.md)
- [Hop-log demo script](docs/gtm/hop-log-demo-script.md)
- [Security questionnaire](docs/gtm/security-questionnaire.md)
- [SKUs and pricing](docs/gtm/skus-and-pricing.md)

## Crypto agility (PQC-ready fields)

`security_context.crypto` carries `policy_version`, `alg_id`, `kem_id`, `sig_id`, `key_id`, `hybrid`. Hybrid PQC is scheduled only after pilot DPA retention/HNDL terms — see [docs/security/crypto-agility.md](docs/security/crypto-agility.md).
