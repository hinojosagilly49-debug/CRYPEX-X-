# CRYPEX-X- Metals Desk — One-Pager (2026)

## Wedge

**Governed metals RFQ desk** for Al / Cu / NMC-style cathode, with freight on a local-path companion. One desk workflow—not a horizontal AI platform.

## Who buys

| Role | Why they care |
|------|----------------|
| Trading desk lead | Fresh governed prices inside the 30-minute desk window; no stale ticker bleed into agent view |
| Risk / compliance | Immutable origin prints, quarantine + substitute audit trail, no silent execute without Incoterms/escrow |

## What ships

**GENIUS+ Pipeline** with **Cryptex X+** as stage-4 orchestration:

`ingest → RAG context → LLM → PreFlect / SARC-DQ → action → learning`

Every RFQ is a Cryptex envelope (`$meta.artifact_id`, versioned `security_context`). The router selects the engine by intent.

| RFQ | Intent | Engine |
|-----|--------|--------|
| Al 3105 (stale ticker) | `enterprise_sync` | 395-connector |
| NMC 811 / Cu cathode | `kem_analysis` | `agent-gpt-4o-secure` |
| SHA–RTM freight | `local` | `llama-3-8b-instruct` |

## Proof (master-record audit)

1. **395-connector** — 30-minute desk window; four invariants; quarantines stale **$2,412/mt** LME print; substitutes governed **$2,286/mt** buffer; **origin immutable**.
2. **Cryptex routing** — `kem_analysis` wrapped in **restricted** `security_context` → `agent-gpt-4o-secure`.
3. **PreFlect** — holds execution when Incoterms or payment escrow are missing (**no silent execute**).

**Supported pilot path:** PreFlect **hold-to-execute**. Fully autonomous settle is out of scope until action→learning is contractually defined.

## Commercial motion

1. 2–3 design-partner desks  
2. Fixed pilot (windowed RFQ + hop-log SLA)  
3. Compliance reference story  
4. Expand SKUs  

## SKUs (summary)

| SKU | Includes |
|-----|----------|
| Desk seat | Pipeline UI + envelope ingest |
| Connector pack (395) | Enterprise sync + SARC-DQ quarantine/substitute |
| Restricted-model route | `kem_analysis` → secure model dispatch |
| Audit log export | Hop-log + quarantine/substitution trail |

**Price against governed decisioning and auditability—not token volume.**

## 90-day outline

| Window | Outcome |
|--------|---------|
| Days 0–30 | One-pager, pilot SOW, demo script, `security_context` versioning |
| Days 30–60 | 1–2 design-partner pilots; catalog egress artifacts |
| Days 60–90 | Case study; hybrid-PQC only where retention/HNDL requires |

## Contact / pilot

See [pilot-sow.md](./pilot-sow.md) and [pilot-runbook.md](./pilot-runbook.md).
