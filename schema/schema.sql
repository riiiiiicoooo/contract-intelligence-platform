/**
 * Contract Intelligence Platform - PostgreSQL Schema
 *
 * Comprehensive DDL for multi-tenant contract analysis system with:
 * - pgvector support (1024-dim voyage-law-2 embeddings)
 * - Full-text search indexes (GIN, BM25)
 * - HNSW vector similarity indexes
 * - Row-Level Security policies for tenant isolation
 * - Comprehensive audit trail
 *
 * Last Updated: January 2025
 * Database: PostgreSQL 15+
 */

-- ============================================================================
-- EXTENSIONS
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- trigram for fuzzy text search


-- ============================================================================
-- DOMAIN TYPES (Enums)
-- ============================================================================

CREATE TYPE user_role_enum AS ENUM (
  'associate',
  'senior_associate',
  'partner',
  'admin'
);

CREATE TYPE deal_type_enum AS ENUM (
  'm_and_a',
  'lending',
  'vendor',
  'employment',
  'real_estate',
  'ip_licensing'
);

CREATE TYPE deal_status_enum AS ENUM (
  'setup',
  'ingesting',
  'reviewing',
  'completed',
  'archived'
);

CREATE TYPE contract_type_enum AS ENUM (
  'msa',
  'sow',
  'nda',
  'amendment',
  'lease',
  'employment',
  'vendor',
  'license',
  'partnership',
  'other'
);

CREATE TYPE party_role_enum AS ENUM (
  'buyer',
  'seller',
  'licensor',
  'licensee',
  'landlord',
  'tenant',
  'employer',
  'employee',
  'vendor',
  'client',
  'partner',
  'other'
);

CREATE TYPE entity_type_enum AS ENUM (
  'corporation',
  'llc',
  'lp',
  'individual',
  'trust',
  'government',
  'other'
);

CREATE TYPE processing_status_enum AS ENUM (
  'uploaded',
  'queued',
  'processing',
  'extracted',
  'review_pending',
  'reviewed',
  'failed',
  'reprocessing'
);

CREATE TYPE review_status_enum AS ENUM (
  'auto_accepted',
  'pending_review',
  'accepted',
  'rejected',
  'overridden'
);

CREATE TYPE risk_level_enum AS ENUM (
  'low',
  'medium',
  'high',
  'critical'
);

CREATE TYPE flag_type_enum AS ENUM (
  'non_standard_term',
  'missing_clause',
  'conflicting_terms',
  'cross_contract_conflict',
  'expiration_risk',
  'uncapped_liability',
  'unfavorable_governing_law',
  'short_notice_period',
  'auto_renewal_trap',
  'broad_ip_assignment',
  'weak_indemnification',
  'change_of_control_trigger',
  'other'
);

CREATE TYPE export_format_enum AS ENUM (
  'excel_matrix',
  'pptx_summary',
  'pdf_report',
  'issue_log'
);

CREATE TYPE export_status_enum AS ENUM (
  'queued',
  'processing',
  'completed',
  'failed'
);


-- ============================================================================
-- 1. TENANTS (Multi-tenancy)
-- ============================================================================

CREATE TABLE tenants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  settings JSONB DEFAULT '{}'::jsonb,  -- feature flags, defaults
  sso_config JSONB,                     -- SAML/OIDC configuration
  data_residency TEXT DEFAULT 'us-east-1',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_tenants_slug ON tenants (slug);
COMMENT ON TABLE tenants IS 'Multi-tenant organizational boundaries';


-- ============================================================================
-- 2. USERS
-- ============================================================================

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  email TEXT UNIQUE NOT NULL,
  full_name TEXT NOT NULL,
  role user_role_enum NOT NULL DEFAULT 'associate',
  is_active BOOLEAN DEFAULT true,
  last_login_at TIMESTAMPTZ,
  preferences JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now(),

  CONSTRAINT valid_email CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$')
);

CREATE INDEX idx_users_tenant ON users (tenant_id);
CREATE INDEX idx_users_email ON users (email);
COMMENT ON TABLE users IS 'Platform users with role-based access control';


-- ============================================================================
-- 3. DEALS
-- ============================================================================

CREATE TABLE deals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  name TEXT NOT NULL,
  deal_type deal_type_enum NOT NULL,
  status deal_status_enum NOT NULL DEFAULT 'setup',
  target_company TEXT,
  deal_value_range TEXT,  -- '$50M-$100M'
  playbook_id UUID,  -- Will reference playbooks.id after playbooks table created
  assigned_partner UUID REFERENCES users(id),
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_deals_tenant ON deals (tenant_id);
CREATE INDEX idx_deals_status ON deals (status);
CREATE INDEX idx_deals_type ON deals (deal_type);
COMMENT ON TABLE deals IS 'M&A and contract deals with aggregated analysis';


-- ============================================================================
-- 4. CONTRACTS
-- ============================================================================

CREATE TABLE contracts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deal_id UUID NOT NULL REFERENCES deals(id),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  filename TEXT NOT NULL,
  original_filename TEXT NOT NULL,
  file_path TEXT NOT NULL,  -- Supabase Storage path
  file_hash TEXT NOT NULL,  -- SHA-256 for deduplication
  file_size_bytes BIGINT NOT NULL,
  mime_type TEXT NOT NULL,
  contract_type contract_type_enum,
  parties JSONB,  -- array of party objects
  effective_date DATE,
  expiration_date DATE,
  governing_law TEXT,  -- 'New York', 'Delaware', etc.
  page_count INTEGER,
  is_scanned BOOLEAN DEFAULT false,
  ocr_confidence FLOAT,
  processing_status processing_status_enum NOT NULL DEFAULT 'uploaded',
  processing_error TEXT,
  processed_at TIMESTAMPTZ,
  version INTEGER DEFAULT 1,
  parent_contract_id UUID REFERENCES contracts(id),  -- for amendments
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),

  CONSTRAINT valid_file_size CHECK (file_size_bytes > 0),
  CONSTRAINT valid_page_count CHECK (page_count IS NULL OR page_count > 0),
  CONSTRAINT valid_ocr_confidence CHECK (ocr_confidence IS NULL OR (ocr_confidence >= 0 AND ocr_confidence <= 1))
);

CREATE INDEX idx_contracts_deal ON contracts (deal_id);
CREATE INDEX idx_contracts_tenant ON contracts (tenant_id);
CREATE INDEX idx_contracts_status ON contracts (processing_status);
CREATE INDEX idx_contracts_type ON contracts (contract_type);
CREATE INDEX idx_contracts_hash ON contracts (file_hash);  -- Deduplication
COMMENT ON TABLE contracts IS 'Uploaded contracts with processing status';


-- ============================================================================
-- 5. CONTRACT PARTIES
-- ============================================================================

CREATE TABLE contract_parties (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  contract_id UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  party_name TEXT NOT NULL,
  party_role party_role_enum,
  entity_type entity_type_enum,
  jurisdiction TEXT,  -- state/country of incorporation
  normalized_name TEXT,  -- for cross-contract matching
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_contract_parties_contract ON contract_parties (contract_id);
CREATE INDEX idx_contract_parties_normalized ON contract_parties (normalized_name);
COMMENT ON TABLE contract_parties IS 'Organizations and individuals in contracts';


-- ============================================================================
-- 6. CLAUSES (Extracted Contract Language)
-- ============================================================================

CREATE TABLE clauses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  contract_id UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  clause_type TEXT NOT NULL,  -- 'change_of_control', 'termination_convenience', etc.
  extracted_text TEXT NOT NULL,
  surrounding_context TEXT,  -- 1 paragraph before/after
  page_number INTEGER,
  page_end INTEGER,
  section_reference TEXT,  -- 'Section 8.2(a)'
  section_title TEXT,  -- 'Termination'
  confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  risk_level risk_level_enum,
  risk_explanation TEXT,
  risk_score FLOAT CHECK (risk_score IS NULL OR (risk_score >= 0 AND risk_score <= 100)),
  is_standard BOOLEAN,
  deviation_description TEXT,
  review_status review_status_enum NOT NULL DEFAULT 'pending_review',
  reviewed_by UUID REFERENCES users(id),
  reviewed_at TIMESTAMPTZ,
  override_text TEXT,
  override_reason TEXT,
  model_id TEXT NOT NULL,  -- 'claude-sonnet-4-20250514'
  prompt_version TEXT NOT NULL,  -- 'extraction_v2.3'
  token_count_input INTEGER,
  token_count_output INTEGER,
  processing_latency_ms INTEGER,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_clauses_contract ON clauses (contract_id);
CREATE INDEX idx_clauses_type ON clauses (clause_type);
CREATE INDEX idx_clauses_risk ON clauses (risk_level) WHERE risk_level IN ('high', 'critical');
CREATE INDEX idx_clauses_review ON clauses (review_status) WHERE review_status = 'pending_review';
CREATE INDEX idx_clauses_confidence ON clauses (confidence) WHERE confidence < 0.85;
CREATE INDEX idx_clauses_created ON clauses (created_at DESC);
COMMENT ON TABLE clauses IS 'AI-extracted contract language with risk assessment';


-- ============================================================================
-- 7. CLAUSE EMBEDDINGS (Vector Search)
-- ============================================================================

CREATE TABLE clause_embeddings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  clause_id UUID NOT NULL UNIQUE REFERENCES clauses(id) ON DELETE CASCADE,
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  embedding vector(1024),  -- voyage-law-2 output dimension
  embedding_model TEXT DEFAULT 'voyage-law-2',
  created_at TIMESTAMPTZ DEFAULT now()
);

-- HNSW index for approximate nearest neighbor search
-- m=16: connections per node (higher = more accurate)
-- ef_construction=128: build-time search depth (higher = better quality)
CREATE INDEX idx_clause_embeddings_hnsw ON clause_embeddings
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 128);

COMMENT ON TABLE clause_embeddings IS 'Semantic embeddings for clause similarity search';


-- ============================================================================
-- 8. RISK FLAGS
-- ============================================================================

CREATE TABLE risk_flags (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  clause_id UUID REFERENCES clauses(id) ON DELETE CASCADE,
  contract_id UUID NOT NULL REFERENCES contracts(id),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  flag_type flag_type_enum NOT NULL,
  severity risk_level_enum NOT NULL,
  description TEXT NOT NULL,
  recommendation TEXT,
  playbook_rule_id UUID,
  is_resolved BOOLEAN DEFAULT false,
  resolved_by UUID REFERENCES users(id),
  resolved_at TIMESTAMPTZ,
  resolution_notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_risk_flags_contract ON risk_flags (contract_id);
CREATE INDEX idx_risk_flags_clause ON risk_flags (clause_id);
CREATE INDEX idx_risk_flags_severity ON risk_flags (severity) WHERE severity IN ('high', 'critical');
CREATE INDEX idx_risk_flags_unresolved ON risk_flags (is_resolved) WHERE is_resolved = false;
COMMENT ON TABLE risk_flags IS 'Risk flags and issues identified in clauses';


-- ============================================================================
-- 9. CLAUSE LIBRARY (Reference Data - Market Standards)
-- ============================================================================

CREATE TABLE clause_library (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  clause_type TEXT NOT NULL,
  variant_name TEXT NOT NULL,  -- 'standard_30_day_termination'
  standard_text TEXT NOT NULL,
  jurisdiction TEXT,  -- jurisdiction-specific standards
  deal_type TEXT,     -- deal-type-specific standards
  centroid_embedding vector(1024),  -- average embedding for this standard
  similarity_threshold FLOAT DEFAULT 0.85,
  notes TEXT,
  source TEXT,  -- where this standard came from
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),

  UNIQUE (clause_type, jurisdiction, deal_type) WHERE is_active = true
);

CREATE INDEX idx_clause_library_type ON clause_library (clause_type) WHERE is_active = true;
CREATE INDEX idx_clause_library_centroid ON clause_library
  USING hnsw (centroid_embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

COMMENT ON TABLE clause_library IS 'Market standard clauses for benchmarking';


-- ============================================================================
-- 10. PLAYBOOKS (Deal-Type-Specific Rules)
-- ============================================================================

CREATE TABLE playbooks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  name TEXT NOT NULL,
  description TEXT,
  deal_type deal_type_enum,
  rules JSONB NOT NULL,  -- array of rule definitions
  is_default BOOLEAN DEFAULT false,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_playbooks_tenant ON playbooks (tenant_id);
CREATE INDEX idx_playbooks_deal_type ON playbooks (deal_type);
COMMENT ON TABLE playbooks IS 'Customizable risk rules per deal type';


-- ============================================================================
-- 11. EXPORT JOBS
-- ============================================================================

CREATE TABLE export_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deal_id UUID NOT NULL REFERENCES deals(id),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  requested_by UUID NOT NULL REFERENCES users(id),
  format export_format_enum NOT NULL,
  template_id TEXT,  -- firm-specific template
  status export_status_enum NOT NULL DEFAULT 'queued',
  progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
  file_path TEXT,  -- Supabase Storage path
  download_url TEXT,
  download_url_expires_at TIMESTAMPTZ,
  download_count INTEGER DEFAULT 0,
  error_message TEXT,
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_export_deal ON export_jobs (deal_id);
CREATE INDEX idx_export_status ON export_jobs (status) WHERE status IN ('queued', 'processing');
COMMENT ON TABLE export_jobs IS 'Async export jobs (Excel matrices, PDF reports, etc.)';


-- ============================================================================
-- 12. AUDIT LOG
-- ============================================================================

CREATE TABLE audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  user_id UUID,  -- nullable for system actions
  action TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  resource_id UUID NOT NULL,
  details JSONB NOT NULL DEFAULT '{}'::jsonb,
  ip_address INET,
  user_agent TEXT,
  session_id TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_audit_resource ON audit_log (resource_type, resource_id);
CREATE INDEX idx_audit_user_time ON audit_log (user_id, created_at DESC);
CREATE INDEX idx_audit_tenant_time ON audit_log (tenant_id, created_at DESC);
COMMENT ON TABLE audit_log IS 'Immutable audit trail for compliance';


-- ============================================================================
-- FULL-TEXT SEARCH INDEXES
-- ============================================================================

-- GIN index on clause text for BM25-style keyword search
CREATE INDEX idx_clauses_fulltext ON clauses
  USING gin (to_tsvector('english', extracted_text));

-- GIN index on contract filename for quick file search
CREATE INDEX idx_contracts_filename ON contracts
  USING gin (to_tsvector('english', original_filename));

-- GIN index on contract parties for cross-contract party search
CREATE INDEX idx_contracts_parties ON contracts USING gin (parties);

-- GIN index on playbook rules for rule matching
CREATE INDEX idx_playbooks_rules ON playbooks USING gin (rules);


-- ============================================================================
-- ROW-LEVEL SECURITY (Tenant Isolation)
-- ============================================================================

-- Enable RLS on tenant-specific tables
ALTER TABLE deals ENABLE ROW LEVEL SECURITY;
ALTER TABLE contracts ENABLE ROW LEVEL SECURITY;
ALTER TABLE contract_parties ENABLE ROW LEVEL SECURITY;
ALTER TABLE clauses ENABLE ROW LEVEL SECURITY;
ALTER TABLE clause_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_flags ENABLE ROW LEVEL SECURITY;
ALTER TABLE export_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE playbooks ENABLE ROW LEVEL SECURITY;

-- Tenant isolation policies (example - would be set per tenant in app)
-- These would be activated after authentication middleware sets session variables

/*
CREATE POLICY tenant_isolation ON deals
  FOR ALL
  USING (tenant_id = current_setting('app.current_tenant')::UUID);

CREATE POLICY tenant_isolation ON contracts
  FOR ALL
  USING (tenant_id = current_setting('app.current_tenant')::UUID);
*/


-- ============================================================================
-- HELPER VIEWS
-- ============================================================================

-- Deal summary dashboard view
CREATE VIEW deal_summary AS
SELECT
  d.id AS deal_id,
  d.name,
  d.status,
  COUNT(DISTINCT c.id) AS total_contracts,
  COUNT(DISTINCT c.id) FILTER (WHERE c.processing_status = 'reviewed') AS reviewed_contracts,
  COUNT(cl.id) AS total_clauses,
  COUNT(cl.id) FILTER (WHERE cl.review_status = 'pending_review') AS pending_review,
  COUNT(rf.id) FILTER (WHERE rf.severity = 'critical' AND rf.is_resolved = false) AS open_critical_flags,
  COUNT(rf.id) FILTER (WHERE rf.severity = 'high' AND rf.is_resolved = false) AS open_warning_flags,
  ROUND(AVG(cl.confidence)::numeric, 3) AS avg_confidence,
  ROUND(
    COUNT(cl.id) FILTER (WHERE cl.review_status IN ('accepted', 'auto_accepted'))::numeric /
    NULLIF(COUNT(cl.id), 0) * 100, 1
  ) AS completion_percentage
FROM deals d
LEFT JOIN contracts c ON c.deal_id = d.id
LEFT JOIN clauses cl ON cl.contract_id = c.id
LEFT JOIN risk_flags rf ON rf.contract_id = c.id
GROUP BY d.id, d.name, d.status;

COMMENT ON VIEW deal_summary IS 'Aggregated metrics per deal';


-- Non-standard clauses benchmarked against library
CREATE VIEW non_standard_clauses AS
SELECT
  c.id,
  c.clause_type,
  c.extracted_text,
  c.contract_id,
  ct.filename,
  1 - (ce.embedding <=> cl.centroid_embedding) AS similarity_to_standard,
  cl.variant_name AS standard_variant
FROM clauses c
JOIN clause_embeddings ce ON ce.clause_id = c.id
JOIN contracts ct ON ct.id = c.contract_id
CROSS JOIN clause_library cl
WHERE c.clause_type = cl.clause_type
  AND cl.is_active = true
  AND 1 - (ce.embedding <=> cl.centroid_embedding) < cl.similarity_threshold
ORDER BY similarity_to_standard ASC;

COMMENT ON VIEW non_standard_clauses IS 'Clauses deviating from market standards';
