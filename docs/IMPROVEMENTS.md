# Contract Intelligence Platform - Improvements & Technology Roadmap

## Product Overview

The Contract Intelligence Platform is an AI-powered document processing system designed for M&A due diligence. It transforms how deal teams analyze contracts during mergers and acquisitions by ingesting hundreds of contracts (PDF/Word), automatically extracting 40+ clause types (change of control, assignment, termination, indemnification, IP ownership, etc.), scoring risk against configurable playbook rules, and generating deal-ready deliverables (Excel matrices, PDF reports, PowerPoint summaries).

The platform targets PE-backed advisory firms that conduct 15-40 transactions annually, where manual contract review costs $150K-$300K per deal and takes 3-4 weeks. The platform reduces this to 2-3 days at $15K-$30K, achieving a 94% F1 extraction accuracy score with 97% risk flag recall.

Key capabilities include:
- Dual-pipeline document ingestion (Docling for native PDFs, Azure Document Intelligence for scanned/OCR)
- Multi-model AI orchestration (Claude primary, GPT-4 fallback) with circuit breakers and retry logic
- PII redaction via Microsoft Presidio before any external API call (attorney-client privilege protection)
- Hybrid search (BM25 + pgvector HNSW + Cohere Rerank) achieving 91% search accuracy
- Human-in-the-loop routing for low-confidence extractions (confidence < 0.85)
- Multi-tenant architecture with PostgreSQL Row-Level Security

---

## Current Architecture

### Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| **AI/LLM** | Anthropic Claude API (primary) | anthropic 0.28.0 |
| **AI/LLM Fallback** | OpenAI GPT-4 Turbo | openai 1.35.0 |
| **Orchestration** | LangGraph state machine | langgraph 0.1.0 |
| **Embeddings** | Voyage AI voyage-law-2 (1024-dim) | voyage-ai 0.2.0 |
| **Document Processing** | Docling (native PDF), Azure Document Intelligence (OCR) | docling 0.20.0 |
| **Vector Database** | pgvector on Supabase PostgreSQL | pgvector 0.2.4 |
| **Search** | BM25 (PostgreSQL GIN) + vector + Cohere Rerank | cohere 4.34.0 |
| **API** | FastAPI + Pydantic v2 | fastapi 0.115.0, pydantic 2.10.0 |
| **PII Compliance** | Microsoft Presidio | presidio-analyzer 2.2.354 |
| **Export** | openpyxl, python-pptx, WeasyPrint | openpyxl 3.1.2 |
| **Async Jobs** | Trigger.dev (extraction), Celery (exports) | celery 5.3.4 |
| **Auth** | Clerk (SSO/SAML) + Next.js middleware | - |
| **Frontend** | Next.js + shadcn/ui + Recharts | - |
| **Observability** | LangSmith tracing + custom evaluators | langsmith (latest) |
| **Workflows** | n8n (ingestion, monitoring) | - |
| **Resilience** | pybreaker (circuit breakers), tenacity (retry) | pybreaker 1.2.0, tenacity 8.2.3 |

### Key Components

1. **`src/ingestion/document_processor.py`** - Dual-pipeline processor that routes native PDFs to Docling and scanned PDFs to Azure OCR. Performs clause-level chunking (200-500 tokens) with section boundary detection via regex patterns. Computes SHA-256 hashes for deduplication.

2. **`src/analysis/clause_extractor.py`** - Multi-model clause extraction with circuit breakers per provider (pybreaker, fail_max=5, reset_timeout=60s) and retry with exponential backoff (tenacity, 3 attempts). Extracts 41 clause types with confidence scoring and risk assessment.

3. **`src/analysis/risk_scorer.py`** - Two-pass risk scoring: rule-based playbook evaluation (12 default M&A rules covering change of control, liability caps, termination notice periods, etc.) plus missing clause detection against expected clause sets per contract type.

4. **`src/compliance/pii_redactor.py`** - Pre-LLM PII redaction using Microsoft Presidio with legal-specific false positive suppression (jurisdiction names, entity type labels, legal role terms). Supports de-anonymization post-LLM for result storage.

5. **`src/search/hybrid_search.py`** - Three-stage search: BM25 keyword search (PostgreSQL GIN), pgvector HNSW approximate nearest neighbor search, and Reciprocal Rank Fusion + Cohere Rerank cross-encoder reranking.

6. **`src/orchestration/analysis_workflow.py`** - LangGraph-style 5-stage state machine: Document Classification, Clause Extraction, Risk Scoring, Cross-Reference Check, Human Review Routing. Conditional routing based on confidence thresholds and risk levels.

7. **`src/export/matrix_generator.py`** - Excel contract matrix generator with RAG conditional formatting (red/amber/green), multi-tab output (Contract Matrix, Risk Flags, Summary), and firm-specific branding templates.

8. **`trigger-jobs/contract_extraction.ts`** - Trigger.dev long-running extraction job with 6 checkpointed stages and LangSmith tracing integration.

9. **`mcp/server.py`** - Model Context Protocol server exposing 4 tools: analyze_contract, search_contracts, get_risk_summary, compare_clauses.

10. **`schema/schema.sql`** - 12-table PostgreSQL schema with pgvector, RLS policies, GIN full-text indexes, HNSW vector indexes (m=16, ef_construction=128), and helper views for deal summaries and non-standard clause detection.

---

## Recommended Improvements

### 1. Upgrade to Claude Structured Output with Tool Use (Critical)

**Current state:** `clause_extractor.py` (line 61-80) uses a freeform text prompt that asks Claude to return JSON. The Trigger.dev job (`contract_extraction.ts`, line 244-248) parses JSON from raw text via regex (`text.match(/\[[\s\S]*\]/)`).

**Problem:** Freeform JSON extraction is fragile. The regex JSON parsing in the TypeScript job is brittle and will fail on edge cases (nested brackets in legal text, markdown-wrapped JSON blocks, partial responses).

**Improvement:** Use Anthropic's tool_use / structured output feature to enforce schema compliance at the API level.

```python
# In clause_extractor.py - replace freeform prompt with tool use
response = self.anthropic_client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=8192,
    temperature=0.2,
    tools=[{
        "name": "extract_clauses",
        "description": "Extract contract clauses with structured fields",
        "input_schema": {
            "type": "object",
            "properties": {
                "clauses": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "clause_type": {"type": "string", "enum": CLAUSE_TYPES},
                            "text": {"type": "string"},
                            "page_number": {"type": "integer"},
                            "section_reference": {"type": "string"},
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                            "risk_level": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                            "risk_explanation": {"type": "string"}
                        },
                        "required": ["clause_type", "text", "confidence", "risk_level"]
                    }
                }
            },
            "required": ["clauses"]
        }
    }],
    tool_choice={"type": "tool", "name": "extract_clauses"},
    messages=[{"role": "user", "content": prompt}],
)
```

This eliminates the regex parsing entirely and guarantees valid JSON with correct field types.

### 2. Implement Prompt Caching for Cost Reduction

**Current state:** The extraction prompt in `clause_extractor.py` (line 61-80) includes the full list of 41 clause types on every API call. The system message and few-shot examples in `src/prompts/clause_extraction.py` (lines 57-321) total approximately 3,000+ tokens that are identical across every extraction call.

**Improvement:** Use Anthropic's prompt caching to cache the system message, clause type list, and few-shot examples. With hundreds of contracts per deal, this would reduce input token costs by 50-70%.

```python
# Cache the static system + few-shot prefix
response = self.anthropic_client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=8192,
    system=[
        {
            "type": "text",
            "text": SYSTEM_MESSAGE + "\n\n" + FEW_SHOT_EXAMPLES,
            "cache_control": {"type": "ephemeral"}
        }
    ],
    messages=[{"role": "user", "content": contract_text}],
)
```

At 200 contracts per deal with ~3,000 cached tokens each, this saves approximately $1.80 per deal in input token costs, and reduces latency by avoiding re-processing of static prefix tokens.

### 3. Replace Condition Evaluation with Structured Attribute Extraction

**Current state:** `risk_scorer.py` has a `_condition_matches` method (lines 208-221) that performs a simplified check -- it just looks at whether `risk_level` is "high" or "critical". The playbook rules define conditions like `"notice_period_days < 30"` and `"is_uncapped"` (lines 31-116) but these are never actually parsed or evaluated.

**Improvement:** Add a lightweight expression evaluator or structured attribute extraction step. After clause extraction, run a second LLM pass to extract structured attributes (notice_period_days, is_exclusive, scope, etc.) per clause, then evaluate playbook conditions against those attributes.

```python
# New: structured attribute extraction per clause
ATTRIBUTE_SCHEMA = {
    "termination_convenience": {
        "notice_period_days": int,
        "is_mutual": bool,
        "requires_cause": bool,
    },
    "limitation_of_liability": {
        "is_uncapped": bool,
        "cap_amount": str,
        "cap_basis": str,  # "annual_fees", "contract_value", "fixed"
        "excludes_indirect": bool,
    },
    "change_of_control": {
        "triggers_termination_right": bool,
        "requires_consent": bool,
        "notice_period_days": int,
        "cure_period_days": int,
    },
}

def _condition_matches(self, rule: PlaybookRule, clause, attributes: dict) -> bool:
    """Evaluate playbook condition against extracted attributes."""
    condition = rule.condition
    # Parse and evaluate: "notice_period_days < 30"
    # Using a safe expression evaluator (not eval())
    import ast
    import operator
    # ... safe expression evaluation against attributes dict
```

### 4. Add Batch Embedding Generation with Voyage AI

**Current state:** `trigger-jobs/contract_extraction.ts` (lines 310-355) generates embeddings clause-by-clause via individual API calls to Voyage AI.

**Improvement:** Voyage AI supports batch embedding with up to 128 texts per request. Batching reduces API calls from N to ceil(N/128) and significantly reduces latency.

```typescript
// Batch embeddings instead of one-by-one
const BATCH_SIZE = 128;
const allTexts = clauses.map(c => c.extracted_text);
const embeddings: Record<string, number[]> = {};

for (let i = 0; i < allTexts.length; i += BATCH_SIZE) {
    const batch = allTexts.slice(i, i + BATCH_SIZE);
    const response = await fetch("https://api.voyage.ai/v1/embeddings", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${process.env.VOYAGE_API_KEY}`,
        },
        body: JSON.stringify({
            model: "voyage-law-2",
            input: batch,
            input_type: "document",
        }),
    });
    // Map batch results back to clause indices
}
```

### 5. Implement Streaming for Long Extraction Responses

**Current state:** The extraction pipeline waits for the full LLM response before processing. For large contracts with many clauses, this can mean 20-30 seconds of dead time before any results appear.

**Improvement:** Use Anthropic's streaming API to process clauses as they are generated, enabling progressive UI updates and earlier database writes.

### 6. Add Document Deduplication at the Deal Level

**Current state:** `document_processor.py` computes SHA-256 hashes (line 238-244) but there is no deduplication logic at the deal level. The `contracts` table has an index on `file_hash` (schema.sql, line 254) but no unique constraint per deal.

**Improvement:** Add a deduplication check before processing:

```python
def check_duplicate(self, file_hash: str, deal_id: str) -> Optional[str]:
    """Check if this exact document was already processed in this deal."""
    # Query: SELECT id FROM contracts WHERE file_hash = $1 AND deal_id = $2
    # If found, return existing contract_id and skip reprocessing
    pass
```

Also consider near-duplicate detection using SimHash or MinHash for contracts that are substantially similar but not byte-identical (e.g., redlined versions).

### 7. Improve Chunking Strategy with Semantic Boundaries

**Current state:** `document_processor.py` (lines 194-236) uses regex-based splitting on numbered section/clause boundaries (`SECTION_PATTERN` and `CLAUSE_PATTERN`). This works for well-structured contracts but fails on non-standard formatting, unnumbered clauses, or contracts with inconsistent numbering.

**Improvement:** Use a hybrid chunking approach:
1. Primary: Regex-based clause boundary detection (current approach, keep as fast path)
2. Fallback: LLM-assisted boundary detection for documents where regex finds fewer than expected clauses
3. Enhancement: Use Docling's DocLayNet layout analysis to detect structural elements (headers, paragraphs, tables, lists) and use those as chunking boundaries

```python
def _chunk_by_clauses(self, page_texts: dict, layout_elements: list = None) -> list:
    """Hybrid chunking: regex-first, layout-assisted fallback."""
    chunks = self._regex_chunk(page_texts)

    if len(chunks) < 5 and layout_elements:
        # Regex found too few boundaries -- use layout analysis
        chunks = self._layout_chunk(page_texts, layout_elements)

    if len(chunks) < 3:
        # Still too few -- use LLM to identify clause boundaries
        chunks = self._llm_assisted_chunk(page_texts)

    return chunks
```

### 8. Add Comprehensive Error Recovery in Trigger.dev Jobs

**Current state:** `trigger-jobs/contract_extraction.ts` has basic try/catch error handling but no checkpointing or partial result recovery. If the job fails at Stage 4 (embeddings), all work from Stages 1-3 is lost.

**Improvement:** Implement idempotent stages with checkpoint storage. Each stage should persist its results before moving to the next, and the job should be able to resume from the last successful checkpoint.

```typescript
// Add checkpoint persistence between stages
async function withCheckpoint<T>(
    contractId: string,
    stage: string,
    fn: () => Promise<T>
): Promise<T> {
    // Check if this stage was already completed
    const cached = await getCheckpoint(contractId, stage);
    if (cached) return cached as T;

    const result = await fn();
    await saveCheckpoint(contractId, stage, result);
    return result;
}
```

### 9. Add Clause Versioning and Diff Tracking

**Current state:** The schema supports `override_text` and `override_reason` on the clauses table (schema.sql, lines 303-304), but there is no version history for clause edits.

**Improvement:** Add a `clause_versions` table to track every edit, enabling audit trails and undo functionality:

```sql
CREATE TABLE clause_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clause_id UUID NOT NULL REFERENCES clauses(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    previous_text TEXT,
    new_text TEXT NOT NULL,
    changed_by UUID REFERENCES users(id),
    change_reason TEXT,
    change_type TEXT NOT NULL, -- 'auto_extraction', 'human_review', 'override'
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (clause_id, version_number)
);
```

### 10. Enhance the Dashboard with Real-Time WebSocket Updates

**Current state:** `dashboard/contract_dashboard.jsx` uses static synthetic data. In production, it would need to poll the API for updates during active extraction runs.

**Improvement:** Integrate Supabase Realtime (which uses WebSockets) to push extraction progress, new risk flags, and review status changes to the dashboard without polling:

```jsx
// Use Supabase Realtime for live updates
useEffect(() => {
    const channel = supabase
        .channel('extraction-updates')
        .on('postgres_changes', {
            event: 'UPDATE',
            schema: 'public',
            table: 'contracts',
            filter: `deal_id=eq.${dealId}`,
        }, (payload) => {
            updateContractStatus(payload.new);
        })
        .subscribe();

    return () => supabase.removeChannel(channel);
}, [dealId]);
```

### 11. Add Rate Limiting and Token Budget Management

**Current state:** No token budget enforcement exists. The `langsmith/tracing_config.py` tracks costs per extraction (lines 176-200) but does not enforce limits.

**Improvement:** Add per-deal and per-tenant token budget enforcement:

```python
class TokenBudgetManager:
    """Enforce token budgets per deal and per tenant."""

    async def check_budget(self, tenant_id: str, deal_id: str, estimated_tokens: int) -> bool:
        """Return True if budget allows this extraction."""
        tenant_budget = await self.get_remaining_budget(tenant_id)
        deal_budget = await self.get_deal_budget(deal_id)
        return estimated_tokens <= min(tenant_budget, deal_budget)

    async def record_usage(self, tenant_id: str, deal_id: str, tokens_used: int, cost_usd: float):
        """Record token usage for billing and budget tracking."""
        pass
```

---

## New Technologies & Trends

### 1. Claude claude-sonnet-4-20250514 with Extended Thinking (Anthropic)

Anthropic's Claude claude-sonnet-4-20250514 model with extended thinking capability allows the model to reason through complex legal provisions before producing structured output. For contract analysis where nuanced interpretation is critical (e.g., determining whether a change-of-control clause truly triggers a termination right vs. merely a notification obligation), extended thinking would improve accuracy on the hardest 10-15% of clauses where the current system routes to human review.

**How to integrate:** Use extended thinking for high-value clause types (change_of_control, indemnification, limitation_of_liability) where the confidence delta between models is largest. Set `thinking: {"type": "enabled", "budget_tokens": 4096}` in the API call.

**Reference:** https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking

### 2. Docling v2 with Advanced Table Extraction (IBM)

Docling has evolved significantly since version 0.20.0. Recent releases (v2.x) include improved DocLayNet layout analysis with better table detection, formula parsing, and multi-column layout handling. The TableFormer model has been upgraded to handle complex nested tables common in financial contracts (payment schedules, milestone tables, fee structures).

**How to integrate:** Upgrade from `docling==0.20.0` to the latest v2.x release. The new API provides structured `DoclingDocument` objects with explicit table, list, and section hierarchy, which would directly improve the chunking quality in `document_processor.py`.

**Reference:** https://github.com/DS4SD/docling

### 3. Voyage AI voyage-3-law (Successor to voyage-law-2)

Voyage AI has released voyage-3 and voyage-3-lite models that outperform voyage-law-2 on legal benchmarks. The voyage-3 model family achieves state-of-the-art performance on MTEB legal retrieval tasks with improved handling of long documents (up to 32K tokens per input). The architecture supports Matryoshka Representation Learning (MRL), allowing dimension reduction from 1024 to 256 or 512 with minimal quality loss, which would reduce storage costs for the clause_embeddings table.

**How to integrate:** Update the embedding model in `hybrid_search.py` and the `clause_embeddings` table schema. Consider using MRL at 512 dimensions to halve storage costs while retaining >98% retrieval quality.

**Reference:** https://docs.voyageai.com/docs/embeddings

### 4. Cohere Rerank 3.5 with Structured Output

Cohere's Rerank v3.5 model supports structured relevance judgments with per-result explanations, which is valuable for legal search where users need to understand WHY a result is relevant. It also supports multi-field reranking, where you can pass clause metadata (clause_type, risk_level, contract_type) alongside the text to improve ranking quality.

**How to integrate:** Update the `_rerank` method in `hybrid_search.py` to use `rerank-v3.5` and pass structured metadata alongside clause text.

**Reference:** https://docs.cohere.com/docs/rerank-2

### 5. LangGraph Checkpointing and Human-in-the-Loop Persistence

LangGraph has matured significantly with built-in state persistence using checkpointers (SQLite, PostgreSQL, Redis). This directly addresses the limitation in `analysis_workflow.py` where the workflow state exists only in memory. With LangGraph checkpointing, the workflow can be paused at the human review stage, persisted to PostgreSQL, and resumed after an analyst reviews and accepts/rejects clauses.

**How to integrate:** Replace the custom state machine in `analysis_workflow.py` with LangGraph's `StateGraph` and PostgreSQL checkpointer:

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(DATABASE_URL)

workflow = StateGraph(AnalysisState)
workflow.add_node("classify", classify_document)
workflow.add_node("extract", extract_clauses)
workflow.add_node("score_risks", score_risks)
workflow.add_node("human_review", human_review_node)  # interrupt_before
workflow.add_node("cross_reference", cross_reference_check)

# Compile with checkpointing
app = workflow.compile(checkpointer=checkpointer, interrupt_before=["human_review"])
```

**Reference:** https://langchain-ai.github.io/langgraph/concepts/persistence/

### 6. Structured Output via Pydantic Models (OpenAI & Anthropic)

Both OpenAI and Anthropic now support Pydantic model-based structured output. Instead of manually crafting JSON schemas, define extraction schemas as Pydantic models and pass them directly to the API. This integrates naturally with the existing Pydantic v2 stack (the project already uses pydantic 2.10.0).

**How to integrate:** Define clause extraction schemas as Pydantic models and use Anthropic's or OpenAI's structured output with `response_format`:

```python
from pydantic import BaseModel, Field

class ExtractedClauseSchema(BaseModel):
    clause_type: str = Field(..., description="One of the 41 predefined clause types")
    text: str = Field(..., description="Exact clause text from the contract")
    confidence: float = Field(..., ge=0.0, le=1.0)
    risk_level: Literal["low", "medium", "high", "critical"]
    risk_explanation: str
```

### 7. Microsoft Presidio v2.3+ with Custom Legal NER

Presidio has added support for custom transformer-based NER models (HuggingFace integration) that significantly outperform the default SpaCy models on legal text. A fine-tuned Legal-BERT NER model can detect entities like case citations, statutory references, and corporate entity names with much higher accuracy than generic NER.

**How to integrate:** Register a custom transformer recognizer in `pii_redactor.py`:

```python
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import TransformersNlpEngine

# Use a legal-domain transformer for better entity detection
nlp_engine = TransformersNlpEngine(
    models=[{"lang_code": "en", "model_name": {"spacy": "en_core_web_trf", "transformers": "nlpaueb/legal-bert-base-uncased"}}]
)
analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
```

**Reference:** https://microsoft.github.io/presidio/

### 8. pgvectorscale for 10x Faster Vector Search at Scale

Timescale's pgvectorscale extension (built on top of pgvector) implements StreamingDiskANN indexing that achieves 28x lower p95 latency compared to standard HNSW indexes at 50M+ vector scale. Since the project already targets 50M+ vectors (README line 37), this is directly relevant.

**How to integrate:** Replace HNSW indexes with StreamingDiskANN in the schema:

```sql
-- Replace HNSW with StreamingDiskANN for better performance at scale
CREATE INDEX idx_clause_embeddings_diskann ON clause_embeddings
  USING diskann (embedding vector_cosine_ops);
```

**Reference:** https://github.com/timescale/pgvectorscale

### 9. LLM-as-Judge Evaluation Framework

The current evaluation in `langsmith/tracing_config.py` uses simple set-based metrics (predicted clause types vs. expected clause types, line 299-308). Modern LLM-as-Judge frameworks like Braintrust (already partially integrated in `evals/braintrust/`) and DeepEval enable more nuanced evaluation of extraction quality, including semantic equivalence checking (did the model extract the same meaning even if wording differs?).

**How to integrate:** Add LLM-as-Judge evaluators for semantic accuracy:

```python
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase

clause_accuracy = GEval(
    name="Clause Extraction Semantic Accuracy",
    criteria="Does the extracted clause capture the same legal meaning as the ground truth?",
    evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.EXPECTED_OUTPUT],
    model="claude-sonnet-4-20250514",
)
```

**Reference:** https://github.com/confident-ai/deepeval

### 10. Agentic RAG with Multi-Step Retrieval

The current search pipeline in `hybrid_search.py` performs a single query-response cycle. For complex legal queries like "find all contracts where termination provisions conflict with the assignment clause", agentic RAG would decompose the query into sub-queries, retrieve relevant clauses for each, and synthesize a cross-referenced answer.

**How to integrate:** Use LangGraph to build an agentic retrieval loop:

```python
def agentic_search(query: str, deal_id: str):
    # Step 1: Decompose complex query into sub-queries
    sub_queries = decompose_query(query)  # LLM call

    # Step 2: Execute each sub-query against hybrid search
    results_per_query = {q: hybrid_search(q, deal_id) for q in sub_queries}

    # Step 3: Cross-reference and synthesize results
    synthesized = synthesize_results(query, results_per_query)  # LLM call

    return synthesized
```

### 11. Contextual Retrieval with Chunk Headers

Anthropic's contextual retrieval technique prepends each chunk with a brief LLM-generated description of its context within the broader document. This significantly improves retrieval quality because individual clauses often lack context about which contract or section they belong to.

**How to integrate:** During the chunking phase in `document_processor.py`, generate a contextual header for each chunk:

```python
# Prepend contextual header to each chunk before embedding
context_prefix = f"This clause is from a {contract_type} between {party_a} and {party_b}, "
                 f"in Section {section_ref} ({section_title}), governing law: {governing_law}. "
chunk_with_context = context_prefix + chunk.text
# Embed chunk_with_context instead of chunk.text
```

**Reference:** https://www.anthropic.com/news/contextual-retrieval

### 12. Fine-Tuned Legal Classification Models

For the document classification stage (`analysis_workflow.py`, lines 264-297), using a fine-tuned smaller model (e.g., Legal-BERT or a fine-tuned DistilBERT) would be faster and cheaper than Claude for the binary/multi-class classification task of determining contract type (MSA, NDA, SOW, etc.). This is a well-defined classification problem that does not require the reasoning capability of a frontier LLM.

**How to integrate:** Train a classifier on labeled contract types and use it for Stage 1, reserving Claude for the more complex extraction and risk scoring stages:

```python
from transformers import pipeline

classifier = pipeline("text-classification", model="your-org/contract-type-classifier")

def classify_document(text: str) -> str:
    result = classifier(text[:512])  # First 512 tokens sufficient for classification
    return result[0]["label"]  # "msa", "nda", "sow", etc.
```

### 13. Multi-Modal Contract Processing

Many contracts include embedded images (signatures, stamps, diagrams, floor plans in leases). Claude's vision capability can process these directly without separate OCR, which is particularly relevant for lease agreements with floor plans and construction contracts with engineering drawings.

**How to integrate:** When processing PDFs with embedded images, extract images and send them alongside text to Claude:

```python
# For pages with significant image content
import base64

image_data = base64.standard_b64encode(page_image_bytes).decode("utf-8")
messages = [
    {
        "role": "user",
        "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_data}},
            {"type": "text", "text": "Extract any contract terms, signatures, or relevant data from this image."}
        ]
    }
]
```

---

## Priority Roadmap

### P0 - Critical (Do First, High Impact, Low-Medium Effort)

| # | Improvement | Effort | Impact | Files Affected |
|---|-----------|--------|--------|---------------|
| 1 | **Upgrade to Claude Structured Output with Tool Use** | 2-3 days | Eliminates JSON parsing failures, improves extraction reliability | `src/analysis/clause_extractor.py`, `trigger-jobs/contract_extraction.ts` |
| 2 | **Implement Prompt Caching** | 1 day | 50-70% reduction in input token costs across all extraction calls | `src/analysis/clause_extractor.py`, `src/prompts/clause_extraction.py` |
| 3 | **Batch Embedding Generation** | 1 day | Reduces Voyage API calls from N to ceil(N/128), significant latency reduction | `trigger-jobs/contract_extraction.ts` |
| 4 | **Add Checkpoint Recovery for Trigger.dev Jobs** | 2-3 days | Prevents loss of work on partial failures during 2-10 min extraction jobs | `trigger-jobs/contract_extraction.ts` |
| 5 | **Document Deduplication at Deal Level** | 1 day | Prevents wasted processing and duplicate entries in the deal analysis | `src/ingestion/document_processor.py`, `schema/schema.sql` |

### P1 - High Priority (Next Sprint, High Impact, Medium Effort)

| # | Improvement | Effort | Impact | Files Affected |
|---|-----------|--------|--------|---------------|
| 6 | **Replace Condition Evaluation in Risk Scorer** | 3-5 days | Enables actual playbook rule evaluation instead of simplified risk_level check | `src/analysis/risk_scorer.py`, `src/analysis/clause_extractor.py` |
| 7 | **LangGraph Checkpointing for Human-in-the-Loop** | 3-5 days | Enables persistent pause/resume workflows for human review | `src/orchestration/analysis_workflow.py` |
| 8 | **Upgrade to Voyage voyage-3 or voyage-3-law** | 2-3 days | Improved retrieval quality, potential storage savings with MRL | `src/search/hybrid_search.py`, `schema/schema.sql` |
| 9 | **Contextual Retrieval Chunk Headers** | 2 days | Significant improvement in search relevance for out-of-context clauses | `src/ingestion/document_processor.py`, `src/search/hybrid_search.py` |
| 10 | **Upgrade Cohere Rerank to v3.5** | 1 day | Better reranking with structured metadata support | `src/search/hybrid_search.py` |

### P2 - Medium Priority (Next Quarter, Medium Impact, Medium-High Effort)

| # | Improvement | Effort | Impact | Files Affected |
|---|-----------|--------|--------|---------------|
| 11 | **Real-Time Dashboard Updates via Supabase Realtime** | 3-5 days | Eliminates polling, live extraction progress during deal analysis | `dashboard/contract_dashboard.jsx` |
| 12 | **Token Budget and Rate Limiting** | 3 days | Prevents runaway costs, enables per-tenant billing | `src/analysis/clause_extractor.py`, `langsmith/tracing_config.py` |
| 13 | **Semantic Chunking Fallback** | 5 days | Handles poorly-formatted contracts that defeat regex-based chunking | `src/ingestion/document_processor.py` |
| 14 | **Clause Version History Table** | 2 days | Full audit trail for all clause edits, enables undo | `schema/schema.sql` |
| 15 | **pgvectorscale StreamingDiskANN Indexes** | 2 days | 10-28x lower p95 latency at 50M+ vector scale | `schema/schema.sql`, `supabase/migrations/` |
| 16 | **LLM-as-Judge Evaluation for Semantic Accuracy** | 3-5 days | More accurate evaluation of extraction quality beyond simple F1 | `langsmith/tracing_config.py`, `evals/` |
| 17 | **Presidio with Legal-Domain Transformer NER** | 3 days | Better PII detection accuracy, fewer false positives in legal text | `src/compliance/pii_redactor.py` |

### P3 - Future (Long-Term, Strategic, High Effort)

| # | Improvement | Effort | Impact | Files Affected |
|---|-----------|--------|--------|---------------|
| 18 | **Extended Thinking for Complex Clause Analysis** | 5-7 days | Improved accuracy on hardest 10-15% of clause extractions | `src/analysis/clause_extractor.py` |
| 19 | **Fine-Tuned Contract Type Classifier** | 2-3 weeks | Faster, cheaper classification stage; reserves LLM for extraction | `src/orchestration/analysis_workflow.py` |
| 20 | **Agentic RAG for Multi-Step Legal Queries** | 2-3 weeks | Handles complex cross-contract queries that current search cannot answer | `src/search/hybrid_search.py` |
| 21 | **Multi-Modal Contract Processing** | 2 weeks | Processes embedded images, signatures, floor plans in lease agreements | `src/ingestion/document_processor.py` |
| 22 | **Docling v2 Upgrade with Advanced Table Extraction** | 1 week | Better handling of payment schedules, milestone tables, fee structures | `src/ingestion/document_processor.py`, `requirements.txt` |
| 23 | **Near-Duplicate Detection (SimHash/MinHash)** | 1 week | Detects substantially similar contracts (redlined versions, amendments) | `src/ingestion/document_processor.py` |
| 24 | **Streaming Extraction for Progressive UI Updates** | 1 week | Users see clauses appearing in real-time during extraction | `src/analysis/clause_extractor.py`, `dashboard/` |

---

## Dependency Upgrade Recommendations

The following dependencies should be upgraded from their current pinned versions:

| Package | Current | Recommended | Reason |
|---------|---------|-------------|--------|
| `anthropic` | 0.28.0 | 0.49.0+ | Structured output, prompt caching, extended thinking, citations API |
| `openai` | 1.35.0 | 1.60.0+ | Structured output with Pydantic, improved function calling |
| `langgraph` | 0.1.0 | 0.3.x+ | PostgreSQL checkpointing, interrupt/resume, subgraphs |
| `langchain` | 0.1.17 | 0.3.x+ | Breaking changes from v0.1 to v0.3; improved LangGraph integration |
| `docling` | 0.20.0 | 2.x+ | DocLayNet v2, improved table extraction, structured document output |
| `voyage-ai` | 0.2.0 | 0.3.x+ | voyage-3 model support, MRL, longer context |
| `cohere` | 4.34.0 | 5.x+ | Rerank v3.5, structured relevance output |
| `pgvector` | 0.2.4 | 0.3.x+ | Improved HNSW performance, halfvec support for storage savings |
| `fastapi` | 0.115.0 | 0.115.0+ | Current version is recent; check for security patches |
| `pydantic` | 2.10.0 | 2.10.0+ | Current version is recent |
| `presidio-analyzer` | 2.2.354 | 2.2.355+ | Transformer NER support, improved legal entity detection |

---

## Summary

The Contract Intelligence Platform has a solid architectural foundation with well-thought-out design decisions (multi-model routing, clause-level chunking, hybrid search, pre-LLM PII redaction). The most impactful near-term improvements are:

1. **Structured output** via tool use (eliminates fragile JSON parsing)
2. **Prompt caching** (50-70% token cost reduction with minimal code changes)
3. **LangGraph checkpointing** (enables true persistent human-in-the-loop workflows)
4. **Batch embeddings** (reduces API calls and latency)
5. **Contextual retrieval** (improves search quality with minimal implementation effort)

These P0/P1 improvements can be implemented within 2-3 sprints and would meaningfully improve reliability, cost efficiency, and extraction quality.
