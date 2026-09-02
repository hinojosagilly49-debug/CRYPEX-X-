# Pilot Runbook — Metals RFQ Desk

## Roles

| Role | Responsibility |
|------|----------------|
| Desk lead | RFQ flow, accept/reject holds |
| Compliance | Review quarantine/substitution logs weekly |
| Vendor SE | Hop-log replay, acceptance gating |
| Vendor support | Connector health, envelope schema issues |

## Daily

1. Confirm 395-connector heartbeats and desk clock skew &lt; 30s.
2. Ingest RFQs as Cryptex envelopes (`artifact_id` + `security_context`).
3. Review PreFlect **holds** queue (Incoterms / escrow) — human clear required before execute.
4. Export prior-day hop logs to customer SIEM or shared audit bucket.

## Weekly

1. Replay master-record cases (see [hop-log-demo-script.md](./hop-log-demo-script.md)).
2. Run `python -m pytest tests/test_acceptance_audit.py -q`.
3. Compliance spot-check: one quarantine event + one restricted `kem_analysis` dispatch.
4. Catalog **egress artifacts** (what left the desk) → update PQC priority list.

## Incident classes

| Class | Example | Response |
|-------|---------|----------|
| Stale price bleed | Agent sees pre-quarantine print | Halt enterprise_sync; replay A2–A4; root-cause connector window |
| Misroute | `kem_analysis` not restricted | Halt secure dispatch; freeze router config; replay A5 |
| Silent execute | Action without Incoterms | Declare severity-1; disable action channel; replay A6–A7 |
| Freight off-box | Local intent left Llama path | Revoke external route; replay A8 |

## Hold-to-execute policy (supported path)

- PreFlect **hold** is success, not failure.
- Pilots must **not** market autonomous settle.
- Clearing a hold requires named desk role + logged reason code.

## Exit checklist

- [ ] A1–A8 green on final replay  
- [ ] Audit export delivered  
- [ ] Egress artifact list signed by compliance  
- [ ] Pilot report filed (see SOW §10)  
