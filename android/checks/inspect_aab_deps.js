#!/usr/bin/env node
/**
 * Android App Bundle dependency inspection fixture.
 * Fails (exit 1) if Stripe SDK packages appear in the dependency list.
 * Unexpected extra args → exit 2 (file injection rejection semantics).
 */
"use strict";

const path = require("path");
const fs = require("fs");
const { inspectAndroidDependencies } = require(
  path.join(__dirname, "..", "..", "src", "xtc-live", "billing"),
);

if (process.argv.length > 3) {
  console.error("unexpected file injection / args");
  process.exit(2);
}

const fixturePath =
  process.argv[2] || path.join(__dirname, "fixtures", "aab_deps.json");

let packages = [
  "com.revenuecat.purchases",
  "com.android.billingclient",
  "androidx.media3.exoplayer",
];

if (fs.existsSync(fixturePath)) {
  packages = JSON.parse(fs.readFileSync(fixturePath, "utf8")).packages || packages;
}

const result = inspectAndroidDependencies(packages);
if (!result.ok) {
  console.error("Stripe SDK packages present in AAB dependency set:", result.forbiddenHits);
  process.exit(1);
}
console.log("AAB zero-Stripe check OK (Google Play Billing via RevenueCat only)");
