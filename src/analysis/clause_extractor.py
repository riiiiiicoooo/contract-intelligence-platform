"""
Clause Extractor - Reference Implementation
Uses Claude API for structured clause extraction with confidence scoring
and multi-model fallback to GPT-4.

Resilience: Uses circuit breakers (pybreaker) per provider to avoid cascading
failures when a model API is degraded, and tenacity for retry with exponential
backoff on transient errors (429, 5xx, timeouts).

Production Notes (not implemented in this demo):
- Document Encryption: Contracts uploaded for analysis should be encrypted at
  rest (AES-256 via AWS KMS with per-tenant keys) and in transit (TLS 1.3).
  Decryption happens only in the extraction pipeline's memory — never written
  to disk unencrypted.
- SOC 2 Audit Logging: Every clause extraction call should log: user_id,
  tenant_id, document_id, model_used, timestamp, and extraction_id to an
  immutable audit trail. Legal teams need to prove who accessed which contract
  and when for privilege and chain-of-custody purposes.
- LLM Output Validation: The structured JSON returned by Claude/GPT-4 should
  be validated against a JSON Schema before being stored. Malformed or
  hallucinated fields (e.g., confidence > 1.0, unknown clause_types) should
  trigger a re-extraction or human review flag.
- Prompt Injection Defense: Contract text is user-uploaded content and could
  contain adversarial instructions. The clause_extraction.py prompt module
  already includes sanitize_prompt_input() — ensure all contract text passes
  through it before any LLM call. See also: NeMo Guardrails for classifier-
  based injection detection as a production-grade complement.
- Cost Controls: Large contracts (100+ pages) can consume significant token
  budgets. Implement per-tenant monthly spend caps and chunk contracts into
  sections before extraction to keep per-call costs predictable.
"""

import json
import logging
import time
from dataclasses import dataclass
from typing import Optional

import pybreaker
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


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


# Circuit breakers: open after 5 consecutive failures, reset after 60 seconds.
# Prevents hammering a degraded API and lets it recover.
claude_breaker = pybreaker.CircuitBreaker(
    fail_max=5,
    reset_timeout=60,
    name="claude_extraction",
)

gpt4_breaker = pybreaker.CircuitBreaker(
    fail_max=5,
    reset_timeout=60,
    name="gpt4_extraction",
)


class ClauseExtractor:
    """
    Extracts clauses from contract text using Claude API with GPT-4 fallback.

    Resilience layers:
    1. Retry with exponential backoff (3 attempts per provider)
    2. Circuit breaker per provider (opens after 5 consecutive failures)
    3. Model fallback (Claude → GPT-4)

    Pipeline:
    1. PII redaction (handled upstream by pii_redactor.py)
    2. Send redacted text to Claude with structured extraction prompt
    3. Parse structured JSON response
    4. Score confidence and risk
    5. If Claude fails or circuit is open, fallback to GPT-4
    """

    PRIMARY_MODEL = "claude-sonnet-4-20250514"
    FALLBACK_MODEL = "gpt-4-turbo-preview"
    MAX_RETRIES = 3
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
        Tries Claude first (with retry + circuit breaker), falls back to GPT-4.
        """
        prompt = EXTRACTION_PROMPT.format(
            clause_types="\n".join(f"- {ct}" for ct in CLAUSE_TYPES),
            contract_type=contract_type,
            contract_text=contract_text,
        )

        # Try primary model (Claude) with circuit breaker
        try:
            result = self._call_claude_with_resilience(prompt)
            if result:
                return result
        except pybreaker.CircuitBreakerError:
            logger.warning("Claude circuit breaker is OPEN, skipping to GPT-4 fallback")
        except Exception as e:
            logger.warning(f"Claude extraction failed after retries: {e}. Falling back to GPT-4.")

        # Fallback to GPT-4 with circuit breaker
        try:
            result = self._call_gpt4_with_resilience(prompt)
            if result:
                return result
        except pybreaker.CircuitBreakerError:
            logger.error("GPT-4 circuit breaker is also OPEN — both providers degraded")
            raise RuntimeError("All extraction model circuits are open")
        except Exception as e:
            logger.error(f"GPT-4 fallback also failed after retries: {e}")
            raise RuntimeError("All extraction models failed")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((TimeoutError, ConnectionError, OSError)),
        reraise=True,
    )
    def _call_claude_with_resilience(self, prompt: str) -> list[ExtractedClause]:
        """Claude call wrapped with retry + circuit breaker."""
        return claude_breaker.call(self._call_claude, prompt)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((TimeoutError, ConnectionError, OSError)),
        reraise=True,
    )
    def _call_gpt4_with_resilience(self, prompt: str) -> list[ExtractedClause]:
        """GPT-4 call wrapped with retry + circuit breaker."""
        return gpt4_breaker.call(self._call_gpt4, prompt)

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
