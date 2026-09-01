# Hop-Log Replay — Demo Script (Sales Engineering)

**Audience:** Desk lead + risk/compliance  
**Duration:** ~20 minutes  
**Goal:** Show master-record audit behaviors live; no platform tour.

---

## Setup (2 min)

- Open Pipeline on the metals desk view.
- Confirm demo fixtures loaded (`tests/fixtures/hop_logs.json`).
- State the rule: **PreFlect hold-to-execute is the supported path.**

---

## Scene 1 — Stale Al 3105 ticker (5 min)

**Intent:** `enterprise_sync` → **395-connector**

1. Submit Al 3105 RFQ carrying LME print **$2,412/mt** outside the 30-minute window.  
2. Show hop: connector **quarantines** stale print.  
3. Show agent view: governed substitute **$2,286/mt**.  
4. Show origin record: **immutable** (source hash unchanged).  
5. Compliance line: “Downstream-only SARC-DQ — we never rewrite the tape.”

**Pass cues:** A1–A4.

---

## Scene 2 — NMC 811 / Cu cathode restricted analysis (5 min)

**Intent:** `kem_analysis` → **agent-gpt-4o-secure**

1. Submit cathode RFQ.  
2. Show envelope: `security_context.classification = restricted`.  
3. Show router: `dispatch_to_model → agent-gpt-4o-secure`.  
4. Point at versioned `alg_id` / `key_id` (crypto agility — no deep PQC detour).  

**Pass cues:** A5.

---

## Scene 3 — PreFlect blocks incomplete trade (5 min)

1. Attempt execute **without Incoterms** → **HOLD**.  
2. Attempt execute **without payment escrow** → **HOLD**.  
3. Complete constraints → hold clears with reason-coded human action.  
4. Emphasize: **no silent execute.**

**Pass cues:** A6–A7.

---

## Scene 4 — Freight stays local (3 min)

**Intent:** `local` → **llama-3-8b-instruct**

1. Submit SHA–RTM freight RFQ.  
2. Show path never leaves local engine (data residency companion control).  

**Pass cues:** A8.

---

## Close (2 min)

- Recap SKUs: desk seat + 395 pack + restricted route + audit export.  
- Pricing frame: governed decisioning / auditability.  
- CTA: pilot SOW + fixed fee; hop-log SLA = acceptance.  
- Explicit non-promise: autonomous settle not in pilot scope.  
