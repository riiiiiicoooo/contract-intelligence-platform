"""
Clause Extractor - Reference Implementation
Uses Claude API for structured clause extraction with confidence scoring
and multi-model fallback to GPT-4.
"""

import json
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class ExtractedClause:
    clause_type: str
    text: str
    page_number: int
    section_reference: Optional[str]
    confidence: float
    risk_level: str  # low, medium, high, critical
    risk_explanation: str
    model_id: str
    token_count_input: int = 0
    token_count_output: int = 0
    latency_ms: int = 0


# The 41 clause types we extract (see PRD Appendix A)
CLAUSE_TYPES = [
    "change_of_control", "assignment", "termination_convenience",
    "termination_cause", "indemnification", "limitation_of_liability",
    "payment_terms", "renewal_auto_renewal", "governing_law",
    "non_compete", "confidentiality", "ip_ownership",
    "notice_requirements", "force_majeure", "exclusivity",
    "warranty_representations", "insurance_requirements", "audit_rights",
    "data_protection", "subcontracting", "price_escalation",
    "minimum_commitment", "service_level_agreement", "dispute_resolution",
    "non_disclosure", "right_of_first_refusal", "most_favored_nation",
    "liquidated_damages", "waiver_provisions", "survival_clauses",
    "anti_bribery", "environmental_compliance", "employee_transfer",
    "material_adverse_change", "regulatory_approval", "escrow_arrangements",
    "earnout_provisions", "drag_along_tag_along", "restrictive_covenants",
    "set_off_rights", "consent_requirements",
]

EXTRACTION_PROMPT = """You are a contract analysis expert. Extract all key clauses from the following contract text.

For each clause found, return a JSON object with:
- clause_type: one of the predefined types listed below
- text: the exact clause text from the contract
- page_number: the page where this clause appears
- section_reference: the section number (e.g., "Section 8.2(a)")
- confidence: your confidence in this extraction (0.0 to 1.0)
- risk_level: low, medium, high, or critical
- risk_explanation: brief explanation of why this risk level was assigned

Clause types to look for:
{clause_types}

Also identify any MISSING clauses that would typically be expected in a {contract_type} but are absent from this contract.

Return your response as a JSON array. Be precise - only extract clauses that actually exist in the text.

Contract text:
{contract_text}"""


class ClauseExtractor:
    """
    Extracts clauses from contract text using Claude API with GPT-4 fallback.

    Pipeline:
    1. PII redaction (handled upstream by pii_redactor.py)
    2. Send redacted text to Claude with structured extraction prompt
    3. Parse structured JSON response
    4. Score confidence and risk
    5. If Claude fails, fallback to GPT-4
    """

    PRIMARY_MODEL = "claude-sonnet-4-20250514"
    FALLBACK_MODEL = "gpt-4-turbo-preview"
    MAX_RETRIES = 2
    TIMEOUT_SECONDS = 30
    TEMPERATURE = 0.2  # Low temperature for deterministic extraction

    def __init__(self, anthropic_client=None, openai_client=None):
        self.anthropic_client = anthropic_client
        self.openai_client = openai_client

    def extract(
        self,
        contract_text: str,
        contract_type: str = "msa",
        document_id: str = "",
    ) -> list[ExtractedClause]:
        """
        Extract clauses from contract text.
        Tries Claude first, falls back to GPT-4 on failure.
        """
        prompt = EXTRACTION_PROMPT.format(
            clause_types="\n".join(f"- {ct}" for ct in CLAUSE_TYPES),
            contract_type=contract_type,
            contract_text=contract_text,
        )

        # Try primary model (Claude)
        try:
            result = self._call_claude(prompt)
            if result:
                return result
        except Exception as e:
            print(f"Claude extraction failed: {e}. Falling back to GPT-4.")

        # Fallback to GPT-4
        try:
            result = self._call_gpt4(prompt)
            if result:
                return result
        except Exception as e:
            print(f"GPT-4 fallback also failed: {e}")
            raise RuntimeError("All extraction models failed")

    def _call_claude(self, prompt: str) -> list[ExtractedClause]:
        """
        Call Claude API for clause extraction.
        Uses structured JSON output with tool use for schema enforcement.
        """
        start_time = time.time()

        # In production:
        # response = self.anthropic_client.messages.create(
        #     model=self.PRIMARY_MODEL,
        #     max_tokens=8192,
        #     temperature=self.TEMPERATURE,
        #     messages=[{"role": "user", "content": prompt}],
        # )

        # Reference: simulate response structure
        latency_ms = int((time.time() - start_time) * 1000)

        # Parse response into ExtractedClause objects
        # In production, parse response.content[0].text as JSON
        sample_response = [
            {
                "clause_type": "change_of_control",
                "text": "In the event of a Change of Control...",
                "page_number": 12,
                "section_reference": "Section 14.2(b)",
                "confidence": 0.94,
                "risk_level": "high",
                "risk_explanation": "60-day notice period is below market standard of 90 days.",
            }
        ]

        return [
            ExtractedClause(
                clause_type=c["clause_type"],
                text=c["text"],
                page_number=c["page_number"],
                section_reference=c.get("section_reference"),
                confidence=c["confidence"],
                risk_level=c["risk_level"],
                risk_explanation=c["risk_explanation"],
                model_id=self.PRIMARY_MODEL,
                latency_ms=latency_ms,
            )
            for c in sample_response
        ]

    def _call_gpt4(self, prompt: str) -> list[ExtractedClause]:
        """
        Fallback to GPT-4 when Claude is unavailable.
        Uses function calling for structured output.
        """
        start_time = time.time()

        # In production:
        # response = self.openai_client.chat.completions.create(
        #     model=self.FALLBACK_MODEL,
        #     temperature=self.TEMPERATURE,
        #     messages=[{"role": "user", "content": prompt}],
        #     response_format={"type": "json_object"},
        # )

        latency_ms = int((time.time() - start_time) * 1000)

        # Parse and return same ExtractedClause format
        return []

    def route_for_review(
        self,
        clauses: list[ExtractedClause],
        confidence_threshold: float = 0.85,
    ) -> tuple[list[ExtractedClause], list[ExtractedClause]]:
        """
        Split extracted clauses into auto-accepted and needs-review lists
        based on confidence threshold.

        At 0.85 threshold:
        - ~81% of clauses are auto-accepted
        - ~19% route to human review
        - 2.4% error rate in auto-accepted (acceptable per DEC-012)
        """
        auto_accepted = []
        needs_review = []

        for clause in clauses:
            if clause.confidence >= confidence_threshold:
                auto_accepted.append(clause)
            else:
                needs_review.append(clause)

        return auto_accepted, needs_review
