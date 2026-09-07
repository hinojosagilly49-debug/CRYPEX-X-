# Security Questionnaire — CRYPEX-X- Metals Desk Pilot

Answers for enterprise security review. Scope: design-partner pilot, hold-to-execute path.

## 1. Architecture

| Question | Answer |
|----------|--------|
| What is the data flow? | ingest → RAG → LLM → PreFlect/SARC-DQ → action → learning; Cryptex orchestrates stage 4 |
| How is each RFQ represented? | Cryptex envelope with `$meta.artifact_id` and versioned `security_context` |
| How is model routing decided? | Intent router: `enterprise_sync` → 395-connector; `kem_analysis` → `agent-gpt-4o-secure`; `local` → `llama-3-8b-instruct` |
| Is autonomous execution enabled? | **No** for pilot. PreFlect **hold-to-execute** is the supported path |

## 2. Data protection

| Question | Answer |
|----------|--------|
| Are origin market prints mutable? | **No.** SARC-DQ is downstream-only; quarantine + substitute; origin immutable |
| Example control | Stale $2,412/mt quarantined; $2,286/mt governed buffer to agent |
| Desk freshness window | 30 minutes (395-connector enforced) |
| Freight / local data path | Stays on local Llama path for `local` intent (residency/confidentiality control) |
| Audit evidence | Hop-log + quarantine/substitution trail exportable (Audit log export SKU) |

## 3. Access and isolation

| Question | Answer |
|----------|--------|
| Restricted workloads | `kem_analysis` requires `classification: restricted` and secure model dispatch |
| Separation of duties | Hold clear requires named desk role + reason code |
| Connector auth | Versioned key IDs in `security_context`; rotation supported (crypto agility) |

## 4. Cryptography (agility-first; PQC secondary)

| Question | Answer |
|----------|--------|
| Algorithm lock-in? | **No.** `security_context` carries `crypto.alg_id`, `crypto.kem_id`, `crypto.sig_id`, `crypto.key_id`, `crypto.policy_version` |
| PQC on day one? | Not required for pilot unless contract names multi-year retention or HNDL-class data |
| Hybrid PQC plan | Envelope transport KEM + immutable artifact signatures after pilot DPA terms; no custom PQC implementations |
| Threat model focus | Long-lived envelopes, audit trails, connector auth, model-dispatch channel |

See [../security/crypto-agility.md](../security/crypto-agility.md) and [../security/threat-model.md](../security/threat-model.md).

## 5. Operations

| Question | Answer |
|----------|--------|
| Acceptance tests | `tests/test_acceptance_audit.py` gates A1–A8 master-record criteria |
| Incident response | Pilot runbook incident classes (stale bleed, misroute, silent execute, freight off-box) |
| Logging | Hop logs retained per pilot DPA; export on request and at wind-down |

## 6. Compliance posture (pilot)

| Question | Answer |
|----------|--------|
| Primary co-buyer concern | Immutable source, quarantine audit, escrow/Incoterms holds |
| Marketing restriction | Do not claim fully autonomous settle during pilot |
| Subprocessors | Disclosed in pilot SOW appendix (customer-specific) |
