# SKUs and Pricing Principles (2026 Vertical SaaS)

## Packaging principle

Sell **governed decisioning and auditability** for one metals desk. Do **not** meter primarily on LLM tokens.

## SKUs

| SKU | Code | Description | Pilot default |
|-----|------|-------------|---------------|
| Desk seat | `SKU-DESK` | Pipeline access, envelope ingest, hold queue UI | 5 seats |
| Connector pack (395) | `SKU-395` | Enterprise sync, 30-min window, SARC-DQ quarantine/substitute | Required |
| Restricted-model route | `SKU-RMR` | `kem_analysis` → restricted context → secure model | Required |
| Audit log export | `SKU-AUD` | Hop-log + quarantine/substitution export | Required |
| Local freight path | `SKU-LOC` | `local` intent → on-prem/local Llama path | Recommended |

## Pricing anchors (guidance)

| Component | Anchor | Notes |
|-----------|--------|-------|
| Pilot | Fixed fee | 30–60 days; hop-log SLA acceptance |
| Production desk | Per desk / month | Includes baseline seats + 395 + audit |
| Extra seats | Per seat / month | Marginal |
| Restricted route | Included or capacity tier | By restricted RFQ volume bands if needed—not raw tokens |
| Audit retention add-on | Per retention year | Triggers crypto/PQC review at multi-year |

## What we do not sell on

- Raw token consumption as the primary SKU  
- Unbounded autonomous execution  
- “Post-quantum complete” as a day-one checkbox without retention-driven need  

## Expansion path

1. Land metals desk wedge  
2. Compliance reference (immutable origin + holds)  
3. Add SKUs only after hop-log acceptance stays green  
