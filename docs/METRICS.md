# Metrics Framework: Contract Intelligence Platform

**Last Updated:** January 2025

---

## 1. North Star Metric

**Contracts accurately reviewed per deal-day**

This metric captures the core value proposition: how many contracts can a deal team process accurately in a single day using the platform. It combines speed (throughput) with quality (accuracy) and is directly tied to the business outcome our users care about - faster, better deal execution.

**Baseline (manual process):** 3-5 contracts per associate per day
**Target (with platform):** 50-80 contracts per deal-day (AI processing + human review)
**Current:** 62 contracts per deal-day (averaged across last 10 deals)

---

## 2. Input Metrics

These are the levers we can pull to improve the North Star.

### 2.1 Extraction Quality

| Metric | Definition | Target | Current | Measurement |
|---|---|---|---|---|
| Clause extraction F1 score | Harmonic mean of precision and recall on clause identification | > 0.93 | 0.94 | Quarterly validation against 50 human-reviewed contracts |
| Risk flag recall | Percentage of actual risk items caught by AI | > 95% | 97% | QA review of completed deals (partner spot-check) |
| Confidence calibration | Correlation between confidence score and actual accuracy | > 0.85 r-squared | 0.88 | Monthly analysis of override rate vs. confidence bands |
| Hallucination rate | Percentage of extractions with no corresponding source text | < 1% | 0.6% | Random sample audit (n=100 clauses per month) |

### 2.2 Processing Speed

| Metric | Definition | Target | Current | Measurement |
|---|---|---|---|---|
| Single document processing time (native PDF) | Upload to extraction complete | < 90 seconds | 72 seconds (p50) | Platform telemetry |
| Single document processing time (scanned PDF) | Upload to extraction complete (including OCR) | < 180 seconds | 145 seconds (p50) | Platform telemetry |
| Batch processing time (200 docs) | First upload to last extraction complete | < 4 hours | 3.1 hours | Platform telemetry |
| Search query latency (p95) | Time from query submission to results displayed | < 2 seconds | 1.4 seconds | Platform telemetry |
| Export generation time (Excel matrix) | Request to download-ready | < 60 seconds | 42 seconds (p50) | Platform telemetry |

### 2.3 Review Efficiency

| Metric | Definition | Target | Current | Measurement |
|---|---|---|---|---|
| Auto-accept rate | Percentage of clauses auto-accepted (confidence >= threshold) | 75-85% | 81% | Platform data |
| Human override rate | Percentage of AI extractions corrected by reviewers | < 15% | 8.3% | Platform data |
| Review velocity | Clauses reviewed per associate per hour | > 60 | 74 | Time tracking + review actions |
| Escalation rate | Percentage of clauses escalated to partner | < 5% | 3.1% | Platform data |
| Time-to-review | Hours from extraction complete to review complete | < 16 hours | 11.2 hours | Platform timestamps |

### 2.4 Adoption

| Metric | Definition | Target | Current | Measurement |
|---|---|---|---|---|
| Deal team adoption | Percentage of active deal teams using the platform | > 80% | 85% | Monthly active deal teams / total deal teams |
| Feature utilization | Percentage of users using search (not just review) | > 50% | 58% | Feature usage analytics |
| Export utilization | Exports generated per deal | >= 3 | 4.2 | Platform data |
| Return usage | Percentage of associates who use platform on 2+ deals | > 70% | 78% | User cohort analysis |

---

## 3. Guardrail Metrics

These metrics should NOT degrade as we optimize for the North Star. If they move in the wrong direction, we pause and investigate.

| Metric | Acceptable Range | Alert Threshold | Why It Matters |
|---|---|---|---|
| Partner override rate | < 5% | > 8% | If partners are frequently overriding associate-approved extractions, quality is slipping |
| Post-delivery corrections | < 2 per deal | > 5 per deal | Client-facing deliverables should not need corrections after delivery |
| AI API error rate | < 2% | > 5% | LLM API failures degrade user experience and slow processing |
| System uptime | > 99.5% | < 99% | Downtime during active deals is unacceptable |
| Audit log completeness | 100% | < 100% | Every action must be logged for compliance. Zero tolerance for gaps. |
| PII leakage rate | 0% | > 0% | Any PII reaching external APIs is a compliance failure. Zero tolerance. |
| Cross-tenant data exposure | 0% | > 0% | RLS failure. Zero tolerance. Automated tests run daily. |

---

## 4. Business Impact Metrics

### 4.1 Cost Reduction

| Metric | Before Platform | After Platform | Improvement |
|---|---|---|---|
| Associate hours per deal (contract review) | 120-160 hours | 15-20 hours | 85-88% reduction |
| Cost per transaction (contract review) | $150K-$300K | $15K-$30K | 90% reduction |
| Annual contract review labor cost (15 deals/year) | $2.25M-$4.5M | $225K-$450K | $2M-$4M annual savings |

### 4.2 Speed Improvement

| Metric | Before Platform | After Platform | Improvement |
|---|---|---|---|
| Contract review timeline per deal | 3-4 weeks | 2-3 days | 85-90% faster |
| Time to first risk flag | Days (after initial reading) | Minutes (after upload) | Near-instant |
| Deliverable generation | 2-3 days (manual Excel) | < 1 hour (automated) | 95% faster |

### 4.3 Quality Improvement

| Metric | Before Platform | After Platform | Improvement |
|---|---|---|---|
| Clause extraction error rate | 12-18% (manual) | 2.4% (AI + human review) | 80-87% fewer errors |
| Risk flags missed | ~30% (fatigue-driven) | ~3% (97% recall) | 90% improvement in coverage |
| Cross-deal consistency | Low (varies by associate) | High (playbook-enforced) | Standardized output |

---

## 5. Metric Relationships

```
                    ┌─────────────────────────┐
                    │     NORTH STAR           │
                    │  Contracts accurately    │
                    │  reviewed per deal-day   │
                    └────────────┬────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
    ┌──────────────────┐ ┌─────────────┐ ┌──────────────────┐
    │ Extraction       │ │ Processing  │ │ Review           │
    │ Quality          │ │ Speed       │ │ Efficiency       │
    │                  │ │             │ │                  │
    │ F1 score         │ │ Doc process │ │ Auto-accept rate │
    │ Risk recall      │ │ time        │ │ Override rate    │
    │ Hallucination    │ │ Batch time  │ │ Review velocity  │
    │ rate             │ │ Search      │ │ Escalation rate  │
    │                  │ │ latency     │ │                  │
    └────────┬─────────┘ └──────┬──────┘ └────────┬─────────┘
             │                  │                  │
             └──────────────────┼──────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │    GUARDRAILS         │
                    │                       │
                    │ Partner override rate  │
                    │ Post-delivery fixes    │
                    │ PII leakage = 0%      │
                    │ Audit completeness    │
                    │ System uptime         │
                    └───────────────────────┘
```

---

## 6. Measurement Cadence

| Frequency | Metrics Reviewed | Forum |
|---|---|---|
| **Real-time** | System uptime, API error rate, PII leakage, processing status | Automated dashboards + alerts (PagerDuty) |
| **Daily** | Processing volume, review queue depth, export count | Team standup dashboard |
| **Weekly** | Auto-accept rate, override rate, review velocity, search usage | Product team review |
| **Monthly** | Confidence calibration, feature utilization, adoption metrics, cost per deal | Product + leadership review |
| **Quarterly** | F1 score validation (vs. human-reviewed sample), business impact metrics, competitive benchmarking | Executive review |

---

## 7. Experiments and Learning

### Completed Experiments

| Experiment | Hypothesis | Result | Decision |
|---|---|---|---|
| Confidence threshold 0.90 vs. 0.85 | Lowering threshold from 0.90 to 0.85 will reduce human review volume without significantly increasing errors | Auto-accept rate increased from 68% to 81%. Error rate increased from 1.1% to 2.4%. | Adopted 0.85. Error rate acceptable per client feedback. |
| Hybrid search vs. vector-only | Adding BM25 to vector search will improve retrieval accuracy for legal terms | Accuracy improved from 72% to 91%. Associates reported finding exact provisions faster. | Adopted hybrid search. |
| Clause-level vs. page-level chunking | Clause-level chunking will improve search precision | Search precision improved 34%. Users clicked on first result 2.3x more often. | Adopted clause-level chunking. |
| Batch embedding (32/request) vs. single | Batching embedding API calls will reduce processing time | Batch processing time reduced 40% for large deals. No accuracy impact. | Adopted batch processing. |

### Active Experiments

| Experiment | Hypothesis | Status | Expected Completion |
|---|---|---|---|
| Cross-encoder reranking (Cohere vs. custom) | Custom cross-encoder fine-tuned on legal queries will outperform Cohere generic | Running on 20% of search traffic | February 2025 |
| Confidence calibration via temperature scaling | Post-hoc temperature scaling will improve confidence-accuracy correlation | Validation in progress | February 2025 |
