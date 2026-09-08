/**
 * Node-compatible port of XTC LIVE secure webhook crypto + handler.
 * Mirrors supabase/functions/XTC_LIVE_Secure_Webhook_Edge_Function.ts
 * for CI vector tests without a Deno runtime.
 */
"use strict";

const crypto = require("crypto");

const MAX_SKEW_SECONDS = 300;
const PRIMARY_SECRET_ENV = "REVENUECAT_WEBHOOK_SIGNING_SECRET";
const FALLBACK_SECRET_ENV = "REVENUECAT_WEBHOOK_SIGNING_SECRET_OLD";

function timingSafeEqual(a, b) {
  if (!Buffer.isBuffer(a)) a = Buffer.from(a);
  if (!Buffer.isBuffer(b)) b = Buffer.from(b);
  if (a.length !== b.length) {
    // Consume time roughly proportional to max length
    const dummy = Buffer.alloc(Math.max(a.length, b.length));
    crypto.timingSafeEqual(dummy, dummy);
    return false;
  }
  return crypto.timingSafeEqual(a, b);
}

function hmacSha256Hex(secret, message) {
  return crypto.createHmac("sha256", secret).update(message, "utf8").digest("hex");
}

function verifyWebhookSignature({
  rawBody,
  signatureHeader,
  timestampHeader,
  primarySecret,
  fallbackSecret,
  nowSeconds = Math.floor(Date.now() / 1000),
  maxSkewSeconds = MAX_SKEW_SECONDS,
}) {
  if (!signatureHeader || !timestampHeader) {
    return { ok: false, code: "missing_signature" };
  }
  const ts = Number(timestampHeader);
  if (!Number.isFinite(ts)) {
    return { ok: false, code: "bad_timestamp" };
  }
  if (Math.abs(nowSeconds - ts) > maxSkewSeconds) {
    return { ok: false, code: "replay", detail: `skew>${maxSkewSeconds}s` };
  }

  const provided = String(signatureHeader).replace(/^sha256=/i, "").trim();
  if (!/^[0-9a-fA-F]+$/.test(provided) || provided.length % 2 !== 0) {
    return { ok: false, code: "bad_signature" };
  }
  const providedBuf = Buffer.from(provided, "hex");
  const message = `${ts}.${rawBody}`;

  const secrets = [];
  if (primarySecret) secrets.push({ kid: "primary", value: primarySecret });
  if (fallbackSecret) secrets.push({ kid: "fallback", value: fallbackSecret });

  for (const s of secrets) {
    const expected = hmacSha256Hex(s.value, message);
    if (timingSafeEqual(providedBuf, Buffer.from(expected, "hex"))) {
      return { ok: true, kid: s.kid };
    }
  }
  return { ok: false, code: "bad_signature" };
}

function maskPii(payload) {
  const SENSITIVE = new Set([
    "email",
    "phone",
    "subscriber_id",
    "app_user_id",
    "original_app_user_id",
    "ip",
    "card_last_four",
  ]);
  const walk = (v) => {
    if (Array.isArray(v)) return v.map(walk);
    if (v && typeof v === "object") {
      const out = {};
      for (const [k, val] of Object.entries(v)) {
        if (SENSITIVE.has(k.toLowerCase())) {
          out[k] = typeof val === "string" && val.length > 0 ? "[REDACTED]" : null;
        } else {
          out[k] = walk(val);
        }
      }
      return out;
    }
    return v;
  };
  return walk(payload);
}

function signBody(secret, rawBody, ts) {
  return hmacSha256Hex(secret, `${ts}.${rawBody}`);
}

async function handleSecureWebhook(req, env, store) {
  const headers = {};
  for (const [k, v] of Object.entries(req.headers || {})) {
    headers[k.toLowerCase()] = v;
  }
  const signature =
    headers["x-revenuecat-signature"] || headers["x-signature"] || headers["authorization"];
  const timestamp = headers["x-revenuecat-timestamp"] || headers["x-timestamp"];

  const verified = verifyWebhookSignature({
    rawBody: req.rawBody,
    signatureHeader: signature,
    timestampHeader: timestamp,
    primarySecret: env.primarySecret,
    fallbackSecret: env.fallbackSecret,
    nowSeconds: env.nowSeconds,
  });

  if (!verified.ok) {
    let payload = {};
    try {
      payload = JSON.parse(req.rawBody);
    } catch {
      payload = { raw: "unparseable" };
    }
    await store.insertDlq({
      eventId: typeof payload.id === "string" ? payload.id : undefined,
      maskedPayload: maskPii(payload),
      reason: verified.code,
    });
    return { status: 401, body: { ok: false, error: verified.code } };
  }

  let body;
  try {
    body = JSON.parse(req.rawBody);
  } catch {
    await store.insertDlq({ maskedPayload: { raw: "unparseable" }, reason: "invalid_json" });
    return { status: 400, body: { ok: false, error: "invalid_json" } };
  }

  const eventId = String(body.id ?? body.event_id ?? "");
  if (!eventId) {
    return { status: 400, body: { ok: false, error: "missing_event_id" } };
  }

  if (await store.hasEvent(eventId)) {
    return { status: 200, body: { ok: true, duplicate: true } };
  }

  const result = await store.insertEvent({
    eventId,
    payload: body,
    kid: verified.kid,
    status: "received",
  });

  // UNIQUE / logical 409 → HTTP 200 OK
  if (result === "duplicate") {
    return { status: 200, body: { ok: true, duplicate: true } };
  }

  return { status: 200, body: { ok: true, event_id: eventId, kid: verified.kid } };
}

function createMemoryStore() {
  const events = new Map();
  const dlq = [];
  return {
    events,
    dlq,
    async hasEvent(id) {
      return events.has(id);
    },
    async insertEvent(row) {
      if (events.has(row.eventId)) return "duplicate";
      events.set(row.eventId, row);
      return "inserted";
    },
    async insertDlq(row) {
      dlq.push(row);
    },
  };
}

module.exports = {
  MAX_SKEW_SECONDS,
  PRIMARY_SECRET_ENV,
  FALLBACK_SECRET_ENV,
  timingSafeEqual,
  verifyWebhookSignature,
  maskPii,
  signBody,
  handleSecureWebhook,
  createMemoryStore,
  hmacSha256Hex,
};
