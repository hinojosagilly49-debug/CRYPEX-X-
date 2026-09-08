/**
 * XTC LIVE Secure Webhook Edge Function (V13-RC2)
 *
 * Controls:
 *  - Constant-time HMAC-SHA256 verification (raw body)
 *  - Zero-downtime key rotation via REVENUECAT_WEBHOOK_SIGNING_SECRET_OLD
 *  - 300-second timestamp drift / replay protection
 *  - Idempotent event_id handling (duplicate → HTTP 200)
 *  - Deterministic PII masking before DLQ insert
 */

export const MAX_SKEW_SECONDS = 300;
export const PRIMARY_SECRET_ENV = "REVENUECAT_WEBHOOK_SIGNING_SECRET";
export const FALLBACK_SECRET_ENV = "REVENUECAT_WEBHOOK_SIGNING_SECRET_OLD";

export type VerifyResult =
  | { ok: true; kid: "primary" | "fallback" }
  | { ok: false; code: "missing_signature" | "bad_signature" | "replay" | "bad_timestamp"; detail?: string };

export type HandleResult = {
  status: number;
  body: Record<string, unknown>;
};

/** Constant-time compare for equal-length byte arrays. */
export function timingSafeEqual(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== b.length) {
    // Still walk to reduce short-circuit signal on length.
    let diff = a.length ^ b.length;
    const len = Math.max(a.length, b.length);
    for (let i = 0; i < len; i++) {
      const av = i < a.length ? a[i] : 0;
      const bv = i < b.length ? b[i] : 0;
      diff |= av ^ bv;
    }
    return false;
  }
  let out = 0;
  for (let i = 0; i < a.length; i++) out |= a[i] ^ b[i];
  return out === 0;
}

function hexToBytes(hex: string): Uint8Array | null {
  if (!/^[0-9a-fA-F]+$/.test(hex) || hex.length % 2 !== 0) return null;
  const out = new Uint8Array(hex.length / 2);
  for (let i = 0; i < out.length; i++) {
    out[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16);
  }
  return out;
}

async function hmacSha256Hex(secret: string, message: string): Promise<string> {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(message));
  return [...new Uint8Array(sig)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/**
 * Verify Authorization / X-Signature header against primary then fallback secret.
 * Signature payload format: `${timestamp}.${rawBody}`
 */
export async function verifyWebhookSignature(opts: {
  rawBody: string;
  signatureHeader: string | null | undefined;
  timestampHeader: string | null | undefined;
  primarySecret: string | null | undefined;
  fallbackSecret?: string | null | undefined;
  nowSeconds?: number;
  maxSkewSeconds?: number;
}): Promise<VerifyResult> {
  const {
    rawBody,
    signatureHeader,
    timestampHeader,
    primarySecret,
    fallbackSecret,
    nowSeconds = Math.floor(Date.now() / 1000),
    maxSkewSeconds = MAX_SKEW_SECONDS,
  } = opts;

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

  const provided = signatureHeader.replace(/^sha256=/i, "").trim();
  const providedBytes = hexToBytes(provided);
  if (!providedBytes) {
    return { ok: false, code: "bad_signature" };
  }

  const message = `${ts}.${rawBody}`;
  const secrets: Array<{ kid: "primary" | "fallback"; value: string }> = [];
  if (primarySecret) secrets.push({ kid: "primary", value: primarySecret });
  // Zero-downtime rotation: keep OLD secret valid ≥24h during rotation windows
  if (fallbackSecret) secrets.push({ kid: "fallback", value: fallbackSecret });

  for (const s of secrets) {
    const expectedHex = await hmacSha256Hex(s.value, message);
    const expectedBytes = hexToBytes(expectedHex)!;
    if (timingSafeEqual(providedBytes, expectedBytes)) {
      return { ok: true, kid: s.kid };
    }
  }
  return { ok: false, code: "bad_signature" };
}

/** Deterministic PII masking for DLQ payloads. */
export function maskPii(payload: Record<string, unknown>): Record<string, unknown> {
  const SENSITIVE = new Set([
    "email",
    "phone",
    "subscriber_id",
    "app_user_id",
    "original_app_user_id",
    "ip",
    "card_last_four",
  ]);

  const walk = (v: unknown): unknown => {
    if (Array.isArray(v)) return v.map(walk);
    if (v && typeof v === "object") {
      const out: Record<string, unknown> = {};
      for (const [k, val] of Object.entries(v as Record<string, unknown>)) {
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

  return walk(payload) as Record<string, unknown>;
}

export interface WebhookStore {
  hasEvent(eventId: string): Promise<boolean>;
  insertEvent(row: {
    eventId: string;
    payload: Record<string, unknown>;
    kid: string;
    status: string;
  }): Promise<"inserted" | "duplicate">;
  insertDlq(row: {
    eventId?: string;
    maskedPayload: Record<string, unknown>;
    reason: string;
  }): Promise<void>;
}

/**
 * Full request handler used by Deno edge runtime and unit tests.
 * Duplicate DB constraint (logical 409) is translated to HTTP 200 OK.
 */
export async function handleSecureWebhook(
  req: {
    rawBody: string;
    headers: Record<string, string | undefined>;
  },
  env: {
    primarySecret?: string;
    fallbackSecret?: string;
    nowSeconds?: number;
  },
  store: WebhookStore,
): Promise<HandleResult> {
  const signature =
    req.headers["x-revenuecat-signature"] ??
    req.headers["x-signature"] ??
    req.headers["authorization"];
  const timestamp = req.headers["x-revenuecat-timestamp"] ?? req.headers["x-timestamp"];

  const verified = await verifyWebhookSignature({
    rawBody: req.rawBody,
    signatureHeader: signature,
    timestampHeader: timestamp,
    primarySecret: env.primarySecret,
    fallbackSecret: env.fallbackSecret,
    nowSeconds: env.nowSeconds,
  });

  if (!verified.ok) {
    let payload: Record<string, unknown> = {};
    try {
      payload = JSON.parse(req.rawBody);
    } catch {
      payload = { raw: "unparseable" };
    }
    await store.insertDlq({
      eventId: typeof payload["id"] === "string" ? payload["id"] : undefined,
      maskedPayload: maskPii(payload),
      reason: verified.code,
    });
    const status = verified.code === "replay" ? 401 : 401;
    return { status, body: { ok: false, error: verified.code } };
  }

  let body: Record<string, unknown>;
  try {
    body = JSON.parse(req.rawBody);
  } catch {
    await store.insertDlq({
      maskedPayload: { raw: "unparseable" },
      reason: "invalid_json",
    });
    return { status: 400, body: { ok: false, error: "invalid_json" } };
  }

  const eventId = String(body["id"] ?? body["event_id"] ?? "");
  if (!eventId) {
    return { status: 400, body: { ok: false, error: "missing_event_id" } };
  }

  // Fast-path idempotency
  if (await store.hasEvent(eventId)) {
    return { status: 200, body: { ok: true, duplicate: true } };
  }

  const result = await store.insertEvent({
    eventId,
    payload: body,
    kid: verified.kid,
    status: "received",
  });

  // UNIQUE violation / race → treat as success (HTTP 409 → 200)
  if (result === "duplicate") {
    return { status: 200, body: { ok: true, duplicate: true } };
  }

  return {
    status: 200,
    body: { ok: true, event_id: eventId, kid: verified.kid },
  };
}

/** Deno.serve entry (no-op import guard for Node test harness). */
export async function denoHandler(request: Request): Promise<Response> {
  const rawBody = await request.text();
  const headers: Record<string, string | undefined> = {};
  request.headers.forEach((v, k) => {
    headers[k.toLowerCase()] = v;
  });

  // Minimal in-memory store is replaced by Postgres bindings in production.
  const memory = new Map<string, true>();
  const store: WebhookStore = {
    async hasEvent(id) {
      return memory.has(id);
    },
    async insertEvent(row) {
      if (memory.has(row.eventId)) return "duplicate";
      memory.set(row.eventId, true);
      return "inserted";
    },
    async insertDlq() {
      /* production: insert masked row into webhook_dlq */
    },
  };

  const result = await handleSecureWebhook(
    { rawBody, headers },
    {
      primarySecret: Deno.env.get(PRIMARY_SECRET_ENV) ?? undefined,
      fallbackSecret: Deno.env.get(FALLBACK_SECRET_ENV) ?? undefined,
    },
    store,
  );

  return new Response(JSON.stringify(result.body), {
    status: result.status,
    headers: { "content-type": "application/json" },
  });
}

// Deno global optional
declare const Deno: { env: { get(name: string): string | undefined }; serve?: unknown };
