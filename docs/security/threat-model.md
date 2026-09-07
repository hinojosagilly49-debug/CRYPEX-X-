# Threat Model (PQC-secondary, GTM-first)

## Assets (long-lived only)

1. Cryptex envelopes — `$meta.artifact_id`, `security_context`  
2. Quarantine / substitution audit trails  
3. Connector authentication material (395)  
4. Model-dispatch channel credentials and routes  

## Out of primary scope (for now)

- Ephemeral UI sessions  
- Short-lived RAG cache entries inside desk window  
- Token-stream payloads with no retention  

## Adversaries / risks

| Risk | Impact | Mitigations now | Later |
|------|--------|-----------------|-------|
| Stale price injection | Bad fills | 30-min window, SARC-DQ quarantine/substitute | — |
| Origin tampering | Audit failure | Immutable source records | Hybrid signatures (phase 2) |
| Restricted data egress | Compliance breach | classification + secure model route; local freight path | Hybrid KEM on transport (phase 1) |
| Silent execute | Unapproved trade | PreFlect holds (Incoterms, escrow) | — |
| HNDL on multi-year archives | Future decrypt | Avoid long retention by default; agility fields | Hybrid PQC when DPA requires |
| Key lock-in | Migration pain | `alg_id` / `key_id` versioning | Policy bumps |

## Product seam

Decision Engine may remain PreFlect-only (“wire never compiles”). **Do not** treat uncompiled autonomous settle as a trust boundary in pilots. Hold queue is the control.

## GTM vs deeper PQC triggers

Go deeper on PQC **only if**:

- Multi-year price/position archives  
- Sovereign-restricted payloads with HNDL exposure  
- RFP hard-requires hybrid/PQC day one  
- Keys are long-lived and non-rotatable (fix rotation regardless)  
