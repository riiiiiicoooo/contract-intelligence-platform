# Product Roadmap: Contract Intelligence Platform

**Last Updated:** January 2025

---

## Roadmap Overview

```
Phase 0: MVP          Phase 1: Deal-Ready     Phase 2: Scale         Phase 3: Intelligence
(Weeks 1-8)           (Weeks 9-16)            (Weeks 17-24)          (Weeks 25+)
                                                                      
Prove extraction      Support full deal       Multi-tenant at        Advanced analytics
accuracy on real      workflow end-to-end     scale across teams     and institutional
contracts                                                            learning
                                                                      
├─ Single doc upload  ├─ Batch upload (200+)  ├─ Multi-tenant RLS    ├─ Clause library
├─ 15 clause types    ├─ 40+ clause types     ├─ SSO integration     ├─ Portfolio analytics
├─ Basic risk scoring ├─ Split-pane review    ├─ Configurable        ├─ Saved searches
├─ Simple review UI   ├─ Risk explanations    │  templates           ├─ Integration APIs
├─ Excel export       ├─ PPT + PDF export     ├─ Cross-doc analysis  ├─ Custom report
└─ Basic audit log    ├─ Semantic search      ├─ Bulk review actions │  builder
                      ├─ Partner escalation   ├─ Keyboard shortcuts  └─ Institutional
                      └─ Human-in-the-loop    └─ SOC 2 prep            memory
```

---

## Phase 0: MVP (Weeks 1-8)

**Goal:** Prove core extraction accuracy on real deal contracts.

**Theme:** Can the AI extract clauses accurately enough that associates trust it?

| Week | Deliverable | Details |
|---|---|---|
| 1-2 | Document ingestion pipeline | Single PDF/DOCX upload, native vs. scanned detection, Docling + Azure Doc Intel dual pipeline, clause-level chunking |
| 3-4 | Clause extraction (15 types) | Claude API integration, structured JSON output, confidence scoring, P0 clause types from Appendix A |
| 5-6 | Basic risk scoring | Low/medium/high/critical classification, risk explanations, aggregate per-contract scores |
| 6-7 | Review interface v1 | List view of extracted clauses, accept/reject per clause, basic filtering by risk level and type |
| 7-8 | Excel matrix export | Contract x clause type matrix, conditional formatting (RAG flags), single template |

**Exit Criteria:**
- 90%+ F1 score on clause extraction validated against 50 human-reviewed contracts
- Processing time < 90 seconds for native PDF
- At least 3 associates complete a test review and provide feedback
- Basic audit logging captures document uploads and AI calls

**Key Risks:**
- Extraction accuracy may not meet 90% threshold on first attempt. Mitigation: budget 1 week for prompt iteration.
- Associates may not engage with test review. Mitigation: schedule dedicated sessions, buy lunch.

---

## Phase 1: Deal-Ready (Weeks 9-16)

**Goal:** Support a full deal workflow end-to-end. Use on 2 live deals.

**Theme:** Can a deal team actually use this on a real engagement?

| Week | Deliverable | Details |
|---|---|---|
| 9-10 | Batch upload + processing queue | ZIP upload, parallel processing via Celery, progress tracking via WebSocket, failed file handling |
| 10-11 | Full clause extraction (40+ types) | Expand from 15 to 40+ clause types, missing clause detection, cross-reference handling |
| 11-12 | Split-pane review interface | PDF viewer (left) with clause highlighting, metadata panel (right), click-to-navigate between clause and source |
| 12-13 | Risk scoring v2 | Risk explanations with specific language references, playbook-based rules (default playbooks per deal type) |
| 13-14 | Partner escalation workflow | Escalate button, partner notification, partner review and response, escalation tracking |
| 14-15 | Semantic search | Hybrid BM25 + vector search, filter by contract type / risk level / clause type, click-through to source |
| 15-16 | PPT + PDF export | Branded PowerPoint executive summary with charts, PDF risk report with table of contents, async generation |

**Exit Criteria:**
- Successfully used on 2 live deals with positive associate feedback (NPS > 30)
- 93%+ F1 score on expanded clause set
- Human override rate < 15%
- Export deliverables accepted by partner without rework on at least 1 deal
- Confidence routing working (low-confidence items flagged for review)

**Key Risks:**
- Live deal pressure may expose UX issues. Mitigation: assign PM (me) as on-call support during first 2 deals.
- Playbook configuration may be too complex for first-time setup. Mitigation: ship default playbooks that work out of the box.

---

## Phase 2: Scale (Weeks 17-24)

**Goal:** Multi-tenant platform supporting concurrent deals across multiple teams.

**Theme:** Can this run 15 deals simultaneously without breaking?

| Week | Deliverable | Details |
|---|---|---|
| 17-18 | Multi-tenant architecture | RLS enforcement on all tables, tenant-scoped storage buckets, admin tenant configuration |
| 18-19 | SSO integration | SAML 2.0 and OIDC support via Supabase Auth, automated user provisioning |
| 19-20 | Configurable extraction templates | Per-deal-type clause sets, custom playbook creation UI, playbook impact preview |
| 20-21 | Cross-document analysis | Conflict detection across contracts in same deal, inconsistency flagging, side-by-side comparison view |
| 21-22 | Bulk review actions | Accept all filtered clauses, bulk escalation, undo capability (30-second window) |
| 22-23 | Performance optimization | Query optimization for 50K+ document corpus, materialized views for dashboards, caching strategy |
| 23-24 | SOC 2 preparation | Vanta/Drata setup, policy documentation, automated compliance monitoring, penetration testing |

**Exit Criteria:**
- 5+ concurrent deals running without performance degradation
- Search latency p95 < 2 seconds on 50K+ document corpus
- RLS enforcement verified by automated integration tests (zero cross-tenant leakage)
- SSO working with at least 2 identity providers
- SOC 2 readiness assessment completed with no critical gaps

**Key Risks:**
- RLS may introduce query performance overhead. Mitigation: benchmark early, optimize indexes.
- SOC 2 preparation may surface infrastructure gaps. Mitigation: start Vanta setup in week 17, not week 23.

---

## Phase 3: Intelligence (Weeks 25+)

**Goal:** Advanced analytics and institutional learning within tenant boundaries.

**Theme:** Can the platform get smarter over time for each client?

| Deliverable | Details | Priority |
|---|---|---|
| Clause library management | Standard clause text per type/jurisdiction, centroid embeddings for benchmarking, similarity thresholds, admin CRUD UI | P0 |
| Portfolio-level risk analytics | Risk trends across deals, clause type distribution visualization, comparative deal analysis | P0 |
| Saved search queries | Save, name, and share search queries within a deal team, scheduled search alerts | P1 |
| Integration APIs | Webhooks for external systems, REST API for third-party integration, document upload via API | P1 |
| Custom report builder | Drag-and-drop report sections, custom templates, scheduled report generation | P2 |
| Institutional memory (per-tenant) | Learn from past review decisions to improve future extractions within same tenant, confidence adjustment based on historical overrides | P2 |
| Multi-language support | Spanish, French, German contract processing, multilingual search | P2 |
| On-premise deployment option | Docker-based deployment for clients requiring on-premise data residency | P3 |

---

## Dependencies and Sequencing

```
Phase 0                    Phase 1                    Phase 2
────────                   ────────                   ────────
Ingestion pipeline ──────▶ Batch upload               Multi-tenant RLS
       │                        │                          │
       ▼                        ▼                          ▼
Clause extraction ──────▶ 40+ clause types ──────────▶ Configurable templates
       │                        │                          │
       ▼                        ▼                          ▼
Risk scoring ────────────▶ Playbook-based scoring ───▶ Cross-doc analysis
       │                        │                          │
       ▼                        ▼                          ▼
Review UI v1 ────────────▶ Split-pane review ─────────▶ Bulk actions
       │                        │                          │
       ▼                        ▼                          ▼
Excel export ────────────▶ PPT + PDF export           Performance optimization
                                │
                                ▼
                          Semantic search
                                │
                                ▼
                          Partner escalation
```

---

## Success Milestones

| Milestone | Target Date | Success Criteria |
|---|---|---|
| **MVP validated** | Week 8 | 90%+ F1 score, 3 associates tested, positive qualitative feedback |
| **First live deal** | Week 12 | Platform used on real engagement, no critical bugs during deal |
| **Deal-ready** | Week 16 | 2 deals completed, NPS > 30, deliverables accepted by partners |
| **Multi-tenant launch** | Week 20 | 3+ tenants onboarded, RLS verified, SSO working |
| **Scale proven** | Week 24 | 5+ concurrent deals, < 2s search latency, SOC 2 ready |
| **Revenue milestone** | Week 30 | Platform generating measurable time savings across 10+ deals |

---

## What We're NOT Building (and Why)

| Feature | Why Not | Revisit When |
|---|---|---|
| Contract drafting/redlining | Different product category (CLM). We're analysis-focused. | Customer demand from 10+ clients |
| Mobile app | Deal teams work on laptops. Mobile adds complexity without clear value. | Usage data shows >10% mobile traffic |
| Real-time collaborative editing | We're analysis tool, not Google Docs. Associates review individually. | Multiple associates reviewing same contract simultaneously |
| Integration with DocuSign/Ironclad CLM | Phase 3 API covers this. Not needed for core value prop. | Phase 3 integration APIs are live |
| Custom model fine-tuning | Prompt engineering + RAG is sufficient. Fine-tuning requires ML team we don't have. | Override rate exceeds 20% (model isn't learning from corrections) |
| Automated negotiation recommendations | Risky to automate legal judgment. Focus on information, not advice. | Legal industry consensus on AI-assisted negotiation |
