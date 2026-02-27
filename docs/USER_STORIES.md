# User Stories: Contract Intelligence Platform

**Last Updated:** January 2025

---

## Epic 1: Document Ingestion

### US-1.1: Single Document Upload
**As a** deal associate
**I want to** upload a contract (PDF or Word) and have it automatically processed
**So that** I don't have to manually read and extract clause information

**Acceptance Criteria:**
- User can drag-and-drop or browse to select a PDF or DOCX file up to 100MB
- System validates file type and size before upload begins
- Upload progress bar shows percentage complete
- System detects whether PDF is native text or scanned image
- Native PDFs are processed via Docling; scanned PDFs route to Azure Document Intelligence for OCR
- Processing status updates in real-time via WebSocket (queued -> processing -> extracted)
- System extracts document metadata (page count, parties, dates) and displays on completion
- If processing fails, user sees a clear error message with recommended action
- Duplicate files (matching SHA-256 hash) are flagged with option to proceed or skip

**Story Points:** 5

---

### US-1.2: Batch Upload
**As a** deal associate
**I want to** upload a ZIP file containing 200+ contracts at once
**So that** I can load an entire deal's contract set in one action

**Acceptance Criteria:**
- User can upload a ZIP file up to 500MB
- System extracts individual files from ZIP and queues each for processing
- Batch progress dashboard shows: total files, processed, failed, in-progress
- Failed files are listed with specific error messages (corrupted, password-protected, unsupported format)
- User receives email and in-app notification when batch processing completes
- Non-contract files in the ZIP (images, spreadsheets) are skipped and listed as "skipped"
- Processing continues even if individual files fail

**Story Points:** 8

---

### US-1.3: Document Version Tracking
**As a** deal associate
**I want to** upload an updated version of a contract and see it linked to the original
**So that** I can track how a contract has changed during negotiations

**Acceptance Criteria:**
- When uploading, user can select "This is a new version of..." and link to an existing contract
- Version history shows all versions with upload dates and who uploaded each
- Clauses can be compared across versions (side-by-side diff)
- Latest version is used for deal-level analytics; older versions remain accessible
- Version number auto-increments (v1, v2, v3)

**Story Points:** 5

---

## Epic 2: AI Clause Extraction

### US-2.1: Automatic Clause Extraction
**As a** deal associate
**I want** the system to automatically identify and extract key clauses from uploaded contracts
**So that** I don't spend hours reading each contract line by line

**Acceptance Criteria:**
- System extracts 40+ clause types (see PRD Appendix A)
- Each extraction includes: clause type, full clause text, page number, section reference, confidence score
- Extractions are stored as structured data (not just highlighted text)
- Average processing time is under 90 seconds per native PDF, under 180 seconds per scanned PDF
- Extraction runs automatically after document ingestion completes (no manual trigger needed)

**Story Points:** 13

---

### US-2.2: Confidence Scoring and Human Routing
**As a** deal associate
**I want** each extraction to include a confidence score that determines whether it needs my review
**So that** I can focus my time on the extractions the AI is least sure about

**Acceptance Criteria:**
- Every extracted clause has a confidence score between 0.0 and 1.0
- Clauses with confidence >= 0.85 are auto-accepted (configurable threshold per tenant)
- Clauses with confidence < 0.85 are routed to the review queue with status "pending_review"
- Review queue shows pending items sorted by confidence (lowest first)
- Dashboard shows count of items pending review per deal
- Auto-accept threshold is configurable by admin in tenant settings

**Story Points:** 5

---

### US-2.3: Missing Clause Detection
**As a** deal associate
**I want** the system to flag when an expected clause type is absent from a contract
**So that** I can identify gaps that represent risk to the buyer

**Acceptance Criteria:**
- Based on the deal's playbook, system checks for expected clause types per contract type
- If an MSA is missing a limitation of liability clause, system generates a "missing_clause" risk flag
- Missing clause flags appear in the risk flag list alongside extracted clause risks
- User can dismiss a missing clause flag with a reason ("intentionally omitted", "covered elsewhere")

**Story Points:** 5

---

## Epic 3: Risk Scoring

### US-3.1: Clause-Level Risk Scoring
**As a** deal associate
**I want** each extracted clause scored for risk level with a clear explanation
**So that** I can quickly prioritize which clauses need attention

**Acceptance Criteria:**
- Each clause is scored: low, medium, high, or critical
- Each score includes a plain-English explanation of why it was rated that level
- Explanation references the specific language that triggered the rating
- Numeric risk score (0-100) is available for sorting and filtering
- Risk scoring happens automatically during extraction (not a separate step)

**Story Points:** 8

---

### US-3.2: Playbook-Based Risk Rules
**As a** deal partner
**I want to** configure risk rules specific to our client's priorities
**So that** risk scoring reflects what actually matters for this deal, not generic standards

**Acceptance Criteria:**
- Admin or partner can create a playbook with rules (e.g., "flag termination notice periods under 60 days as critical")
- Playbook can be assigned to a deal during setup or changed mid-deal
- Rules support conditions on clause attributes: notice period days, liability cap amount, consent requirements
- Default playbook exists for each deal type (M&A, lending, vendor)
- Changes to playbook rules trigger re-scoring of existing clauses (with notification)

**Story Points:** 8

---

### US-3.3: Cross-Document Conflict Detection
**As a** deal associate
**I want** the system to identify conflicting terms across different contracts in the same deal
**So that** I can flag inconsistencies for the buyer before they become post-close issues

**Acceptance Criteria:**
- System compares key terms across all contracts in a deal (e.g., different governing law, conflicting exclusivity)
- Conflicts generate a "conflicting_terms" risk flag linking both clauses
- Conflict view shows the two clauses side-by-side with the conflict highlighted
- User can resolve a conflict flag with notes explaining why it's acceptable or needs action

**Story Points:** 8

---

### US-3.4: Deal-Level Risk Dashboard
**As a** deal partner
**I want** a dashboard showing aggregated risk across all contracts in a deal
**So that** I can quickly assess overall deal risk without reviewing every contract

**Acceptance Criteria:**
- Dashboard shows: total contracts, total clauses extracted, risk breakdown (critical/high/medium/low)
- Top risk categories listed with counts (e.g., "23 contracts have change-of-control issues")
- Click on any risk category to drill down to the specific clauses
- Review progress bar showing percentage of clauses reviewed
- Average confidence score across the deal
- Dashboard loads in under 3 seconds

**Story Points:** 5

---

## Epic 4: Review Workflow

### US-4.1: Split-Pane Review Interface
**As a** deal associate
**I want to** see the original PDF on the left and extracted metadata on the right
**So that** I can verify AI extractions against the source document

**Acceptance Criteria:**
- Left pane: PDF viewer with page navigation, zoom, text search
- Right pane: extracted clauses for the current document with risk levels and confidence scores
- Clicking a clause in the right pane scrolls the PDF to the relevant page and highlights the clause text
- Clause highlighting overlays are visible on the PDF (colored by risk level)
- Interface is responsive on screens 1280px and wider
- PDF loads in under 5 seconds for documents up to 200 pages

**Story Points:** 13

---

### US-4.2: Accept / Reject / Override
**As a** deal associate
**I want to** accept, reject, or correct each extracted clause
**So that** I can ensure the final output is accurate before generating deliverables

**Acceptance Criteria:**
- Each clause has Accept, Reject, and Override buttons
- Accept marks the clause as reviewed with no changes
- Reject removes the clause from the final output (with required reason)
- Override opens an inline editor to correct the extracted text, change the clause type, or adjust risk level
- Override requires a reason (logged in audit trail)
- All actions are logged with user ID, timestamp, and before/after state
- Keyboard shortcuts: A (accept), R (reject), O (override), N (next clause), P (previous clause)

**Story Points:** 8

---

### US-4.3: Bulk Review Actions
**As a** deal associate
**I want to** accept all low-risk, high-confidence clauses in one action
**So that** I can clear the easy items quickly and focus on the ones that need attention

**Acceptance Criteria:**
- User can filter the review queue by risk level, confidence, clause type
- "Accept all visible" button accepts all currently filtered clauses
- Confirmation dialog shows count of clauses that will be accepted
- Bulk actions are logged as individual audit entries (one per clause)
- Undo available for 30 seconds after bulk action

**Story Points:** 5

---

### US-4.4: Escalate to Partner
**As a** deal associate
**I want to** flag specific clauses for partner review
**So that** unusual or high-risk items get senior attention before we finalize

**Acceptance Criteria:**
- Each clause has an "Escalate" button
- Escalation requires selecting a partner and adding a note explaining the concern
- Partner receives in-app notification and email for escalated items
- Partner can review and respond directly (accept, reject, override, or add comments)
- Escalation status is visible in the review queue (escalated, awaiting response, resolved)

**Story Points:** 5

---

### US-4.5: Review Progress Tracking
**As a** deal partner
**I want to** see how far along the review is for each deal
**So that** I can manage timelines and allocate resources

**Acceptance Criteria:**
- Deal dashboard shows: X of Y contracts reviewed, X of Y clauses reviewed
- Progress bar with percentage complete
- Breakdown by review status: auto-accepted, pending, accepted, rejected, overridden, escalated
- Filter by associate to see individual progress
- Estimated completion time based on current review velocity

**Story Points:** 3

---

## Epic 5: Search

### US-5.1: Natural Language Search
**As a** deal associate
**I want to** search across all contracts in a deal using natural language
**So that** I can quickly find specific provisions without opening every document

**Acceptance Criteria:**
- Search bar accepts natural language queries (e.g., "contracts with change of control provisions that require consent")
- Results show matching clause text with the search terms or relevant concepts highlighted
- Each result links to the source document and page number
- Clicking a result opens the split-pane viewer at the exact clause location
- Search returns results in under 2 seconds
- Empty state suggests example queries

**Story Points:** 8

---

### US-5.2: Filtered Search
**As a** deal associate
**I want to** filter search results by contract type, risk level, clause type, and party
**So that** I can narrow down results to exactly what I need

**Acceptance Criteria:**
- Filter panel available alongside search results
- Filters: contract type, clause type, risk level, party name, date range
- Filters combine with search query (AND logic)
- Active filters shown as chips with "x" to remove
- Result count updates as filters are applied
- Filters persist during the session (reset on page reload)

**Story Points:** 5

---

## Epic 6: Export and Deliverables

### US-6.1: Contract Matrix (Excel)
**As a** deal associate
**I want to** generate an Excel spreadsheet showing all contracts and their extracted provisions
**So that** I can deliver the standard contract review matrix to the client

**Acceptance Criteria:**
- Rows represent contracts; columns represent clause types
- Each cell contains the extracted clause summary text
- Conditional formatting: red (critical), amber (high), yellow (medium), green (low)
- First columns: contract name, type, parties, effective date, expiration date, governing law
- Separate tab for risk flags with severity, description, and recommendation
- Summary tab with aggregate statistics
- Template matches firm branding (configurable)
- Export handles up to 500 contracts without timeout

**Story Points:** 8

---

### US-6.2: Executive Summary (PowerPoint)
**As a** deal partner
**I want to** generate a PowerPoint presentation summarizing key findings
**So that** I can present to the client without manually building slides

**Acceptance Criteria:**
- Uses firm-branded template
- Slides include: deal overview, methodology, risk summary, top findings by category, recommendations, appendix
- Charts: risk distribution pie chart, contracts by type, top risk categories bar chart
- Each finding slide shows the clause text, risk explanation, and recommendation
- Speaker notes auto-generated with additional context
- Export completes in under 60 seconds for a standard deal

**Story Points:** 8

---

### US-6.3: Risk Report (PDF)
**As a** deal associate
**I want to** generate a detailed PDF risk report
**So that** we have comprehensive documentation of all identified risks

**Acceptance Criteria:**
- Table of contents with clickable links to sections
- Cover page with deal name, date, firm branding
- Executive summary section with key statistics
- Per-contract section with all extracted clauses and risk flags
- Risk flags grouped by severity (critical first)
- Page numbers and headers/footers
- Report handles up to 500 contracts (multi-hundred page output)

**Story Points:** 8

---

### US-6.4: Async Export with Progress
**As a** deal associate
**I want** large exports to run in the background with progress updates
**So that** I can continue working while the export generates

**Acceptance Criteria:**
- Export request returns immediately with a job ID
- Progress updates via WebSocket: percentage complete, current step
- In-app notification when export is ready
- Download link with 24-hour expiration
- Export history shows all past exports with download links (if not expired)
- Failed exports show error message and option to retry

**Story Points:** 5

---

## Epic 7: Compliance and Security

### US-7.1: PII Redaction
**As a** compliance officer
**I want** all personally identifiable information removed before any text is sent to external AI APIs
**So that** we maintain attorney-client privilege and comply with data handling agreements

**Acceptance Criteria:**
- Microsoft Presidio processes all text before LLM API calls
- Detected PII types: person names, SSNs, email addresses, phone numbers, physical addresses, dates of birth
- PII replaced with typed placeholders (<PERSON_1>, <SSN_1>, etc.)
- Mapping table stored in encrypted storage (separate from AI API flow)
- De-anonymization happens after AI response, before storing results
- Confidence threshold configurable (default 0.7)
- Admin can view PII detection statistics (count of entities redacted per document)

**Story Points:** 8

---

### US-7.2: Audit Trail
**As a** compliance officer
**I want** a complete log of every action taken on every document
**So that** we can demonstrate proper handling in case of regulatory inquiry or privilege challenge

**Acceptance Criteria:**
- Every document view logged with user, timestamp, IP address
- Every AI API call logged with input hash, model version, output, confidence, token count
- Every clause override logged with before/after state and reason
- Every export logged with format, requesting user, download count
- Audit log is append-only (no edits or deletions)
- Audit log accessible to partner and admin roles only
- Audit log retained for 7 years minimum
- Audit log exportable to CSV for external review

**Story Points:** 5

---

### US-7.3: Tenant Isolation
**As a** platform administrator
**I want** each firm's data completely isolated from other firms
**So that** there is zero risk of data leakage between clients

**Acceptance Criteria:**
- PostgreSQL Row-Level Security enabled on all tenant data tables
- Every query automatically filtered by tenant_id via session variable
- No API endpoint can return data from a different tenant, regardless of input
- Tenant isolation verified by automated integration tests
- Supabase Storage buckets are tenant-scoped
- Cross-tenant search is impossible even for admin users

**Story Points:** 5

---

### US-7.4: Role-Based Access Control
**As a** deal partner
**I want** associates to only see deals they're assigned to
**So that** sensitive deal information is limited to the team that needs it

**Acceptance Criteria:**
- Roles: associate, senior_associate, partner, admin
- Associates see only deals they're assigned to
- Partners see all deals within their tenant
- Admins have full access within their tenant including user management
- Role changes take effect immediately (no cache delay)
- Audit log tracks role changes

**Story Points:** 3

---

## Epic 8: Administration

### US-8.1: User Management
**As a** platform administrator
**I want to** add, deactivate, and manage user accounts
**So that** I can control who has access to the platform

**Acceptance Criteria:**
- Admin can invite users via email
- Admin can assign roles and deal access
- Admin can deactivate users (preserving audit history)
- SSO integration: users authenticate via firm's identity provider (SAML/OIDC)
- User list shows last login date, role, active status

**Story Points:** 5

---

### US-8.2: Playbook Management
**As a** deal partner
**I want to** create and edit risk playbooks
**So that** I can customize risk scoring rules for different deal types and clients

**Acceptance Criteria:**
- Create new playbook with name, description, deal type
- Add rules: clause type + condition + severity + message
- Preview rule impact: "This rule would flag 23 clauses across your active deals"
- Set a playbook as default for a deal type
- Clone existing playbook as starting point for new one
- Playbook changes can be applied retroactively (re-score existing deals)

**Story Points:** 8

---

### US-8.3: Clause Library Management
**As a** deal partner
**I want to** maintain a library of standard clause language
**So that** the system can benchmark extracted clauses against our standards

**Acceptance Criteria:**
- Add standard clause text with: clause type, jurisdiction, deal type
- System generates centroid embedding automatically
- Set similarity threshold per standard (how close is "standard enough")
- View how many existing clauses would be flagged as non-standard with current thresholds
- Import/export clause library as CSV
- Clause library updates trigger re-evaluation of existing clause "is_standard" flags

**Story Points:** 8

---

## Story Map Summary

| Epic | Stories | Total Points | Priority |
|---|---|---|---|
| 1. Document Ingestion | 3 stories | 18 | P0 |
| 2. AI Clause Extraction | 3 stories | 23 | P0 |
| 3. Risk Scoring | 4 stories | 29 | P0 |
| 4. Review Workflow | 5 stories | 34 | P0 |
| 5. Search | 2 stories | 13 | P0 |
| 6. Export and Deliverables | 4 stories | 29 | P0 |
| 7. Compliance and Security | 4 stories | 21 | P0 |
| 8. Administration | 3 stories | 21 | P1 |
| **Total** | **28 stories** | **188 points** | |

### Sprint Allocation (2-week sprints, ~30 points/sprint)

| Sprint | Epics | Focus |
|---|---|---|
| Sprint 1-2 | Epic 1, Epic 2 (partial) | Ingestion pipeline, basic extraction |
| Sprint 3-4 | Epic 2 (complete), Epic 3 (partial) | Full extraction, risk scoring |
| Sprint 5-6 | Epic 3 (complete), Epic 4 | Risk dashboard, review workflow |
| Sprint 7-8 | Epic 5, Epic 6 | Search, export deliverables |
| Sprint 9-10 | Epic 7, Epic 8 | Compliance, admin tools |
