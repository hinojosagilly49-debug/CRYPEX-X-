# XTC🌐LIVE V13-RC2 — Deployment Readiness

**Status:** PRODUCTION CANDIDATE (not fully PRODUCTION READY)

## Remediation closed in this branch

| Defect | Fix | Path |
|--------|-----|------|
| DB migration / Realtime view syntax | Publish `webhook_events` **base table**; generated `event_type` from JSONB `type` | `supabase/migrations/20260831000001_create_transactional_outbox.sql` |
| Secret rotation fallback | Restore `REVENUECAT_WEBHOOK_SIGNING_SECRET_OLD` | `supabase/functions/XTC_LIVE_Secure_Webhook_Edge_Function.ts` |
| Ephemeral CI tag clobber | `git rev-parse "refs/tags/${TAG}"` + remote probe | `scripts/release.sh` |
| Missing `dist/` on CI | Explicit `npm run build` | `.github/workflows/ci-release.yml` |
| Webhook vector gaps | T1–T10 including duplicate idempotency + fallback | `tests/ci_webhook_tests.js` |

## Architecture locks

- **Outbox:** PostgreSQL transactional outbox + BullMQ/Redis with `FOR UPDATE SKIP LOCKED` (Kafka deferred until >10k events/sec).
- **PIRA:** MPC n=4, γ=0.3 — **VOD/Shorts only**; live uses WebRTC/LL-HLS edge failover.
- **Billing:** Stripe (web) vs Google Play Billing 9.0.0 via RevenueCat (Android); zero Stripe binaries in AAB.
- **Security:** constant-time HMAC-SHA256, 300s timestamp skew, UNIQUE `event_id`, masked DLQ PII.

## Verification matrix

| Requirement | Implemented | Tested | Verified |
| :--- | :--- | :--- | :--- |
| Android 16 (API 36) Target | Yes | Yes | Verified (fixture) |
| Zero-Stripe Binaries in AAB | Yes | Yes | Verified |
| Constant-Time HMAC & Fallback | Yes | Yes | Verified |
| DB Base Table & Publication | Yes | Syntax review | Verified |
| Remote Git Tag Clobber Check | Yes | Yes | Verified |
| PIRA VOD Optimization Bounds | Yes | Yes | Verified |
| Maia 200 50k Concurrency Soak | Yes | Simulated | **Requires validation** (hardware) |
| Google Play 14-Day Closed Test | Yes | Not executed | **Requires validation** (calendar) |

## Unverified external blockers

1. Azure Maia 200 physical allocation (US Central) for 50k connection soak.
2. Google Play 14-day closed testing track with ≥12 continuously opted-in testers.

## Next steps

```bash
./scripts/release.sh v13-rc2 --final-verified
# Deploy AAB; invite 15–20 closed testers
# az webapp load-test — 50k connections against Maia 200
```

Keep fallback signing secrets valid ≥24h during rotation windows.
