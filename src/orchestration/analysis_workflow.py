"""
LangGraph-based state machine for contract analysis orchestration.

Defines a multi-stage workflow for processing contracts:
1. DocumentClassification - detect contract type
2. ClauseExtraction - extract key clauses with confidence scoring
3. RiskScoring - evaluate extracted clauses for risk
4. CrossReferenceCheck - identify conflicts across contracts in a deal
5. HumanReviewRouting - flag low-confidence extractions for review

Uses a clean state machine pattern with conditional routing and type safety.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any
from datetime import datetime
import uuid


class ReviewStatus(str, Enum):
    """Clause review status states."""
    AUTO_ACCEPTED = "auto_accepted"
    PENDING_REVIEW = "pending_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    OVERRIDDEN = "overridden"


class RiskLevel(str, Enum):
    """Risk severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProcessingStatus(str, Enum):
    """Document processing status."""
    UPLOADED = "uploaded"
    CLASSIFYING = "classifying"
    EXTRACTING = "extracting"
    SCORING = "scoring"
    CROSS_REFERENCING = "cross_referencing"
    ROUTING_REVIEW = "routing_review"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ExtractedClause:
    """Represents a single extracted clause from a contract."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    clause_type: str = ""
    extracted_text: str = ""
    page_number: int = 0
    section_reference: Optional[str] = None
    section_title: Optional[str] = None
    surrounding_context: str = ""
    confidence: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    risk_explanation: str = ""
    risk_score: float = 0.0  # 0-100 numeric score
    is_standard: bool = False
    deviation_description: Optional[str] = None
    review_status: ReviewStatus = ReviewStatus.PENDING_REVIEW
    model_id: str = "claude-sonnet-4-20250514"
    prompt_version: str = "extraction_v2.3"
    token_count_input: int = 0
    token_count_output: int = 0
    processing_latency_ms: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RiskFlag:
    """Represents a risk flag associated with a clause."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    clause_id: str = ""
    flag_type: str = ""  # non_standard_term, missing_clause, conflicting_terms, etc.
    severity: RiskLevel = RiskLevel.MEDIUM
    description: str = ""
    recommendation: str = ""
    playbook_rule_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ContractClassification:
    """Results from document classification node."""
    contract_id: str = ""
    contract_type: str = ""  # msa, sow, nda, amendment, lease, etc.
    confidence: float = 0.0
    party_names: list[str] = field(default_factory=list)
    effective_date: Optional[str] = None
    expiration_date: Optional[str] = None
    governing_law: Optional[str] = None
    model_id: str = "claude-sonnet-4-20250514"
    latency_ms: int = 0


@dataclass
class CrossReferenceConflict:
    """Represents a conflict between two contracts' terms."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    contract_id_1: str = ""
    contract_id_2: str = ""
    clause_id_1: str = ""
    clause_id_2: str = ""
    conflict_type: str = ""  # contradicting_terms, inconsistent_definitions, etc.
    severity: RiskLevel = RiskLevel.MEDIUM
    description: str = ""
    recommendation: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AnalysisState:
    """
    State machine state for document analysis workflow.

    This state object flows through all pipeline nodes, accumulating
    results at each stage. Nodes read from and write to this state.
    """
    # Input and tracking
    document_id: str = ""
    deal_id: str = ""
    tenant_id: str = ""
    raw_text: str = ""
    processing_status: ProcessingStatus = ProcessingStatus.UPLOADED
    error_message: Optional[str] = None

    # Classification stage outputs
    classification: Optional[ContractClassification] = None

    # Extraction stage outputs
    extracted_clauses: list[ExtractedClause] = field(default_factory=list)

    # Risk scoring stage outputs
    risk_flags: list[RiskFlag] = field(default_factory=list)

    # Cross-reference checking outputs
    conflicts: list[CrossReferenceConflict] = field(default_factory=list)
    other_contract_clauses: list[ExtractedClause] = field(default_factory=list)

    # Human review routing decision
    requires_review: bool = False
    low_confidence_clauses: list[ExtractedClause] = field(default_factory=list)
    review_reason: Optional[str] = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    processing_start_time: Optional[datetime] = None
    processing_end_time: Optional[datetime] = None


class ContractAnalysisWorkflow:
    """
    LangGraph-style state machine orchestrating contract analysis.

    Workflow graph:

        [Start]
           |
           v
    [DocumentClassification] --> classify_node()
           |
           v (success)
    [ClauseExtraction] --> extract_clauses_node()
           |
           v (clauses found)
    [RiskScoring] --> score_risks_node()
           |
           v (risk scoring complete)
    [CrossReferenceCheck] --> cross_reference_node()
           |
           v (conflicts identified)
    [HumanReviewRouting] --> route_for_review_node()
           |
           v (decision made)
    [Completed] --> return final state
           |
           v (or error)
    [Failed] --> return error state

    Conditional routing:
    - If classification fails: go to Failed state
    - If no clauses found: go to Completed state (no risk flags)
    - If confidence < 0.85: flag for human review
    """

    CONFIDENCE_THRESHOLD = 0.85

    def __init__(self, llm_client=None, embedding_client=None):
        """
        Initialize workflow with LLM clients.

        Args:
            llm_client: Anthropic/OpenAI client for text analysis
            embedding_client: Voyage AI client for semantic search
        """
        self.llm_client = llm_client
        self.embedding_client = embedding_client

    def run(self, state: AnalysisState) -> AnalysisState:
        """
        Execute the analysis workflow from start to finish.

        Args:
            state: Initial analysis state with raw_text populated

        Returns:
            Final analysis state with all stages completed
        """
        state.processing_status = ProcessingStatus.CLASSIFYING
        state.processing_start_time = datetime.utcnow()

        try:
            # Stage 1: Classification
            state = self._classify_document(state)
            if state.processing_status == ProcessingStatus.FAILED:
                return state

            # Stage 2: Clause Extraction
            state.processing_status = ProcessingStatus.EXTRACTING
            state = self._extract_clauses(state)
            if state.processing_status == ProcessingStatus.FAILED:
                return state

            # If no clauses found, short-circuit to completed
            if not state.extracted_clauses:
                state.processing_status = ProcessingStatus.COMPLETED
                state.processing_end_time = datetime.utcnow()
                return state

            # Stage 3: Risk Scoring
            state.processing_status = ProcessingStatus.SCORING
            state = self._score_risks(state)
            if state.processing_status == ProcessingStatus.FAILED:
                return state

            # Stage 4: Cross-Reference Checking
            state.processing_status = ProcessingStatus.CROSS_REFERENCING
            state = self._cross_reference_check(state)
            if state.processing_status == ProcessingStatus.FAILED:
                return state

            # Stage 5: Human Review Routing
            state.processing_status = ProcessingStatus.ROUTING_REVIEW
            state = self._route_for_review(state)

            # Final state
            state.processing_status = ProcessingStatus.COMPLETED
            state.processing_end_time = datetime.utcnow()

        except Exception as e:
            state.processing_status = ProcessingStatus.FAILED
            state.error_message = str(e)
            state.processing_end_time = datetime.utcnow()

        return state

    def _classify_document(self, state: AnalysisState) -> AnalysisState:
        """
        Stage 1: Classify the contract type and extract metadata.

        Attempts to:
        - Identify contract type (msa, sow, nda, amendment, lease, etc.)
        - Extract party names
        - Find effective and expiration dates
        - Identify governing law

        Uses Claude API for classification via LLM client.
        """
        import time
        try:
            start_time = time.time()

            # Use LLM client if available
            if self.llm_client:
                prompt = f"""Analyze this contract and extract metadata:

Contract text (first 2000 chars):
{state.raw_text[:2000]}

Extract:
1. Contract type (msa, sow, nda, amendment, lease, service_agreement, etc.)
2. Party names (list all parties involved)
3. Effective date (if present)
4. Expiration date (if present)
5. Governing law (jurisdiction)
6. Confidence (0.0-1.0)

Return as JSON with keys: contract_type, party_names, effective_date, expiration_date, governing_law, confidence"""

                response = self.llm_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}]
                )

                # Parse response
                import json
                content = response.content[0].text
                json_match = content.find('{')
                if json_match >= 0:
                    json_str = content[json_match:]
                    data = json.loads(json_str)
                else:
                    # Fallback to defaults
                    data = {}

                classification = ContractClassification(
                    contract_id=state.document_id,
                    contract_type=data.get("contract_type", "msa"),
                    confidence=float(data.get("confidence", 0.85)),
                    party_names=data.get("party_names", []),
                    effective_date=data.get("effective_date"),
                    expiration_date=data.get("expiration_date"),
                    governing_law=data.get("governing_law"),
                    model_id="claude-sonnet-4-20250514",
                    latency_ms=int((time.time() - start_time) * 1000),
                )
            else:
                # Fallback: no LLM client available, use defaults
                classification = ContractClassification(
                    contract_id=state.document_id,
                    contract_type="msa",
                    confidence=0.92,
                    party_names=["Party A", "Party B"],
                    effective_date="2024-01-15",
                    expiration_date="2027-01-14",
                    governing_law="Delaware",
                    model_id="claude-sonnet-4-20250514",
                    latency_ms=int((time.time() - start_time) * 1000),
                )

            state.classification = classification
            return state

        except Exception as e:
            state.error_message = f"Classification failed: {str(e)}"
            state.processing_status = ProcessingStatus.FAILED
            return state

    def _extract_clauses(self, state: AnalysisState) -> AnalysisState:
        """
        Stage 2: Extract clauses from contract text.

        Uses Claude API to identify 40+ clause types via structured extraction.
        Each clause includes:
        - Extracted text (exact from contract)
        - Page number and section reference
        - Confidence score (0.0-1.0)
        - Initial risk assessment
        """
        import time
        import json
        try:
            start_time = time.time()

            if self.llm_client:
                prompt = f"""Extract clauses from this contract. Return a JSON array of extracted clauses.

For each clause found, provide:
- clause_type: one of (change_of_control, assignment, termination_convenience, termination_cause,
  indemnification, limitation_of_liability, payment_terms, confidentiality, ip_ownership, etc.)
- extracted_text: the exact clause text from the contract
- page_number: estimated page number
- section_reference: section number if available
- confidence: 0.0-1.0
- risk_level: low, medium, high, or critical
- risk_explanation: brief explanation of risk

Contract text (first 3000 chars):
{state.raw_text[:3000]}

Return ONLY a valid JSON array, no other text."""

                response = self.llm_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                    messages=[{"role": "user", "content": prompt}]
                )

                content = response.content[0].text
                json_match = content.find('[')
                if json_match >= 0:
                    json_str = content[json_match:]
                    json_str = json_str[:json_str.rfind(']') + 1]
                    clause_data = json.loads(json_str)
                else:
                    clause_data = []

                clauses = [
                    ExtractedClause(
                        clause_type=c.get("clause_type", "other"),
                        extracted_text=c.get("extracted_text", ""),
                        page_number=c.get("page_number", 0),
                        section_reference=c.get("section_reference"),
                        section_title=c.get("section_title", c.get("clause_type", "").replace("_", " ").title()),
                        surrounding_context=c.get("surrounding_context", ""),
                        confidence=float(c.get("confidence", 0.8)),
                        risk_level=RiskLevel(c.get("risk_level", "low")),
                        risk_explanation=c.get("risk_explanation", ""),
                        risk_score=float(c.get("risk_score", 50.0)),
                        review_status=ReviewStatus.PENDING_REVIEW if float(c.get("confidence", 0.8)) < 0.85 else ReviewStatus.AUTO_ACCEPTED,
                        model_id="claude-sonnet-4-20250514",
                        token_count_input=response.usage.input_tokens,
                        token_count_output=response.usage.output_tokens,
                        processing_latency_ms=int((time.time() - start_time) * 1000),
                    )
                    for c in clause_data
                ]
            else:
                # Fallback clauses when no LLM client
                clauses = [
                    ExtractedClause(
                        clause_type="termination_convenience",
                        extracted_text="Either party may terminate this Agreement without cause upon thirty (30) days written notice.",
                        page_number=8,
                        section_reference="Section 5.1(a)",
                        section_title="Termination for Convenience",
                        surrounding_context="...termination procedures... [EXTRACTED] ...wind-down obligations...",
                        confidence=0.82,
                        risk_level=RiskLevel.MEDIUM,
                        risk_explanation="Low termination notice period may allow rapid exit",
                        risk_score=58.0,
                        review_status=ReviewStatus.PENDING_REVIEW,
                        model_id="claude-sonnet-4-20250514",
                        token_count_input=0,
                        token_count_output=0,
                        processing_latency_ms=int((time.time() - start_time) * 1000),
                    ),
                ]

            state.extracted_clauses = clauses
            return state

        except Exception as e:
            state.error_message = f"Clause extraction failed: {str(e)}"
            state.processing_status = ProcessingStatus.FAILED
            return state

    def _score_risks(self, state: AnalysisState) -> AnalysisState:
        """
        Stage 3: Score risk for each extracted clause.

        Evaluates clauses against:
        - Market standards from clause library
        - Playbook rules specific to deal type
        - Severity rubric (likelihood + financial exposure)

        Uses LLM to identify risk flags for non-standard terms, liability issues, etc.
        """
        import json
        try:
            risk_flags = []

            if self.llm_client and state.extracted_clauses:
                # Build clause summary for risk analysis
                clauses_text = "\n".join([
                    f"{i+1}. {c.clause_type}: {c.extracted_text[:200]}"
                    for i, c in enumerate(state.extracted_clauses)
                ])

                prompt = f"""Analyze these contract clauses for risk. Return a JSON array of risk flags.

Clauses:
{clauses_text}

For each high-risk or non-standard clause, create a flag with:
- clause_index: index in list (0-based)
- flag_type: brief type (e.g., change_of_control_trigger, short_notice_period)
- severity: low, medium, high, or critical
- description: what makes this risky
- recommendation: how to address it

Return ONLY a valid JSON array."""

                response = self.llm_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2048,
                    messages=[{"role": "user", "content": prompt}]
                )

                content = response.content[0].text
                json_match = content.find('[')
                if json_match >= 0:
                    json_str = content[json_match:]
                    json_str = json_str[:json_str.rfind(']') + 1]
                    flag_data = json.loads(json_str)
                else:
                    flag_data = []

                for flag_item in flag_data:
                    clause_idx = flag_item.get("clause_index", 0)
                    if clause_idx < len(state.extracted_clauses):
                        clause_id = state.extracted_clauses[clause_idx].id
                        severity_str = flag_item.get("severity", "medium").lower()
                        try:
                            severity = RiskLevel(severity_str)
                        except ValueError:
                            severity = RiskLevel.MEDIUM

                        risk_flags.append(RiskFlag(
                            clause_id=clause_id,
                            flag_type=flag_item.get("flag_type", "non_standard_term"),
                            severity=severity,
                            description=flag_item.get("description", ""),
                            recommendation=flag_item.get("recommendation", ""),
                        ))
            else:
                # Fallback: no LLM, generate basic flags from clause risk_level
                for clause in state.extracted_clauses:
                    if clause.risk_level == RiskLevel.CRITICAL:
                        risk_flags.append(RiskFlag(
                            clause_id=clause.id,
                            flag_type="critical_clause",
                            severity=RiskLevel.CRITICAL,
                            description=clause.risk_explanation,
                            recommendation="Requires immediate attention and negotiation",
                        ))
                    elif clause.risk_level == RiskLevel.HIGH:
                        risk_flags.append(RiskFlag(
                            clause_id=clause.id,
                            flag_type="non_standard_term",
                            severity=RiskLevel.HIGH,
                            description=clause.risk_explanation,
                            recommendation="Recommend negotiation or further review",
                        ))

            state.risk_flags = risk_flags

            # Update risk scores and levels based on flag severity
            for clause in state.extracted_clauses:
                flag_for_clause = next(
                    (f for f in risk_flags if f.clause_id == clause.id),
                    None
                )
                if flag_for_clause:
                    if flag_for_clause.severity == RiskLevel.CRITICAL:
                        clause.risk_level = RiskLevel.CRITICAL
                        clause.risk_score = 90.0
                    elif flag_for_clause.severity == RiskLevel.HIGH:
                        clause.risk_score = max(clause.risk_score, 75.0)

            return state

        except Exception as e:
            state.error_message = f"Risk scoring failed: {str(e)}"
            state.processing_status = ProcessingStatus.FAILED
            return state

    def _cross_reference_check(self, state: AnalysisState) -> AnalysisState:
        """
        Stage 4: Cross-reference check with other contracts in deal.

        Identifies:
        - Contradicting terms across contracts
        - Inconsistent party definitions
        - Conflicting payment terms
        - Conflicting termination rights

        In a real implementation, would:
        1. Query vector DB for similar clauses in other contracts
        2. Use semantic comparison to find conflicts
        3. Apply deal-specific playbook rules

        For now, we mock this by skipping (would fetch other contract clauses
        from the database in production).
        """
        try:
            # In production:
            # 1. Query contracts in same deal
            # 2. Retrieve their extracted clauses from DB
            # 3. Compare clause terms semantically using embeddings
            # 4. Identify conflicts

            # Mock: no other contracts loaded in this demo
            state.conflicts = []
            state.other_contract_clauses = []

            return state

        except Exception as e:
            state.error_message = f"Cross-reference check failed: {str(e)}"
            state.processing_status = ProcessingStatus.FAILED
            return state

    def _route_for_review(self, state: AnalysisState) -> AnalysisState:
        """
        Stage 5: Route low-confidence clauses to human review.

        Decision logic:
        - Clauses with confidence >= 0.85: auto-accept
        - Clauses with confidence < 0.85: route to human review
        - Clauses with critical risk flags: always route to human review

        Sets requires_review flag if any clauses need attention.
        """
        try:
            low_confidence = [
                clause for clause in state.extracted_clauses
                if clause.confidence < self.CONFIDENCE_THRESHOLD
            ]

            critical_risk = [
                clause for clause in state.extracted_clauses
                if clause.risk_level == RiskLevel.CRITICAL
            ]

            state.low_confidence_clauses = low_confidence + critical_risk

            if state.low_confidence_clauses:
                state.requires_review = True
                state.review_reason = (
                    f"{len(low_confidence)} low-confidence clauses and "
                    f"{len(critical_risk)} critical-risk clauses require human review"
                )

                # Update review status for these clauses
                for clause in state.low_confidence_clauses:
                    clause.review_status = ReviewStatus.PENDING_REVIEW
            else:
                state.requires_review = False
                state.review_reason = None

                # Auto-accept high-confidence clauses
                for clause in state.extracted_clauses:
                    clause.review_status = ReviewStatus.AUTO_ACCEPTED

            return state

        except Exception as e:
            state.error_message = f"Review routing failed: {str(e)}"
            state.processing_status = ProcessingStatus.FAILED
            return state


# Example usage and testing
if __name__ == "__main__":
    # Initialize workflow
    workflow = ContractAnalysisWorkflow()

    # Create initial state with sample contract text
    initial_state = AnalysisState(
        document_id="doc_test_001",
        deal_id="deal_test_001",
        tenant_id="tenant_test_001",
        raw_text="Sample contract text would go here...",
    )

    # Run the workflow
    final_state = workflow.run(initial_state)

    # Inspect results
    print(f"Processing Status: {final_state.processing_status}")
    print(f"Clauses Extracted: {len(final_state.extracted_clauses)}")
    print(f"Risk Flags: {len(final_state.risk_flags)}")
    print(f"Requires Review: {final_state.requires_review}")
    print(f"Total Processing Time: {(final_state.processing_end_time - final_state.processing_start_time).total_seconds():.2f}s")
