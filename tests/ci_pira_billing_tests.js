#!/usr/bin/env node
"use strict";

const assert = require("assert");
const path = require("path");
const fs = require("fs");

const { planPiraSchedule, assertNotLive, LOOKAHEAD_N, GAMMA } = require(
  path.join(__dirname, "..", "src", "xtc-live", "pira"),
);
const {
  resolveBillingProvider,
  parseDeepLink,
  inspectAndroidDependencies,
  SURFACES,
} = require(path.join(__dirname, "..", "src", "xtc-live", "billing"));

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

console.log("XTC LIVE PIRA + billing vectors");

test("PIRA defaults n=4 γ=0.3", () => {
  assert.strictEqual(LOOKAHEAD_N, 4);
  assert.strictEqual(GAMMA, 0.3);
});

test("PIRA VOD schedule produces finite cost", () => {
  const segs = [
    { bitrateKbps: 2500, cdnCostPerMb: 0.02, quality: 0.8 },
    { bitrateKbps: 1500, cdnCostPerMb: 0.01, quality: 0.6, candidateTiers: [
      { bitrateKbps: 1500, cdnCostPerMb: 0.01, quality: 0.6 },
      { bitrateKbps: 800, cdnCostPerMb: 0.005, quality: 0.4 },
    ]},
  ];
  const plan = planPiraSchedule(segs, { mode: "VOD" });
  assert.strictEqual(plan.mode, "VOD");
  assert.ok(plan.schedule.length === 2);
  assert.ok(Number.isFinite(plan.totalCost));
});

test("PIRA refuses LIVE mode", () => {
  assert.throws(() => planPiraSchedule([{ bitrateKbps: 1, cdnCostPerMb: 1, quality: 1 }], { mode: "LIVE" }));
  assert.throws(() => assertNotLive("LIVE"));
});

test("Billing seam web→stripe android→play", () => {
  assert.strictEqual(resolveBillingProvider("web"), SURFACES.WEB);
  assert.strictEqual(resolveBillingProvider("android"), SURFACES.ANDROID);
});

test("Meta Edits deep link xtc://edit", () => {
  const r = parseDeepLink("xtc://edit?clip=42");
  assert.strictEqual(r.ok, true);
  assert.strictEqual(r.intent, "meta_edits");
  assert.strictEqual(r.params.clip, "42");
});

test("AAB zero-Stripe inspection", () => {
  const clean = inspectAndroidDependencies([
    "com.revenuecat.purchases",
    "com.android.billingclient",
  ]);
  assert.strictEqual(clean.ok, true);
  const dirty = inspectAndroidDependencies(["com.stripe.android"]);
  assert.strictEqual(dirty.ok, false);
});

test("dist/ build-info exists after build or skip", () => {
  const p = path.join(__dirname, "..", "dist", "build-info.json");
  if (fs.existsSync(p)) {
    const info = JSON.parse(fs.readFileSync(p, "utf8"));
    assert.strictEqual(info.product, "XTC-LIVE");
  }
});

if (process.exitCode) {
  console.error("\nPIRA/billing suite FAILED");
  process.exit(1);
}
console.log(`\nAll PIRA/billing vectors passed (${passed})`);
