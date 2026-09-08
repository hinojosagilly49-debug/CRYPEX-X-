/**
 * PIRA — Pan-CDN Intra-video Resource Adaptation (VOD / Shorts only)
 *
 * Model Predictive Control with n=4 look-ahead and γ=0.3 cost weight.
 * Mathematically incompatible with live ingestion (future segments must exist).
 */
"use strict";

const LOOKAHEAD_N = 4;
const GAMMA = 0.3;
const MODES = Object.freeze(["VOD", "SHORTS"]);

/**
 * @param {Array<{ bitrateKbps: number, cdnCostPerMb: number, quality: number }>} segments
 * @param {{ gamma?: number, n?: number, mode?: string }} [opts]
 * @returns {{ schedule: number[], totalCost: number, avgQuality: number, mode: string }}
 */
function planPiraSchedule(segments, opts = {}) {
  const mode = opts.mode || "VOD";
  if (!MODES.includes(mode)) {
    throw new Error(`PIRA MPC is bounded to ${MODES.join("/")} — refused mode=${mode}`);
  }
  if (!Array.isArray(segments) || segments.length === 0) {
    return { schedule: [], totalCost: 0, avgQuality: 0, mode };
  }

  const gamma = opts.gamma ?? GAMMA;
  const n = opts.n ?? LOOKAHEAD_N;
  const schedule = [];
  let totalCost = 0;
  let qualitySum = 0;

  for (let i = 0; i < segments.length; i++) {
    const window = segments.slice(i, Math.min(segments.length, i + n));
    // Score = quality - gamma * normalized_cost; pick best first-hop CDN tier index
    // Each segment may expose candidateTiers[]; default single tier uses itself.
    const candidates = window[0].candidateTiers || [window[0]];
    let bestIdx = 0;
    let bestScore = -Infinity;
    candidates.forEach((tier, idx) => {
      const futureCost =
        window.reduce((s, seg) => s + (seg.cdnCostPerMb || 0) * ((seg.bitrateKbps || 0) / 8000), 0) /
        window.length;
      const score = (tier.quality || 0) - gamma * (tier.cdnCostPerMb || futureCost);
      if (score > bestScore) {
        bestScore = score;
        bestIdx = idx;
      }
    });
    const chosen = candidates[bestIdx];
    schedule.push(bestIdx);
    totalCost += (chosen.cdnCostPerMb || 0) * ((chosen.bitrateKbps || 0) / 8000);
    qualitySum += chosen.quality || 0;
  }

  return {
    schedule,
    totalCost,
    avgQuality: qualitySum / segments.length,
    mode,
    lookahead: n,
    gamma,
  };
}

function assertNotLive(mode) {
  if (String(mode).toUpperCase() === "LIVE") {
    const err = new Error(
      "PIRA MPC requires future media segments in storage; live streams must use WebRTC/LL-HLS edge failover",
    );
    err.code = "PIRA_LIVE_UNSUPPORTED";
    throw err;
  }
}

module.exports = {
  LOOKAHEAD_N,
  GAMMA,
  MODES,
  planPiraSchedule,
  assertNotLive,
};
