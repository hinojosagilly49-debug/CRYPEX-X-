# Crypto Agility — security_context Versioning

## Mandate

Classical → hybrid PQC must be a **configuration change**, not a pipeline rewrite. Every Cryptex envelope carries explicit algorithm and key identifiers.

## security_context fields

Defined in [`schemas/security_context.schema.json`](../../schemas/security_context.schema.json):

| Field | Purpose |
|-------|---------|
| `classification` | e.g. `public`, `internal`, `restricted` |
| `crypto.policy_version` | Integer policy generation |
| `crypto.alg_id` | Suite identifier (classical or hybrid) |
| `crypto.kem_id` | KEM algorithm ID (envelope transport) |
| `crypto.sig_id` | Signature algorithm ID (artifact immutability) |
| `crypto.key_id` | Key rotation handle |
| `crypto.hybrid` | `false` until pilot DPA requires hybrid |
| `crypto.classical_fallback` | Allowed only when policy_version permits |

## Phase plan

| Phase | When | Action |
|-------|------|--------|
| 0 | Now | Ship versioned IDs on all envelopes; rotation runbook |
| 1 | After pilot DPA names retention/HNDL | Hybrid KEM on envelope transport |
| 2 | Same trigger for long-lived artifacts | Hybrid/PQC signatures on immutable origin + audit chain |
| — | Deferred | Algorithm bake-offs, custom PQC impls, full HNDL panic rewrites |

## Local path complementarity

`local` → `llama-3-8b-instruct` reduces egress for freight intents. It **complements** PQC; it does not replace envelope crypto agility.

## Router interaction

`kem_analysis` requires `classification: restricted`. Crypto fields are orthogonal but must be present before dispatch to `agent-gpt-4o-secure`.
