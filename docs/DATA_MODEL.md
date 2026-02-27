# Data Model: Contract Intelligence Platform

**Last Updated:** January 2025
**Database:** PostgreSQL 15 (via Supabase) + pgvector + pgvectorscale

---

## 1. Entity Relationship Diagram

```
┌───────────────┐
│    tenants    │
│───────────────│
│ id (PK)       │
│ name          │
│ settings      │
│ sso_config    │
└───────┬───────┘
        │
        │ 1:N
        ▼
┌───────────────┐       ┌───────────────┐
│    users      │       │    deals      │
│───────────────│       │───────────────│
│ id (PK)       │       │ id (PK)       │
│ tenant_id(FK) │       │ tenant_id(FK) │
│ email         │       │ name          │
│ role          │       │ deal_type     │
│ full_name     │       │ status        │
└───────┬───────┘       └───────┬───────┘
        │                       │
        │                       │ 1:N
        │                       ▼
        │               ┌───────────────┐       ┌───────────────────┐
        │               │  contracts    │       │  contract_parties │
        │               │───────────────│       │───────────────────│
        │               │ id (PK)       │──1:N──│ id (PK)           │
        │               │ deal_id (FK)  │       │ contract_id (FK)  │
        │               │ tenant_id(FK) │       │ party_name        │
        │               │ filename      │       │ party_role        │
        │               │ contract_type │       │ entity_type       │
        │               │ processing_   │       └───────────────────┘
        │               │   status      │
        │               └───────┬───────┘
        │                       │
        │                       │ 1:N
        │                       ▼
        │               ┌───────────────┐       ┌───────────────────┐
        │               │   clauses     │──1:1──│ clause_embeddings │
        │               │───────────────│       │───────────────────│
        │               │ id (PK)       │       │ id (PK)           │
        │               │ contract_id   │       │ clause_id (FK)    │
        │               │ clause_type   │       │ embedding         │
        │               │ extracted_text│       │   vector(1024)    │
        │               │ confidence    │       └───────────────────┘
        │               │ risk_level    │
        │               │ review_status │
        │               │ reviewed_by   │──FK──> users
        │               └───────┬───────┘
        │                       │
        │                       │ 1:N
        │                       ▼
        │               ┌───────────────┐
        │               │  risk_flags   │
        │               │───────────────│
        │               │ id (PK)       │
        │               │ clause_id(FK) │
        │               │ flag_type     │
        │               │ severity      │
        │               │ description   │
        │               │ playbook_ref  │
        │               └───────────────┘
        │
        │               ┌───────────────┐
        │               │ export_jobs   │
        │               │───────────────│
        │               │ id (PK)       │
        │               │ deal_id (FK)  │
        │               │ requested_by  │──FK──> users
        │               │ format        │
        │               │ status        │
        │               │ file_path     │
        │               │ download_url  │
        │               └───────────────┘
        │
        └──────────────▶┌───────────────┐
                        │  audit_log    │
                        │───────────────│
                        │ id (PK)       │
                        │ tenant_id(FK) │
                        │ user_id (FK)  │
                        │ action        │
                        │ resource_type │
                        │ resource_id   │
                        │ details       │
                        │ ip_address    │
                        └───────────────┘

        ┌───────────────┐
        │clause_library │  (reference data - standard clause benchmarks)
        │───────────────│
        │ id (PK)       │
        │ clause_type   │
        │ standard_text │
        │ jurisdiction  │
        │ centroid      │
        │   vector(1024)│
        │ threshold     │
        └───────────────┘

        ┌───────────────┐
        │  playbooks    │  (configurable risk rules per client/deal type)
        │───────────────│
        │ id (PK)       │
        │ tenant_id(FK) │
        │ name          │
        │ deal_type     │
        │ rules         │
        └───────────────┘
```

---

## 2. Full Schema Definition

### 2.1 Tenants

```sql
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,                    -- URL-friendly identifier
    settings JSONB DEFAULT '{}'::jsonb,           -- feature flags, defaults
    sso_config JSONB,                             -- SAML/OIDC configuration
    data_residency TEXT DEFAULT 'us-east-1',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Example settings JSONB:
-- {
--   "default_playbook_id": "uuid",
--   "max_file_size_mb": 500,
--   "allowed_export_formats": ["excel", "pptx", "pdf"],
--   "require_partner_approval": true,
--   "auto_approve_confidence_threshold": 0.90
-- }
```

### 2.2 Users

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY REFERENCES auth.users(id),  -- Supabase Auth
    tenant_id UUID REFERENCES tenants(id) NOT NULL,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('associate', 'senior_associate', 'partner', 'admin')),
    is_active BOOLEAN DEFAULT true,
    last_login_at TIMESTAMPTZ,
    preferences JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### 2.3 Deals

```sql
CREATE TABLE deals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) NOT NULL,
    name TEXT NOT NULL,
    deal_type TEXT NOT NULL CHECK (deal_type IN (
        'm_and_a', 'lending', 'vendor', 'employment', 'real_estate', 'ip_licensing'
    )),
    status TEXT NOT NULL CHECK (status IN (
        'setup', 'ingesting', 'reviewing', 'completed', 'archived'
    )) DEFAULT 'setup',
    target_company TEXT,
    deal_value_range TEXT,                         -- '$50M-$100M'
    playbook_id UUID REFERENCES playbooks(id),
    assigned_partner UUID REFERENCES users(id),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Example metadata JSONB:
-- {
--   "client_name": "Alpine Capital Partners",
--   "industry": "healthcare",
--   "expected_close_date": "2025-03-15",
--   "contract_count_estimate": 250,
--   "notes": "Focus on change-of-control and assignment provisions"
-- }
```

### 2.4 Contracts

```sql
CREATE TABLE contracts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id UUID REFERENCES deals(id) NOT NULL,
    tenant_id UUID REFERENCES tenants(id) NOT NULL,
    filename TEXT NOT NULL,
    original_filename TEXT NOT NULL,               -- before sanitization
    file_path TEXT NOT NULL,                       -- Supabase Storage path
    file_hash TEXT NOT NULL,                       -- SHA-256 for deduplication
    file_size_bytes BIGINT NOT NULL,
    mime_type TEXT NOT NULL,
    contract_type TEXT CHECK (contract_type IN (
        'msa', 'sow', 'nda', 'amendment', 'lease', 'employment',
        'vendor', 'license', 'partnership', 'other'
    )),
    parties JSONB,
    effective_date DATE,
    expiration_date DATE,
    governing_law TEXT,                            -- 'New York', 'Delaware', etc.
    page_count INTEGER,
    is_scanned BOOLEAN DEFAULT false,
    ocr_confidence FLOAT,                          -- average OCR confidence if scanned
    processing_status TEXT NOT NULL CHECK (processing_status IN (
        'uploaded', 'queued', 'processing', 'extracted', 'review_pending',
        'reviewed', 'failed', 'reprocessing'
    )) DEFAULT 'uploaded',
    processing_error TEXT,                         -- error message if failed
    processed_at TIMESTAMPTZ,
    version INTEGER DEFAULT 1,
    parent_contract_id UUID REFERENCES contracts(id),  -- for amendments/addenda
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

### 2.5 Contract Parties

```sql
CREATE TABLE contract_parties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id UUID REFERENCES contracts(id) ON DELETE CASCADE NOT NULL,
    tenant_id UUID REFERENCES tenants(id) NOT NULL,
    party_name TEXT NOT NULL,
    party_role TEXT CHECK (party_role IN (
        'buyer', 'seller', 'licensor', 'licensee', 'landlord', 'tenant',
        'employer', 'employee', 'vendor', 'client', 'partner', 'other'
    )),
    entity_type TEXT CHECK (entity_type IN (
        'corporation', 'llc', 'lp', 'individual', 'trust', 'government', 'other'
    )),
    jurisdiction TEXT,                             -- state/country of incorporation
    normalized_name TEXT,                          -- for cross-contract matching
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Index for finding all contracts involving a specific party
CREATE INDEX idx_parties_normalized ON contract_parties (normalized_name);
```

### 2.6 Clauses

```sql
CREATE TABLE clauses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id UUID REFERENCES contracts(id) ON DELETE CASCADE NOT NULL,
    tenant_id UUID REFERENCES tenants(id) NOT NULL,
    clause_type TEXT NOT NULL,                     -- 'change_of_control', 'termination_convenience', etc.
    extracted_text TEXT NOT NULL,                   -- the actual clause text
    surrounding_context TEXT,                       -- 1 paragraph before/after for context
    page_number INTEGER,
    page_end INTEGER,                              -- if clause spans multiple pages
    section_reference TEXT,                         -- 'Section 8.2(a)'
    section_title TEXT,                             -- 'Termination'
    confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    risk_level TEXT CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    risk_explanation TEXT,                          -- AI-generated reasoning
    risk_score FLOAT,                              -- numeric 0-100 for sorting
    is_standard BOOLEAN,                           -- benchmarked against clause library
    deviation_description TEXT,                     -- how it deviates from standard
    review_status TEXT NOT NULL CHECK (review_status IN (
        'auto_accepted',      -- confidence >= threshold, auto-approved
        'pending_review',     -- confidence < threshold, needs human
        'accepted',           -- human reviewed and accepted
        'rejected',           -- human reviewed and rejected extraction
        'overridden'          -- human provided corrected text
    )) DEFAULT 'pending_review',
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMPTZ,
    override_text TEXT,                            -- corrected text if overridden
    override_reason TEXT,
    model_id TEXT NOT NULL,                        -- 'claude-sonnet-4-20250514'
    prompt_version TEXT NOT NULL,                   -- 'extraction_v2.3'
    token_count_input INTEGER,
    token_count_output INTEGER,
    processing_latency_ms INTEGER,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

### 2.7 Clause Embeddings

```sql
CREATE TABLE clause_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clause_id UUID REFERENCES clauses(id) ON DELETE CASCADE NOT NULL,
    tenant_id UUID REFERENCES tenants(id) NOT NULL,
    embedding vector(1024),                        -- voyage-law-2 output dimension
    embedding_model TEXT DEFAULT 'voyage-law-2',
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### 2.8 Risk Flags

```sql
CREATE TABLE risk_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clause_id UUID REFERENCES clauses(id) ON DELETE CASCADE NOT NULL,
    contract_id UUID REFERENCES contracts(id) NOT NULL,
    tenant_id UUID REFERENCES tenants(id) NOT NULL,
    flag_type TEXT NOT NULL CHECK (flag_type IN (
        'non_standard_term',     -- deviates from market standard
        'missing_clause',        -- expected clause not found in contract
        'conflicting_terms',     -- contradicts another clause in same contract
        'cross_contract_conflict', -- contradicts clause in another deal contract
        'expiration_risk',       -- approaching expiration without renewal
        'uncapped_liability',    -- no limitation on liability
        'unfavorable_governing_law',
        'short_notice_period',
        'auto_renewal_trap',     -- auto-renews with difficult exit
        'broad_ip_assignment',
        'weak_indemnification',
        'change_of_control_trigger',
        'other'
    )),
    severity TEXT NOT NULL CHECK (severity IN ('info', 'warning', 'critical')),
    description TEXT NOT NULL,                     -- human-readable explanation
    recommendation TEXT,                           -- suggested action
    playbook_rule_id UUID,                         -- which playbook rule triggered this
    is_resolved BOOLEAN DEFAULT false,
    resolved_by UUID REFERENCES users(id),
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### 2.9 Clause Library (Reference Data)

```sql
CREATE TABLE clause_library (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clause_type TEXT NOT NULL,
    variant_name TEXT NOT NULL,                    -- 'standard_30_day_termination'
    standard_text TEXT NOT NULL,                    -- benchmark clause text
    jurisdiction TEXT,                              -- jurisdiction-specific standards
    deal_type TEXT,                                 -- deal-type-specific standards
    centroid_embedding vector(1024),               -- average embedding for this standard
    similarity_threshold FLOAT DEFAULT 0.85,       -- cosine distance threshold for "standard"
    notes TEXT,
    source TEXT,                                    -- where this standard came from
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Unique standard per clause_type + jurisdiction + deal_type
CREATE UNIQUE INDEX idx_clause_library_unique
    ON clause_library (clause_type, jurisdiction, deal_type)
    WHERE is_active = true;
```

### 2.10 Playbooks

```sql
CREATE TABLE playbooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    deal_type TEXT,
    rules JSONB NOT NULL,                          -- array of rule definitions
    is_default BOOLEAN DEFAULT false,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Example rules JSONB:
-- [
--   {
--     "clause_type": "termination_convenience",
--     "condition": "notice_period_days < 30",
--     "severity": "critical",
--     "message": "Notice period below 30 days is non-standard for this deal type"
--   },
--   {
--     "clause_type": "limitation_of_liability",
--     "condition": "is_uncapped",
--     "severity": "critical",
--     "message": "Uncapped liability exposure"
--   },
--   {
--     "clause_type": "change_of_control",
--     "condition": "requires_consent",
--     "severity": "warning",
--     "message": "Change of control triggers consent requirement - flag for buyer"
--   }
-- ]
```

### 2.11 Export Jobs

```sql
CREATE TABLE export_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id UUID REFERENCES deals(id) NOT NULL,
    tenant_id UUID REFERENCES tenants(id) NOT NULL,
    requested_by UUID REFERENCES users(id) NOT NULL,
    format TEXT NOT NULL CHECK (format IN ('excel_matrix', 'pptx_summary', 'pdf_report', 'issue_log')),
    template_id TEXT,                              -- firm-specific template
    status TEXT NOT NULL CHECK (status IN (
        'queued', 'processing', 'completed', 'failed'
    )) DEFAULT 'queued',
    progress INTEGER DEFAULT 0,                    -- 0-100
    file_path TEXT,                                 -- Supabase Storage path
    download_url TEXT,                             -- pre-signed URL
    download_url_expires_at TIMESTAMPTZ,
    download_count INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### 2.12 Audit Log

```sql
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) NOT NULL,
    user_id UUID NOT NULL,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id UUID NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    ip_address INET,
    user_agent TEXT,
    session_id TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Partition by month for performance at scale
-- (implement when audit_log exceeds 10M rows)
-- CREATE TABLE audit_log_2025_01 PARTITION OF audit_log
--     FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
```

---

## 3. Indexing Strategy

### 3.1 Vector Indexes

```sql
-- HNSW index for approximate nearest neighbor search on clause embeddings
-- m=16: connections per node (higher = more accurate, more memory)
-- ef_construction=128: build-time search depth (higher = better index quality)
CREATE INDEX idx_clause_embeddings_hnsw ON clause_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 128);

-- Set search-time parameter (higher = more accurate, slower)
-- Default ef_search = 40, increase for higher recall requirements
SET hnsw.ef_search = 64;

-- Clause library centroid embeddings (smaller table, exact search is fine)
CREATE INDEX idx_clause_library_centroid ON clause_library
    USING hnsw (centroid_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

### 3.2 Full-Text Search Indexes

```sql
-- GIN index on clause text for BM25-style keyword search
CREATE INDEX idx_clauses_fulltext ON clauses
    USING gin (to_tsvector('english', extracted_text));

-- GIN index on contract filename for quick file search
CREATE INDEX idx_contracts_filename ON contracts
    USING gin (to_tsvector('english', original_filename));
```

### 3.3 B-Tree Indexes (Filtering and Lookups)

```sql
-- High-cardinality lookups
CREATE INDEX idx_clauses_contract ON clauses (contract_id);
CREATE INDEX idx_clauses_type ON clauses (clause_type);
CREATE INDEX idx_clauses_risk ON clauses (risk_level) WHERE risk_level IN ('high', 'critical');
CREATE INDEX idx_clauses_review ON clauses (review_status) WHERE review_status = 'pending_review';
CREATE INDEX idx_clauses_confidence ON clauses (confidence) WHERE confidence < 0.85;

CREATE INDEX idx_contracts_deal ON contracts (deal_id);
CREATE INDEX idx_contracts_status ON contracts (processing_status);
CREATE INDEX idx_contracts_type ON contracts (contract_type);
CREATE INDEX idx_contracts_tenant_deal ON contracts (tenant_id, deal_id);

CREATE INDEX idx_risk_flags_contract ON risk_flags (contract_id);
CREATE INDEX idx_risk_flags_severity ON risk_flags (severity) WHERE severity = 'critical';
CREATE INDEX idx_risk_flags_unresolved ON risk_flags (is_resolved) WHERE is_resolved = false;

CREATE INDEX idx_audit_resource ON audit_log (resource_type, resource_id);
CREATE INDEX idx_audit_user_time ON audit_log (user_id, created_at DESC);
CREATE INDEX idx_audit_tenant_time ON audit_log (tenant_id, created_at DESC);

CREATE INDEX idx_export_deal ON export_jobs (deal_id);
CREATE INDEX idx_export_status ON export_jobs (status) WHERE status IN ('queued', 'processing');
```

### 3.4 JSONB Indexes

```sql
-- Index on contract parties for cross-contract party search
CREATE INDEX idx_contracts_parties ON contracts USING gin (parties);

-- Index on playbook rules for rule matching
CREATE INDEX idx_playbooks_rules ON playbooks USING gin (rules);
```

---

## 4. Row-Level Security Policies

Every table with tenant data has RLS enabled. Policies use PostgreSQL session variables set by the API middleware on each request.

```sql
-- Enable RLS on all tenant tables
ALTER TABLE deals ENABLE ROW LEVEL SECURITY;
ALTER TABLE contracts ENABLE ROW LEVEL SECURITY;
ALTER TABLE contract_parties ENABLE ROW LEVEL SECURITY;
ALTER TABLE clauses ENABLE ROW LEVEL SECURITY;
ALTER TABLE clause_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_flags ENABLE ROW LEVEL SECURITY;
ALTER TABLE export_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE playbooks ENABLE ROW LEVEL SECURITY;

-- Tenant isolation: users can only see data from their own tenant
CREATE POLICY tenant_isolation ON deals
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant')::UUID);

CREATE POLICY tenant_isolation ON contracts
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant')::UUID);

CREATE POLICY tenant_isolation ON clauses
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant')::UUID);

-- Role-based access within tenant
-- Associates: see only deals they're assigned to
-- Partners: see all deals in their tenant
-- Admins: full access within tenant
CREATE POLICY role_access ON deals
    FOR SELECT
    USING (
        current_setting('app.user_role') IN ('partner', 'admin')
        OR id IN (
            SELECT deal_id FROM deal_assignments
            WHERE user_id = current_setting('app.user_id')::UUID
        )
    );

-- Audit log: read-only for partners and admins, write by system only
CREATE POLICY audit_read ON audit_log
    FOR SELECT
    USING (
        tenant_id = current_setting('app.current_tenant')::UUID
        AND current_setting('app.user_role') IN ('partner', 'admin')
    );
```

---

## 5. Common Query Patterns

### 5.1 Get all clauses for a contract with risk flags

```sql
SELECT
    c.id,
    c.clause_type,
    c.extracted_text,
    c.page_number,
    c.section_reference,
    c.confidence,
    c.risk_level,
    c.risk_explanation,
    c.review_status,
    c.is_standard,
    json_agg(json_build_object(
        'flag_type', rf.flag_type,
        'severity', rf.severity,
        'description', rf.description,
        'recommendation', rf.recommendation
    )) FILTER (WHERE rf.id IS NOT NULL) AS risk_flags
FROM clauses c
LEFT JOIN risk_flags rf ON rf.clause_id = c.id
WHERE c.contract_id = $1
GROUP BY c.id
ORDER BY
    CASE c.risk_level
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        WHEN 'low' THEN 4
    END,
    c.page_number;
```

### 5.2 Hybrid search (BM25 + vector)

```sql
-- Step 1: BM25 keyword search
WITH bm25_results AS (
    SELECT
        c.id,
        c.extracted_text,
        c.contract_id,
        ts_rank(to_tsvector('english', c.extracted_text), plainto_tsquery($1)) AS bm25_score
    FROM clauses c
    WHERE to_tsvector('english', c.extracted_text) @@ plainto_tsquery($1)
    ORDER BY bm25_score DESC
    LIMIT 50
),

-- Step 2: Vector similarity search
vector_results AS (
    SELECT
        c.id,
        c.extracted_text,
        c.contract_id,
        1 - (ce.embedding <=> $2::vector) AS vector_score  -- $2 = query embedding
    FROM clause_embeddings ce
    JOIN clauses c ON c.id = ce.clause_id
    ORDER BY ce.embedding <=> $2::vector
    LIMIT 50
),

-- Step 3: Reciprocal Rank Fusion
combined AS (
    SELECT
        COALESCE(b.id, v.id) AS clause_id,
        COALESCE(b.extracted_text, v.extracted_text) AS text,
        COALESCE(b.contract_id, v.contract_id) AS contract_id,
        -- RRF formula: 1/(k+rank) with k=60
        COALESCE(1.0 / (60 + ROW_NUMBER() OVER (ORDER BY b.bm25_score DESC NULLS LAST)), 0) +
        COALESCE(1.0 / (60 + ROW_NUMBER() OVER (ORDER BY v.vector_score DESC NULLS LAST)), 0)
        AS rrf_score
    FROM bm25_results b
    FULL OUTER JOIN vector_results v ON b.id = v.id
)

SELECT * FROM combined
ORDER BY rrf_score DESC
LIMIT 20;

-- Step 4: Cohere Rerank (application layer)
-- Send top 20 results to Cohere Rerank API
-- Return top 10 reranked results to user
```

### 5.3 Deal summary dashboard

```sql
SELECT
    d.id AS deal_id,
    d.name,
    d.status,
    COUNT(DISTINCT con.id) AS total_contracts,
    COUNT(DISTINCT con.id) FILTER (WHERE con.processing_status = 'reviewed') AS reviewed_contracts,
    COUNT(cl.id) AS total_clauses,
    COUNT(cl.id) FILTER (WHERE cl.review_status = 'pending_review') AS pending_review,
    COUNT(rf.id) FILTER (WHERE rf.severity = 'critical' AND rf.is_resolved = false) AS open_critical_flags,
    COUNT(rf.id) FILTER (WHERE rf.severity = 'warning' AND rf.is_resolved = false) AS open_warning_flags,
    ROUND(AVG(cl.confidence)::numeric, 3) AS avg_confidence,
    ROUND(
        COUNT(cl.id) FILTER (WHERE cl.review_status IN ('accepted', 'auto_accepted'))::numeric /
        NULLIF(COUNT(cl.id), 0) * 100, 1
    ) AS completion_percentage
FROM deals d
LEFT JOIN contracts con ON con.deal_id = d.id
LEFT JOIN clauses cl ON cl.contract_id = con.id
LEFT JOIN risk_flags rf ON rf.contract_id = con.id
WHERE d.id = $1
GROUP BY d.id;
```

### 5.4 Find non-standard clauses benchmarked against library

```sql
SELECT
    c.id,
    c.clause_type,
    c.extracted_text,
    c.contract_id,
    con.filename,
    1 - (ce.embedding <=> cl.centroid_embedding) AS similarity_to_standard,
    cl.variant_name AS standard_variant
FROM clauses c
JOIN clause_embeddings ce ON ce.clause_id = c.id
JOIN contracts con ON con.id = c.contract_id
CROSS JOIN clause_library cl
WHERE c.clause_type = cl.clause_type
    AND cl.is_active = true
    AND con.deal_id = $1
    AND 1 - (ce.embedding <=> cl.centroid_embedding) < cl.similarity_threshold
ORDER BY similarity_to_standard ASC
LIMIT 50;
```

---

## 6. Data Lifecycle

### 6.1 Document Processing States

```
uploaded -> queued -> processing -> extracted -> review_pending -> reviewed
                         |                                           |
                         v                                           v
                       failed -> reprocessing                    completed
```

### 6.2 Clause Review States

```
                 ┌─────────────────┐
                 │  AI Extraction   │
                 └────────┬────────┘
                          │
                    ┌─────┴──────┐
                    │            │
           conf >= 0.85    conf < 0.85
                    │            │
                    ▼            ▼
            ┌──────────┐  ┌──────────────┐
            │  auto_    │  │  pending_    │
            │  accepted │  │  review      │
            └──────────┘  └──────┬───────┘
                                 │
                          ┌──────┼───────┐
                          ▼      ▼       ▼
                    ┌────────┐ ┌────┐ ┌──────────┐
                    │accepted│ │rej-│ │overridden│
                    │        │ │ect-│ │(corrected│
                    │        │ │ed  │ │ text)    │
                    └────────┘ └────┘ └──────────┘
```

### 6.3 Retention Policy

| Data Type | Retention | Reason |
|---|---|---|
| Active deal data | Duration of engagement + 90 days | Client access during deal |
| Completed deal data | 7 years | Regulatory and audit requirements |
| Audit logs | 7 years | Compliance requirement |
| Export files | 90 days after generation | Storage cost management |
| Clause embeddings | Same as parent clause | Tied to clause lifecycle |
| User sessions | 30 days | Security |

### 6.4 Deletion Cascade

When a deal is archived, the following cascade applies:

```
Deal (archived)
  └── Contracts (soft delete: archived = true)
        └── Clauses (soft delete)
              ├── Clause Embeddings (hard delete - recoverable via re-embedding)
              └── Risk Flags (soft delete)
  └── Export Jobs (hard delete after 90 days)

-- Audit logs are NEVER deleted (regulatory requirement)
```

---

## 7. Migration Strategy

### 7.1 Migration Numbering

```
migrations/
├── 001_create_tenants.sql
├── 002_create_users.sql
├── 003_create_deals.sql
├── 004_create_contracts.sql
├── 005_create_contract_parties.sql
├── 006_create_clauses.sql
├── 007_create_clause_embeddings.sql
├── 008_create_risk_flags.sql
├── 009_create_clause_library.sql
├── 010_create_playbooks.sql
├── 011_create_export_jobs.sql
├── 012_create_audit_log.sql
├── 013_enable_rls.sql
├── 014_create_indexes.sql
└── 015_seed_clause_library.sql
```

### 7.2 Backfill Procedures

When adding new clause types or updating the embedding model:

```sql
-- Backfill embeddings after model upgrade
-- Run as background job, not blocking production
INSERT INTO clause_embeddings (clause_id, tenant_id, embedding, embedding_model)
SELECT
    c.id,
    c.tenant_id,
    generate_embedding(c.extracted_text),  -- application-level function
    'voyage-law-2-v2'
FROM clauses c
LEFT JOIN clause_embeddings ce ON ce.clause_id = c.id AND ce.embedding_model = 'voyage-law-2-v2'
WHERE ce.id IS NULL
ORDER BY c.created_at DESC  -- newest first
LIMIT 1000;                  -- batch processing
```
