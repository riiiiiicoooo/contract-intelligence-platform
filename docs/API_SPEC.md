# API Specification: Contract Intelligence Platform

**Last Updated:** January 2025
**Base URL:** `https://api.contractintel.io/v1`
**Authentication:** Bearer token (JWT via Supabase Auth)
**Format:** JSON (all requests and responses)

---

## 1. Authentication

All API requests require a valid JWT token in the Authorization header.

```
Authorization: Bearer <jwt_token>
```

The JWT contains `user_id`, `tenant_id`, and `role`. The API middleware extracts these and sets PostgreSQL session variables for RLS enforcement.

**Token refresh:** Tokens expire after 1 hour. Use the Supabase Auth refresh endpoint to obtain a new token.

**Error response (401):**
```json
{
  "error": "unauthorized",
  "message": "Invalid or expired token"
}
```

---

## 2. Standard Response Format

All responses follow a consistent envelope:

**Success:**
```json
{
  "data": { ... },
  "meta": {
    "request_id": "req_abc123",
    "timestamp": "2025-01-15T14:30:00Z"
  }
}
```

**Paginated:**
```json
{
  "data": [ ... ],
  "meta": {
    "total": 245,
    "page": 1,
    "per_page": 25,
    "total_pages": 10,
    "request_id": "req_abc123"
  }
}
```

**Error:**
```json
{
  "error": "validation_error",
  "message": "Human-readable description",
  "details": [ ... ],
  "meta": {
    "request_id": "req_abc123"
  }
}
```

**Standard HTTP status codes:**

| Code | Usage |
|---|---|
| 200 | Success |
| 201 | Created |
| 202 | Accepted (async job queued) |
| 400 | Validation error |
| 401 | Unauthorized |
| 403 | Forbidden (valid token, insufficient permissions) |
| 404 | Resource not found |
| 409 | Conflict (duplicate resource) |
| 429 | Rate limited |
| 500 | Internal server error |

---

## 3. Documents API

### 3.1 Upload Document

Upload a single contract for processing.

```
POST /documents
Content-Type: multipart/form-data
```

**Parameters:**

| Field | Type | Required | Description |
|---|---|---|---|
| file | File | Yes | PDF or DOCX file (max 100MB) |
| deal_id | UUID | Yes | Deal to associate with |
| contract_type | String | No | msa, sow, nda, amendment, lease, employment, vendor, license, other |
| effective_date | Date | No | YYYY-MM-DD |
| notes | String | No | Free text notes |

**Response (201):**
```json
{
  "data": {
    "id": "doc_8f3a2b1c-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
    "filename": "MSA_Acme_Corp_2024.pdf",
    "deal_id": "deal_1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
    "processing_status": "queued",
    "file_size_bytes": 2456789,
    "page_count": null,
    "is_scanned": null,
    "created_at": "2025-01-15T14:30:00Z"
  }
}
```

### 3.2 Batch Upload

Upload multiple contracts via ZIP file.

```
POST /documents/batch
Content-Type: multipart/form-data
```

**Parameters:**

| Field | Type | Required | Description |
|---|---|---|---|
| file | File | Yes | ZIP file containing PDFs/DOCXs (max 500MB) |
| deal_id | UUID | Yes | Deal to associate with |

**Response (202):**
```json
{
  "data": {
    "batch_id": "batch_9a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d",
    "deal_id": "deal_1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
    "total_files": 247,
    "status": "processing",
    "created_at": "2025-01-15T14:30:00Z"
  }
}
```

### 3.3 Get Document

```
GET /documents/{document_id}
```

**Response (200):**
```json
{
  "data": {
    "id": "doc_8f3a2b1c-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
    "deal_id": "deal_1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
    "filename": "MSA_Acme_Corp_2024.pdf",
    "original_filename": "MSA_Acme_Corp_2024.pdf",
    "contract_type": "msa",
    "parties": [
      {"name": "Acme Corporation", "role": "vendor", "entity_type": "corporation"},
      {"name": "Beta Industries LLC", "role": "client", "entity_type": "llc"}
    ],
    "effective_date": "2024-03-01",
    "expiration_date": "2027-02-28",
    "governing_law": "Delaware",
    "page_count": 42,
    "is_scanned": false,
    "processing_status": "extracted",
    "clause_count": 18,
    "risk_summary": {
      "critical": 1,
      "high": 3,
      "medium": 7,
      "low": 7
    },
    "processed_at": "2025-01-15T14:31:22Z",
    "created_at": "2025-01-15T14:30:00Z"
  }
}
```

### 3.4 List Documents for a Deal

```
GET /documents?deal_id={deal_id}&page=1&per_page=25
```

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| deal_id | UUID | Required | Filter by deal |
| contract_type | String | All | Filter by type |
| processing_status | String | All | Filter by status |
| risk_level | String | All | Filter by highest risk level (critical, high, medium, low) |
| sort_by | String | created_at | created_at, filename, risk_level, processing_status |
| sort_order | String | desc | asc, desc |
| page | Integer | 1 | Page number |
| per_page | Integer | 25 | Results per page (max 100) |

**Response (200):**
```json
{
  "data": [
    {
      "id": "doc_8f3a2b1c...",
      "filename": "MSA_Acme_Corp_2024.pdf",
      "contract_type": "msa",
      "processing_status": "extracted",
      "clause_count": 18,
      "risk_summary": {"critical": 1, "high": 3, "medium": 7, "low": 7},
      "created_at": "2025-01-15T14:30:00Z"
    }
  ],
  "meta": {
    "total": 247,
    "page": 1,
    "per_page": 25,
    "total_pages": 10
  }
}
```

### 3.5 Get Batch Status

```
GET /documents/batch/{batch_id}
```

**Response (200):**
```json
{
  "data": {
    "batch_id": "batch_9a8b7c6d...",
    "status": "processing",
    "total_files": 247,
    "processed": 189,
    "failed": 3,
    "progress_percentage": 77,
    "failed_files": [
      {"filename": "scan_old_contract.pdf", "error": "OCR failed: image quality too low"},
      {"filename": "corrupted.pdf", "error": "Unable to parse PDF"},
      {"filename": "password_protected.docx", "error": "File is password protected"}
    ],
    "started_at": "2025-01-15T14:30:05Z",
    "estimated_completion": "2025-01-15T15:45:00Z"
  }
}
```

### 3.6 Get Document File (Download)

```
GET /documents/{document_id}/file
```

**Response (200):** Returns a pre-signed URL redirect.

```json
{
  "data": {
    "download_url": "https://storage.supabase.co/...",
    "expires_at": "2025-01-16T14:30:00Z"
  }
}
```

---

## 4. Analysis API

### 4.1 Get Clauses for a Document

```
GET /documents/{document_id}/clauses
```

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| clause_type | String | All | Filter by clause type |
| risk_level | String | All | Filter by risk (critical, high, medium, low) |
| review_status | String | All | pending_review, accepted, rejected, overridden, auto_accepted |
| min_confidence | Float | 0.0 | Minimum confidence score |
| sort_by | String | page_number | page_number, confidence, risk_level, clause_type |

**Response (200):**
```json
{
  "data": [
    {
      "id": "clause_2b3c4d5e...",
      "clause_type": "change_of_control",
      "extracted_text": "In the event of a Change of Control of either party, the non-affected party shall have the right to terminate this Agreement upon sixty (60) days written notice.",
      "surrounding_context": "...preceding paragraph text... [EXTRACTED CLAUSE] ...following paragraph text...",
      "page_number": 12,
      "section_reference": "Section 14.2(b)",
      "section_title": "Assignment and Change of Control",
      "confidence": 0.94,
      "risk_level": "high",
      "risk_explanation": "60-day notice period for change of control termination is shorter than the 90-day market standard. This could allow the counterparty to exit during an acquisition.",
      "risk_score": 78,
      "is_standard": false,
      "deviation_description": "Notice period 60 days vs. standard 90 days; termination right is bilateral (market standard is typically unilateral for non-affected party only)",
      "review_status": "pending_review",
      "model_id": "claude-sonnet-4-20250514",
      "risk_flags": [
        {
          "flag_type": "change_of_control_trigger",
          "severity": "warning",
          "description": "Change of control triggers termination right for counterparty",
          "recommendation": "Negotiate for consent requirement instead of termination right, or extend notice period to 90 days"
        }
      ],
      "created_at": "2025-01-15T14:31:15Z"
    }
  ],
  "meta": {
    "total": 18,
    "page": 1,
    "per_page": 50
  }
}
```

### 4.2 Get Deal Risk Summary

Aggregated risk view across all contracts in a deal.

```
GET /deals/{deal_id}/risk-summary
```

**Response (200):**
```json
{
  "data": {
    "deal_id": "deal_1a2b3c4d...",
    "total_contracts": 247,
    "total_clauses_extracted": 4218,
    "total_risk_flags": 89,
    "risk_breakdown": {
      "critical": 12,
      "high": 31,
      "medium": 46,
      "low": 0
    },
    "top_risk_categories": [
      {"flag_type": "change_of_control_trigger", "count": 23, "severity": "critical"},
      {"flag_type": "uncapped_liability", "count": 8, "severity": "critical"},
      {"flag_type": "short_notice_period", "count": 15, "severity": "warning"},
      {"flag_type": "auto_renewal_trap", "count": 11, "severity": "warning"}
    ],
    "review_progress": {
      "auto_accepted": 3412,
      "pending_review": 312,
      "accepted": 481,
      "rejected": 8,
      "overridden": 5,
      "completion_percentage": 92.6
    },
    "avg_confidence": 0.912,
    "contracts_by_risk": {
      "critical": 8,
      "high": 34,
      "medium": 112,
      "low": 93
    }
  }
}
```

### 4.3 Reprocess Document

Trigger re-extraction (after model update or configuration change).

```
POST /documents/{document_id}/reprocess
```

**Request body:**
```json
{
  "reason": "Updated extraction prompt to v2.4",
  "preserve_overrides": true
}
```

**Response (202):**
```json
{
  "data": {
    "document_id": "doc_8f3a2b1c...",
    "processing_status": "reprocessing",
    "previous_clause_count": 18,
    "overrides_preserved": 3
  }
}
```

---

## 5. Review API

### 5.1 Accept Clause Extraction

```
POST /clauses/{clause_id}/accept
```

**Response (200):**
```json
{
  "data": {
    "id": "clause_2b3c4d5e...",
    "review_status": "accepted",
    "reviewed_by": "user_5f6a7b8c...",
    "reviewed_at": "2025-01-15T16:22:00Z"
  }
}
```

### 5.2 Reject Clause Extraction

```
POST /clauses/{clause_id}/reject
```

**Request body:**
```json
{
  "reason": "This is a general warranty, not a limitation of liability clause"
}
```

**Response (200):**
```json
{
  "data": {
    "id": "clause_2b3c4d5e...",
    "review_status": "rejected",
    "reviewed_by": "user_5f6a7b8c...",
    "reviewed_at": "2025-01-15T16:22:00Z"
  }
}
```

### 5.3 Override Clause Extraction

Correct the extracted text or reclassify the clause.

```
PUT /clauses/{clause_id}/override
```

**Request body:**
```json
{
  "override_text": "Corrected clause text here...",
  "clause_type": "indemnification",
  "risk_level": "critical",
  "reason": "AI misclassified this as limitation_of_liability but it's actually an indemnification clause with uncapped exposure"
}
```

**Response (200):**
```json
{
  "data": {
    "id": "clause_2b3c4d5e...",
    "clause_type": "indemnification",
    "extracted_text": "Original AI-extracted text...",
    "override_text": "Corrected clause text here...",
    "risk_level": "critical",
    "review_status": "overridden",
    "reviewed_by": "user_5f6a7b8c...",
    "reviewed_at": "2025-01-15T16:22:00Z"
  }
}
```

### 5.4 Bulk Review Actions

Accept or reject multiple clauses at once.

```
POST /clauses/bulk-review
```

**Request body:**
```json
{
  "action": "accept",
  "clause_ids": [
    "clause_2b3c4d5e...",
    "clause_3c4d5e6f...",
    "clause_4d5e6f7a..."
  ],
  "filter": {
    "deal_id": "deal_1a2b3c4d...",
    "risk_level": "low",
    "min_confidence": 0.95
  }
}
```

Note: Provide either `clause_ids` (explicit list) or `filter` (batch by criteria), not both.

**Response (200):**
```json
{
  "data": {
    "action": "accept",
    "total_updated": 142,
    "clause_ids_updated": ["clause_2b3c4d5e...", "..."]
  }
}
```

### 5.5 Escalate to Partner

Flag a clause for partner review.

```
POST /clauses/{clause_id}/escalate
```

**Request body:**
```json
{
  "partner_id": "user_7a8b9c0d...",
  "note": "Unusual indemnification structure - need partner guidance on risk classification"
}
```

**Response (200):**
```json
{
  "data": {
    "id": "clause_2b3c4d5e...",
    "escalated_to": "user_7a8b9c0d...",
    "escalated_by": "user_5f6a7b8c...",
    "escalation_note": "Unusual indemnification structure...",
    "escalated_at": "2025-01-15T16:25:00Z"
  }
}
```

---

## 6. Search API

### 6.1 Hybrid Search

Natural language search across all clauses in a deal.

```
POST /search
```

**Request body:**
```json
{
  "query": "contracts with unlimited liability or uncapped damages",
  "deal_id": "deal_1a2b3c4d...",
  "filters": {
    "contract_type": ["msa", "sow"],
    "risk_level": ["high", "critical"],
    "clause_type": ["limitation_of_liability", "indemnification"]
  },
  "limit": 10
}
```

**Response (200):**
```json
{
  "data": {
    "results": [
      {
        "clause_id": "clause_2b3c4d5e...",
        "contract_id": "doc_8f3a2b1c...",
        "contract_filename": "MSA_Acme_Corp_2024.pdf",
        "clause_type": "limitation_of_liability",
        "extracted_text": "Neither party's aggregate liability under this Agreement shall be limited...",
        "page_number": 15,
        "section_reference": "Section 10.1",
        "risk_level": "critical",
        "relevance_score": 0.94,
        "highlight_spans": [
          {"start": 45, "end": 67, "text": "shall be limited"}
        ]
      }
    ],
    "total_results": 8,
    "search_method": "hybrid_bm25_vector_rerank",
    "query_time_ms": 342
  }
}
```

---

## 7. Export API

### 7.1 Generate Export

```
POST /exports
```

**Request body:**
```json
{
  "deal_id": "deal_1a2b3c4d...",
  "format": "excel_matrix",
  "template": "firm_default",
  "options": {
    "include_risk_flags": true,
    "include_clause_text": true,
    "conditional_formatting": true,
    "contracts_filter": {
      "processing_status": "reviewed"
    }
  }
}
```

**Response (202):**
```json
{
  "data": {
    "job_id": "export_6f7a8b9c...",
    "deal_id": "deal_1a2b3c4d...",
    "format": "excel_matrix",
    "status": "queued",
    "estimated_duration_seconds": 45,
    "created_at": "2025-01-15T17:00:00Z"
  }
}
```

### 7.2 Get Export Status

```
GET /exports/{job_id}
```

**Response (200) - Processing:**
```json
{
  "data": {
    "job_id": "export_6f7a8b9c...",
    "status": "processing",
    "progress": 65,
    "current_step": "Generating contract matrix (162 of 247 contracts)"
  }
}
```

**Response (200) - Completed:**
```json
{
  "data": {
    "job_id": "export_6f7a8b9c...",
    "status": "completed",
    "progress": 100,
    "download_url": "https://storage.supabase.co/...",
    "download_url_expires_at": "2025-01-16T17:00:00Z",
    "file_size_bytes": 1456789,
    "completed_at": "2025-01-15T17:00:45Z"
  }
}
```

### 7.3 List Exports for a Deal

```
GET /exports?deal_id={deal_id}
```

**Response (200):**
```json
{
  "data": [
    {
      "job_id": "export_6f7a8b9c...",
      "format": "excel_matrix",
      "status": "completed",
      "download_url": "https://storage.supabase.co/...",
      "download_url_expires_at": "2025-01-16T17:00:00Z",
      "download_count": 3,
      "created_at": "2025-01-15T17:00:00Z"
    }
  ]
}
```

---

## 8. Deals API

### 8.1 Create Deal

```
POST /deals
```

**Request body:**
```json
{
  "name": "Project Atlas - Acme Corp Acquisition",
  "deal_type": "m_and_a",
  "target_company": "Acme Corporation",
  "deal_value_range": "$50M-$100M",
  "playbook_id": "pb_1a2b3c4d...",
  "assigned_partner": "user_7a8b9c0d...",
  "metadata": {
    "client_name": "Alpine Capital Partners",
    "industry": "healthcare",
    "expected_close_date": "2025-03-15"
  }
}
```

**Response (201):**
```json
{
  "data": {
    "id": "deal_1a2b3c4d...",
    "name": "Project Atlas - Acme Corp Acquisition",
    "deal_type": "m_and_a",
    "status": "setup",
    "created_at": "2025-01-15T14:00:00Z"
  }
}
```

### 8.2 Get Deal

```
GET /deals/{deal_id}
```

### 8.3 List Deals

```
GET /deals?status=active&sort_by=updated_at&sort_order=desc
```

### 8.4 Update Deal

```
PATCH /deals/{deal_id}
```

---

## 9. Audit API

### 9.1 Get Audit Log

Available to partner and admin roles only.

```
GET /audit?resource_type=clause&resource_id={clause_id}
```

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| resource_type | String | All | contract, clause, deal, export |
| resource_id | UUID | All | Specific resource |
| user_id | UUID | All | Filter by user |
| action | String | All | document_upload, document_view, ai_extraction, clause_override, etc. |
| start_date | DateTime | 30 days ago | ISO 8601 |
| end_date | DateTime | Now | ISO 8601 |
| page | Integer | 1 | Page number |
| per_page | Integer | 50 | Max 200 |

**Response (200):**
```json
{
  "data": [
    {
      "id": "audit_3c4d5e6f...",
      "user_id": "user_5f6a7b8c...",
      "user_name": "Sarah Chen",
      "action": "clause_override",
      "resource_type": "clause",
      "resource_id": "clause_2b3c4d5e...",
      "details": {
        "original_clause_type": "limitation_of_liability",
        "new_clause_type": "indemnification",
        "original_risk_level": "medium",
        "new_risk_level": "critical",
        "reason": "AI misclassified this clause"
      },
      "ip_address": "203.0.113.42",
      "created_at": "2025-01-15T16:22:00Z"
    }
  ],
  "meta": {
    "total": 1247,
    "page": 1,
    "per_page": 50
  }
}
```

### 9.2 AI Decision Log

Detailed log of every AI model invocation. Required for privilege defense.

```
GET /audit/ai-decisions?document_id={document_id}
```

**Response (200):**
```json
{
  "data": [
    {
      "id": "ai_4d5e6f7a...",
      "document_id": "doc_8f3a2b1c...",
      "model_id": "claude-sonnet-4-20250514",
      "prompt_version": "extraction_v2.3",
      "input_text_hash": "sha256:a1b2c3d4...",
      "pii_entities_redacted": 4,
      "output_clause_count": 18,
      "avg_confidence": 0.912,
      "token_count_input": 48230,
      "token_count_output": 3890,
      "latency_ms": 12450,
      "cost_usd": 0.087,
      "triggered_by": "user_5f6a7b8c...",
      "created_at": "2025-01-15T14:31:15Z"
    }
  ]
}
```

---

## 10. WebSocket Events

Real-time updates for long-running operations.

**Connection:**
```
wss://api.contractintel.io/v1/ws?token={jwt_token}
```

**Event types:**

### Document Processing Progress
```json
{
  "event": "document.processing",
  "data": {
    "document_id": "doc_8f3a2b1c...",
    "status": "processing",
    "step": "clause_extraction",
    "progress": 65
  }
}
```

### Batch Upload Progress
```json
{
  "event": "batch.progress",
  "data": {
    "batch_id": "batch_9a8b7c6d...",
    "total": 247,
    "processed": 189,
    "failed": 3,
    "progress_percentage": 77
  }
}
```

### Export Ready
```json
{
  "event": "export.completed",
  "data": {
    "job_id": "export_6f7a8b9c...",
    "download_url": "https://storage.supabase.co/...",
    "format": "excel_matrix"
  }
}
```

### Escalation Notification
```json
{
  "event": "clause.escalated",
  "data": {
    "clause_id": "clause_2b3c4d5e...",
    "contract_filename": "MSA_Acme_Corp_2024.pdf",
    "escalated_by": "Sarah Chen",
    "note": "Unusual indemnification structure"
  }
}
```

---

## 11. Rate Limits

| Endpoint | Limit | Window |
|---|---|---|
| POST /documents | 50 requests | per minute |
| POST /documents/batch | 5 requests | per minute |
| POST /search | 100 requests | per minute |
| POST /exports | 10 requests | per minute |
| GET endpoints | 300 requests | per minute |
| WebSocket connections | 5 concurrent | per user |

Rate limit headers included in every response:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1705334400
```

---

## 12. Error Codes

| Code | Description | Common Cause |
|---|---|---|
| `validation_error` | Request body failed validation | Missing required field, invalid type |
| `unauthorized` | Invalid or expired JWT | Token expired, not provided |
| `forbidden` | Insufficient role permissions | Associate accessing admin endpoint |
| `not_found` | Resource doesn't exist or isn't accessible | Wrong ID, RLS blocking access |
| `conflict` | Duplicate resource | Re-uploading same file (matching hash) |
| `processing_error` | Document processing failed | Corrupted PDF, OCR failure |
| `rate_limited` | Too many requests | Exceeded rate limit |
| `export_error` | Export generation failed | Template error, data issue |
| `ai_service_error` | LLM API failure | Claude/GPT-4 API timeout or error |
| `internal_error` | Unexpected server error | Bug, infrastructure issue |

**Error response example:**
```json
{
  "error": "processing_error",
  "message": "Failed to process document: OCR confidence below minimum threshold (0.62 < 0.80)",
  "details": {
    "document_id": "doc_8f3a2b1c...",
    "ocr_confidence": 0.62,
    "threshold": 0.80,
    "recommendation": "Upload a higher quality scan or provide the native digital version"
  },
  "meta": {
    "request_id": "req_abc123"
  }
}
```
