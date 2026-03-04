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

        In production, this would use Claude API. Here we mock the LLM call.
        """
        try:
            # Mock LLM classification
            # In production: use self.llm_client.messages.create()
            classification = ContractClassification(
                contract_id=state.document_id,
                contract_type="msa",  # Would be detected from text
                confidence=0.92,
                party_names=["Acme Corporation", "Beta Industries LLC"],
                effective_date="2024-01-15",
                expiration_date="2027-01-14",
                governing_law="Delaware",
                model_id="claude-sonnet-4-20250514",
                latency_ms=1250,
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

        Uses Claude API (mocked here) to identify 40+ clause types:
        - change_of_control
        - assignment
        - termination_convenience
        - limitation_of_liability
        - indemnification
        - etc.

        Each clause includes:
        - Extracted text (exact from contract)
        - Page number and section reference
        - Confidence score (0.0-1.0)
        - Initial risk assessment
        """
        try:
            # Mock clause extraction
            # In production: use self.llm_client.messages.create() with structured output
            clauses = [
                ExtractedClause(
                    clause_type="change_of_control",
                    extracted_text="In the event of a Change of Control of either party, "
                                  "the non-affected party shall have the right to terminate "
                                  "this Agreement upon sixty (60) days written notice.",
                    page_number=12,
                    section_reference="Section 14.2(b)",
                    section_title="Assignment and Change of Control",
                    surrounding_context="...governing assignment provisions... [EXTRACTED] ...effects on termination...",
                    confidence=0.94,
                    risk_level=RiskLevel.HIGH,
                    risk_explanation="60-day notice is below market standard of 90 days",
                    risk_score=78.0,
                    review_status=ReviewStatus.AUTO_ACCEPTED,
                    model_id="claude-sonnet-4-20250514",
                    token_count_input=2450,
                    token_count_output=180,
                    processing_latency_ms=3200,
                ),
                ExtractedClause(
                    clause_type="limitation_of_liability",
                    extracted_text="Neither party's aggregate liability under this Agreement "
                                  "shall exceed the total fees paid in the twelve (12) months "
                                  "preceding the claim.",
                    page_number=18,
                    section_reference="Section 10.1",
                    section_title="Limitation of Liability",
                    surrounding_context="...damages and remedies... [EXTRACTED] ...exceptions and carve-outs...",
                    confidence=0.88,
                    risk_level=RiskLevel.MEDIUM,
                    risk_explanation="Standard market cap but excludes indirect damages",
                    risk_score=42.0,
                    review_status=ReviewStatus.AUTO_ACCEPTED,
                    model_id="claude-sonnet-4-20250514",
                    token_count_input=2450,
                    token_count_output=145,
                    processing_latency_ms=2900,
                ),
                ExtractedClause(
                    clause_type="payment_terms",
                    extracted_text="Invoices shall be due net thirty (30) days from receipt. "
                                  "Late payments accrue interest at 1.5% per month or the "
                                  "maximum rate allowed by law, whichever is less.",
                    page_number=5,
                    section_reference="Section 3.2",
                    section_title="Payment Terms",
                    surrounding_context="...billing arrangements... [EXTRACTED] ...credit terms...",
                    confidence=0.97,
                    risk_level=RiskLevel.LOW,
                    risk_explanation="Standard payment terms with reasonable grace period",
                    risk_score=15.0,
                    review_status=ReviewStatus.AUTO_ACCEPTED,
                    model_id="claude-sonnet-4-20250514",
                    token_count_input=2450,
                    token_count_output=120,
                    processing_latency_ms=2800,
                ),
                ExtractedClause(
                    clause_type="termination_convenience",
                    extracted_text="Either party may terminate this Agreement without cause "
                                  "upon thirty (30) days written notice to the other party. "
                                  "Upon such termination...",
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
                    token_count_input=2450,
                    token_count_output=135,
                    processing_latency_ms=3100,
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

        Generates risk flags for:
        - Non-standard terms (deviation from library)
        - Uncapped liability
        - Unfavorable termination rights
        - Missing expected clauses
        - etc.
        """
        try:
            # Mock risk scoring
            # In production: compare against clause_library embeddings, apply playbook rules
            risk_flags = [
                RiskFlag(
                    clause_id=state.extracted_clauses[0].id,
                    flag_type="change_of_control_trigger",
                    severity=RiskLevel.WARNING,
                    description="Change of control triggers termination right for counterparty",
                    recommendation="Negotiate for consent requirement instead of termination right, "
                                 "or extend notice period to 90 days minimum",
                    playbook_rule_id="pb_rule_coc_001",
                ),
                RiskFlag(
                    clause_id=state.extracted_clauses[1].id,
                    flag_type="non_standard_term",
                    severity=RiskLevel.INFO,
                    description="Liability cap is tied to fees paid, which is market standard",
                    recommendation="No action required for liability cap",
                    playbook_rule_id="pb_rule_lol_001",
                ),
            ]

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
                    elif flag_for_clause.severity == RiskLevel.WARNING:
                        clause.risk_score = max(clause.risk_score, 60.0)

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
