# Contract Intelligence Platform

**AI-Powered Contract Analysis for M&A Due Diligence**

An intelligent document processing platform that transforms how deal teams analyze contracts during M&A transactions. Built for a PE-backed advisory firm, this system ingests hundreds of contracts (PDF/Word), extracts key commercial terms, flags risk clauses, and generates deal-ready deliverables - reducing contract review timelines from weeks to hours.

---

## Modern Stack (Production Infrastructure)

This project includes comprehensive modern tooling infrastructure for production-grade deployment:

### AI & Observability
- **LangSmith Tracing** - Distributed tracing for all LLM calls with @traceable decorators
- **Custom Evaluators** - Clause extraction accuracy (F1 >= 0.94), risk flag precision (>= 0.90), hallucination detection
- **Evaluation Datasets** - Sample contracts with ground-truth clause extractions and expected risk flags
- **Cost Tracking** - Per-extraction token counting and cost aggregation by contract type

### Async Job Processing
- **Trigger.dev** - Long-running contract extraction jobs (2-10 min/document) with checkpointing between stages
- **Batch Deal Analysis** - Fan-out extraction, fan-in aggregation, portfolio pattern detection
- **Error Handling** - Retry logic with exponential backoff and dead-letter queue

### Workflow Automation
- **n8n Workflows** - Two production workflows:
  - **deal_room_ingestion.json** - Document webhook → classify → extract → notify analyst
  - **extraction_monitoring.json** - Hourly LangSmith audit → quality metrics → Slack/email alerts (>5% error rate)

### Authentication & Authorization
- **Clerk Integration** - SSO, SAML, passwordless auth with role-based middleware
- **Next.js Middleware** - Route protection, role-based access control (Partner/Associate/Analyst)
- **Tenant Isolation** - Organization-based data boundaries enforced at middleware + database level

### Database & Migrations
- **Supabase PostgreSQL** - Managed PostgreSQL with pgvector, RLS policies, and storage buckets
- **Migration System** - Supabase-compatible DDL with tenant-level RLS policies for each table
- **Vector Search** - HNSW indexes (m=16, ef_construction=128) for 50M+ scale semantic similarity

### Email & Notifications
- **React Email Templates** - TypeScript/JSX email components:
  - **extraction_complete.tsx** - Contract extraction summary with risk flag counts, confidence, action items
  - **deal_summary.tsx** - Weekly deal progress digest with risk matrix, pending reviews, action items
- **Resend** - Transactional email delivery with click tracking
- **Slack Webhooks** - Real-time alerts for extraction quality degradation

### Configuration & Deployment
- **.cursorrules** - Comprehensive Cursor AI context (architecture, tech stack, design decisions, conventions)
- **.replit + replit.nix** - Replit cloud development environment with PostgreSQL and Node.js
- **vercel.json** - Vercel deployment configuration with edge caching, API function sizing, cron jobs
- **.env.example** - Template for all environment variables (organized by service)

### Architecture Diagram

```
                    Analyst Dashboard (Next.js)
                           │
                           ▼
         ┌─────────────────────────────────────┐
         │  Clerk Auth (SSO) + Middleware      │
         │  Role-based route protection        │
         └─────────────────┬───────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   n8n        │ │ Trigger.dev  │ │ Supabase API │
│ Workflows    │ │ Jobs         │ │ GraphQL      │
│              │ │              │ │              │
│ - Ingestion  │ │ - Extract    │ │ - Auth       │
│ - Monitoring │ │ - Analyze    │ │ - Storage    │
└──────────────┘ └──────────────┘ └──────────────┘
        │              │                  │
        └──────────────┬──────────────────┘
                       ▼
         ┌──────────────────────────────┐
         │ Supabase (PostgreSQL)        │
         │ - pgvector (embeddings)      │
         │ - RLS policies (tenant iso)  │
         │ - Storage buckets (docs)     │
         └──────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
    ┌────────┐   ┌─────────┐   ┌──────────┐
    │Anthropic│   │OpenAI   │   │Voyage    │
    │Claude   │   │GPT-4    │   │law-2     │
    │API      │   │API      │   │API       │
    └────────┘   └─────────┘   └──────────┘
        │              │              │
        └──────────────┼──────────────┘
                       ▼
         ┌──────────────────────────────┐
         │ LangSmith Observability      │
         │ - Tracing (@traceable)       │
         │ - Custom evaluators          │
         │ - Cost tracking              │
         │ - Dataset management         │
         └──────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
    ┌──────────┐  ┌────────┐  ┌──────────┐
    │Slack     │  │Resend  │  │Metrics   │
    │Webhooks  │  │Email   │  │Dashboard │
    └──────────┘  └────────┘  └──────────┘
```

### Quick Start (Infrastructure)

1. **Clone and configure environment:**
   ```bash
   cp .env.example .env.local
   # Fill in API keys and endpoints
   ```

2. **Initialize database:**
   ```bash
   npx supabase db push
   # Applies migrations from supabase/migrations/
   ```

3. **Set up authentication:**
   - Create Clerk organization and configure SAML/SSO
   - Middleware in `/clerk/middleware.ts` enforces role-based access

4. **Configure workflows:**
   - Import n8n workflows from `/n8n/` directory
   - Create Slack and Resend webhooks

5. **Deploy Trigger.dev jobs:**
   - Configure TypeScript jobs in `/trigger-jobs/`
   - Set up webhook endpoints in n8n for job triggering

6. **Deploy to Vercel:**
   ```bash
   vercel deploy
   # Uses vercel.json for API function sizing, crons, environment variables
   ```

---

## The Problem

During M&A due diligence, deal teams manually review 200–500+ contracts per transaction. Associates spend 3–4 weeks reading contracts line by line, extracting terms into spreadsheets, and flagging risk provisions. This process is:

- **Slow** - a single mid-market deal ties up 2–3 associates for weeks
- **Error-prone** - fatigue-driven mistakes in clause extraction and risk identification
- **Expensive** - $150K–$300K in labor costs per transaction for contract review alone
- **Inconsistent** - different reviewers apply different standards to the same clause types

## The Solution

A platform that combines multi-model AI orchestration with structured legal document processing to deliver consistent, auditable contract analysis at scale.

**Core Capabilities:**

- **Clause Extraction** - Automatically identifies and extracts 40+ clause types (change of control, assignment, termination, indemnification, exclusivity, payment terms, renewal, IP ownership, non-compete, governing law)
- **Risk Scoring** - Flags high-risk provisions with severity ratings and explanations, benchmarked against standard market terms
- **Cross-Document Analysis** - Identifies conflicts, inconsistencies, and patterns across the full contract portfolio
- **Semantic Search** - Natural language queries across all ingested contracts ("show me all contracts with unlimited liability provisions")
- **Deal-Ready Deliverables** - Auto-generates contract matrices (Excel), risk reports (PDF), and executive summaries (PowerPoint)

## Results

| Metric | Before | After |
|---|---|---|
| Contract review time (per deal) | 3–4 weeks | 2–3 days |
| Cost per transaction | $150K–$300K | $15K–$30K |
| Clause extraction accuracy | Manual (varies) | 94% F1 score |
| Risk flags caught | ~70% (human fatigue) | 97% recall |
| Contracts processed per hour | 3–5 (manual) | 50–80 (automated) |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                             │
│  Next.js + shadcn/ui │ PDF Viewer │ Risk Dashboard │ Search UI  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API GATEWAY (FastAPI)                       │
│  /upload  │  /analyze  │  /search  │  /export  │  /review       │
└──────────────────────────────┬──────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
┌──────────────────┐ ┌─────────────────┐ ┌──────────────────┐
│   INGESTION      │ │  AI ANALYSIS    │ │  DELIVERY        │
│                  │ │                 │ │                  │
│ Docling (native) │ │ Claude API      │ │ openpyxl (Excel) │
│ Azure Doc Intel  │ │ GPT-4 (fallback)│ │ python-pptx (PPT)│
│ (scanned/OCR)    │ │ voyage-law-2    │ │ WeasyPrint (PDF) │
│ python-docx      │ │ embeddings      │ │ S3 + presigned   │
│ (Word files)     │ │                 │ │ URLs             │
└────────┬─────────┘ │ LangGraph       │ └────────┬─────────┘
         │           │ orchestration   │          │
         ▼           └────────┬────────┘          │
┌─────────────────────────────┴───────────────────┴──────────────┐
│                     DATA LAYER                                  │
│  Supabase (PostgreSQL + pgvector + RLS + Auth)                  │
│  Hybrid search: BM25 + vector + Cohere Rerank                   │
│  Clause library with centroid embeddings                        │
└─────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| **AI/NLP** | Claude API (primary), GPT-4 (fallback) | Multi-model routing for accuracy; Claude's 200K context handles full contracts |
| **Embeddings** | Voyage-law-2 | Outperforms OpenAI by 6% on legal retrieval benchmarks |
| **Document Processing** | Docling (native PDF), Azure Document Intelligence (scanned/OCR) | Docling: MIT license, DocLayNet layout analysis; Azure: 99.8% OCR accuracy |
| **Vector Search** | pgvector + pgvectorscale on Supabase | 471 QPS at 99% recall on 50M vectors; hybrid BM25 + semantic search |
| **Orchestration** | LangGraph (AI agents), Temporal (durable pipelines), Celery (async exports) | Stateful agent graphs with human-in-the-loop review injection |
| **Frontend** | Next.js, shadcn/ui, react-pdf-highlighter, Tiptap | Split-pane contract viewer with inline clause highlighting and annotation |
| **Compliance** | Presidio (PII redaction), PostgreSQL RLS, ZDR API agreements | Attorney-client privilege protection; tenant-level data isolation |
| **Export** | openpyxl, python-pptx, WeasyPrint | Deal-ready deliverables matching firm templates and branding |

## Key Design Decisions

| Decision | Choice | Alternative Considered | Rationale |
|---|---|---|---|
| Multi-model vs. single model | Multi-model routing | Single Claude API | Different clause types benefit from different model strengths; fallback prevents single-point-of-failure |
| Vector database | pgvector on Supabase | Pinecone, Weaviate | Unified PostgreSQL stack (vectors + metadata + auth + RLS in one database); eliminates data sync complexity |
| Chunking strategy | Clause-level hierarchical (200–500 tokens) | Fixed-size chunks | Legal documents have natural clause boundaries; preserves legal context and enables precise attribution |
| PII handling | Pre-processing redaction (Presidio) | Post-processing filtering | *United States v. Heppner* (2026) - AI-processed documents without PII redaction risk privilege waiver |
| OCR pipeline | Dual-path (Docling native + Azure OCR) | Single OCR for all | 70% of contracts are native PDFs - Docling is faster and free; Azure OCR only for scanned documents |
| Human-in-the-loop | LangGraph conditional routing | Fully automated | Confidence < 0.85 routes to human review; maintains attorney oversight for privilege protection |

## AI Pipeline Detail

```
Document Upload
      │
      ▼
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Detect Type │────▶│  Native PDF?     │─Yes─▶│  Docling         │
│  (native vs  │     │  (text/size      │      │  (DocLayNet +    │
│   scanned)   │     │   ratio check)   │      │  TableFormer)    │
└─────────────┘     └──────────────────┘      └────────┬─────────┘
                            │ No                        │
                            ▼                           │
                    ┌──────────────────┐                │
                    │  Azure Document  │                │
                    │  Intelligence    │                │
                    │  (OCR + layout)  │                │
                    └────────┬─────────┘                │
                             │                          │
                             ▼                          ▼
                    ┌──────────────────────────────────────────┐
                    │  Clause-Level Chunking                    │
                    │  (200-500 tokens, preserve hierarchy)     │
                    │  Metadata: section, clause #, page, type  │
                    └─────────────────┬────────────────────────┘
                                      │
                                      ▼
                    ┌──────────────────────────────────────────┐
                    │  PII Redaction (Microsoft Presidio)       │
                    │  Confidence > 0.7 → anonymize             │
                    │  Mapping table in encrypted storage        │
                    └─────────────────┬────────────────────────┘
                                      │
                    ┌─────────────────┬┴────────────────┐
                    ▼                 ▼                  ▼
            ┌──────────────┐ ┌──────────────┐  ┌──────────────┐
            │ Claude API   │ │ Risk Scoring │  │ Embedding    │
            │ Clause       │ │ (severity +  │  │ Generation   │
            │ Extraction   │ │ explanation) │  │ (voyage-     │
            │ (structured  │ │              │  │  law-2)      │
            │  JSON output)│ │              │  │              │
            └──────┬───────┘ └──────┬───────┘  └──────┬───────┘
                   │                │                  │
                   ▼                ▼                  ▼
            ┌──────────────────────────────────────────────────┐
            │  Supabase (PostgreSQL + pgvector)                 │
            │  Contracts → Clauses → Risk Flags → Embeddings    │
            │  Hybrid search: BM25 + vector + Cohere Rerank     │
            └──────────────────────────────────────────────────┘
```

## Repository Structure

```
contract-intelligence-platform/
├── README.md                          # You are here
├── docs/
│   ├── PRD.md                         # Product Requirements Document
│   ├── ARCHITECTURE.md                # Detailed system architecture
│   ├── USER_STORIES.md                # Epics and acceptance criteria
│   ├── DATA_MODEL.md                  # Database schema and ERD
│   ├── API_SPEC.md                    # REST API documentation
│   ├── COMPETITIVE_ANALYSIS.md        # Market landscape
│   ├── METRICS.md                     # KPIs and success metrics
│   ├── ROADMAP.md                     # Phased rollout plan
│   └── DECISION_LOG.md               # Technical trade-off decisions
├── src/
│   ├── ingestion/                     # Document processing pipeline
│   ├── analysis/                      # AI clause extraction + risk scoring
│   ├── search/                        # Hybrid vector + keyword search
│   ├── export/                        # Report generation (Excel, PPT, PDF)
│   └── api/                           # FastAPI endpoints
├── tests/                             # Unit and integration tests
├── docker-compose.yml                 # Local development environment
├── requirements.txt                   # Python dependencies
└── .github/
    └── ISSUE_TEMPLATE/                # Feature request + bug report templates
```

## Product Documents

| Document | Description |
|---|---|
| [PRD](docs/PRD.md) | Full product requirements - personas, user flows, functional specs, constraints |
| [Architecture](docs/ARCHITECTURE.md) | System design, data flows, infrastructure, scaling considerations |
| [User Stories](docs/USER_STORIES.md) | Epics broken into stories with acceptance criteria |
| [Data Model](docs/DATA_MODEL.md) | PostgreSQL schema, entity relationships, indexing strategy |
| [API Spec](docs/API_SPEC.md) | RESTful endpoints, request/response schemas, authentication |
| [Competitive Analysis](docs/COMPETITIVE_ANALYSIS.md) | Harvey, Luminance, Ironclad, Kira - positioning and differentiation |
| [Metrics](docs/METRICS.md) | North star metric, input metrics, guardrail metrics |
| [Roadmap](docs/ROADMAP.md) | Phase 0 (MVP) through Phase 3, with milestones |
| [Decision Log](docs/DECISION_LOG.md) | Key technical decisions with context and trade-offs |

## Competitive Landscape

| Platform | Approach | Differentiation | Our Advantage |
|---|---|---|---|
| **Harvey AI** | Custom foundation model, LexisNexis integration | Deep legal training corpus | We're purpose-built for M&A due diligence workflows, not general legal |
| **Luminance** | "Panel of Judges" multi-model architecture | 150M+ document training set | Open architecture vs. black box; client owns their data |
| **Ironclad** | GPT-4 agent family (6 specialized agents) | CLM + AI Playbooks | We focus on analysis, not contract lifecycle management |
| **Kira/Litera** | 1,400+ pre-trained provision models | Broadest clause coverage | Modern AI architecture vs. legacy ML models |

## Compliance and Security

This platform was designed with legal industry compliance requirements at the center, not bolted on after the fact.

- **Attorney-Client Privilege** - PII redaction before AI processing; human-in-the-loop review maintains attorney supervision per *Heppner* (2026)
- **Zero Data Retention** - All LLM API calls under ZDR agreements; no training on client data
- **Tenant Isolation** - PostgreSQL Row-Level Security enforces firm/matter-level data boundaries
- **Audit Trail** - Every document view, AI interaction, modification, and export is logged with timestamps, user identity, and before/after states
- **SOC 2 Type II** - Architecture designed for SOC 2 compliance from day one (Vanta/Drata automated monitoring)

## About This Project

This repository documents a product I built as **Principal Product Manager** for a PE-backed advisory firm. I owned the full product lifecycle - from initial client discovery through architecture decisions, sprint planning, and production deployment.

**My role included:**
- Conducting discovery with deal teams, associates, and partners to map due diligence workflows
- Defining product requirements and writing technical specifications
- Making technology selection decisions (documented in [Decision Log](docs/DECISION_LOG.md))
- Partnering with engineering on architecture, API design, and data modeling
- Establishing success metrics and building analytics dashboards
- Managing stakeholder communication and phased rollout

**Note:** Client-identifying details have been anonymized. Metrics and architecture reflect the actual production system.


