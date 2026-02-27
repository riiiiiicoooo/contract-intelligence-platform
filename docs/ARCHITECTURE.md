# System Architecture: Contract Intelligence Platform

**Last Updated:** January 2025
**Status:** Production (v2.1)

---

## 1. High-Level Architecture

```
                              ┌──────────────────────┐
                              │     USERS            │
                              │  Associates, Partners │
                              │  Compliance, Admin    │
                              └──────────┬───────────┘
                                         │
                                         ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                   │
│                                                                        │
│  Next.js (App Router, SSR)                                             │
│  ├── Split-pane contract viewer (react-pdf-highlighter + metadata)     │
│  ├── Risk dashboard (Recharts)                                         │
│  ├── Search interface (hybrid keyword + semantic)                      │
│  ├── Review workflow (accept/reject/escalate)                          │
│  └── Export manager (async job tracking)                               │
│                                                                        │
│  Component library: shadcn/ui (Radix primitives + Tailwind CSS)        │
│  Rich text: Tiptap (ProseMirror)                                       │
│  Auth: Supabase Auth (SAML/OIDC for enterprise SSO)                    │
└────────────────────────────────┬───────────────────────────────────────┘
                                 │ HTTPS / WebSocket
                                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         API LAYER (FastAPI)                             │
│                                                                        │
│  /api/v1/documents    - Upload, status, metadata                       │
│  /api/v1/analysis     - Trigger extraction, get results                │
│  /api/v1/search       - Hybrid search queries                          │
│  /api/v1/review       - Accept, reject, override, escalate             │
│  /api/v1/export       - Generate deliverables (async)                  │
│  /api/v1/admin        - Tenant config, user management                 │
│  /api/v1/audit        - Audit log queries                              │
│                                                                        │
│  Middleware: auth validation, tenant context injection, rate limiting,  │
│  request logging, PII scanning                                         │
└──────────┬──────────────┬──────────────┬──────────────┬───────────────┘
           │              │              │              │
           ▼              ▼              ▼              ▼
┌──────────────┐ ┌────────────────┐ ┌──────────┐ ┌──────────────────┐
│  INGESTION   │ │  AI ANALYSIS   │ │  SEARCH  │ │  EXPORT          │
│  SERVICE     │ │  SERVICE       │ │  SERVICE │ │  SERVICE         │
└──────┬───────┘ └───────┬────────┘ └────┬─────┘ └────────┬─────────┘
       │                 │               │                 │
       ▼                 ▼               ▼                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                                     │
│                                                                        │
│  Supabase (PostgreSQL 15 + pgvector + pgvectorscale)                   │
│  ├── Relational: contracts, clauses, parties, obligations, audit_log   │
│  ├── Vectors: clause embeddings (voyage-law-2, 1024 dimensions)        │
│  ├── Auth: Supabase Auth + RLS policies                                │
│  ├── Storage: Supabase Storage (contract files, exports)               │
│  └── Realtime: WebSocket subscriptions for job progress                │
│                                                                        │
│  Redis: task queue, caching, rate limiting                             │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Service Architecture

The platform is organized into four core services, each independently deployable but sharing the same Supabase database.

### 2.1 Ingestion Service

Handles document upload, type detection, OCR, parsing, and chunking.

```
File Upload (PDF/Word/ZIP)
      │
      ▼
┌─────────────────────┐
│  File Validation     │
│  - Type check        │
│  - Size limit (500MB)│
│  - Virus scan        │
│  - Duplicate detect  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐     ┌─────────────────────────┐
│  Type Detection      │────▶│  ZIP?                    │
│                      │     │  -> Extract to individual │
│                      │     │     files, process each   │
└──────────┬──────────┘     └─────────────────────────┘
           │
     ┌─────┴──────┐
     ▼            ▼
┌─────────┐  ┌──────────┐
│ Native  │  │ Scanned  │
│ PDF     │  │ PDF      │
│         │  │          │
│ Docling │  │ Azure    │
│ (fast,  │  │ Document │
│  free)  │  │ Intel    │
│         │  │ (OCR)    │
└────┬────┘  └────┬─────┘
     │            │
     └─────┬──────┘
           ▼
┌─────────────────────┐
│  Word Document?      │
│  python-docx         │
│  (extract text +     │
│   tracked changes)   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Clause-Level        │
│  Chunking            │
│  - Split at section/ │
│    clause boundaries │
│  - 200-500 tokens    │
│  - Preserve hierarchy│
│  - Attach metadata:  │
│    section, clause#, │
│    page, doc_id      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Store in Supabase   │
│  - Raw text chunks   │
│  - Document metadata │
│  - Processing status │
└─────────────────────┘
```

**Native vs. scanned detection logic:**

```python
def is_scanned(pdf_path):
    doc = fitz.open(pdf_path)
    for page in doc:
        text = page.get_text()
        images = page.get_images()
        # If text is minimal but images cover the page, it's scanned
        if len(text.strip()) < 50 and len(images) > 0:
            return True
        # Check for OCR artifact fonts
        for font in page.get_fonts():
            if "GlyphlessFont" in font[3]:
                return True
    return False
```

### 2.2 AI Analysis Service

Handles clause extraction, risk scoring, and embedding generation. Orchestrated by LangGraph.

```
Document chunks from Ingestion
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│                    LangGraph Agent Pipeline                    │
│                                                                │
│  ┌──────────────┐    ┌───────────────┐    ┌───────────────┐   │
│  │ PII Redaction │───▶│ Document      │───▶│ Clause        │   │
│  │ (Presidio)   │    │ Classifier    │    │ Extractor     │   │
│  │              │    │               │    │ (Claude API)  │   │
│  │ Detect:      │    │ Contract type:│    │               │   │
│  │ - Names      │    │ - MSA         │    │ Structured    │   │
│  │ - SSN        │    │ - SOW         │    │ JSON output:  │   │
│  │ - Email      │    │ - NDA         │    │ {clause_type, │   │
│  │ - Phone      │    │ - Amendment   │    │  text,        │   │
│  │ - Addresses  │    │ - Lease       │    │  location,    │   │
│  │              │    │ - Employment  │    │  confidence}  │   │
│  │ Threshold:   │    │               │    │               │   │
│  │ conf > 0.7   │    │               │    │ Temp: 0.2     │   │
│  └──────────────┘    └───────────────┘    └───────┬───────┘   │
│                                                    │           │
│                                           ┌────────┴────────┐ │
│                                           │                 │ │
│                                           ▼                 ▼ │
│                                  ┌──────────────┐  ┌─────────┐│
│                                  │ Risk Scorer  │  │Embedding││
│                                  │              │  │Generator ││
│                                  │ Compare vs.  │  │         ││
│                                  │ playbook     │  │voyage-  ││
│                                  │ standards    │  │law-2    ││
│                                  │              │  │         ││
│                                  │ Output:      │  │1024-dim ││
│                                  │ severity +   │  │vectors  ││
│                                  │ explanation  │  │         ││
│                                  └──────┬───────┘  └────┬────┘│
│                                         │               │     │
│                                         ▼               │     │
│                                  ┌──────────────┐       │     │
│                                  │ Confidence    │       │     │
│                                  │ Router        │       │     │
│                                  │               │       │     │
│                                  │ >= 0.85:      │       │     │
│                                  │   auto-accept │       │     │
│                                  │               │       │     │
│                                  │ < 0.85:       │       │     │
│                                  │   route to    │       │     │
│                                  │   human review│       │     │
│                                  └──────┬───────┘       │     │
│                                         │               │     │
└─────────────────────────────────────────┼───────────────┼─────┘
                                          │               │
                                          ▼               ▼
                                   ┌─────────────────────────┐
                                   │  Supabase                │
                                   │  - clauses table         │
                                   │  - risk_flags table      │
                                   │  - clause_embeddings     │
                                   │  - review_queue          │
                                   └─────────────────────────┘
```

**Multi-model routing logic:**

The system routes to different models based on task type and fallback conditions:

| Task | Primary Model | Fallback | Reasoning |
|---|---|---|---|
| Clause extraction | Claude (200K context) | GPT-4 | Claude handles full contracts in a single pass |
| Risk scoring | Claude | GPT-4 | Chain-of-thought reasoning for explanations |
| Document classification | Claude Haiku | Claude Sonnet | Fast classification doesn't need full model |
| Embedding generation | voyage-law-2 | text-embedding-3-small | Legal-specific embeddings for retrieval |
| Reranking | Cohere Rerank | Cross-encoder fallback | Search result relevance scoring |

Fallback triggers: API timeout (30s), rate limit (429), server error (5xx), or confidence below threshold on primary model output.

### 2.3 Search Service

Hybrid search combining BM25 keyword matching with vector semantic search and reranking.

```
User Query: "contracts with unlimited liability provisions"
                    │
                    ▼
            ┌───────────────┐
            │ Query Parser   │
            │ - Extract      │
            │   filters      │
            │ - Identify     │
            │   intent       │
            └───────┬───────┘
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
   ┌─────────────┐    ┌──────────────┐
   │ BM25 Search │    │ Vector Search│
   │ (PostgreSQL │    │ (pgvector    │
   │  full-text) │    │  HNSW index) │
   │             │    │              │
   │ Catches:    │    │ Catches:     │
   │ exact terms │    │ semantic     │
   │ "unlimited  │    │ equivalents  │
   │  liability" │    │ "uncapped    │
   │             │    │  damages"    │
   └──────┬──────┘    └──────┬───────┘
          │                  │
          └────────┬─────────┘
                   ▼
          ┌────────────────┐
          │ Reciprocal Rank│
          │ Fusion (RRF)   │
          │                │
          │ Merge ranked   │
          │ lists with     │
          │ weighted scores│
          └───────┬────────┘
                  │
                  ▼
          ┌────────────────┐
          │ Cohere Rerank  │
          │                │
          │ Cross-encoder  │
          │ rescoring of   │
          │ top 20 results │
          └───────┬────────┘
                  │
                  ▼
          ┌────────────────┐
          │ Return top 10  │
          │ with:          │
          │ - Clause text  │
          │ - Source doc   │
          │ - Page number  │
          │ - Risk level   │
          │ - Relevance    │
          │   score        │
          └────────────────┘
```

**Why hybrid over vector-only:** Legal text has a unique property where both exact terminology and semantic equivalence matter. "Force majeure" is a precise legal term that BM25 catches perfectly, but "acts of God" or "events beyond reasonable control" require semantic matching. Benchmarks show hybrid search with reranking achieves 91% accuracy vs. 58% for BM25 alone and 72% for vector-only.

### 2.4 Export Service

Generates deal deliverables asynchronously using Celery workers.

```
POST /api/v1/export
  {deal_id, format: "matrix", template: "firm_default"}
                    │
                    ▼
           ┌────────────────┐
           │ Create Job      │
           │ Return job_id   │
           │ Status: queued  │
           └───────┬────────┘
                   │
                   ▼
           ┌────────────────┐
           │ Celery Worker   │
           │                 │
           │ Parallel tasks: │
           │ ┌─────────────┐ │
           │ │ Excel matrix│ │  openpyxl
           │ │ (contracts  │ │  - Rows: contracts
           │ │  x clauses) │ │  - Cols: clause types
           │ │             │ │  - RAG conditional formatting
           │ └─────────────┘ │
           │ ┌─────────────┐ │
           │ │ PowerPoint  │ │  python-pptx
           │ │ (exec       │ │  - Branded template
           │ │  summary)   │ │  - Embedded charts
           │ └─────────────┘ │
           │ ┌─────────────┐ │
           │ │ PDF report  │ │  WeasyPrint + Jinja2
           │ │ (detailed   │ │  - HTML template
           │ │  risk)      │ │  - CSS print layout
           │ └─────────────┘ │
           └───────┬────────┘
                   │
                   ▼
           ┌────────────────┐
           │ Merge outputs   │
           │ Upload to       │
           │ Supabase Storage│
           │                 │
           │ Generate pre-   │
           │ signed URL      │
           │ (24hr expiry)   │
           └───────┬────────┘
                   │
                   ▼
           ┌────────────────┐
           │ Notify user     │
           │ via WebSocket   │
           │                 │
           │ {status: done,  │
           │  download_url}  │
           └────────────────┘
```

---

## 3. Data Architecture

### 3.1 Core Schema

```sql
-- Tenant isolation
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Deals/engagements
CREATE TABLE deals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) NOT NULL,
    name TEXT NOT NULL,
    deal_type TEXT CHECK (deal_type IN ('m_and_a', 'lending', 'vendor', 'employment')),
    status TEXT CHECK (status IN ('active', 'completed', 'archived')),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Contracts
CREATE TABLE contracts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id UUID REFERENCES deals(id) NOT NULL,
    tenant_id UUID REFERENCES tenants(id) NOT NULL,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    contract_type TEXT,  -- MSA, SOW, NDA, amendment, lease, employment
    parties JSONB,       -- [{name, role, entity_type}]
    effective_date DATE,
    expiration_date DATE,
    processing_status TEXT CHECK (processing_status IN (
        'uploaded', 'processing', 'extracted', 'reviewed', 'failed'
    )),
    page_count INTEGER,
    is_scanned BOOLEAN DEFAULT false,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Extracted clauses
CREATE TABLE clauses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id UUID REFERENCES contracts(id) NOT NULL,
    tenant_id UUID REFERENCES tenants(id) NOT NULL,
    clause_type TEXT NOT NULL,       -- 'change_of_control', 'termination_convenience', etc.
    extracted_text TEXT NOT NULL,
    page_number INTEGER,
    section_reference TEXT,          -- "Section 8.2(a)"
    confidence FLOAT NOT NULL,       -- 0.0 to 1.0
    risk_level TEXT CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    risk_explanation TEXT,
    is_standard BOOLEAN,             -- vs. non-standard based on clause library
    review_status TEXT CHECK (review_status IN (
        'pending', 'accepted', 'rejected', 'overridden'
    )) DEFAULT 'pending',
    reviewed_by UUID,
    reviewed_at TIMESTAMPTZ,
    override_text TEXT,              -- if reviewer corrected the extraction
    model_version TEXT,              -- 'claude-sonnet-4-20250514'
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Clause embeddings for semantic search
CREATE TABLE clause_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clause_id UUID REFERENCES clauses(id) NOT NULL,
    tenant_id UUID REFERENCES tenants(id) NOT NULL,
    embedding vector(1024),          -- voyage-law-2 dimension
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Audit trail
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) NOT NULL,
    user_id UUID NOT NULL,
    action TEXT NOT NULL,             -- 'document_view', 'clause_override', 'export', 'ai_call'
    resource_type TEXT NOT NULL,      -- 'contract', 'clause', 'deal', 'export'
    resource_id UUID NOT NULL,
    details JSONB NOT NULL,           -- action-specific payload
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Row-Level Security policies
ALTER TABLE contracts ENABLE ROW LEVEL SECURITY;
ALTER TABLE clauses ENABLE ROW LEVEL SECURITY;
ALTER TABLE clause_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_contracts ON contracts
    USING (tenant_id = current_setting('app.current_tenant')::UUID);

CREATE POLICY tenant_isolation_clauses ON clauses
    USING (tenant_id = current_setting('app.current_tenant')::UUID);
```

### 3.2 Indexes

```sql
-- Vector similarity search (HNSW for fast approximate nearest neighbor)
CREATE INDEX idx_clause_embeddings_hnsw ON clause_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 128);

-- Full-text search (BM25 via PostgreSQL tsvector)
CREATE INDEX idx_clauses_fulltext ON clauses
    USING gin (to_tsvector('english', extracted_text));

-- Metadata filtering
CREATE INDEX idx_clauses_type ON clauses (clause_type);
CREATE INDEX idx_clauses_risk ON clauses (risk_level);
CREATE INDEX idx_clauses_review ON clauses (review_status);
CREATE INDEX idx_contracts_deal ON contracts (deal_id);
CREATE INDEX idx_contracts_status ON contracts (processing_status);
CREATE INDEX idx_audit_resource ON audit_log (resource_type, resource_id);
CREATE INDEX idx_audit_user ON audit_log (user_id, created_at DESC);
```

### 3.3 Entity Relationship Diagram

```
┌──────────┐       ┌──────────┐       ┌──────────────┐
│ tenants  │──1:N──│  deals   │──1:N──│  contracts   │
└──────────┘       └──────────┘       └──────┬───────┘
                                              │
                                             1:N
                                              │
                                       ┌──────┴───────┐
                                       │   clauses    │──1:1──┌──────────────────┐
                                       └──────┬───────┘       │ clause_embeddings│
                                              │               └──────────────────┘
                                             N:1
                                              │
                                       ┌──────┴───────┐
                                       │  audit_log   │
                                       └──────────────┘

contracts ──N:M── parties (via contracts.parties JSONB)
deals ──1:N── export_jobs
clauses ──N:1── clause_library (standard benchmarks)
```

---

## 4. Infrastructure

### 4.1 Deployment Architecture

```
┌─────────────────────────────────────────────────┐
│                    Vercel                         │
│                                                   │
│  Next.js Frontend                                 │
│  - SSR for document-heavy pages                   │
│  - Edge functions for auth                        │
│  - CDN for static assets                          │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│              Railway / Render                     │
│                                                   │
│  FastAPI Backend                                  │
│  ├── API server (uvicorn, 2+ replicas)            │
│  ├── Celery workers (4+ for export/processing)    │
│  └── Redis (task queue + caching)                 │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│                  Supabase                         │
│                                                   │
│  ├── PostgreSQL 15 + pgvector                     │
│  ├── Auth (JWT, SAML, OIDC)                       │
│  ├── Storage (contract files, exports)            │
│  ├── Realtime (WebSocket subscriptions)           │
│  └── Edge Functions (lightweight serverless)      │
└─────────────────────────────────────────────────┘

External APIs:
  ├── Anthropic (Claude API) - clause extraction, risk scoring
  ├── OpenAI (GPT-4) - fallback model
  ├── Voyage AI - legal text embeddings
  ├── Azure Document Intelligence - OCR
  └── Cohere - search reranking
```

### 4.2 Local Development

```yaml
# docker-compose.yml
services:
  api:
    build: ./src/api
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/contracts
      - REDIS_URL=redis://redis:6379
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - VOYAGE_API_KEY=${VOYAGE_API_KEY}
    depends_on: [db, redis]

  worker:
    build: ./src/api
    command: celery -A tasks worker --loglevel=info --concurrency=4
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/contracts
      - REDIS_URL=redis://redis:6379
    depends_on: [db, redis]

  db:
    image: supabase/postgres:15.1.1.41
    ports: ["5432:5432"]
    environment:
      - POSTGRES_PASSWORD=postgres
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./sql/init.sql:/docker-entrypoint-initdb.d/init.sql

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  frontend:
    build: ./src/frontend
    ports: ["3000:3000"]
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
      - NEXT_PUBLIC_SUPABASE_URL=${SUPABASE_URL}

volumes:
  pgdata:
```

---

## 5. Security Architecture

### 5.1 Data Flow with PII Protection

```
Contract text (contains PII: names, SSNs, addresses)
                    │
                    ▼
         ┌─────────────────────┐
         │  Microsoft Presidio │
         │                     │
         │  Detectors:         │
         │  - SpaCy NER        │
         │  - Regex patterns   │
         │  - Context-aware    │
         │  - Checksum (SSN)   │
         │                     │
         │  Confidence > 0.7:  │
         │  Replace with typed │
         │  placeholders       │
         │                     │
         │  "John Smith" ->    │
         │  "<PERSON_1>"       │
         │                     │
         │  "123-45-6789" ->   │
         │  "<SSN_1>"          │
         └──────────┬──────────┘
                    │
         ┌──────────┴──────────┐
         │  Mapping table       │
         │  (encrypted storage) │
         │                      │
         │  <PERSON_1> = "John  │
         │   Smith"             │
         │  <SSN_1> = "123-45- │
         │   6789"             │
         └──────────┬──────────┘
                    │
    Redacted text   │
    goes to LLM     │
                    ▼
         ┌─────────────────────┐
         │  Claude API         │
         │  (ZDR agreement)    │
         │                     │
         │  Receives only      │
         │  redacted text      │
         │                     │
         │  Returns structured │
         │  extraction with    │
         │  placeholders       │
         └──────────┬──────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  De-anonymization   │
         │                     │
         │  Map placeholders   │
         │  back to originals  │
         │  using mapping      │
         │  table              │
         └──────────┬──────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  Audit Log Entry    │
         │                     │
         │  - Input hash       │
         │  - Model version    │
         │  - Output stored    │
         │  - Confidence score │
         │  - User who         │
         │    triggered        │
         │  - Timestamp        │
         └─────────────────────┘
```

### 5.2 Authentication and Authorization

```
User Request
      │
      ▼
┌──────────────────┐
│ Supabase Auth    │
│                  │
│ JWT validation   │
│ Extract:         │
│ - user_id        │
│ - tenant_id      │
│ - role           │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ API Middleware    │
│                  │
│ Set PostgreSQL   │
│ session vars:    │
│                  │
│ SET app.current  │
│ _tenant = '...'  │
│                  │
│ SET app.user_id  │
│ = '...'          │
│                  │
│ SET app.user_role│
│ = '...'          │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ PostgreSQL RLS   │
│                  │
│ Every query      │
│ automatically    │
│ filtered by      │
│ tenant_id        │
│                  │
│ Role-based:      │
│ - associate: own │
│   deals only     │
│ - partner: team  │
│   deals          │
│ - admin: all     │
│   tenant deals   │
└──────────────────┘
```

### 5.3 Audit Trail Schema

Every action is logged with enough detail to reconstruct the full history of any document or clause.

| Action | What's Logged |
|---|---|
| `document_upload` | filename, file_hash, uploader, file_size, deal_id |
| `document_view` | contract_id, user_id, timestamp, ip_address |
| `ai_extraction` | input_text_hash, model_version, output, confidence, token_count, latency_ms |
| `clause_override` | clause_id, original_text, new_text, reviewer_id, reason |
| `risk_override` | clause_id, original_risk, new_risk, reviewer_id, reason |
| `search_query` | query_text, results_count, user_id |
| `export_generated` | deal_id, format, file_hash, download_count |
| `export_downloaded` | export_id, user_id, ip_address |

---

## 6. Performance Considerations

### 6.1 Processing Pipeline Optimization

| Bottleneck | Solution | Impact |
|---|---|---|
| OCR on scanned PDFs | Dual pipeline - skip OCR for native PDFs (70% of documents) | 3x faster average processing |
| LLM API latency | Batch clause extraction - send full contract in one API call vs. per-clause | 80% reduction in API calls |
| Embedding generation | Batch embedding API calls (32 chunks per request) | 10x fewer API calls |
| Large export generation | Celery parallel workers - generate Excel, PPT, PDF concurrently | 3x faster export |
| Search latency | HNSW index on embeddings + GIN index on full-text | < 200ms p95 for hybrid search |
| Dashboard load | Materialized views for aggregate risk scores per deal | < 500ms dashboard render |

### 6.2 Scaling Strategy

| Scale Point | Current | Strategy |
|---|---|---|
| 1-5 concurrent deals | Single API server, 2 Celery workers | Sufficient for MVP |
| 5-15 concurrent deals | 2 API replicas, 4 Celery workers | Horizontal scaling |
| 15-50 concurrent deals | Auto-scaling API, 8+ workers, read replicas | Database read replicas for search |
| 50K+ total documents | pgvectorscale partitioning, CDN for exports | Index partitioning by tenant |

### 6.3 Caching Strategy

| Cache Target | TTL | Invalidation |
|---|---|---|
| Search results | 5 minutes | On new document processing for same deal |
| Dashboard aggregations | 1 minute | On clause review action |
| User session/auth | 1 hour | On logout or role change |
| Export download URLs | 24 hours | On regeneration |
| Clause library standards | 24 hours | On admin update |

---

## 7. Monitoring and Observability

### 7.1 Key Metrics

| Category | Metric | Alert Threshold |
|---|---|---|
| **API** | Request latency (p95) | > 2 seconds |
| **API** | Error rate (5xx) | > 1% |
| **Processing** | Document processing time | > 5 minutes (single doc) |
| **Processing** | Batch completion time | > 6 hours (200 docs) |
| **AI** | Extraction confidence (average) | < 0.80 |
| **AI** | Human override rate | > 20% |
| **AI** | LLM API error rate | > 2% |
| **Search** | Query latency (p95) | > 3 seconds |
| **Database** | Connection pool utilization | > 80% |
| **Database** | Storage utilization | > 75% |

### 7.2 LLM Observability

LangSmith (or Langfuse for self-hosted) traces every AI interaction:

- Token usage per extraction (input + output)
- Latency per model call (p50, p95, p99)
- Cost per document and per deal
- Confidence score distribution (detect model degradation)
- Fallback trigger rate (primary model failures)
- Human override correlation with confidence scores (calibration check)

---

## 8. Technology Selection Summary

| Component | Choice | Alternatives Evaluated | Decision Driver |
|---|---|---|---|
| Frontend | Next.js + shadcn/ui | React SPA, Vue | SSR for document-heavy pages; shadcn gives full component control |
| API | FastAPI | Express, Django | Async Python; native Pydantic validation; auto-generated OpenAPI docs |
| Database | Supabase (PostgreSQL + pgvector) | Pinecone + separate PostgreSQL | Single database for vectors + relational + auth + RLS; fewer moving parts |
| Task Queue | Celery + Redis | Bull (Node), RabbitMQ | Python ecosystem; proven at scale; simple Redis backend |
| AI Orchestration | LangGraph | LangChain, custom | Stateful agent graphs; native human-in-the-loop; growing ecosystem |
| Pipeline Orchestration | Temporal | Airflow, Prefect | Durable execution; survives crashes; signal/query for human review |
| PDF Processing | Docling + Azure Doc Intel | PyMuPDF, Unstructured.io | Docling: best open-source for native; Azure: best accuracy for scanned |
| Embeddings | voyage-law-2 | text-embedding-3-large, BGE-M3 | 6% better on legal retrieval benchmarks |
| PII Redaction | Microsoft Presidio | spaCy NER only, AWS Comprehend | 20+ entity types; custom recognizers; open-source |
| Export | openpyxl + python-pptx + WeasyPrint | ReportLab, FPDF2 | Each tool best-in-class for its format; Python-native |
