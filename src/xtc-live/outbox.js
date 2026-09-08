/**
 * Logical model of outbox claim semantics (FOR UPDATE SKIP LOCKED).
 * Used in CI to document concurrency limits without a live Postgres.
 */
"use strict";

function claimBatch(rows, workerId, batchSize = 50, now = Date.now()) {
  const claimed = [];
  for (const row of rows) {
    if (claimed.length >= batchSize) break;
    if (row.publishedAt) continue;
    if (row.availableAt && row.availableAt > now) continue;
    if (row.lockedAt && now - row.lockedAt < 5 * 60 * 1000) continue;
    row.lockedAt = now;
    row.lockedBy = workerId;
    row.attempts = (row.attempts || 0) + 1;
    claimed.push(row);
  }
  return claimed;
}

module.exports = { claimBatch };
