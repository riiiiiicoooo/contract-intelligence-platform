# Source Code: Reference Implementation

> **Note:** This code is a PM-authored reference implementation demonstrating the core technical concepts behind the Contract Intelligence Platform. It is not production code. These prototypes were built to validate feasibility, communicate architecture to engineering, and demonstrate technical fluency during product development.

## Contents

| File | Purpose |
|---|---|
| `ingestion/document_processor.py` | Document type detection, routing to Docling (native) or Azure OCR (scanned), clause-level chunking |
| `analysis/clause_extractor.py` | Claude API integration for clause extraction with structured JSON output, confidence scoring, and multi-model fallback |
| `analysis/risk_scorer.py` | Risk scoring engine with playbook-based rules and AI-generated explanations |
| `search/hybrid_search.py` | Hybrid BM25 + vector search with Reciprocal Rank Fusion and Cohere reranking |
| `export/matrix_generator.py` | Excel contract matrix generation with conditional formatting (RAG flags) |
| `compliance/pii_redactor.py` | Microsoft Presidio integration for PII detection and redaction before LLM API calls |

## How These Were Used

As PM, I wrote these prototypes to:

1. **Validate feasibility** before committing to architecture decisions (e.g., testing hybrid search accuracy vs. vector-only)
2. **Communicate with engineering** using working code rather than just requirements docs
3. **Benchmark options** (e.g., Docling vs. PyMuPDF processing speed, voyage-law-2 vs. OpenAI embedding quality)
4. **Demo to stakeholders** during product reviews with real contract data
5. **Inform the PRD and architecture docs** with hands-on understanding of technical constraints
