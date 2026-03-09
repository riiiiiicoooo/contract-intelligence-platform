# Decision Log: Contract Intelligence Platform

**Last Updated:** January 2025

This document records key technical and product decisions made during the development of the Contract Intelligence Platform. Each entry captures the context, options considered, decision made, and the reasoning behind it.

---

## DEC-001: Multi-Model AI vs. Single Model

**Date:** March 2024
**Status:** Accepted
**Decider:** Jacob George (PM), Engineering Lead

**Context:**
We needed to choose whether to build the extraction pipeline around a single LLM provider or architect for multi-model routing. The platform's core value depends on extraction accuracy, so this was the highest-stakes architectural decision.

**Options Considered:**

| Option | Pros | Cons |
|---|---|---|
| **A: Single model (Claude only)** | Simpler architecture, one vendor relationship, consistent output format | Single point of failure, no fallback, locked to one provider's strengths/weaknesses |
| **B: Multi-model with routing** | Fallback on outages, leverage different model strengths per task, vendor negotiation leverage | More complex architecture, need to normalize outputs across models, higher maintenance |
| **C: Fine-tuned open-source model** | Full control, no API dependency, lower marginal cost | 6+ month investment, need ML engineering team, accuracy gap vs. frontier models |

**Decision:** Option B - Multi-model routing with Claude as primary, GPT-4 as fallback.

**Reasoning:**
- During a live deal, an API outage would be catastrophic. Multi-model gives us a fallback path.
- Claude's 200K context window handles full contracts in a single pass (most contracts are 30-80 pages). GPT-4 requires chunking for longer contracts but performs well on shorter extractions.
- Different tasks benefit from different models. Claude excels at structured extraction with complex instructions. GPT-4 is strong at nuanced risk reasoning.
- Vendor lock-in risk is real. Having two providers integrated means we can shift traffic if pricing or quality changes.
- Option C was rejected because we don't have the ML team to maintain a fine-tuned model, and the accuracy gap vs. frontier models is significant for legal text.

**Consequences:**
- Need an abstraction layer normalizing outputs across models
- Need model-specific prompt templates (what works for Claude doesn't always work for GPT-4)
- Routing logic adds ~200ms latency but eliminates single-provider downtime risk

---

## DEC-002: pgvector on Supabase vs. Dedicated Vector Database

**Date:** March 2024
**Status:** Accepted
**Decider:** Jacob George (PM), Engineering Lead

**Context:**
We needed vector search for semantic clause retrieval. The choice was between adding vector capabilities to our existing PostgreSQL database or deploying a dedicated vector database.

**Options Considered:**

| Option | Pros | Cons |
|---|---|---|
| **A: Pinecone** | Purpose-built, fully managed, fast at scale | Separate system to manage, data sync complexity, vendor lock-in, cost scales with vectors |
| **B: Weaviate** | Best hybrid search, native multi-tenancy | Another service to deploy/manage, learning curve, overkill for early stage |
| **C: pgvector on Supabase** | Same database for vectors + relational + auth + RLS, SQL joins between embeddings and metadata, simpler architecture | Slower than purpose-built at very large scale (100M+ vectors), HNSW index rebuild on updates |

**Decision:** Option C - pgvector on Supabase.

**Reasoning:**
- Our core query pattern is "find similar clauses AND filter by tenant, deal, contract type, risk level." With pgvector, that's one SQL query joining the embeddings table with the clauses table. With Pinecone, it's two queries (vector search + metadata filter) that need to be reconciled in the application layer.
- Supabase gives us PostgreSQL + pgvector + auth + RLS + storage + realtime in one platform. Adding Pinecone would mean syncing data between two systems and managing consistency.
- pgvectorscale benchmarks show 471 QPS at 99% recall on 50M vectors. Our projected scale (50K documents, ~500K clause embeddings) is well within this.
- RLS enforcement happens at the database level. With a separate vector DB, we'd need to implement tenant isolation in the application layer - an additional security surface.
- Cost: Supabase Pro ($25/mo) vs. Pinecone ($70/mo minimum for production) + Supabase anyway for relational data.

**Consequences:**
- Need to manage HNSW index parameters (m=16, ef_construction=128) and monitor recall quality
- Index rebuilds on large embedding batches may cause brief latency spikes
- If we exceed 50M vectors, we'll need to evaluate pgvectorscale partitioning or migrate hot path to dedicated vector DB

**Revisit trigger:** Query latency p95 exceeds 500ms or recall drops below 95%.

---

## DEC-003: Clause-Level Chunking vs. Fixed-Size Chunking

**Date:** April 2024
**Status:** Accepted
**Decider:** Jacob George (PM)

**Context:**
We needed a chunking strategy for breaking contracts into pieces for embedding and retrieval. The choice directly impacts search quality and extraction accuracy.

**Options Considered:**

| Option | Pros | Cons |
|---|---|---|
| **A: Fixed-size (512 tokens)** | Simple to implement, consistent chunk sizes, predictable embedding costs | Splits clauses mid-sentence, loses legal context, partial indemnity clause is useless |
| **B: Clause-level (200-500 tokens)** | Preserves legal meaning, natural document structure, precise attribution | Variable chunk sizes, requires section detection logic, some clauses exceed 500 tokens |
| **C: Page-level** | Easy to implement, preserves page context | Too large for precise retrieval, one page may contain 3+ different clause types |

**Decision:** Option B - Clause-level hierarchical chunking.

**Reasoning:**
- Legal documents have natural boundaries (numbered sections, clause headers). Splitting mid-clause destroys the legal meaning. "The Seller shall indemnify..." is useless without the rest of the indemnification scope.
- Clause-level chunks map directly to our data model (one chunk = one row in the clauses table). This makes attribution simple - every search result points to an exact clause.
- We implemented hierarchical levels: L1 (full contract summary), L2 (section-level), L3 (clause-level). Broad queries hit L1/L2, specific queries hit L3.
- For clauses exceeding 500 tokens (some indemnification sections run 800+ tokens), we keep them as single chunks rather than splitting. The embedding model handles up to 1024 tokens, and preserving the full clause is more important than consistent chunk size.

**Consequences:**
- Need section detection logic (regex for numbered sections + header detection)
- Some chunks are 100 tokens, others are 800. Embedding costs are slightly less predictable.
- Hierarchical approach requires query routing logic to pick the right level

---

## DEC-004: PII Redaction Before vs. After LLM Processing

**Date:** April 2024
**Status:** Accepted
**Decider:** Jacob George (PM), General Counsel

**Context:**
The Heppner ruling (Feb 2026, S.D.N.Y.) established that AI-processed documents may not be protected by attorney-client privilege if PII is exposed to consumer AI tools. We needed to decide when and how to handle PII.

**Options Considered:**

| Option | Pros | Cons |
|---|---|---|
| **A: Pre-processing redaction (before LLM)** | PII never reaches external APIs, strongest privilege protection, audit-friendly | Adds processing step, potential over-redaction may lose context, need de-anonymization mapping |
| **B: Post-processing filtering** | Simpler pipeline, LLM has full context for better extraction | PII sent to external API (privilege risk), relies on API provider not logging, non-compliant post-Heppner |
| **C: On-device processing (no API)** | Zero data exposure | No frontier model available for on-device, accuracy gap too large |

**Decision:** Option A - Pre-processing redaction using Microsoft Presidio.

**Reasoning:**
- After Heppner, sending unredacted PII to external LLM APIs creates privilege waiver risk. This is non-negotiable for our legal clients.
- Presidio handles 20+ entity types with configurable confidence thresholds. We set threshold at 0.7 to balance recall (catching PII) vs. precision (not over-redacting legal terms that look like names).
- The de-anonymization mapping (<PERSON_1> -> "John Smith") is stored in encrypted storage, never sent to the LLM. After the LLM returns its extraction, we map placeholders back to real values.
- We tested extraction quality with redacted vs. unredacted input. The accuracy drop was < 2% for clause extraction because the AI primarily cares about clause structure and legal language, not specific names.
- ZDR agreements with Anthropic and OpenAI provide a second layer of protection, but redaction is our primary defense.

**Consequences:**
- ~500ms added to processing pipeline per document for PII scan
- Need to maintain and test Presidio recognizers for legal-specific entities (case numbers, bar IDs)
- De-anonymization mapping adds storage overhead (~2KB per document)
- Over-redaction of entity names that are also common words requires ongoing tuning

---

## DEC-005: Hybrid Search (BM25 + Vector + Rerank) vs. Vector-Only

**Date:** May 2024
**Status:** Accepted
**Decider:** Jacob George (PM), Engineering Lead

**Context:**
Legal text has a unique property: both exact terminology and semantic equivalence matter. "Force majeure" is a precise legal term, but "events beyond reasonable control" means the same thing.

**Options Considered:**

| Option | Pros | Cons |
|---|---|---|
| **A: Vector-only** | Catches semantic equivalents, simpler implementation | Misses exact legal terms, "force majeure" returns "act of God" but may miss exact matches |
| **B: BM25 keyword only** | Fast, catches exact terms, well-understood | Misses semantic equivalents, "termination for cause" won't match "right to end for breach" |
| **C: Hybrid BM25 + vector + rerank** | Best of both worlds, 91% accuracy in benchmarks | More complex, three-step pipeline, reranking adds latency |

**Decision:** Option C - Hybrid search with Cohere Rerank.

**Reasoning:**
- Benchmarks showed hybrid with reranking at 91% accuracy vs. 72% vector-only vs. 58% BM25-only on our legal test set.
- Associates search for both exact terms ("Section 14.2 assignment") and concepts ("contracts where we can't transfer the agreement"). One approach can't serve both.
- Reciprocal Rank Fusion (RRF) merges BM25 and vector results without needing to calibrate score distributions.
- Cohere Rerank adds ~150ms but significantly improves result ordering for the top 10. Worth it because users only look at the first page of results.
- The three-step pipeline runs in under 500ms total (BM25: ~50ms, vector: ~100ms, rerank: ~150ms, overhead: ~100ms), well within our 2-second target.

**Consequences:**
- Need to maintain both full-text (GIN) and vector (HNSW) indexes
- Reranking adds a Cohere API dependency (but it's not on the critical extraction path)
- RRF weighting (k=60) may need tuning as the corpus grows

---

## DEC-006: Async Export Generation vs. Synchronous

**Date:** June 2024
**Status:** Accepted
**Decider:** Jacob George (PM)

**Context:**
Generating a contract matrix for a 200+ contract deal produces a large Excel file with conditional formatting, multiple tabs, and embedded data. Initial tests showed this taking 30-90 seconds.

**Options Considered:**

| Option | Pros | Cons |
|---|---|---|
| **A: Synchronous (block until complete)** | Simple, user gets file immediately | HTTP timeout risk, blocks UI, poor UX for large deals, server resource contention |
| **B: Async with polling** | Non-blocking, handles large exports | Client must poll for status, slightly more complex |
| **C: Async with WebSocket progress** | Non-blocking, real-time progress, best UX | Most complex, requires WebSocket infrastructure |

**Decision:** Option C - Async with WebSocket progress updates.

**Reasoning:**
- A 250-contract matrix takes 45-60 seconds to generate. That's too long for a synchronous request and will hit HTTP timeouts on some reverse proxies.
- Associates need to continue reviewing while exports generate. Blocking the UI is unacceptable.
- WebSocket progress ("Generating contract matrix: 162 of 247 contracts") sets user expectations and prevents "is it stuck?" anxiety. We already use WebSockets for document processing progress, so the infrastructure exists.
- Celery workers handle export jobs in parallel. Multiple users can request exports simultaneously without blocking each other.
- Pre-signed URLs with 24-hour expiration handle the download securely without maintaining session state.

**Consequences:**
- Need Celery workers dedicated to export tasks (separate from ingestion workers)
- Need to handle edge cases: user closes browser mid-export, export partially fails
- Download URLs expire - users may try to re-download after 24 hours and get a 403

---

## DEC-007: Docling + Azure Document Intelligence vs. Single OCR Pipeline

**Date:** May 2024
**Status:** Accepted
**Decider:** Jacob George (PM), Engineering Lead

**Context:**
Contracts arrive as a mix of native-text PDFs (created digitally) and scanned PDFs (photocopied paper documents). These require fundamentally different processing approaches.

**Options Considered:**

| Option | Pros | Cons |
|---|---|---|
| **A: Single pipeline (Azure Doc Intel for everything)** | One tool, consistent output, handles both types | Expensive for native PDFs that don't need OCR, slower, unnecessary API calls for 70% of documents |
| **B: Single pipeline (Docling for everything)** | Free (MIT license), fast for native | Poor accuracy on scanned documents, no production-grade OCR |
| **C: Dual pipeline (detect then route)** | Best tool for each type, cost-optimized, faster average processing | Two codepaths to maintain, need reliable scanned detection |

**Decision:** Option C - Dual pipeline with automatic detection.

**Reasoning:**
- 70% of our contracts are native-text PDFs. Docling processes these in 2-3 seconds. Sending them to Azure Document Intelligence would take 8-12 seconds and cost $0.01-0.05 per page.
- For the 30% that are scanned, Azure Document Intelligence achieves 99.8% character accuracy vs. Docling's OCR integration which is still maturing.
- The detection logic is straightforward: extract text via PyMuPDF, check text-to-filesize ratio, check image coverage, check for OCR artifact fonts. This runs in <100ms and has been 99%+ accurate in testing.
- Cost savings: processing 200 native PDFs through Docling instead of Azure saves ~$40-100 per deal. Over 15-20 deals per year, that's meaningful.

**Consequences:**
- Two processing codepaths to maintain and test
- Edge case: mixed documents (some pages scanned, some native) require per-page detection
- Docling is newer (released late 2024) and may have stability issues - need to monitor

---

## DEC-008: Supabase Auth + RLS vs. Custom Auth

**Date:** March 2024
**Status:** Accepted
**Decider:** Jacob George (PM), Engineering Lead

**Context:**
We needed authentication and tenant-level data isolation. The choice was between using Supabase's built-in auth and RLS or building custom authentication middleware.

**Options Considered:**

| Option | Pros | Cons |
|---|---|---|
| **A: Custom JWT + application-level filtering** | Full control, no platform dependency | Must implement tenant filtering in every query, security bugs likely, more code to audit |
| **B: Supabase Auth + PostgreSQL RLS** | Auth handled, RLS enforces isolation at DB level, impossible to accidentally leak cross-tenant data | Tied to Supabase platform, RLS adds query planning overhead, harder to debug |
| **C: Auth0 + custom RLS** | Mature auth platform, SAML/OIDC built-in | Two vendors (Auth0 + database), complex integration, Auth0 pricing at scale |

**Decision:** Option B - Supabase Auth + PostgreSQL RLS.

**Reasoning:**
- RLS enforces tenant isolation at the database level. Even if application code has a bug that forgets a WHERE clause, the database won't return another tenant's data. This is defense-in-depth that application-level filtering can't match.
- Supabase Auth handles JWT issuance, refresh tokens, and SSO (SAML/OIDC for enterprise clients) out of the box. Building this from scratch would take 4-6 weeks.
- The API middleware sets PostgreSQL session variables (app.current_tenant, app.user_id, app.user_role) on each request. RLS policies reference these variables. This pattern is clean and auditable.
- RLS overhead is measurable (~5-10% on complex queries) but acceptable for the security guarantee it provides.

**Consequences:**
- Must set session variables on every database connection (middleware responsibility)
- RLS policy debugging requires EXPLAIN ANALYZE with session variables set
- Tied to Supabase for auth (migration path exists to raw PostgreSQL + custom auth if needed)

---

## DEC-009: voyage-law-2 vs. General-Purpose Embeddings

**Date:** May 2024
**Status:** Accepted
**Decider:** Jacob George (PM)

**Context:**
Embedding model choice directly impacts search quality. We evaluated legal-specific vs. general-purpose embedding models.

**Options Considered:**

| Option | Pros | Cons |
|---|---|---|
| **A: OpenAI text-embedding-3-large** | General-purpose, widely used, good documentation | Not optimized for legal text, lower recall on legal retrieval benchmarks |
| **B: voyage-law-2** | Purpose-built for legal text, 6% better on legal benchmarks | Smaller company (Voyage AI), less community support, potential availability risk |
| **C: BGE-M3 (self-hosted)** | Open-source, no API dependency, fine-tunable | Infrastructure to manage, no legal-specific training without fine-tuning |

**Decision:** Option B - voyage-law-2.

**Reasoning:**
- voyage-law-2 outperforms OpenAI text-embedding-3-large by 6% average across 8 legal retrieval benchmarks, and by >10% on 3 of them. For a product where search quality is core, 6% matters.
- Harvey AI (the $8B legal AI company) uses custom Voyage embeddings for their production system. This validates the approach.
- Voyage AI offers competitive pricing and the API is stable. The risk of a smaller vendor is mitigated by the fact that embeddings are generated once and stored - if Voyage went down, existing embeddings still work, and we can re-embed with a different model.
- Self-hosted BGE-M3 was rejected because we don't want to manage GPU infrastructure for embeddings at this stage.

**Consequences:**
- Vendor dependency on Voyage AI for embedding generation
- 1024-dimension vectors (vs. OpenAI's configurable dimensions) - fixed storage cost per embedding
- Need to re-embed entire corpus if we switch models (migration plan documented)

---

## DEC-010: LangGraph vs. Custom Pipeline Orchestration

**Date:** June 2024
**Status:** Accepted
**Decider:** Jacob George (PM), Engineering Lead

**Context:**
The AI analysis pipeline has conditional logic: extract clauses, score risk, route low-confidence items to human review, generate report. We needed an orchestration framework for this.

**Options Considered:**

| Option | Pros | Cons |
|---|---|---|
| **A: Custom Python code** | Full control, no framework dependency | State management is hard, no built-in human-in-the-loop, error handling complexity |
| **B: LangChain** | Large ecosystem, many integrations | Overly abstracted, hard to debug, "chain" paradigm doesn't fit conditional routing well |
| **C: LangGraph** | Stateful graphs, native human-in-the-loop (interrupt_before), growing ecosystem | Newer framework, smaller community than LangChain, learning curve for graph concepts |

**Decision:** Option C - LangGraph.

**Reasoning:**
- The pipeline is naturally a directed graph, not a linear chain. Document classification branches into different extraction strategies. Risk scoring has conditional routing (high confidence -> auto-accept, low -> human review). LangGraph models this directly.
- LangGraph's `interrupt_before` primitive is exactly what we need for human-in-the-loop. When a clause has low confidence, the graph pauses execution, waits for human input, then resumes. Building this with custom code would take weeks.
- LangGraph state persistence means if the server restarts mid-processing, the pipeline can resume from where it left off. Critical for long-running batch jobs.
- LangSmith integration provides deep tracing of every node in the graph - token usage, latency, cost. Essential for monitoring extraction quality over time.
- ~400 companies deployed LangGraph in production by late 2025. The framework is mature enough for our use case.

**Consequences:**
- Team needs to learn graph-based programming concepts
- Debugging requires LangSmith (or Langfuse) for visibility into graph execution
- LangGraph updates may require prompt/graph refactoring

---

## DEC-011: WeasyPrint + Jinja2 vs. ReportLab for PDF Generation

**Date:** July 2024
**Status:** Accepted
**Decider:** Jacob George (PM)

**Context:**
Risk reports need to be professional, branded PDFs. We evaluated approaches for generating these programmatically.

**Options Considered:**

| Option | Pros | Cons |
|---|---|---|
| **A: ReportLab** | Python-native, precise control over layout | Programmatic layout is tedious, hard to iterate on design, steep learning curve |
| **B: WeasyPrint + Jinja2** | Write reports as HTML/CSS, leverage web design skills, easy to template | CSS print support has quirks, WeasyPrint is slower, external dependency |
| **C: LaTeX** | Beautiful output, academic standard | Overkill, team doesn't know LaTeX, template management is painful |

**Decision:** Option B - WeasyPrint with Jinja2 templates.

**Reasoning:**
- HTML/CSS is a skill our team already has. ReportLab requires learning a proprietary API for layout.
- Jinja2 templates with loops and conditionals handle dynamic content naturally (iterate over contracts, conditionally show risk flags, template inheritance for consistent headers/footers).
- CSS flexbox/grid handles complex layouts (multi-column risk summaries, data tables) better than ReportLab's flowable model.
- Firm branding (colors, logos, fonts) is trivial to implement in CSS. Updating the template is editing an HTML file, not rewriting Python code.
- WeasyPrint is slower than ReportLab (~3x), but reports generate async via Celery, so absolute speed is less important than maintainability.

**Consequences:**
- CSS `@page` rules for headers, footers, and page numbers have quirks across browsers/renderers
- WeasyPrint requires system-level font installation for firm-specific fonts
- Large reports (500+ pages) may require memory optimization

---

## DEC-012: Confidence Threshold at 0.85

**Date:** August 2024
**Status:** Accepted (revised from 0.90)
**Decider:** Jacob George (PM)

**Context:**
We needed to set the confidence threshold that determines whether an extraction is auto-accepted or routed to human review. Too high = too much human review (defeats the purpose). Too low = errors slip through.

**Analysis:**

We tested on a validation set of 500 human-reviewed clauses across 50 contracts:

| Threshold | Auto-accept rate | Error rate in auto-accepted | Human review volume |
|---|---|---|---|
| 0.95 | 52% | 0.3% | 48% of all clauses |
| 0.90 | 68% | 1.1% | 32% of all clauses |
| 0.85 | 81% | 2.4% | 19% of all clauses |
| 0.80 | 89% | 4.8% | 11% of all clauses |
| 0.75 | 93% | 7.2% | 7% of all clauses |

**Decision:** 0.85 threshold.

**Reasoning:**
- At 0.85, associates review ~19% of clauses instead of 100%. That's the difference between 3 days of review and 3 weeks.
- 2.4% error rate in auto-accepted clauses is within our tolerance. These are typically minor misclassifications (e.g., "termination for convenience" labeled as "termination for cause") rather than complete hallucinations.
- The original threshold of 0.90 resulted in 32% human review volume. Associates reported this was still too much and the items flagged were often clearly correct.
- 0.80 was considered but 4.8% error rate was too high for our clients' risk tolerance.
- Threshold is configurable per tenant. Conservative clients can raise it; high-volume clients can lower it.

**Consequences:**
- ~2.4% of auto-accepted clauses will have errors that slip through. Mitigated by partner spot-check process.
- Associates should still review the auto-accepted list periodically (random sampling)
- Need to re-evaluate threshold when extraction model is updated (confidence distributions may shift)

---

## DEC-013: Multi-Model Routing Over Single-Model Architecture

**Date:** September 2024
**Status:** Accepted (supersedes earlier approach)
**Decider:** Jacob George (PM), Engineering Lead

**Context:**
V1 used GPT-4 exclusively for all clause extraction and risk scoring. Chose GPT-4 for its strong legal reasoning and context window.

**What Happened:**
Accuracy degraded significantly on non-standard clause structures — earn-out provisions with conditional triggers, multi-party indemnification chains, and nested change-of-control definitions. GPT-4 achieved 89% F1 on standard clauses but dropped to 71% on complex structures. Associates flagged 15-20 false negatives per deal on critical risk provisions. Partner feedback: "If I can't trust the red flags, I have to re-read everything anyway."

**Decision:**
Implemented model routing based on clause complexity. Standard clauses (non-compete, assignment, termination) → GPT-4. Complex multi-party clauses and financial provisions → Claude (stronger at structured reasoning). Fallback to dual-model consensus for high-risk flags.

**Rationale:**
Claude's structured output and reasoning chains performed better on nested conditional logic (82% → 94% F1 on complex clauses). Routing adds ~200ms per clause but reduces associate review time by 40%.

**Consequences:**
- Increased API costs by ~35%. Required building a clause complexity classifier (2 weeks). Need to maintain prompt templates for both models. But partner trust increased — "Now when I see a red flag, I actually believe it."

---

## DEC-014: Multi-Model Routing with Claude as Primary (Accuracy-Driven Pivot)

**Date:** October 2024
**Status:** Accepted (supersedes single-model approach)
**Decider:** Jacob George (PM), Engineering Lead

**Context:**

DEC-001 established multi-model architecture in theory but V1 implementation launched with GPT-4 as the default model. This was chosen because: (1) initial testing favored GPT-4's 89% accuracy on contract extraction, (2) faster latency, (3) lower API costs, and (4) team comfort with OpenAI's API.

For the first 2 months, all extractions used GPT-4. Associates ran the platform on real deals and provided feedback: "The red flags are good, but we're finding errors on the complex stuff."

**What Happened:**

Post-launch analysis revealed accuracy degradation on specific clause types:
- **Indemnification clauses:** 78% accuracy (GPT-4). These are critical risk provisions (associates will spend hours analyzing them). 22% error rate was unacceptable.
- **Full-contract extraction:** GPT-4 achieved 89% F1 overall, but individual clause categories ranged from 71% (indemnity) to 95% (assignment).

The turning point: a partner ran a structured benchmark. The team extracted 50 sample indemnification clauses using both Claude and GPT-4 against human-reviewed ground truth:
- **Claude:** 94% accuracy
- **GPT-4:** 78% accuracy
- **Difference:** 16 percentage points on a single critical clause type

Additionally, Claude's structured output mode (JSON schema validation) prevented hallucinated fields that GPT-4 occasionally produced.

**Decision:**

Implemented multi-model routing (per DEC-001) with Claude as primary model for all extraction. GPT-4 relegated to fallback (high-latency scenario where Claude API is unavailable) and specific clause type routing (rare cases where GPT-4 outperforms).

**Implementation:**
- Clause type classifier (built in 1 week) analyzes incoming contract and routes complex clauses to Claude, simple ones to either model
- Results show: full-contract accuracy improved from 89% to 93% F1
- Indemnification accuracy improved from 78% to 94%
- API costs increased ~25% (Claude 3.5 Opus is more expensive) but offset by reduced associate review time

**Rationale:**

1. **Accuracy is non-negotiable:** One missed indemnification clause in a $50M deal can expose the client to unlimited liability. 78% accuracy → 94% accuracy is not a marginal improvement; it's the difference between a usable product and a liability.

2. **Claude's structured reasoning:** Claude's chain-of-thought reasoning in extraction tasks produces fewer hallucinations than GPT-4's more direct outputs. On indemnity clauses, Claude traces through conditions ("if breach occurs AND damage exceeds $X AND within Y years, then..."), producing correct conditional logic.

3. **Cost-benefit:** Yes, Claude costs 25% more per API call. But this saves associates 2-3 hours per 50-contract deal in review time. At $200/hour labor cost, that's $400-600 saved per deal. The $30 additional API cost is a rounding error.

4. **Reversibility:** Multi-model routing allows testing hypotheses. Can A/B test Claude vs. GPT-4 on real deals. If GPT-4 improves in future, can re-enable it for specific use cases.

**Consequences:**

- **Short-term:** Rewrote extraction pipeline to support multi-model routing (2 weeks). Required building clause complexity classifier. Need to maintain dual prompt templates (what works for Claude doesn't always work for GPT-4).
- **Long-term:** Claude becomes primary dependency. Binding ourselves to Anthropic API (mitigated by having fallback, but still a vendor risk). Cost scales with contract volume.
- **Trust:** Partner feedback improved significantly. "The accuracy feels real now" and "We're catching things we would have missed" indicate the 16pp improvement in indemnification accuracy is noticeable in practice.

**Lesson:**

Optimize for the hardest case, not the average case. GPT-4's 89% average accuracy looked good on dashboards, but the 71% accuracy on indemnification clauses (the most critical provision) was a product killer. Claude's 94% on the hard cases justified the cost increase.

---
