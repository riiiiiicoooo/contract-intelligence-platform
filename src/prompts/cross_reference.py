"""
Production-style prompt for cross-contract reference checking.

This module defines a structured prompt for identifying conflicts and
inconsistencies between two contracts' terms. Used to detect:
- Contradicting termination rights
- Inconsistent payment terms
- Conflicting indemnification obligations
- Missing reciprocal provisions

Output includes:
- Conflict type and severity
- Specific contradictions with page references
- Deal impact analysis
- Resolution recommendations
"""

from typing import TypedDict, Optional
import re


# Sanitize contract text to mitigate prompt injection — in production, use
# dedicated guardrail libraries (e.g., NeMo Guardrails, Guardrails AI)
def sanitize_prompt_input(text: str) -> str:
    """Strip or escape common prompt injection patterns from user-controlled text.

    This is a basic defense-in-depth measure. It catches obvious injection
    attempts such as:
    - Instructions to ignore/override the system prompt
    - System prompt delimiter sequences (```, <|, [INST], etc.)
    - XML-like tags that could confuse instruction boundaries
    - Role-play or persona-switching attempts

    In production, pair this with a dedicated guardrail service that runs
    classifier-based injection detection (e.g., Lakera Guard, Rebuff, or
    NVIDIA NeMo Guardrails).
    """
    if not text:
        return text

    # Patterns that attempt to override system instructions
    injection_patterns = [
        r"(?i)ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions|prompts|directives|rules)",
        r"(?i)disregard\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions|prompts|directives|rules)",
        r"(?i)forget\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions|prompts|directives|rules)",
        r"(?i)override\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions|prompts|directives|rules)",
        r"(?i)you\s+are\s+now\s+(a|an|the)\s+",
        r"(?i)new\s+instructions?\s*:",
        r"(?i)system\s*prompt\s*:",
        r"(?i)act\s+as\s+(a|an|the)\s+",
    ]

    sanitized = text
    for pattern in injection_patterns:
        sanitized = re.sub(pattern, "[REDACTED_INJECTION_ATTEMPT]", sanitized)

    # Strip system prompt delimiters that could break prompt boundaries
    delimiter_sequences = [
        "```",           # Markdown code fences
        "<|system|>",    # ChatML-style delimiters
        "<|user|>",
        "<|assistant|>",
        "<|im_start|>",
        "<|im_end|>",
        "[INST]",        # Llama-style delimiters
        "[/INST]",
        "<<SYS>>",
        "<</SYS>>",
    ]
    for delimiter in delimiter_sequences:
        sanitized = sanitized.replace(delimiter, "")

    # Escape XML-like tags that could confuse instruction boundaries
    sanitized = re.sub(r"<(/?)(?:system|instruction|prompt|role|context|admin)(\s[^>]*)?>",
                       r"[\1\2]", sanitized, flags=re.IGNORECASE)

    return sanitized


class CrossReferenceConflict(TypedDict):
    """Output schema for cross-contract conflict detection."""
    conflict_id: str
    contract_1_id: str
    contract_1_name: str
    contract_2_id: str
    contract_2_name: str
    clause_type: str
    conflict_type: str  # contradicting_terms, missing_reciprocal, inconsistent_definitions
    severity: str  # critical, high, medium, low
    contract_1_text: str
    contract_2_text: str
    description: str
    financial_impact: str
    resolution_recommendations: list[str]
    confidence: float


# ============================================================================
# SYSTEM MESSAGE
# ============================================================================

SYSTEM_MESSAGE = """You are an M&A contract specialist analyzing contract consistency across a deal.

Your task is to identify conflicts, contradictions, and inconsistencies between
two contracts' terms. This is critical because:

1. TERMINATION CONFLICTS - One contract allows termination with 30 days' notice
   while another requires 90 days → creates asymmetric deal risk

2. PAYMENT CONFLICTS - Different payment terms for same services across contracts
   → accounting complexity and potential disputes

3. LIABILITY CONFLICTS - Indemnification cap in Contract A is 1x revenue, but
   Contract B excludes indemnification from liability cap → creates exposure

4. DEFINITION CONFLICTS - "Material Breach" defined differently in two contracts
   → triggers termination rights inconsistently

5. MISSING RECIPROCITY - Contract A requires consent to assignment, but Contract B
   allows unilateral assignment → asymmetric risk

For each conflict found, assess:
- Whether it creates deal risk or is merely administrative
- Financial impact (e.g., "could create $2M exposure in indemnification")
- Severity relative to deal context
- Recommended resolution approach"""


# ============================================================================
# FEW-SHOT EXAMPLES
# ============================================================================

EXAMPLE_1_INPUT = """
Contract 1 (Service Agreement - Acme → Beta):
Clause: Change of Control (Section 8.2)
Text: "Seller shall have the right to terminate this Agreement upon sixty (60) days'
written notice in the event of a Change of Control of Buyer."

Contract 2 (Supply Agreement - Acme → Beta):
Clause: Change of Control (Section 14.1)
Text: "Either party may terminate this Agreement upon one hundred twenty (120) days'
written notice in the event of a Change of Control. Notwithstanding the foregoing,
if Buyer undergoes a Change of Control and continues to operate under its current
business model, Seller may not terminate this Agreement."

Deal Context: M&A transaction, Acme acquiring Beta
"""

EXAMPLE_1_OUTPUT: CrossReferenceConflict = {
    "conflict_id": "conflict_001",
    "contract_1_id": "contract_svc",
    "contract_1_name": "Service Agreement",
    "contract_2_id": "contract_sup",
    "contract_2_name": "Supply Agreement",
    "clause_type": "change_of_control",
    "conflict_type": "contradicting_terms",
    "severity": "critical",
    "contract_1_text": "Seller shall have the right to terminate upon 60 days' notice on Change of Control of Buyer",
    "contract_2_text": "Either party may terminate upon 120 days' notice, except Seller cannot terminate if Buyer continues operations",
    "description": "The two change-of-control provisions are fundamentally inconsistent. Service Agreement "
                  "grants Seller unilateral 60-day termination right. Supply Agreement requires 120-day notice "
                  "but prohibits Seller from terminating if Buyer continues operations. This creates ambiguity: "
                  "which provision controls? If Seller relies on Service Agreement, Buyer could argue Supply "
                  "Agreement carve-out prevents termination.",
    "financial_impact": "Contradictory provisions could prevent Seller from exiting during acquisition. "
                       "Service Agreement suggests clean exit with 60 days' notice. Supply Agreement suggests "
                       "Seller is trapped for 120 days AND cannot terminate if operations continue. "
                       "Estimated financial impact: $400K-$800K (lost opportunity to divest/transition supplier).",
    "resolution_recommendations": [
        "Harmonize notice periods: adopt single 90-day minimum notice period across all three contracts",
        "Clarify COC definition: does 'continues to operate' mean same revenue, same management, same markets?",
        "Add carve-out: Seller can terminate if Buyer's credit rating drops below X or financial metrics decline",
        "Consider: align termination rights with actual commercial relationship (who is more critical to whom?)",
        "Document deal-specific amendment: 'COC provisions in Services and Supply Agreements are superseded by "
        "Buyer's acquisition and both parties retain termination rights with 90-day notice'",
    ],
    "confidence": 0.95,
}

EXAMPLE_2_INPUT = """
Contract 1 (Master Service Agreement):
Clause: Limitation of Liability (Section 10.1)
Text: "Neither party's aggregate liability shall exceed the total fees paid
in the twelve (12) months preceding the claim."

Clause: Indemnification (Section 11)
Text: "Each party shall indemnify the other against third-party IP claims.
Indemnification obligations are subject to the liability limitations in Section 10."

Contract 2 (Statement of Work):
Clause: Limitation of Liability (Section 5)
Text: "Client's liability is capped at fees paid. Vendor's liability is capped
at 2x fees paid."

Clause: Indemnification (Section 6)
Text: "Vendor indemnifies Client for IP infringement claims. Indemnification
is NOT subject to liability limitations in Section 5."

Deal Context: Multi-year service engagement with multiple SOWs under single MSA
"""

EXAMPLE_2_OUTPUT: CrossReferenceConflict = {
    "conflict_id": "conflict_002",
    "contract_1_id": "contract_msa",
    "contract_1_name": "Master Service Agreement",
    "contract_2_id": "contract_sow",
    "contract_2_name": "Statement of Work",
    "clause_type": "limitation_of_liability",
    "conflict_type": "contradicting_terms",
    "severity": "high",
    "contract_1_text": "Liability cap applies to all claims including indemnification",
    "contract_2_text": "Liability cap does NOT apply to indemnification obligations; Vendor cap is 2x vs 1x",
    "description": "MSA and SOW have conflicting indemnification cap treatments. MSA states indemnification "
                  "is subject to 12-month fee cap (Section 11). SOW explicitly states indemnification is "
                  "NOT subject to liability cap and imposes asymmetric caps (Vendor: 2x, Client: 1x). "
                  "If IP claim arises, which terms apply? If MSA controls, Vendor's exposure is capped. "
                  "If SOW controls, Vendor exposure could exceed 2x fees without further cap.",
    "financial_impact": "For a $2M annual SOW, the difference is significant: "
                       "MSA cap = $2M (12-month fees); SOW cap for Vendor = $4M (2x fees) for indemnification. "
                       "If third-party IP claim ($5M) arises, MSA interpretation limits exposure to $2M, "
                       "but SOW could require $4M+ in indemnification. Risk: $2M+ unbudgeted exposure.",
    "resolution_recommendations": [
        "Clarify SOW terms: 'Indemnification carve-out is uncapped up to 2x annual fees, then limited by MSA cap'",
        "Add explicit hierarchy: 'In case of conflict, SOW terms prevail for that Statement of Work'",
        "Harmonize asymmetry: apply same liability caps to both parties or explain why Vendor needs higher cap",
        "Document IP indemnification limits: 'Vendor liability for IP claims shall not exceed $3M per incident'",
        "Consider adding: 'Vendor shall maintain E&O insurance with $2M minimum to cover IP indemnification exposure'",
    ],
    "confidence": 0.91,
}


# ============================================================================
# PROMPT TEMPLATE
# ============================================================================

COMPARISON_PROMPT = """Identify conflicts and inconsistencies between the following two contracts.

CONTRACT 1: {contract_1_name}
Document ID: {contract_1_id}
Contract Type: {contract_1_type}
Page Count: {contract_1_pages}

CONTRACT 2: {contract_2_name}
Document ID: {contract_2_id}
Contract Type: {contract_2_type}
Page Count: {contract_2_pages}

DEAL CONTEXT:
Deal Type: {deal_type}
Target Company: {target_company}
Key Counterparty: {counterparty_name}
Expected Impact: {deal_impact_description}

===== CONTRACT 1 EXTRACTED CLAUSES =====
{contract_1_clauses}

===== CONTRACT 2 EXTRACTED CLAUSES =====
{contract_2_clauses}

===== CONFLICT DETECTION TASK =====

Analyze the extracted clauses above and identify any conflicts, contradictions,
or inconsistencies between the two contracts. For each conflict found, assess:

CONFLICT CATEGORIES TO CHECK:

1. **Termination Rights Conflicts**
   - Different notice periods for same event (e.g., 30 days vs. 90 days)
   - Unilateral vs. mutual termination rights
   - Different consequences of termination (e.g., wind-down obligations, fee obligations)
   - Check: do termination triggers in one contract overlap with consequences in another?

2. **Liability & Indemnification Conflicts**
   - Liability caps: are they consistent? (e.g., 1x vs. 2x revenue)
   - Do liability caps in one contract apply to indemnification in another?
   - Are carve-outs (e.g., "excluding indemnification") consistent?
   - Check: asymmetric caps where one party has higher/lower limits

3. **Payment Terms Conflicts**
   - Net terms: are they the same? (e.g., Net 30 vs. Net 60)
   - Invoice timing: due upon invoice vs. due upon completion
   - Late payment penalties: interest rates, thresholds
   - Check: which contract controls if same service billed under multiple contracts?

4. **Definition Conflicts**
   - "Material Breach" defined differently
   - "Change of Control" defined differently
   - "Confidential Information" scope varies
   - Check: if two definitions overlap, which applies?

5. **Assignment & Consent Conflicts**
   - One contract requires consent for assignment, other allows unilateral assignment
   - Different carve-outs (e.g., affiliate assignments in one but not other)
   - Check: can a party assign under one contract but not the other?

6. **Missing Reciprocity**
   - Obligation in Contract 1 but no corresponding obligation in Contract 2
   - E.g., Insurance requirements, audit rights, data protection
   - Check: if services are related, should obligations be mutual?

7. **Automatic Renewal Conflicts**
   - Different renewal terms (automatic vs. manual)
   - Different notice periods to prevent renewal
   - Check: could a contract auto-renew when the other one terminates?

8. **Dispute Resolution Conflicts**
   - Different governing law (Delaware vs. New York)
   - Different dispute resolution methods (arbitration vs. litigation)
   - Check: conflicting forum could complicate dispute handling

SCORING CONFLICT SEVERITY:

CRITICAL:
- Contradictions that could prevent deal close
- Asymmetric termination rights during acquisition window
- Uncapped liability in one contract but capped in another
- Conflicting indemnification obligations with different financial exposure

HIGH:
- Notice period differences (30 vs. 60 days) requiring alignment
- Asymmetric liability caps requiring negotiation
- Missing reciprocal provisions requiring amendment

MEDIUM:
- Definitional inconsistencies (easy to clarify)
- Administrative differences (payment invoice formats)
- Non-material process conflicts

LOW:
- Redundant provisions (both consistent)
- Administrative-only discrepancies
- Context-dependent differences

RETURN FORMAT:
Return a JSON array of conflicts found:

```json
[
  {{
    "conflict_id": "conflict_001",
    "contract_1_id": "{contract_1_id}",
    "contract_1_name": "{contract_1_name}",
    "contract_2_id": "{contract_2_id}",
    "contract_2_name": "{contract_2_name}",
    "clause_type": "change_of_control|liability|payment_terms|etc",
    "conflict_type": "contradicting_terms|missing_reciprocal|inconsistent_definitions",
    "severity": "critical|high|medium|low",
    "contract_1_text": "Quote from Contract 1 clause...",
    "contract_2_text": "Quote from Contract 2 clause...",
    "description": "Detailed explanation of the conflict. Why is this a problem?",
    "financial_impact": "What is the deal impact if this conflict is not resolved?",
    "resolution_recommendations": [
      "Recommendation 1: specific action to resolve",
      "Recommendation 2: alternative approach",
      "Recommendation 3: fallback approach"
    ],
    "confidence": 0.92
  }}
]
```

IMPORTANT GUIDELINES:
- Only flag ACTUAL conflicts, not minor wording differences
- Consider context: is the difference intentional (e.g., different service scopes)?
- Focus on clauses that could materially impact the deal
- For each conflict, provide specific page references and quotes
- Confidence score should reflect certainty that this is a genuine conflict (vs. misunderstanding)
- If conflict is ambiguous, note it in description (e.g., "unclear which contract takes precedence")
- If no conflicts found, return empty array: []"""


def get_cross_reference_prompt(
    contract_1_name: str,
    contract_1_id: str,
    contract_1_type: str,
    contract_1_pages: int,
    contract_1_clauses: str,
    contract_2_name: str,
    contract_2_id: str,
    contract_2_type: str,
    contract_2_pages: int,
    contract_2_clauses: str,
    deal_type: str = "m_and_a",
    target_company: str = "Target Inc.",
    counterparty_name: str = "Counterparty LLC",
    deal_impact_description: str = "Multi-year service engagement",
) -> str:
    """
    Generate a formatted cross-reference prompt for conflict detection.

    Args:
        contract_1_name: Name/title of first contract
        contract_1_id: Unique ID of first contract
        contract_1_type: Type (msa, sow, nda, etc.)
        contract_1_pages: Number of pages
        contract_1_clauses: Formatted extracted clauses
        contract_2_name: Name/title of second contract
        contract_2_id: Unique ID of second contract
        contract_2_type: Type (msa, sow, nda, etc.)
        contract_2_pages: Number of pages
        contract_2_clauses: Formatted extracted clauses
        deal_type: Type of deal (m_and_a, lending, vendor, etc.)
        target_company: Name of target company
        counterparty_name: Name of counterparty
        deal_impact_description: Description of expected deal impact

    Returns:
        Formatted prompt string ready for LLM API call
    """
    # Sanitize user-controlled clause text before injection into prompt
    sanitized_clauses_1 = sanitize_prompt_input(contract_1_clauses)
    sanitized_clauses_2 = sanitize_prompt_input(contract_2_clauses)

    return COMPARISON_PROMPT.format(
        contract_1_name=contract_1_name,
        contract_1_id=contract_1_id,
        contract_1_type=contract_1_type,
        contract_1_pages=contract_1_pages,
        contract_1_clauses=sanitized_clauses_1,
        contract_2_name=contract_2_name,
        contract_2_id=contract_2_id,
        contract_2_type=contract_2_type,
        contract_2_pages=contract_2_pages,
        contract_2_clauses=sanitized_clauses_2,
        deal_type=deal_type,
        target_company=target_company,
        counterparty_name=counterparty_name,
        deal_impact_description=deal_impact_description,
    )
