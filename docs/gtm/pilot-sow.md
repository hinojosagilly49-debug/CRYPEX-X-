# Pilot Statement of Work — Metals RFQ Desk

## 1. Purpose

Fixed-scope design-partner pilot of CRYPEX-X- on one metals trading desk. Validate hop-log acceptance criteria against the master-record audit under live RFQ traffic.

## 2. Parties

- **Vendor:** CRYPEX-X- / Cryptex X+ (GENIUS+ Pipeline stage-4 orchestration)
- **Customer:** Design-partner desk (trading lead + risk/compliance sponsor)

## 3. Scope (in)

- Intents: `enterprise_sync`, `kem_analysis`, `local` (freight companion)
- Engines: 395-connector, `agent-gpt-4o-secure`, `llama-3-8b-instruct`
- Guardrails: SARC-DQ downstream-only remediation; PreFlect hold-to-execute
- Deliverables: desk seats (agreed count), connector pack (395), restricted-model route, audit log export
- Acceptance: hop-log SLA matching §6

## 4. Scope (out)

- Fully autonomous settle / compiled Decision Engine “wire” beyond PreFlect hold
- Custom PQC implementations or algorithm bake-offs
- Multi-vertical expansion beyond Al / Cu / NMC-style cathode + freight
- Token-volume-based pricing metrics as success criteria

## 5. Duration and window

- **Pilot length:** 30–60 days (selectable at kickoff)
- **Desk pricing window:** 30 minutes (395-connector enforced)
- **Support hours:** agreed business hours for the desk timezone

## 6. Hop-log acceptance criteria (master-record)

| ID | Criterion | Pass condition |
|----|-----------|----------------|
| A1 | Desk window | Quotes older than 30 minutes cannot enter agent view as live |
| A2 | Quarantine | Stale **$2,412/mt** LME print is quarantined |
| A3 | Substitute | Governed **$2,286/mt** buffer is presented to the agent |
| A4 | Immutability | Original source print remains immutable (no in-place overwrite) |
| A5 | Restricted route | `kem_analysis` → `security_context.classification = restricted` → `agent-gpt-4o-secure` |
| A6 | PreFlect Incoterms | Missing Incoterms → execution **held** (no silent execute) |
| A7 | PreFlect escrow | Missing payment escrow → execution **held** |
| A8 | Local freight | `local` freight intent stays on `llama-3-8b-instruct` path |

Automated regression: `tests/test_acceptance_audit.py` (must remain green for pilot exit).

## 7. Customer obligations

- Nominate desk lead and compliance co-sponsor
- Provide sample RFQs and reference price feeds for replay
- Complete security questionnaire review within 10 business days of kickoff
- Attend weekly hop-log review (30 minutes)

## 8. Vendor obligations

- Provision SKUs in §3
- Run weekly acceptance replay against §6
- Export audit logs in agreed format
- Document egress artifacts (feeds PQC prioritization)

## 9. Commercial terms (pilot)

- **Fee:** fixed pilot fee (not usage/token based)
- **Success:** paid conversion path defined at kickoff; hop-log §6 is technical acceptance
- **Data:** retention and confidentiality named in pilot DPA addendum (triggers hybrid-PQC schedule if multi-year or HNDL-class)

## 10. Exit

- **Pass:** §6 criteria green + joint pilot report  
- **Extend:** written change order  
- **Wind down:** access revoked; audit exports delivered within 10 business days  

## 11. Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Desk lead | | | |
| Risk / compliance | | | |
| Vendor | | | |
