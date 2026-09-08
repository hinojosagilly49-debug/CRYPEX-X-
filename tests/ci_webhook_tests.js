#!/usr/bin/env node
/**
 * XTC LIVE webhook vector suite T1–T10 (100% path coverage target)
 * Covers: constant-time HMAC, 300s drift, fallback secret, idempotency, PII mask.
 */
"use strict";

const assert = require("assert");
const path = require("path");

const {
  MAX_SKEW_SECONDS,
  verifyWebhookSignature,
  maskPii,
  signBody,
  handleSecureWebhook,
  createMemoryStore,
  timingSafeEqual,
} = require(path.join(__dirname, "..", "src", "xtc-live", "webhook"));

const PRIMARY = "test_primary_secret_v13";
const FALLBACK = "test_fallback_secret_old";
const NOW = 1_700_000_000;

let passed = 0;
function test(name, fn) {
  try {
    fn();
    passed += 1;
    console.log(`  PASS  ${name}`);
  } catch (err) {
    console.error(`  FAIL  ${name}`);
    console.error(err);
    process.exitCode = 1;
  }
}

async function atest(name, fn) {
  try {
    await fn();
    passed += 1;
    console.log(`  PASS  ${name}`);
  } catch (err) {
    console.error(`  FAIL  ${name}`);
    console.error(err);
    process.exitCode = 1;
  }
}

console.log("XTC LIVE webhook vectors T1–T10");

// T1: valid primary signature
test("T1 valid primary HMAC-SHA256", () => {
  const rawBody = JSON.stringify({ id: "evt_t1", type: "INITIAL_PURCHASE" });
  const ts = String(NOW);
  const sig = signBody(PRIMARY, rawBody, ts);
  const r = verifyWebhookSignature({
    rawBody,
    signatureHeader: `sha256=${sig}`,
    timestampHeader: ts,
    primarySecret: PRIMARY,
    fallbackSecret: FALLBACK,
    nowSeconds: NOW,
  });
  assert.strictEqual(r.ok, true);
  assert.strictEqual(r.kid, "primary");
});

// T2: fallback secret path (rotation)
test("T2 fallback REVENUECAT_WEBHOOK_SIGNING_SECRET_OLD", () => {
  const rawBody = JSON.stringify({ id: "evt_t2", type: "RENEWAL" });
  const ts = String(NOW);
  const sig = signBody(FALLBACK, rawBody, ts);
  const r = verifyWebhookSignature({
    rawBody,
    signatureHeader: sig,
    timestampHeader: ts,
    primarySecret: PRIMARY,
    fallbackSecret: FALLBACK,
    nowSeconds: NOW,
  });
  assert.strictEqual(r.ok, true);
  assert.strictEqual(r.kid, "fallback");
});

// T3: bad signature rejected
test("T3 bad signature rejected", () => {
  const rawBody = JSON.stringify({ id: "evt_t3", type: "CANCELLATION" });
  const r = verifyWebhookSignature({
    rawBody,
    signatureHeader: "sha256=" + "ab".repeat(32),
    timestampHeader: String(NOW),
    primarySecret: PRIMARY,
    fallbackSecret: FALLBACK,
    nowSeconds: NOW,
  });
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.code, "bad_signature");
});

// T4: missing signature
test("T4 missing signature", () => {
  const r = verifyWebhookSignature({
    rawBody: "{}",
    signatureHeader: null,
    timestampHeader: String(NOW),
    primarySecret: PRIMARY,
    nowSeconds: NOW,
  });
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.code, "missing_signature");
});

// T5: replay / clock drift > 300s
test("T5 replay rejection skew > 300s", () => {
  const rawBody = JSON.stringify({ id: "evt_t5", type: "RENEWAL" });
  const ts = String(NOW - (MAX_SKEW_SECONDS + 1));
  const sig = signBody(PRIMARY, rawBody, ts);
  const r = verifyWebhookSignature({
    rawBody,
    signatureHeader: sig,
    timestampHeader: ts,
    primarySecret: PRIMARY,
    nowSeconds: NOW,
  });
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.code, "replay");
});

// T6: drift within 300s accepted
test("T6 drift within 300s accepted", () => {
  const rawBody = JSON.stringify({ id: "evt_t6", type: "PRODUCT_CHANGE" });
  const ts = String(NOW - (MAX_SKEW_SECONDS - 1));
  const sig = signBody(PRIMARY, rawBody, ts);
  const r = verifyWebhookSignature({
    rawBody,
    signatureHeader: sig,
    timestampHeader: ts,
    primarySecret: PRIMARY,
    nowSeconds: NOW,
  });
  assert.strictEqual(r.ok, true);
});

// T7: constant-time equal length mismatch
test("T7 timingSafeEqual detects mismatch", () => {
  const a = Buffer.from("0".repeat(64), "hex");
  const b = Buffer.from("1".repeat(64), "hex");
  assert.strictEqual(timingSafeEqual(a, b), false);
  assert.strictEqual(timingSafeEqual(a, Buffer.from(a)), true);
});

// T8: PII masking deterministic
test("T8 deterministic PII masking for DLQ", () => {
  const masked = maskPii({
    id: "evt_t8",
    email: "user@example.com",
    nested: { app_user_id: "au_123", ok: true },
    type: "INITIAL_PURCHASE",
  });
  assert.strictEqual(masked.email, "[REDACTED]");
  assert.strictEqual(masked.nested.app_user_id, "[REDACTED]");
  assert.strictEqual(masked.nested.ok, true);
  assert.strictEqual(masked.id, "evt_t8");
});

(async () => {
  // T9: end-to-end accept + duplicate idempotency (409→200)
  await atest("T9 handle accept then duplicate → 200", async () => {
    const store = createMemoryStore();
    const rawBody = JSON.stringify({ id: "evt_t9", type: "INITIAL_PURCHASE", email: "a@b.c" });
    const ts = String(NOW);
    const sig = signBody(PRIMARY, rawBody, ts);
    const req = {
      rawBody,
      headers: {
        "x-revenuecat-signature": sig,
        "x-revenuecat-timestamp": ts,
      },
    };
    const env = { primarySecret: PRIMARY, fallbackSecret: FALLBACK, nowSeconds: NOW };
    const first = await handleSecureWebhook(req, env, store);
    assert.strictEqual(first.status, 200);
    assert.strictEqual(first.body.ok, true);
    assert.strictEqual(first.body.duplicate, undefined);

    const second = await handleSecureWebhook(req, env, store);
    assert.strictEqual(second.status, 200);
    assert.strictEqual(second.body.duplicate, true);
  });

  // T10: failed auth writes masked DLQ; race insert duplicate
  await atest("T10 DLQ on bad sig + insert race duplicate", async () => {
    const store = createMemoryStore();
    const rawBody = JSON.stringify({
      id: "evt_t10",
      type: "RENEWAL",
      email: "leak@example.com",
      app_user_id: "au_leak",
    });
    const bad = await handleSecureWebhook(
      {
        rawBody,
        headers: {
          "x-revenuecat-signature": "00".repeat(32),
          "x-revenuecat-timestamp": String(NOW),
        },
      },
      { primarySecret: PRIMARY, fallbackSecret: FALLBACK, nowSeconds: NOW },
      store,
    );
    assert.strictEqual(bad.status, 401);
    assert.strictEqual(store.dlq.length, 1);
    assert.strictEqual(store.dlq[0].maskedPayload.email, "[REDACTED]");
    assert.strictEqual(store.dlq[0].maskedPayload.app_user_id, "[REDACTED]");

    // Simulate UNIQUE race: pre-seed then insertEvent returns duplicate
    const okBody = JSON.stringify({ id: "evt_t10b", type: "RENEWAL" });
    const ts = String(NOW);
    const sig = signBody(FALLBACK, okBody, ts);
    store.events.set("evt_t10b", { seeded: true });
    // Force insert path by clearing hasEvent? hasEvent true → duplicate via fast path.
    // Instead override hasEvent false then insert sees existing:
    store.hasEvent = async () => false;
    const raced = await handleSecureWebhook(
      {
        rawBody: okBody,
        headers: {
          "x-revenuecat-signature": sig,
          "x-revenuecat-timestamp": ts,
        },
      },
      { primarySecret: PRIMARY, fallbackSecret: FALLBACK, nowSeconds: NOW },
      store,
    );
    assert.strictEqual(raced.status, 200);
    assert.strictEqual(raced.body.duplicate, true);
  });

  if (process.exitCode) {
    console.error(`\nWebhook suite FAILED (${passed} passed before failure)`);
    process.exit(1);
  }
  console.log(`\nAll webhook vectors passed (${passed})`);
})();
