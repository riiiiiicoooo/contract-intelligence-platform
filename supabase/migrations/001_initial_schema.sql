-- Supabase Migration: Contract Intelligence Platform - Initial Schema
-- This migration includes RLS policies for tenant isolation and storage bucket configuration
-- Database: PostgreSQL 15+ (Supabase managed)
-- Extensions: pgvector, uuid-ossp, pg_trgm

-- ============================================================================
-- EXTENSIONS
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS "pgvector" SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS "pg_trgm" SCHEMA extensions;

-- Create vector type accessible
CREATE TYPE vector AS EXTENSION;


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
-- 1. TENANTS (Multi-tenancy - PE Firms)
-- ============================================================================

CREATE TABLE tenants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  settings JSONB DEFAULT '{}'::jsonb,
  sso_config JSONB,
  data_residency TEXT DEFAULT 'us-east-1',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_tenants_slug ON tenants (slug);
COMMENT ON TABLE tenants IS 'Multi-tenant organizational boundaries (PE firms)';


-- ============================================================================
-- 2. USERS (Role-based access control)
-- ============================================================================

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  clerk_user_id TEXT UNIQUE NOT NULL,
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
CREATE INDEX idx_users_clerk_id ON users (clerk_user_id);
COMMENT ON TABLE users IS 'Platform users with role-based access control';

-- RLS: Users can only see themselves and their tenant members
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

CREATE POLICY users_tenant_isolation ON users
  FOR ALL
  USING (tenant_id = auth.jwt() ->> 'tenant_id'::text AND is_active = true);


-- ============================================================================
-- 3. DEALS (M&A Transactions)
-- ============================================================================

CREATE TABLE deals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  deal_type deal_type_enum NOT NULL,
  status deal_status_enum NOT NULL DEFAULT 'setup',
  target_company TEXT,
  deal_value_range TEXT,
  playbook_id UUID,
  assigned_partner UUID REFERENCES users(id),
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_deals_tenant ON deals (tenant_id);
CREATE INDEX idx_deals_status ON deals (status);
CREATE INDEX idx_deals_type ON deals (deal_type);
CREATE INDEX idx_deals_created ON deals (created_at DESC);
COMMENT ON TABLE deals IS 'M&A and contract deals with aggregated analysis';

-- RLS: Deal isolation by tenant
ALTER TABLE deals ENABLE ROW LEVEL SECURITY;

CREATE POLICY deals_tenant_isolation ON deals
  FOR ALL
  USING (tenant_id = auth.jwt() ->> 'tenant_id'::text);


-- ============================================================================
-- 4. CONTRACTS (Uploaded Documents)
-- ============================================================================

CREATE TABLE contracts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deal_id UUID NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  filename TEXT NOT NULL,
  original_filename TEXT NOT NULL,
  file_path TEXT NOT NULL,
  file_hash TEXT NOT NULL UNIQUE,
  file_size_bytes BIGINT NOT NULL,
  mime_type TEXT NOT NULL,
  contract_type contract_type_enum,
  parties JSONB,
  effective_date DATE,
  expiration_date DATE,
  governing_law TEXT,
  page_count INTEGER,
  is_scanned BOOLEAN DEFAULT false,
  ocr_confidence FLOAT,
  processing_status processing_status_enum NOT NULL DEFAULT 'uploaded',
  processing_error TEXT,
  processed_at TIMESTAMPTZ,
  version INTEGER DEFAULT 1,
  parent_contract_id UUID REFERENCES contracts(id),
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
CREATE INDEX idx_contracts_hash ON contracts (file_hash);
CREATE INDEX idx_contracts_created ON contracts (created_at DESC);
COMMENT ON TABLE contracts IS 'Uploaded contracts with processing status';

-- RLS: Contract isolation by tenant and deal
ALTER TABLE contracts ENABLE ROW LEVEL SECURITY;

CREATE POLICY contracts_tenant_isolation ON contracts
  FOR ALL
  USING (tenant_id = auth.jwt() ->> 'tenant_id'::text);


-- ============================================================================
-- 5. CONTRACT PARTIES (Organizations in contracts)
-- ============================================================================

CREATE TABLE contract_parties (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  contract_id UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  party_name TEXT NOT NULL,
  party_role party_role_enum,
  entity_type entity_type_enum,
  jurisdiction TEXT,
  normalized_name TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_contract_parties_contract ON contract_parties (contract_id);
CREATE INDEX idx_contract_parties_normalized ON contract_parties (normalized_name);
CREATE INDEX idx_contract_parties_tenant ON contract_parties (tenant_id);
COMMENT ON TABLE contract_parties IS 'Organizations and individuals in contracts';

-- RLS: Party isolation by tenant
ALTER TABLE contract_parties ENABLE ROW LEVEL SECURITY;

CREATE POLICY contract_parties_tenant_isolation ON contract_parties
  FOR ALL
  USING (tenant_id = auth.jwt() ->> 'tenant_id'::text);


-- ============================================================================
-- 6. CLAUSES (Extracted Contract Language)
-- ============================================================================

CREATE TABLE clauses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  contract_id UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  clause_type TEXT NOT NULL,
  extracted_text TEXT NOT NULL,
  surrounding_context TEXT,
  page_number INTEGER,
  page_end INTEGER,
  section_reference TEXT,
  section_title TEXT,
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
  model_id TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
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
CREATE INDEX idx_clauses_fulltext ON clauses USING gin (to_tsvector('english', extracted_text));
COMMENT ON TABLE clauses IS 'AI-extracted contract language with risk assessment';

-- RLS: Clause isolation by tenant
ALTER TABLE clauses ENABLE ROW LEVEL SECURITY;

CREATE POLICY clauses_tenant_isolation ON clauses
  FOR ALL
  USING (tenant_id = auth.jwt() ->> 'tenant_id'::text);


-- ============================================================================
-- 7. CLAUSE EMBEDDINGS (Vector Search with pgvector)
-- ============================================================================

CREATE TABLE clause_embeddings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  clause_id UUID NOT NULL UNIQUE REFERENCES clauses(id) ON DELETE CASCADE,
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  embedding extensions.vector(1024),
  embedding_model TEXT DEFAULT 'voyage-law-2',
  created_at TIMESTAMPTZ DEFAULT now()
);

-- HNSW index for approximate nearest neighbor search (up to 50M vectors at 99% recall)
CREATE INDEX idx_clause_embeddings_hnsw ON clause_embeddings
  USING hnsw (embedding extensions.vector_cosine_ops)
  WITH (m = 16, ef_construction = 128);

CREATE INDEX idx_clause_embeddings_tenant ON clause_embeddings (tenant_id);
COMMENT ON TABLE clause_embeddings IS 'Semantic embeddings for clause similarity search with HNSW indexing';

-- RLS: Embedding isolation by tenant
ALTER TABLE clause_embeddings ENABLE ROW LEVEL SECURITY;

CREATE POLICY clause_embeddings_tenant_isolation ON clause_embeddings
  FOR ALL
  USING (tenant_id = auth.jwt() ->> 'tenant_id'::text);


-- ============================================================================
-- 8. RISK FLAGS (Issues Identified)
-- ============================================================================

CREATE TABLE risk_flags (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  clause_id UUID REFERENCES clauses(id) ON DELETE CASCADE,
  contract_id UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
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
CREATE INDEX idx_risk_flags_tenant ON risk_flags (tenant_id);
COMMENT ON TABLE risk_flags IS 'Risk flags and issues identified in clauses';

-- RLS: Risk flag isolation by tenant
ALTER TABLE risk_flags ENABLE ROW LEVEL SECURITY;

CREATE POLICY risk_flags_tenant_isolation ON risk_flags
  FOR ALL
  USING (tenant_id = auth.jwt() ->> 'tenant_id'::text);


-- ============================================================================
-- 9. CLAUSE LIBRARY (Market Standard Clauses)
-- ============================================================================

CREATE TABLE clause_library (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
  clause_type TEXT NOT NULL,
  variant_name TEXT NOT NULL,
  standard_text TEXT NOT NULL,
  jurisdiction TEXT,
  deal_type TEXT,
  centroid_embedding extensions.vector(1024),
  similarity_threshold FLOAT DEFAULT 0.85,
  notes TEXT,
  source TEXT,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),

  UNIQUE (tenant_id, clause_type, jurisdiction, deal_type) WHERE is_active = true
);

CREATE INDEX idx_clause_library_type ON clause_library (clause_type) WHERE is_active = true;
CREATE INDEX idx_clause_library_tenant ON clause_library (tenant_id);
CREATE INDEX idx_clause_library_centroid ON clause_library
  USING hnsw (centroid_embedding extensions.vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
COMMENT ON TABLE clause_library IS 'Market standard clauses per tenant for benchmarking';

-- RLS: Library isolation by tenant (shared defaults + tenant-specific custom)
ALTER TABLE clause_library ENABLE ROW LEVEL SECURITY;

CREATE POLICY clause_library_tenant_isolation ON clause_library
  FOR ALL
  USING (tenant_id IS NULL OR tenant_id = auth.jwt() ->> 'tenant_id'::text);


-- ============================================================================
-- 10. PLAYBOOKS (Deal-Type-Specific Rules)
-- ============================================================================

CREATE TABLE playbooks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  deal_type deal_type_enum,
  rules JSONB NOT NULL,
  is_default BOOLEAN DEFAULT false,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_playbooks_tenant ON playbooks (tenant_id);
CREATE INDEX idx_playbooks_deal_type ON playbooks (deal_type);
CREATE INDEX idx_playbooks_rules ON playbooks USING gin (rules);
COMMENT ON TABLE playbooks IS 'Customizable risk rules per deal type';

-- RLS: Playbook isolation by tenant
ALTER TABLE playbooks ENABLE ROW LEVEL SECURITY;

CREATE POLICY playbooks_tenant_isolation ON playbooks
  FOR ALL
  USING (tenant_id = auth.jwt() ->> 'tenant_id'::text);


-- ============================================================================
-- 11. EXPORT JOBS (Async Report Generation)
-- ============================================================================

CREATE TABLE export_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deal_id UUID NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  requested_by UUID NOT NULL REFERENCES users(id),
  format export_format_enum NOT NULL,
  template_id TEXT,
  status export_status_enum NOT NULL DEFAULT 'queued',
  progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
  file_path TEXT,
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
CREATE INDEX idx_export_tenant ON export_jobs (tenant_id);
COMMENT ON TABLE export_jobs IS 'Async export jobs (Excel matrices, PDF reports, etc.)';

-- RLS: Export job isolation by tenant
ALTER TABLE export_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY export_jobs_tenant_isolation ON export_jobs
  FOR ALL
  USING (tenant_id = auth.jwt() ->> 'tenant_id'::text);


-- ============================================================================
-- 12. AUDIT LOG (Immutable Compliance Trail)
-- ============================================================================

CREATE TABLE audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id),
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
CREATE INDEX idx_audit_created ON audit_log (created_at DESC);
COMMENT ON TABLE audit_log IS 'Immutable audit trail for compliance (SOC 2, regulatory discovery)';

-- RLS: Audit log isolation by tenant (users see only their tenant's logs)
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY audit_log_tenant_isolation ON audit_log
  FOR ALL
  USING (tenant_id = auth.jwt() ->> 'tenant_id'::text);


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

COMMENT ON VIEW deal_summary IS 'Aggregated metrics per deal for dashboard';


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

COMMENT ON VIEW non_standard_clauses IS 'Clauses deviating from tenant-specific market standards';


-- ============================================================================
-- SUPABASE STORAGE BUCKETS (Document & Export Storage)
-- ============================================================================

-- Note: Storage bucket configuration is managed via Supabase UI or supabase CLI
-- Create buckets with RLS policies:
--
-- 1. contracts-uploads (private, tenant-isolated)
--    - Objects stored as: {tenant_id}/{deal_id}/{contract_id}/{filename}
--    - Policy: Users can only access contracts from their tenant
--
-- 2. exports (private, tenant-isolated)
--    - Objects stored as: {tenant_id}/{deal_id}/{export_id}/{filename}
--    - Policy: Download URLs expire after 7 days
--
-- 3. clause-library-standards (public read, private write)
--    - Objects stored as: {clause_type}/{jurisdiction}/{variant_name}.pdf
--    - Policy: Admins only can upload; all tenants can read


-- ============================================================================
-- FUNCTIONS & TRIGGERS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply update timestamp trigger to all tables with updated_at
CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON tenants
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_deals_updated_at BEFORE UPDATE ON deals
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_contracts_updated_at BEFORE UPDATE ON contracts
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_clauses_updated_at BEFORE UPDATE ON clauses
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_playbooks_updated_at BEFORE UPDATE ON playbooks
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_clause_library_updated_at BEFORE UPDATE ON clause_library
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- Function to audit all mutations
CREATE OR REPLACE FUNCTION audit_log_trigger()
RETURNS TRIGGER AS $$
DECLARE
  action_type TEXT;
BEGIN
  action_type := CASE
    WHEN TG_OP = 'INSERT' THEN 'CREATE'
    WHEN TG_OP = 'UPDATE' THEN 'UPDATE'
    WHEN TG_OP = 'DELETE' THEN 'DELETE'
  END;

  INSERT INTO audit_log (
    tenant_id, user_id, action, resource_type, resource_id, details
  ) VALUES (
    COALESCE(NEW.tenant_id, OLD.tenant_id),
    auth.uid(),
    action_type,
    TG_TABLE_NAME,
    COALESCE(NEW.id, OLD.id),
    jsonb_build_object(
      'old', to_jsonb(OLD),
      'new', to_jsonb(NEW)
    )
  );

  RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Apply audit trigger to core tables (optional - can be expensive at scale)
-- CREATE TRIGGER audit_contracts AFTER INSERT OR UPDATE OR DELETE ON contracts FOR EACH ROW EXECUTE FUNCTION audit_log_trigger();
-- CREATE TRIGGER audit_clauses AFTER INSERT OR UPDATE OR DELETE ON clauses FOR EACH ROW EXECUTE FUNCTION audit_log_trigger();
-- CREATE TRIGGER audit_risk_flags AFTER INSERT OR UPDATE OR DELETE ON risk_flags FOR EACH ROW EXECUTE FUNCTION audit_log_trigger();


-- ============================================================================
-- SEED DATA (Optional - Market Standard Clause Library)
-- ============================================================================

-- Insert global (tenant_id = NULL) standard clauses
INSERT INTO clause_library (
  clause_type, variant_name, standard_text, jurisdiction, deal_type, is_active, source, notes
) VALUES
  (
    'change_of_control',
    'standard_mna_change_control',
    'Upon a Change of Control (defined as the acquisition of more than 50% of the equity or voting power), all material contracts shall require written consent from counterparty within 30 days.',
    'New York',
    'm_and_a',
    true,
    'ABA Model M&A Purchase Agreement',
    'Market standard for mid-market M&A'
  ),
  (
    'termination_convenience',
    'standard_30_day_termination',
    'Either party may terminate this Agreement for any reason with 30 days written notice, provided that such termination shall not affect obligations accrued prior to the effective date of termination.',
    'New York',
    'vendor',
    true,
    'NYSBA Standard Vendor Form',
    'Common in non-exclusive vendor agreements'
  ),
  (
    'indemnification',
    'standard_mutual_indemnification',
    'Each party shall indemnify, defend, and hold harmless the other party from and against any and all third-party claims, damages, and costs (including reasonable attorneys fees) arising out of breach of this Agreement.',
    'Delaware',
    'm_and_a',
    true,
    'Practical Law - Indemnification Checklist',
    'Balanced approach for M&A agreements'
  ),
  (
    'governing_law',
    'new_york_choice_of_law',
    'This Agreement shall be governed by and construed in accordance with the laws of the State of New York, without regard to conflict of law principles.',
    'New York',
    NULL,
    true,
    'ABA Standard Forms',
    'Most common US jurisdiction'
  )
ON CONFLICT DO NOTHING;
