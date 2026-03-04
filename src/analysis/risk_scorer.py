"""
Risk Scorer - Reference Implementation
Scores extracted clauses against playbook-defined rules and generates
AI-powered risk explanations.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PlaybookRule:
    clause_type: str
    condition: str          # e.g., "notice_period_days < 30"
    severity: str           # info, warning, critical
    message: str
    recommendation: Optional[str] = None


@dataclass
class RiskFlag:
    flag_type: str
    severity: str
    description: str
    recommendation: str
    clause_id: Optional[str] = None
    playbook_rule_id: Optional[str] = None


# Default M&A playbook rules
DEFAULT_MA_PLAYBOOK: list[PlaybookRule] = [
    PlaybookRule(
        clause_type="change_of_control",
        condition="triggers_termination_right",
        severity="critical",
        message="Change of control triggers counterparty termination right",
        recommendation="Negotiate for consent requirement instead of termination right",
    ),
    PlaybookRule(
        clause_type="change_of_control",
        condition="requires_consent",
        severity="warning",
        message="Change of control requires counterparty consent",
        recommendation="Assess likelihood of consent; consider pre-closing outreach",
    ),
    PlaybookRule(
        clause_type="limitation_of_liability",
        condition="is_uncapped",
        severity="critical",
        message="No cap on liability exposure",
        recommendation="Negotiate liability cap at contract value or annual fees",
    ),
    PlaybookRule(
        clause_type="termination_convenience",
        condition="notice_period_days < 30",
        severity="critical",
        message="Termination notice period below 30 days (market standard: 60-90 days)",
        recommendation="Negotiate minimum 60-day notice period",
    ),
    PlaybookRule(
        clause_type="termination_convenience",
        condition="notice_period_days < 60",
        severity="warning",
        message="Termination notice period below 60 days",
        recommendation="Consider extending to 90 days",
    ),
    PlaybookRule(
        clause_type="renewal_auto_renewal",
        condition="auto_renews AND cancellation_window_days < 30",
        severity="warning",
        message="Auto-renewal with narrow cancellation window",
        recommendation="Flag for buyer - ensure calendar reminder for cancellation deadline",
    ),
    PlaybookRule(
        clause_type="exclusivity",
        condition="is_exclusive AND term_years > 3",
        severity="high",
        message="Long-term exclusivity (>3 years) limits buyer's operational flexibility",
        recommendation="Evaluate if exclusivity is core to value or a constraint",
    ),
    PlaybookRule(
        clause_type="non_compete",
        condition="scope_is_broad AND duration_months > 24",
        severity="high",
        message="Broad non-compete exceeding 24 months may be unenforceable and operationally limiting",
        recommendation="Assess enforceability by jurisdiction; narrow scope if possible",
    ),
    PlaybookRule(
        clause_type="indemnification",
        condition="is_unilateral_against_target",
        severity="warning",
        message="Indemnification obligation is one-sided against the target company",
        recommendation="Evaluate total indemnification exposure across all contracts",
    ),
    PlaybookRule(
        clause_type="assignment",
        condition="requires_consent_no_exceptions",
        severity="critical",
        message="Assignment requires consent with no carve-out for M&A transactions",
        recommendation="Critical for deal execution - must obtain consent or negotiate carve-out pre-close",
    ),
    PlaybookRule(
        clause_type="ip_ownership",
        condition="broad_assignment_to_counterparty",
        severity="high",
        message="Broad IP assignment to counterparty may transfer valuable work product",
        recommendation="Review IP assignment scope; ensure target retains key IP rights",
    ),
    PlaybookRule(
        clause_type="governing_law",
        condition="unfavorable_jurisdiction",
        severity="warning",
        message="Contract governed by jurisdiction unfavorable to buyer",
        recommendation="Assess litigation risk and enforceability implications",
    ),
]

# Expected clause types per contract type (for missing clause detection)
EXPECTED_CLAUSES = {
    "msa": [
        "termination_convenience", "termination_cause", "indemnification",
        "limitation_of_liability", "confidentiality", "governing_law",
        "assignment", "notice_requirements", "force_majeure",
        "payment_terms", "ip_ownership", "warranty_representations",
    ],
    "nda": [
        "confidentiality", "non_disclosure", "termination_convenience",
        "governing_law", "notice_requirements", "survival_clauses",
    ],
    "employment": [
        "termination_cause", "non_compete", "confidentiality",
        "ip_ownership", "governing_law", "notice_requirements",
    ],
    "lease": [
        "payment_terms", "termination_convenience", "renewal_auto_renewal",
        "assignment", "governing_law", "notice_requirements",
        "insurance_requirements", "indemnification",
    ],
}


class RiskScorer:
    """
    Scores extracted clauses against playbook rules and detects missing clauses.

    Two-pass scoring:
    1. Rule-based: match clauses against playbook conditions
    2. AI-enhanced: generate detailed risk explanations using Claude

    Missing clause detection:
    - Compare extracted clause types against expected types for contract type
    - Flag any expected clause that wasn't found
    """

    def __init__(self, playbook: list[PlaybookRule] = None):
        self.playbook = playbook or DEFAULT_MA_PLAYBOOK

    def score_clauses(self, clauses: list, contract_type: str = "msa") -> list[RiskFlag]:
        """
        Score all extracted clauses and return risk flags.
        Also checks for missing expected clauses.
        """
        flags = []

        # Pass 1: Score each extracted clause against playbook rules
        for clause in clauses:
            clause_flags = self._evaluate_against_playbook(clause)
            flags.extend(clause_flags)

        # Pass 2: Check for missing clauses
        missing_flags = self._detect_missing_clauses(clauses, contract_type)
        flags.extend(missing_flags)

        return flags

    def _evaluate_against_playbook(self, clause) -> list[RiskFlag]:
        """Evaluate a single clause against all applicable playbook rules."""
        flags = []

        for rule in self.playbook:
            if rule.clause_type != clause.clause_type:
                continue

            # In production: evaluate rule.condition against clause attributes
            # using a lightweight expression evaluator
            #
            # Example conditions:
            #   "notice_period_days < 30"  -> parse clause text to extract days
            #   "is_uncapped"             -> check if liability clause has no cap
            #   "requires_consent"        -> check if consent language present
            #
            # For reference implementation, we flag based on the clause's
            # existing risk_level from the extraction step

            if self._condition_matches(rule, clause):
                flags.append(
                    RiskFlag(
                        flag_type=self._determine_flag_type(clause.clause_type),
                        severity=rule.severity,
                        description=rule.message,
                        recommendation=rule.recommendation or "",
                        clause_id=getattr(clause, "id", None),
                    )
                )

        return flags

    def _condition_matches(self, rule: PlaybookRule, clause) -> bool:
        """
        Evaluate whether a playbook rule condition matches a clause.

        In production, this would parse the condition string and evaluate
        against extracted clause attributes. For reference, we do a
        simplified check.
        """
        # Simplified: if clause risk_level is high or critical,
        # and the rule targets this clause type, flag it
        if hasattr(clause, "risk_level"):
            if clause.risk_level in ("high", "critical"):
                return True
        return False

    def _detect_missing_clauses(
        self, clauses: list, contract_type: str
    ) -> list[RiskFlag]:
        """
        Check if any expected clause types are missing from the contract.
        Missing clauses are a risk signal (e.g., MSA without limitation of liability).
        """
        expected = EXPECTED_CLAUSES.get(contract_type, [])
        extracted_types = {c.clause_type for c in clauses}

        flags = []
        for expected_type in expected:
            if expected_type not in extracted_types:
                flags.append(
                    RiskFlag(
                        flag_type="missing_clause",
                        severity="warning",
                        description=f"Expected clause type '{expected_type}' not found in this {contract_type.upper()}",
                        recommendation=f"Verify whether {expected_type} is intentionally omitted or covered in a separate agreement",
                    )
                )

        return flags

    def _determine_flag_type(self, clause_type: str) -> str:
        """Map clause type to risk flag type."""
        flag_type_map = {
            "change_of_control": "change_of_control_trigger",
            "limitation_of_liability": "uncapped_liability",
            "termination_convenience": "short_notice_period",
            "renewal_auto_renewal": "auto_renewal_trap",
            "assignment": "assignment_restriction",
            "ip_ownership": "broad_ip_assignment",
            "indemnification": "weak_indemnification",
            "governing_law": "unfavorable_governing_law",
            "exclusivity": "non_standard_term",
            "non_compete": "non_standard_term",
        }
        return flag_type_map.get(clause_type, "non_standard_term")

    def aggregate_deal_risk(self, all_flags: list[RiskFlag]) -> dict:
        """
        Aggregate risk flags across all contracts in a deal.
        Used for the deal-level risk dashboard.
        """
        summary = {
            "total_flags": len(all_flags),
            "by_severity": {"critical": 0, "warning": 0, "info": 0},
            "by_type": {},
            "top_risks": [],
        }

        for flag in all_flags:
            summary["by_severity"][flag.severity] = (
                summary["by_severity"].get(flag.severity, 0) + 1
            )
            summary["by_type"][flag.flag_type] = (
                summary["by_type"].get(flag.flag_type, 0) + 1
            )

        # Top risks sorted by count
        summary["top_risks"] = sorted(
            [{"type": k, "count": v} for k, v in summary["by_type"].items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:10]

        return summary
