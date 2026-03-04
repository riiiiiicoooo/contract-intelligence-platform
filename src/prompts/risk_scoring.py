"""
Production-style prompt for risk scoring extracted clauses.

This module defines a structured prompt for evaluating extracted clauses
against a risk rubric. Scores clauses based on:
- Severity (likelihood of impact)
- Financial exposure (magnitude of impact)
- Deviation from market standards
- Deal-type specific implications

Output includes:
- Risk level (low/medium/high/critical)
- Risk score (0-100 numeric scale)
- Severity and likelihood scores
- Comparative analysis to market standards
- Playbook rule triggers
"""

from typing import TypedDict, Optional
from enum import Enum


class RiskScoringOutput(TypedDict):
    """Output schema for risk scoring evaluation."""
    clause_id: str
    clause_type: str
    risk_level: str
    risk_score: float
    severity_score: float  # 1-10 scale
    likelihood_score: float  # 1-10 scale
    financial_exposure_score: float  # 1-10 scale
    is_standard: bool
    deviation_explanation: str
    market_comparison: str
    playbook_flags: list[str]
    recommendations: list[str]
    confidence: float


# ============================================================================
# SYSTEM MESSAGE
# ============================================================================

SYSTEM_MESSAGE = """You are an expert M&A lawyer evaluating contract risk provisions.

Your task is to assess the risk level and financial impact of extracted contract clauses.
Risk assessment considers:
1. Likelihood of negative impact (1-10 scale)
2. Severity if impact occurs (1-10 scale)
3. Financial exposure (magnitude of potential loss)
4. Deviation from market standards
5. Deal type and context

Risk Level Categories:
- CRITICAL: Could kill the deal or materially impact valuation
  - Uncapped liability exposure
  - Unilateral termination rights on change of control
  - Automatic renewal traps that could prevent exit
  - Missing key protective provisions

- HIGH: Significant risk requiring negotiation or mitigation
  - Non-standard termination notice periods
  - Unfavorable payment terms
  - Asymmetric indemnification obligations
  - Restricted assignment rights

- MEDIUM: Notable risk but manageable with standard market terms
  - Typical limitations of liability at 1x revenue
  - Standard 30-90 day termination notice
  - Market-standard carve-outs present

- LOW: Minimal risk, aligned with market practice
  - Standard payment terms
  - Reasonable notice periods
  - Comprehensive carve-outs
  - Balanced risk allocation

For each clause, you will:
1. Extract key variables (notice periods, caps, percentages, etc.)
2. Compare to market benchmarks for this contract type and jurisdiction
3. Calculate risk scores using the rubric below
4. Flag trigger items from deal-specific playbooks
5. Provide negotiation recommendations"""


# ============================================================================
# RISK SCORING RUBRIC
# ============================================================================

RISK_RUBRIC = """
RISK SCORING RUBRIC (for clause-level assessment)

Variable: NOTICE PERIOD (for termination rights)
  - < 15 days: Likelihood 10, Severity 8 → Risk 90-100 (CRITICAL)
  - 15-30 days: Likelihood 9, Severity 7 → Risk 75-85 (HIGH)
  - 30-60 days: Likelihood 6, Severity 6 → Risk 50-70 (MEDIUM)
  - 60-90 days: Likelihood 4, Severity 5 → Risk 35-50 (MEDIUM)
  - 90+ days: Likelihood 2, Severity 3 → Risk 15-30 (LOW)

Variable: LIABILITY CAP
  - Uncapped: Likelihood 9, Severity 9 → Risk 85-95 (CRITICAL)
  - > 3x annual revenue: Likelihood 8, Severity 7 → Risk 70-80 (HIGH)
  - 1x-3x annual revenue: Likelihood 4, Severity 6 → Risk 45-60 (MEDIUM)
  - < 1x annual revenue: Likelihood 3, Severity 4 → Risk 20-40 (MEDIUM)
  - 12-month cap tied to fees: Likelihood 2, Severity 3 → Risk 10-25 (LOW)

Variable: ASSIGNMENT RESTRICTIONS
  - Consent required (unreasonably withheld): Likelihood 6, Severity 7 → Risk 60-75 (HIGH)
  - Consent required (not to be unreasonably withheld): Likelihood 3, Severity 5 → Risk 30-45 (MEDIUM)
  - Affiliate carve-out present: Likelihood 1, Severity 2 → Risk 5-15 (LOW)
  - Unilateral assignment right: Likelihood 0, Severity 0 → Risk 0-5 (LOW)

Variable: PAYMENT TERMS
  - Net 60+ days: Likelihood 5, Severity 5 → Risk 40-55 (MEDIUM)
  - Net 30 days: Likelihood 2, Severity 3 → Risk 10-25 (LOW)
  - Net 15 days or less: Likelihood 4, Severity 6 → Risk 50-65 (MEDIUM)
  - COD / Prepayment: Likelihood 3, Severity 5 → Risk 35-50 (MEDIUM)

Variable: AUTO-RENEWAL
  - Present without easy exit: Likelihood 8, Severity 7 → Risk 75-85 (HIGH)
  - With 90+ day notice to terminate: Likelihood 2, Severity 3 → Risk 10-20 (LOW)
  - Missing entirely (concerns for renewal): Likelihood 6, Severity 5 → Risk 50-65 (MEDIUM)

Variable: INDEMNIFICATION
  - Uncapped, including indirect damages: Likelihood 9, Severity 9 → Risk 85-95 (CRITICAL)
  - Uncapped for IP indemnity only: Likelihood 6, Severity 8 → Risk 70-80 (HIGH)
  - Capped at 1x revenue: Likelihood 2, Severity 4 → Risk 25-40 (MEDIUM)
  - Mutual indemnification with carve-outs: Likelihood 1, Severity 2 → Risk 5-15 (LOW)

FINANCIAL EXPOSURE CALCULATION:
  - Uncapped: Score 10
  - > $10M assumed exposure: Score 8-9
  - $1M-$10M exposure: Score 6-7
  - $100K-$1M exposure: Score 4-5
  - < $100K exposure: Score 2-3
"""


# ============================================================================
# FEW-SHOT EXAMPLES
# ============================================================================

EXAMPLE_1_INPUT = """
Clause Type: change_of_control
Extracted Text: "In the event of a Change of Control of Buyer, Seller shall have the right to
terminate this Agreement upon sixty (60) days' written notice."

Contract Type: MSA (Master Service Agreement)
Governing Law: Delaware
Contract Value Range: $500K-$2M annually

Related Playbook Rules:
- Rule COC-001: Change of control triggers > 30 days notice = WARNING
- Rule COC-002: Unilateral termination right for non-changing party = CRITICAL
"""

EXAMPLE_1_OUTPUT: RiskScoringOutput = {
    "clause_id": "clause_001",
    "clause_type": "change_of_control",
    "risk_level": "high",
    "risk_score": 78.0,
    "severity_score": 7.5,  # High impact if triggered (seller can exit during acquisition)
    "likelihood_score": 6.0,  # Moderate likelihood (acquisition scenarios common in M&A)
    "financial_exposure_score": 8.0,  # High exposure (loss of revenue stream)
    "is_standard": False,
    "deviation_explanation": "Notice period of 60 days is below market standard of 90 days for MSAs. "
                           "Unilateral termination right (not requiring mutual consent) is non-standard. "
                           "Combined with short notice period, creates significant deal risk.",
    "market_comparison": "Delaware MSAs: market standard is 90-day notice period with mutual consent requirement "
                        "or 50% fee cap. This provision uses 60 days with unilateral right - 33% shorter notice "
                        "and no consent requirement. Compares to 25th percentile of market terms.",
    "playbook_flags": [
        "COC-001: Change of control triggers short notice (60 < 90 days)",
        "COC-002: Unilateral termination right for non-changing party",
        "DEAL-RISK: Seller can terminate during buyer's acquisition window",
    ],
    "recommendations": [
        "Negotiate notice period to 90+ days minimum",
        "Add requirement for seller consent (not to be unreasonably withheld)",
        "Add carve-out: acquisitions by PE firms or financial buyers",
        "Add carve-out: stock issuance or equity restructuring",
        "Consider including cure period (e.g., 30 days to remedy)",
    ],
    "confidence": 0.92,
}

EXAMPLE_2_INPUT = """
Clause Type: limitation_of_liability
Extracted Text: "Neither party's aggregate liability under this Agreement shall be limited
to the total fees paid by Client in the twelve (12) months immediately preceding the date
of the claim, except for: (a) indemnification obligations; (b) breach of confidentiality;
(c) gross negligence or willful misconduct."

Contract Type: MSA
Governing Law: New York
Contract Value Range: $2M-$5M annually
"""

EXAMPLE_2_OUTPUT: RiskScoringOutput = {
    "clause_id": "clause_002",
    "clause_type": "limitation_of_liability",
    "risk_level": "medium",
    "risk_score": 48.0,
    "severity_score": 6.0,  # Moderate severity (carve-outs remove cap for key areas)
    "likelihood_score": 4.0,  # Moderate likelihood (depends on nature of service)
    "financial_exposure_score": 5.5,  # Moderate exposure (uncapped for indemnity + IP)
    "is_standard": True,
    "deviation_explanation": "This is a market-standard limitation of liability clause for MSAs. "
                           "Caps aggregate liability to 12-month fees. Carve-outs for indemnification, "
                           "confidentiality, and gross negligence are standard exceptions. "
                           "Risk is moderate because carve-outs create potential for exposure beyond cap.",
    "market_comparison": "New York MSAs: this clause is at 60th percentile of market terms. "
                        "12-month fee cap is standard (ranges 6-24 months). Carve-outs for indemnity "
                        "are market standard but create exposure. Mutual cap applies to both parties.",
    "playbook_flags": [
        "LOL-001: Limitation of liability cap present and reasonable",
        "LOL-003: Carve-out for indemnification (creates potential uncapped exposure)",
        "LOL-005: Carve-out for confidentiality breach (aligns with TIPA risk)",
    ],
    "recommendations": [
        "Add cap to indemnification carve-out (e.g., 2x annual fees)",
        "Clarify that gross negligence excludes ordinary negligence",
        "Consider adding: carve-out does not apply to direct damages exceeding X",
        "Confirm mutual application of caps (both parties subject to same limits)",
        "Consider adding: proportionate liability for joint/comparative fault scenarios",
    ],
    "confidence": 0.88,
}


# ============================================================================
# PROMPT TEMPLATE
# ============================================================================

SCORING_PROMPT = """Evaluate the risk level and financial exposure of the following extracted clause.

EXTRACTED CLAUSE:
Clause Type: {clause_type}
Clause Text: {clause_text}
Page: {page_number}
Section: {section_reference}
Confidence in Extraction: {confidence}

CONTEXT:
Contract Type: {contract_type}
Governing Law: {governing_law}
Deal Type: {deal_type}
Contract Value (annual): {contract_value}

RELATED EXTRACTED CLAUSES (for context):
{related_clauses}

PLAYBOOK RULES (deal-type specific):
{playbook_rules}

MARKET BENCHMARKS:
{market_benchmarks}

===== SCORING TASK =====

Use the risk rubric provided to evaluate this clause across five dimensions:

1. **severity_score** (1-10 scale):
   - 9-10: If triggered, would cause major business impact (loss of revenue, regulatory issues)
   - 7-8: Significant negative impact but manageable
   - 5-6: Moderate impact
   - 3-4: Minor impact
   - 1-2: Negligible impact

2. **likelihood_score** (1-10 scale):
   - 9-10: Highly likely to be triggered
   - 7-8: Likely to occur
   - 5-6: Moderate probability
   - 3-4: Unlikely but possible
   - 1-2: Very unlikely to occur

3. **financial_exposure_score** (1-10 scale):
   - 10: Uncapped exposure
   - 8-9: > $10M estimated exposure
   - 6-7: $1M-$10M exposure
   - 4-5: $100K-$1M exposure
   - 2-3: $10K-$100K exposure
   - 1: < $10K exposure

4. **is_standard** (boolean):
   - True: Matches or exceeds market standard for this contract type and jurisdiction
   - False: Below market standard, requiring negotiation

5. **risk_level** (categorical):
   Calculate combined score: risk_score = (severity × 0.35) + (likelihood × 0.35) + (financial_exposure × 0.30)

   Then map to category:
   - CRITICAL: risk_score >= 80
   - HIGH: risk_score 60-79
   - MEDIUM: risk_score 40-59
   - LOW: risk_score < 40

6. **playbook_flags** (list):
   - Check each playbook rule
   - Include any that are triggered (flag_condition = true)
   - Format: "RULE-ID: Description"

7. **recommendations** (list):
   - Provide 3-5 specific negotiation recommendations
   - Prioritize by impact (most important first)
   - Make actionable and concrete

RETURN FORMAT:
```json
{{
  "clause_id": "{clause_id}",
  "clause_type": "{clause_type}",
  "risk_level": "high|medium|low|critical",
  "risk_score": 78.5,
  "severity_score": 7.5,
  "likelihood_score": 6.0,
  "financial_exposure_score": 8.0,
  "is_standard": false,
  "deviation_explanation": "Explanation of how this deviates from market standard...",
  "market_comparison": "Comparison to market benchmarks for {governing_law} {contract_type}...",
  "playbook_flags": [
    "RULE-001: Description",
    "RULE-002: Description"
  ],
  "recommendations": [
    "First recommendation",
    "Second recommendation",
    "Third recommendation"
  ],
  "confidence": 0.88
}}
```

IMPORTANT GUIDELINES:
- Be precise in numerical scoring (0.1 increments)
- Justify each score with reference to market standards
- Consider deal context (M&A vs. recurring service vs. licensing)
- Flag ambiguities or unclear provisions in deviation_explanation
- Recommendations should be achievable in typical negotiations
- Consider asymmetries (if cap applies only to one party, flag it)
- Reference specific market benchmarks when available"""


def get_risk_scoring_prompt(
    clause_type: str,
    clause_text: str,
    page_number: int,
    section_reference: str,
    confidence: float,
    contract_type: str = "msa",
    governing_law: str = "Delaware",
    deal_type: str = "m_and_a",
    contract_value: str = "$1M-$5M",
    related_clauses: str = "",
    playbook_rules: str = "",
    market_benchmarks: str = "",
    clause_id: str = "clause_001",
) -> str:
    """
    Generate a formatted risk scoring prompt for a clause.

    Args:
        clause_type: Type of clause (e.g., 'change_of_control')
        clause_text: Full extracted clause text
        page_number: Page where clause appears
        section_reference: Section number/reference
        confidence: Extraction confidence (0.0-1.0)
        contract_type: Type of contract (msa, sow, etc.)
        governing_law: Jurisdiction for market standards
        deal_type: Deal type (m_and_a, lending, etc.)
        contract_value: Annual contract value range
        related_clauses: Text of related clauses for context
        playbook_rules: Applicable playbook rules in JSON
        market_benchmarks: Market standard data
        clause_id: Unique clause identifier

    Returns:
        Formatted prompt string ready for LLM API call
    """
    return SCORING_PROMPT.format(
        clause_id=clause_id,
        clause_type=clause_type,
        clause_text=clause_text,
        page_number=page_number,
        section_reference=section_reference,
        confidence=confidence,
        contract_type=contract_type,
        governing_law=governing_law,
        deal_type=deal_type,
        contract_value=contract_value,
        related_clauses=related_clauses,
        playbook_rules=playbook_rules,
        market_benchmarks=market_benchmarks,
    )
