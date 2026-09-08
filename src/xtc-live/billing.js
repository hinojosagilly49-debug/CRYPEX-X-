/**
 * Dual-billing monetization seam (V13-RC2)
 *  - Web: Stripe
 *  - Android: Google Play Billing 9.0.0 via RevenueCat (zero Stripe SDK on device)
 */
"use strict";

const SURFACES = Object.freeze({
  WEB: "stripe",
  ANDROID: "google_play_revenuecat",
});

/**
 * Route a purchase intent to the correct billing provider.
 * Android path must never load Stripe.
 */
function resolveBillingProvider(surface) {
  const key = String(surface || "").toLowerCase();
  if (key === "web" || key === "stripe") return SURFACES.WEB;
  if (key === "android" || key === "play" || key === "google_play") return SURFACES.ANDROID;
  throw new Error(`Unknown billing surface: ${surface}`);
}

/**
 * Meta Edits deep-link intent routing: xtc://edit
 */
function parseDeepLink(url) {
  const raw = String(url || "");
  if (!raw.startsWith("xtc://")) {
    return { ok: false, error: "unsupported_scheme" };
  }
  try {
    const u = new URL(raw);
    const host = u.host || u.hostname;
    if (host === "edit") {
      return {
        ok: true,
        intent: "meta_edits",
        path: u.pathname || "/",
        params: Object.fromEntries(u.searchParams.entries()),
      };
    }
    return { ok: false, error: "unknown_host", host };
  } catch {
    return { ok: false, error: "malformed" };
  }
}

/**
 * Static allow-list of Android app dependencies for AAB binary inspection.
 * Stripe packages must be absent.
 */
const ANDROID_FORBIDDEN_PACKAGES = Object.freeze([
  "com.stripe.android",
  "com.stripe.stripeterminal",
  "stripe-android",
]);

function inspectAndroidDependencies(packageList) {
  const list = Array.isArray(packageList) ? packageList : [];
  const hits = list.filter((p) =>
    ANDROID_FORBIDDEN_PACKAGES.some((f) => String(p).toLowerCase().includes(f.toLowerCase())),
  );
  return {
    ok: hits.length === 0,
    forbiddenHits: hits,
    billing: SURFACES.ANDROID,
  };
}

module.exports = {
  SURFACES,
  resolveBillingProvider,
  parseDeepLink,
  ANDROID_FORBIDDEN_PACKAGES,
  inspectAndroidDependencies,
};
