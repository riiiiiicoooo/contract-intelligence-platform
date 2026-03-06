# Architecture Decision Records

**Project:** Contract Intelligence Platform
**Last Updated:** 2024-09

This document captures key architectural decisions that shaped the platform's design. Each ADR explains the context, decision, alternatives evaluated, and resulting trade-offs.

---

## ADR-001: Claude as Primary LLM with GPT-4 Fallback and Circuit Breaker Resilience

**Status:** Accepted
**Date:** 2024-03

**Context:**
The clause extraction pipeline is the platform's core value driver. An LLM API outage during a live M&A deal would be catastrophic, as associates depend on extraction results to meet tight due diligence deadlines. We needed to decide between a single-model architecture, multi-model routing, or fine-tuned open-source models. Claude's 200K context window was attractive because most contracts (30-80 pages) can be processed in a single pass without chunking, but relying on a single provider introduced availability risk.

**Decision:**
Use Claude (claude-sonnet-4-20250514) as the primary extraction model with GPT-4 Turbo as a fallback. Wrap each provider in a per-provider circuit breaker (pybreaker, fail_max=5, reset_timeout=60s) and tenacity retry with exponential backoff (3 attempts, 2-30s wait). The extraction flow is: try Claude with retry -> if Claude circuit opens or retries exhaust, fall back to GPT-4 with its own circuit breaker -> if both circuits are open, raise a RuntimeError. Temperature is set to 0.2 for deterministic extraction.

**Alternatives Considered:**
- **Single model (Claude only):** Simpler architecture but a single point of failure with no recovery path during outages.
- **Fine-tuned open-source model (e.g., Llama):** Would eliminate API dependency and reduce marginal cost, but required an ML engineering team we did not have and benchmarked 15-20% below frontier models on legal text extraction accuracy.
- **Multi-model consensus (run both, compare):** Best accuracy but doubled API costs and latency.

**Consequences:**
- Requires an abstraction layer that normalizes output schemas across Claude and GPT-4 response formats.
- Prompt templates differ per model (Claude excels with detailed structured instructions; GPT-4 works better with function calling / JSON mode).
- Circuit breaker routing adds approximately 200ms latency on the fallback path, but eliminates complete downtime from any single provider.
- Token costs are tracked per model (input/output) and stored on each extracted clause for cost attribution.
- API cost increased roughly 35% compared to single-model, offset by reduced associate review time.

---

## ADR-002: Confidence Threshold at 0.85 for Human Review Routing

**Status:** Accepted (revised from 0.90)
**Date:** 2024-08

**Context:**
Every extracted clause receives a confidence score from the LLM (0.0-1.0). We needed a threshold to determine which clauses are auto-accepted and which are routed to human review. The threshold directly controls two opposing risks: too high means associates still review most clauses (defeating the purpose of AI extraction), and too low means errors slip through undetected. We validated against 500 human-reviewed clauses across 50 contracts.

**Decision:**
Set the default confidence threshold at 0.85, configurable per tenant. At this threshold, approximately 81% of clauses are auto-accepted with a 2.4% error rate in the auto-accepted set, and 19% are routed to human review. Additionally, any clause with a critical risk flag is always routed to human review regardless of confidence score. The route_for_review method in ClauseExtractor and the _route_for_review stage in ContractAnalysisWorkflow both enforce this threshold.

**Alternatives Considered:**
- **0.95 threshold:** Only 52% auto-accepted (0.3% error rate). Associates reported the review volume was barely less than manual review.
- **0.90 threshold:** 68% auto-accepted (1.1% error rate), but associates reported the flagged items were often obviously correct, creating unnecessary review fatigue.
- **0.80 threshold:** 89% auto-accepted (4.8% error rate). Partners deemed this unacceptable for client deliverables.
- **0.75 threshold:** 93% auto-accepted (7.2% error rate). Rejected as unsuitable for legal work product.

**Consequences:**
- Roughly 2.4% of auto-accepted clauses contain errors, typically minor misclassifications (e.g., "termination for convenience" mislabeled as "termination for cause") rather than complete hallucinations. Mitigated by partner spot-check sampling.
- The threshold must be re-evaluated whenever the extraction model is updated, because confidence distributions shift between model versions.
- Conservative tenants can raise the threshold; high-volume tenants processing hundreds of NDAs can lower it.
- The partial index `idx_clauses_confidence ON clauses (confidence) WHERE confidence < 0.85` in the database schema directly reflects this threshold for efficient review queue queries.

---

## ADR-003: Few-Shot Prompt Engineering with Structured JSON Output

**Status:** Accepted
**Date:** 2024-04

**Context:**
The clause extraction and risk scoring prompts needed to produce consistent, machine-parseable output across thousands of contract analyses. Free-form text output would require heavy NLP post-processing and was prone to format drift. We also needed to minimize hallucination on critical fields such as notice_period_days, confidence scores, and trigger_events, where an invented value could lead to incorrect deal risk assessments.

**Decision:**
Use structured JSON output format with typed fields, enforced through detailed prompt instructions and two carefully selected few-shot examples per prompt template. The system message defines the role and task. The prompt template provides 19 numbered field descriptions with explicit type constraints (e.g., notice_period_days must be integer or null, confidence must be float between 0.0 and 1.0). Two few-shot examples demonstrate: (1) a canonical case with straightforward clause language and high confidence, and (2) a complex edge case with embedded/partial clause language and lower confidence. User-controlled contract text is placed inside `<contract_document>` XML tags with explicit instructions that the text is data to analyze, not instructions to follow. A `sanitize_prompt_input()` function strips injection patterns before interpolation.

**Alternatives Considered:**
- **Free-form text output:** Simpler prompts but required NLP parsing of responses, format drift across model versions, and no type safety on critical numeric fields.
- **Single few-shot example:** Insufficient to establish the pattern; testing showed 20-30% lower F1 score on edge cases compared to two examples.
- **Five or more few-shot examples:** Diminishing returns on accuracy, significant token cost increase, and risk of conflicting examples confusing the model.
- **Tool use / function calling for schema enforcement:** Considered for GPT-4 (response_format: json_object), but Claude's structured extraction with detailed field instructions benchmarked higher on our legal test set.

**Consequences:**
- Prompt templates are long (each is 300-400 lines including examples), consuming significant context window, but this is acceptable given Claude's 200K token limit.
- Adding new clause types requires updating the prompt templates, the CLAUSE_TYPES list (41 types currently), and ideally adding evaluation cases.
- The XML tag boundary (`<contract_document>`) and sanitization provide defense-in-depth against prompt injection, but are not a complete mitigation (noted in SECURITY_REVIEW.md).
- Each prompt module (clause_extraction.py, risk_scoring.py, cross_reference.py) includes its own sanitize_prompt_input function and "REMINDER" instructions to ignore embedded directives.

---

## ADR-004: Hybrid Search with BM25 + pgvector + Cohere Rerank

**Status:** Accepted
**Date:** 2024-05

**Context:**
Legal text has a distinctive property: both exact terminology and semantic equivalence matter for retrieval. "Force majeure" is a precise legal term that keyword search catches perfectly, but "events beyond reasonable control" is semantically equivalent and requires vector search. Neither approach alone achieved acceptable recall for legal professionals. We benchmarked three approaches on a legal test set.

**Decision:**
Implement a three-stage hybrid search pipeline: (1) parallel BM25 keyword search via PostgreSQL GIN full-text index and pgvector HNSW approximate nearest neighbor search using voyage-law-2 embeddings (1024 dimensions), (2) Reciprocal Rank Fusion (RRF, k=60) to merge ranked lists without needing to calibrate score distributions, (3) Cohere Rerank (rerank-english-v3.0) cross-encoder rescoring of the top 20 fused results, returning the final top 10. BM25 uses `to_tsvector('english', extracted_text)` with a GIN index. Vector search uses HNSW with m=16, ef_construction=128, and cosine distance.

**Alternatives Considered:**
- **Vector-only (pgvector):** 72% accuracy. Missed exact legal terms and section references like "Section 14.2" that associates commonly search for.
- **BM25-only (PostgreSQL full-text):** 58% accuracy. Missed semantic equivalents entirely. "Termination for cause" would not match "right to end agreement for material breach."
- **Hybrid without reranking:** 83% accuracy. Good but Cohere's cross-encoder added 8 percentage points of accuracy for approximately 150ms additional latency.

**Consequences:**
- Must maintain both GIN (full-text) and HNSW (vector) indexes, increasing storage and write overhead.
- Cohere Rerank adds an external API dependency on the search path (not the extraction path). If Cohere is down, the system falls back to RRF-only ordering.
- Total search latency is under 500ms (BM25 ~50ms, vector ~100ms, rerank ~150ms, overhead ~100ms), well within the 2-second target.
- RRF k=60 weighting may need tuning as the clause corpus grows beyond 500K embeddings.
- voyage-law-2 was chosen over text-embedding-3-large because it outperforms by 6% on legal retrieval benchmarks and is used in production by other legal AI companies.

---

## ADR-005: Multi-Tenant Row-Level Security via Supabase PostgreSQL RLS

**Status:** Accepted
**Date:** 2024-03

**Context:**
The platform is multi-tenant, with each tenant (law firm or PE fund) having strict data isolation requirements. A query bug that leaks one tenant's contract data to another would be a career-ending breach for legal professionals. We needed to decide between application-level tenant filtering (WHERE tenant_id = X on every query), database-level enforcement via Row-Level Security, or a separate database per tenant.

**Decision:**
Use PostgreSQL Row-Level Security policies enforced at the database level on all tenant-scoped tables (deals, contracts, contract_parties, clauses, clause_embeddings, risk_flags, export_jobs, audit_log, playbooks). Each table has a tenant_id column and an RLS policy: `USING (tenant_id = (auth.jwt() ->> 'tenant_id')::UUID)`. The Clerk middleware extracts the tenant_id from the authenticated user's metadata and sets it in request headers and cookies. The Supabase client propagates this through auth.jwt() for RLS enforcement. Every query is automatically filtered without application code needing to include WHERE clauses.

**Alternatives Considered:**
- **Application-level filtering (WHERE tenant_id = X):** Full control but relies on every developer remembering to include the filter on every query. A single missing WHERE clause would be a cross-tenant data leak. Not acceptable for legal data.
- **Database-per-tenant:** Strongest isolation but operationally complex at scale (schema migrations across N databases, connection pool management, cost). Overkill for our projected scale of 50-200 tenants.
- **Auth0 + custom RLS:** Mature auth platform with enterprise SSO, but two vendor dependencies (Auth0 + Supabase) with complex integration.

**Consequences:**
- Even if application code has a bug that omits a tenant filter, the database will not return another tenant's data. This defense-in-depth is the primary security benefit.
- RLS adds approximately 5-10% overhead on complex queries due to additional plan nodes, which is acceptable for the isolation guarantee.
- The clause_library table uses a special policy `USING (tenant_id IS NULL OR tenant_id = ...)` to allow shared global standards plus tenant-specific custom entries.
- Debugging RLS-filtered queries requires setting session variables and using EXPLAIN ANALYZE, which adds friction during development.
- The audit_log_trigger function uses SECURITY DEFINER to bypass RLS for writing audit entries (noted as a security concern in SECURITY_REVIEW.md).

---

## ADR-006: 41-Type Clause Taxonomy with Missing Clause Detection

**Status:** Accepted
**Date:** 2024-04

**Context:**
M&A due diligence requires extracting specific clause types from contracts and comparing them against expected standards. We needed to define a taxonomy that was comprehensive enough to catch deal-critical provisions but not so granular that it produced noise. The taxonomy also needed to support "missing clause" detection -- flagging when an expected clause type is absent from a contract, which is itself a risk signal.

**Decision:**
Define a taxonomy of 41 clause types (in CLAUSE_TYPES list in clause_extractor.py) spanning change_of_control, assignment, termination_convenience, termination_cause, indemnification, limitation_of_liability, payment_terms, renewal_auto_renewal, governing_law, non_compete, confidentiality, ip_ownership, and 29 additional types including force_majeure, exclusivity, anti_bribery, earnout_provisions, drag_along_tag_along, and consent_requirements. Define expected clause lists per contract type (MSA, NDA, employment, lease) in the EXPECTED_CLAUSES dictionary. The RiskScorer._detect_missing_clauses method compares extracted types against expected types and generates "missing_clause" risk flags with warning severity.

**Alternatives Considered:**
- **Open-ended extraction (let the LLM decide what to extract):** No predefined types. Risk of inconsistent extraction across documents and models. Makes comparison and matrix generation impossible without normalization.
- **Small taxonomy (10-15 types):** Simpler but missed deal-critical provisions like earnout_provisions, drag_along_tag_along, and most_favored_nation that PE fund partners specifically asked for.
- **Large taxonomy (80+ types):** More granular but testing showed diminishing extraction accuracy past 50 types as the prompt became overloaded with type definitions.

**Consequences:**
- Adding a new clause type requires updating CLAUSE_TYPES, the extraction prompt, EXPECTED_CLAUSES (if applicable), the matrix column order in MATRIX_COLUMNS, and ideally evaluation test cases.
- Missing clause detection enables a high-value feature: the system flags "this MSA has no limitation_of_liability clause" which is a critical risk signal in M&A.
- The clause_library table stores market standard text per clause type, jurisdiction, and deal type, enabling deviation detection via embedding similarity (similarity_threshold = 0.85).
- The 41-type taxonomy is encoded in PostgreSQL as a TEXT field rather than an ENUM to allow easier addition of new types without schema migrations.
