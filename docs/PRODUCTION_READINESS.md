# Production Readiness Checklist

**Project:** Contract Intelligence Platform
**Last Updated:** 2024-09
**Purpose:** Track readiness across security, reliability, observability, performance, compliance, and deployment.

Items marked `[x]` are implemented in the current codebase. Items marked `[ ]` are planned or required but not yet present.

---

## Security

### Authentication and Authorization
- [x] Clerk authentication middleware with JWT validation for all protected routes (`clerk/middleware.ts`)
- [x] Role-based access control (RBAC) with partner, associate, analyst roles and per-route enforcement (`clerk/middleware.ts` ROUTE_CONFIG)
- [x] Organization-based tenant isolation via Clerk metadata (tenant_id, organization_id)
- [x] Public route allowlist explicitly defined (/, /sign-in, /sign-up, /pricing, /features, /api/webhooks)
- [x] Redirect to sign-in with return URL for unauthenticated access attempts
- [ ] Strip incoming x-tenant-id, x-user-role, x-user-id headers before middleware sets them (prevent header spoofing)
- [ ] HMAC-sign tenant identity headers or use server-side getAuth() in each API route instead of trusting headers
- [ ] Webhook signature verification (Clerk svix signatures) on /api/webhooks endpoint
- [ ] MCP server authentication -- currently no inbound auth check on tool invocations
- [ ] Rate limiting on API endpoints (mentioned in ARCHITECTURE.md but not implemented in code)

### Secrets Management
- [x] API keys loaded from environment variables (ANTHROPIC_API_KEY, OPENAI_API_KEY, VOYAGE_API_KEY, SUPABASE_KEY, LANGSMITH_API_KEY)
- [ ] Fail-fast startup validation when required API keys are missing (currently defaults to empty strings)
- [ ] Migrate n8n workflow API keys from webhook payload passthrough to encrypted credential storage
- [ ] Replace default database credentials in .env.example with obviously invalid placeholders
- [ ] Secret scanning pre-commit hook to prevent accidental credential commits

### Prompt Injection Defense
- [x] sanitize_prompt_input() function strips injection patterns (ignore instructions, system prompt delimiters, role-play attempts) in all three prompt modules
- [x] XML tag boundary (`<contract_document>`, `<clause_text>`, `<related_clauses>`) separating instructions from user-controlled data
- [x] Explicit REMINDER instructions in prompts telling the LLM to ignore directives in contract text
- [x] Separate system message and user message roles defined in prompt structure
- [ ] Classifier-based injection detection (e.g., NeMo Guardrails, Lakera Guard) as production complement to regex-based sanitization
- [ ] Output validation to detect anomalous LLM responses (e.g., zero clauses from a multi-page contract)

### Data Protection
- [x] PII redaction before LLM API calls using Microsoft Presidio with typed placeholders (pii_redactor.py)
- [x] De-anonymization mapping for restoring original values after LLM processing
- [x] Legal term allowlist to suppress false positive PII detection on jurisdiction names, entity types, and legal roles
- [x] Context-aware false positive filtering (e.g., "governed by the laws of [STATE]" not treated as PII)
- [ ] Encrypt PII entity mapping at rest with per-request keys
- [ ] TTL-based automatic purging of PII de-anonymization mappings
- [ ] Document encryption at rest (AES-256 via KMS with per-tenant keys) -- noted in code comments as production requirement
- [ ] TLS 1.3 enforcement for all data in transit

### Security Headers
- [x] X-Content-Type-Options: nosniff on API routes (vercel.json)
- [x] X-Frame-Options: DENY on API routes (vercel.json)
- [x] Cache-Control: no-store, must-revalidate on API routes (vercel.json)
- [ ] Content-Security-Policy header
- [ ] Strict-Transport-Security header (HSTS)
- [ ] Referrer-Policy: strict-origin-when-cross-origin
- [ ] Permissions-Policy: camera=(), microphone=(), geolocation=()

---

## Reliability

### High Availability and Failover
- [x] Multi-model fallback: Claude primary with GPT-4 fallback for clause extraction (clause_extractor.py)
- [x] Per-provider circuit breakers (pybreaker, fail_max=5, reset_timeout=60s) preventing cascading failures
- [x] Retry with exponential backoff (tenacity, 3 attempts, 2-30s wait) on transient errors (429, 5xx, timeouts)
- [x] Graceful degradation: cross-reference analysis returns empty results on failure rather than failing the pipeline
- [x] Pipeline error handling: each workflow stage catches exceptions and sets ProcessingStatus.FAILED with error message
- [ ] Database connection pooling with health checks and automatic reconnection
- [ ] Redis cluster or sentinel for task queue high availability
- [ ] API server horizontal scaling with 2+ replicas behind load balancer
- [ ] Database read replicas for search-heavy query paths

### Processing Resilience
- [x] Trigger.dev job with distributed checkpointing between pipeline stages (contract_extraction.ts)
- [x] Failed contract status tracking (processing_status set to "failed" with error message on pipeline failure)
- [x] Processing status state machine (uploaded -> queued -> processing -> extracted -> review_pending -> reviewed | failed | reprocessing)
- [x] SHA-256 file hash computation for document deduplication
- [ ] Idempotent extraction -- reprocessing the same document should not create duplicate clauses
- [ ] Dead letter queue for permanently failed extraction jobs
- [ ] Automatic retry of transiently failed documents after backoff period

### Backup and Recovery
- [ ] Automated database backups with point-in-time recovery
- [ ] Backup verification via periodic restore tests
- [ ] Document storage backup strategy for Supabase Storage buckets
- [ ] Disaster recovery runbook with RTO/RPO targets
- [ ] Export job artifact retention policy

---

## Observability

### Logging
- [x] Python structured logging via standard logging module (clause_extractor.py, analysis_workflow.py)
- [x] Trigger.dev logger for pipeline stage tracking with structured metadata (contract_extraction.ts)
- [x] Processing status transitions logged at each workflow stage
- [x] Circuit breaker state changes logged (OPEN warnings, fallback triggers)
- [ ] Centralized log aggregation (Datadog, CloudWatch, or equivalent)
- [ ] Correlation IDs across pipeline stages for request tracing
- [ ] Sanitized error messages in user-facing responses (currently exposes raw exception strings)

### LLM Observability
- [x] LangSmith tracing integration with @traceable decorator for all pipeline stages (tracing_config.py)
- [x] Per-extraction cost tracking (input/output token counts, USD cost calculation)
- [x] Token usage metrics stored per clause (token_count_input, token_count_output, processing_latency_ms)
- [x] Model version tracking per extraction (model_id and prompt_version stored on every clause)
- [x] Environment-aware project naming (contract-intelligence-dev, contract-intelligence-staging, contract-intelligence-prod)
- [x] Custom evaluators: extraction accuracy F1, hallucination detection, risk flag precision, conflict detection recall
- [ ] Confidence score distribution monitoring to detect model degradation
- [ ] Fallback trigger rate alerting (primary model failure rate)
- [ ] Human override correlation tracking with confidence scores (calibration monitoring)

### Metrics and Alerting
- [x] Deal summary dashboard view with aggregated metrics (deal_summary SQL view)
- [x] Risk flag severity breakdown (critical/high/medium/low counts per deal)
- [x] Review completion percentage tracking
- [x] Average confidence score calculation per deal
- [ ] API request latency monitoring (p50, p95, p99) with >2s alert threshold
- [ ] API error rate (5xx) monitoring with >1% alert threshold
- [ ] Document processing time alerting (>5 min single doc, >6 hr batch of 200)
- [ ] Database connection pool utilization monitoring (>80% alert)
- [ ] Storage utilization monitoring (>75% alert)
- [ ] LLM API error rate monitoring (>2% alert)
- [ ] PagerDuty or Opsgenie integration for on-call alerting

---

## Performance

### Caching
- [ ] Search result caching with 5-minute TTL, invalidated on new document processing for same deal
- [ ] Dashboard aggregation caching with 1-minute TTL, invalidated on clause review action
- [ ] User session/auth caching with 1-hour TTL
- [ ] Clause library standards caching with 24-hour TTL
- [ ] Redis-backed cache layer for frequently accessed data

### Database Optimization
- [x] HNSW vector similarity index on clause_embeddings (m=16, ef_construction=128, cosine distance)
- [x] GIN full-text search index on clauses.extracted_text for BM25 keyword search
- [x] GIN trigram index for fuzzy text search (pg_trgm extension enabled)
- [x] Partial indexes for hot query paths: risk_level IN ('high', 'critical'), review_status = 'pending_review', confidence < 0.85
- [x] Covering indexes on foreign keys (contract_id, deal_id, tenant_id) for efficient joins
- [x] File hash index for O(1) deduplication lookups
- [x] Timestamp descending indexes on audit_log and clauses for recent-first queries
- [x] GIN index on JSONB columns (contracts.parties, playbooks.rules)
- [ ] Materialized views for dashboard aggregate risk scores (mentioned in architecture, not implemented)
- [ ] Database connection pooling configuration (PgBouncer or Supabase pooler)
- [ ] Query performance monitoring and slow query logging

### Processing Optimization
- [x] Dual document processing pipeline: Docling (fast, free) for native PDFs, Azure Document Intelligence (OCR) for scanned PDFs
- [x] Scanned vs. native PDF auto-detection (<100ms) based on text-to-filesize ratio, image coverage, OCR artifact fonts
- [x] Clause-level hierarchical chunking (200-500 tokens) preserving legal document structure
- [x] Batch embedding generation via Voyage AI (32 chunks per request)
- [x] Low LLM temperature (0.2) for deterministic extraction
- [x] Full-contract single-pass extraction (no per-clause API calls) leveraging Claude's 200K context window
- [ ] Async export generation via Celery workers with WebSocket progress updates
- [ ] Parallel export format generation (Excel, PPTX, PDF concurrently)

### Load Testing
- [ ] Load test suite covering extraction pipeline under concurrent deal processing
- [ ] Search latency benchmarks under concurrent query load (target: <200ms p95 hybrid search)
- [ ] Export generation benchmarks (target: 20-60s for 200 contracts)
- [ ] Database connection exhaustion testing

---

## Compliance

### Audit Trail
- [x] Immutable audit_log table with tenant_id, user_id, action, resource_type, resource_id, details JSONB, ip_address, user_agent, session_id
- [x] Audit log trigger function (audit_log_trigger) for automatic mutation logging on core tables
- [x] Route access audit logging in Clerk middleware (user_id, action, resource, method, role, tenant_id)
- [x] RLS policy on audit_log ensuring tenants can only see their own audit entries
- [x] Indexed audit queries: by resource (resource_type, resource_id), by user (user_id, created_at DESC), by tenant (tenant_id, created_at DESC)
- [ ] Audit trigger activation on core tables (contracts, clauses, risk_flags) -- defined but commented out for performance
- [ ] SOC 2 audit logging: every LLM call logged with user_id, tenant_id, document_id, model_used, timestamp, extraction_id
- [ ] Audit log immutability enforcement (prevent UPDATE/DELETE on audit_log)
- [ ] Audit log retention policy and archival strategy

### Data Retention and Privacy
- [x] PII detection and redaction pipeline before external LLM API calls (Presidio-based)
- [x] Zero Data Retention (ZDR) agreements referenced for Anthropic and OpenAI
- [ ] Data retention policy per tenant with configurable retention periods
- [ ] Automated data purging for expired deals and contracts
- [ ] Right to erasure (GDPR Article 17) implementation
- [ ] Data processing agreements (DPAs) with all third-party data processors
- [ ] Data residency enforcement (tenant.data_residency field exists but not enforced)

### Access Controls
- [x] Row-Level Security policies on all 9 tenant-scoped tables (Supabase migration)
- [x] Role-based route protection: partner-only for settings/team/playbooks, partner+associate for upload/review/export
- [x] User role enum (associate, senior_associate, partner, admin)
- [x] Clause review tracking with reviewed_by user ID and reviewed_at timestamp
- [x] Risk flag resolution tracking with resolved_by and resolution_notes
- [ ] Field-level encryption for highly sensitive clause text
- [ ] Export download access controls (currently pre-signed URLs with 24hr expiry)
- [ ] Session management: concurrent session limits, forced logout on role change

---

## Deployment

### CI/CD Pipeline
- [x] Vercel deployment configuration for Next.js frontend (vercel.json)
- [x] Supabase migration files for database schema versioning (supabase/migrations/)
- [x] Promptfoo evaluation configuration for automated prompt regression testing (promptfooconfig.yaml)
- [x] RAGAS and Braintrust evaluation scripts for extraction quality benchmarking (evals/)
- [ ] Automated CI pipeline (GitHub Actions or equivalent) running tests on every PR
- [ ] Automated database migration deployment on merge to main
- [ ] Prompt regression tests integrated into CI (run promptfoo on model update PRs)
- [ ] Docker containerization for API and worker services
- [ ] Infrastructure as Code (Terraform, Pulumi, or SST) for reproducible environments

### Rollback Strategy
- [x] Database migration versioning via Supabase CLI (sequential numbered migrations)
- [x] Model version and prompt version tracking on every extracted clause for auditability
- [ ] Blue-green or canary deployment strategy for API updates
- [ ] Feature flags for gradual rollout of new extraction models or prompt versions
- [ ] One-click rollback procedure for API deployments
- [ ] Database migration rollback scripts (reverse migrations)

### Environment Management
- [x] Environment-based LangSmith project naming (dev, staging, prod)
- [x] Environment-aware cookie security (secure: true only in production, clerk/middleware.ts)
- [x] Cron job scheduling via Vercel for extraction monitoring (hourly) and deal summary emails (weekly Monday 9am)
- [ ] Staging environment that mirrors production data schema
- [ ] Production access controls (principle of least privilege for deployment credentials)
- [ ] Secrets rotation strategy for API keys and database credentials
- [ ] Dependency vulnerability scanning (pip-audit, npm audit, Dependabot or Renovate)

### Monitoring in Production
- [ ] Health check endpoints for API server and worker processes
- [ ] Uptime monitoring with external synthetic checks
- [ ] Error tracking service (Sentry) with source maps for frontend and backend
- [ ] Runbook for common operational scenarios (LLM API outage, database failover, queue backlog)
- [ ] Incident response process with defined severity levels and escalation paths
