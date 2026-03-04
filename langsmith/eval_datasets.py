"""
LangSmith Evaluation Datasets for Contract Intelligence Platform

Defines test datasets and expected outputs for:
- Clause extraction accuracy (F1 >= 0.94)
- Risk flag precision (>= 0.90)
- Hallucination detection
- Cross-reference conflict detection (recall >= 0.85)
"""

import json
from typing import List, Dict, Any
from dataclasses import dataclass, asdict


# ============================================================================
# Sample Test Cases
# ============================================================================

@dataclass
class ClauseExtractionExample:
    """Example for clause extraction evaluation."""
    input_text: str
    contract_type: str
    expected_clauses: List[Dict[str, Any]]
    description: str

    def to_dataset_format(self) -> Dict[str, Any]:
        """Convert to LangSmith dataset format."""
        return {
            "inputs": {
                "text": self.input_text,
                "contract_type": self.contract_type
            },
            "outputs": {
                "clauses": self.expected_clauses,
                "description": self.description
            }
        }


# Sample 1: MSA with Change of Control Clause
SAMPLE_CHANGE_OF_CONTROL_MSA = ClauseExtractionExample(
    input_text="""
    MASTER SERVICE AGREEMENT

    1. SERVICES
    Provider shall furnish the services described in Statements of Work (SOWs)
    attached hereto as Exhibits A-D.

    2. CHANGE OF CONTROL
    2.1 In the event of a Change of Control (defined as the acquisition of
    more than fifty percent (50%) of the outstanding equity interests or voting
    power of Company), all material contracts shall be subject to written
    consent of the non-controlling party within thirty (30) days of notice
    of such Change of Control. Failure to obtain consent shall constitute
    a material breach unless waived in writing.

    2.2 "Change of Control" includes: (a) any merger, consolidation, or
    reorganization; (b) sale of substantially all assets; or (c) acquisition
    of 50%+ voting control.

    3. TERMINATION
    Either party may terminate this Agreement for convenience with ninety (90)
    days written notice...
    """,
    contract_type="msa",
    expected_clauses=[
        {
            "clause_type": "change_of_control",
            "extracted_text": "In the event of a Change of Control (defined as the acquisition of more than fifty percent (50%) of the outstanding equity interests or voting power of Company), all material contracts shall be subject to written consent of the non-controlling party within thirty (30) days of notice of such Change of Control.",
            "page_number": 1,
            "section_reference": "Section 2.1",
            "risk_level": "high",
            "confidence": 0.98,
            "is_standard": False,
            "deviation_description": "30-day consent requirement is aggressive; market standard is 60+ days"
        },
        {
            "clause_type": "change_of_control_definition",
            "extracted_text": "Change of Control includes: (a) any merger, consolidation, or reorganization; (b) sale of substantially all assets; or (c) acquisition of 50%+ voting control.",
            "page_number": 1,
            "section_reference": "Section 2.2",
            "risk_level": "medium",
            "confidence": 0.96,
            "is_standard": True
        },
        {
            "clause_type": "termination_convenience",
            "extracted_text": "Either party may terminate this Agreement for convenience with ninety (90) days written notice",
            "page_number": 1,
            "section_reference": "Section 3",
            "risk_level": "low",
            "confidence": 0.94,
            "is_standard": True
        }
    ],
    description="MSA with non-standard change of control consent requirement"
)


# Sample 2: NDA with IP Assignment
SAMPLE_IP_ASSIGNMENT_NDA = ClauseExtractionExample(
    input_text="""
    NON-DISCLOSURE AGREEMENT

    1. CONFIDENTIAL INFORMATION
    "Confidential Information" means all non-public, proprietary information
    disclosed by Disclosing Party to Receiving Party, including technical data,
    business plans, financial information, and trade secrets.

    2. INTELLECTUAL PROPERTY ASSIGNMENT
    2.1 All Intellectual Property (IP), including patents, copyrights, trade
    secrets, and inventions, created, developed, or improved by Receiving Party
    in the course of performing services shall be the sole and exclusive property
    of Disclosing Party.

    2.2 Receiving Party hereby assigns all right, title, and interest in any
    IP to Disclosing Party, including moral rights and rights of attribution.

    2.3 Receiving Party shall execute all documents reasonably requested to
    perfect Disclosing Party's ownership.

    3. RETURN OF MATERIALS
    Upon termination, Receiving Party shall promptly return or certify
    destruction of all Confidential Information and materials...
    """,
    contract_type="nda",
    expected_clauses=[
        {
            "clause_type": "ip_assignment",
            "extracted_text": "All Intellectual Property (IP), including patents, copyrights, trade secrets, and inventions, created, developed, or improved by Receiving Party in the course of performing services shall be the sole and exclusive property of Disclosing Party.",
            "page_number": 1,
            "section_reference": "Section 2.1",
            "risk_level": "critical",
            "confidence": 0.97,
            "is_standard": False,
            "deviation_description": "Extremely broad IP assignment; covers all improvements and is one-way (only to Disclosing Party)"
        },
        {
            "clause_type": "moral_rights_waiver",
            "extracted_text": "Receiving Party hereby assigns all right, title, and interest in any IP to Disclosing Party, including moral rights and rights of attribution.",
            "page_number": 1,
            "section_reference": "Section 2.2",
            "risk_level": "critical",
            "confidence": 0.95,
            "is_standard": False,
            "deviation_description": "Assignment of moral rights is non-standard and may be unenforceable in some jurisdictions"
        },
        {
            "clause_type": "return_of_materials",
            "extracted_text": "Upon termination, Receiving Party shall promptly return or certify destruction of all Confidential Information and materials",
            "page_number": 1,
            "section_reference": "Section 3",
            "risk_level": "medium",
            "confidence": 0.92,
            "is_standard": True
        }
    ],
    description="NDA with extremely broad and one-way IP assignment"
)


# Sample 3: Amendment to Existing Contract
SAMPLE_AMENDMENT_TERMINATION = ClauseExtractionExample(
    input_text="""
    AMENDMENT NO. 1 TO VENDOR SERVICES AGREEMENT

    WHEREAS, Parties entered into that certain Vendor Services Agreement
    dated January 1, 2023 (the "Agreement");

    WHEREAS, Parties desire to amend Section 5 (Termination) as follows:

    1. AMENDMENT TO SECTION 5 (TERMINATION)

    Section 5.1 of the Agreement is hereby deleted in its entirety and
    replaced with the following:

    "5.1 TERMINATION FOR CAUSE
    Either party may terminate this Agreement immediately upon written notice
    if the other party materially breaches any provision hereof and fails to
    cure such breach within fifteen (15) days after receiving written notice
    specifying the breach in reasonable detail.

    5.2 TERMINATION FOR CONVENIENCE
    Client may terminate this Agreement for any reason with thirty (30) days
    written notice. Vendor may only terminate for convenience with ninety (90)
    days written notice. All accrued fees shall be due upon termination."

    2. REMAINING TERMS
    Except as expressly amended hereby, all terms and conditions of the
    Agreement remain in full force and effect...
    """,
    contract_type="amendment",
    expected_clauses=[
        {
            "clause_type": "termination_for_cause",
            "extracted_text": "Either party may terminate this Agreement immediately upon written notice if the other party materially breaches any provision hereof and fails to cure such breach within fifteen (15) days after receiving written notice",
            "page_number": 1,
            "section_reference": "Section 5.1",
            "risk_level": "medium",
            "confidence": 0.93,
            "is_standard": False,
            "deviation_description": "15-day cure period is short; standard is 30 days"
        },
        {
            "clause_type": "termination_convenience",
            "extracted_text": "Client may terminate this Agreement for any reason with thirty (30) days written notice. Vendor may only terminate for convenience with ninety (90) days written notice.",
            "page_number": 1,
            "section_reference": "Section 5.2",
            "risk_level": "high",
            "confidence": 0.96,
            "is_standard": False,
            "deviation_description": "Asymmetric termination: Client has 30-day notice while Vendor requires 90 days. Unfavorable to Vendor."
        },
        {
            "clause_type": "amendment_scope",
            "extracted_text": "Section 5.1 of the Agreement is hereby deleted in its entirety and replaced with the following",
            "page_number": 1,
            "section_reference": "Section 1",
            "risk_level": "low",
            "confidence": 0.97,
            "is_standard": True
        }
    ],
    description="Amendment introducing asymmetric termination rights"
)


# ============================================================================
# Cross-Reference Test Cases (Deal-Level Analysis)
# ============================================================================

@dataclass
class CrossReferenceExample:
    """Example for cross-reference analysis evaluation."""
    deal_id: str
    contracts: List[Dict[str, Any]]
    expected_conflicts: List[Dict[str, Any]]
    expected_inconsistencies: List[Dict[str, Any]]
    description: str

    def to_dataset_format(self) -> Dict[str, Any]:
        """Convert to LangSmith dataset format."""
        return {
            "inputs": {
                "deal_id": self.deal_id,
                "contracts": self.contracts
            },
            "outputs": {
                "conflicts": self.expected_conflicts,
                "inconsistencies": self.expected_inconsistencies,
                "description": self.description
            }
        }


# Sample Cross-Reference Case: Conflicting Payment Terms
SAMPLE_PAYMENT_CONFLICT = CrossReferenceExample(
    deal_id="deal-2025-acme",
    contracts=[
        {
            "contract_id": "msa-001",
            "filename": "ACME_MSA_Final.pdf",
            "clause": "Net 30 payment terms. Invoices due within 30 days of receipt."
        },
        {
            "contract_id": "sow-001",
            "filename": "ACME_SOW_Phase1.pdf",
            "clause": "Net 15 payment terms. Invoices due within 15 days of month-end."
        },
        {
            "contract_id": "nda-001",
            "filename": "ACME_NDA.pdf",
            "clause": "No payment obligations. This is a mutual non-disclosure agreement."
        }
    ],
    expected_conflicts=[
        {
            "conflict_type": "payment_terms",
            "severity": "high",
            "affected_contracts": ["msa-001", "sow-001"],
            "issue": "MSA specifies Net 30 terms while SOW specifies Net 15. Unclear which takes precedence.",
            "recommendation": "Clarify payment terms hierarchy. Typically SOW overrides MSA for specific statements of work."
        }
    ],
    expected_inconsistencies=[
        {
            "type": "payment_due_date_basis",
            "contracts": ["msa-001", "sow-001"],
            "msa_language": "within 30 days of receipt",
            "sow_language": "within 15 days of month-end",
            "issue": "Different invoice due date calculations may create timing confusion"
        }
    ],
    description="Payment terms conflict between MSA and SOW"
)


# ============================================================================
# Risk Flag Accuracy Test Cases
# ============================================================================

@dataclass
class RiskFlagExample:
    """Example for risk flag accuracy evaluation."""
    contract_id: str
    extracted_clauses: List[Dict[str, Any]]
    expected_risk_flags: List[Dict[str, Any]]
    description: str

    def to_dataset_format(self) -> Dict[str, Any]:
        """Convert to LangSmith dataset format."""
        return {
            "inputs": {
                "contract_id": self.contract_id,
                "clauses": self.extracted_clauses
            },
            "outputs": {
                "risk_flags": self.expected_risk_flags,
                "description": self.description
            }
        }


# Sample Risk Flags
SAMPLE_RISK_FLAGS = RiskFlagExample(
    contract_id="contract-critical-terms",
    extracted_clauses=[
        {
            "clause_type": "liability_cap",
            "extracted_text": "Neither party shall be liable for any indirect, incidental, special, consequential, or punitive damages, even if advised of the possibility thereof.",
            "risk_level": None
        },
        {
            "clause_type": "liability_exclusion",
            "extracted_text": "Company's total liability under this Agreement shall not exceed the fees paid in the prior 12 months, with no cap.",
            "risk_level": None
        },
        {
            "clause_type": "indemnification",
            "extracted_text": "Company indemnifies Vendor against all claims arising from Company's use of the Services.",
            "risk_level": None
        }
    ],
    expected_risk_flags=[
        {
            "flag_type": "uncapped_liability",
            "severity": "critical",
            "clause_type": "liability_exclusion",
            "description": "Liability cap on Company is uncapped, creating unlimited exposure",
            "recommendation": "Negotiate mutual liability cap (typically 12-month fees)"
        },
        {
            "flag_type": "broad_indemnification",
            "severity": "high",
            "clause_type": "indemnification",
            "description": "Company indemnifies Vendor without limitation on causation",
            "recommendation": "Limit indemnification to Company's negligence or breach"
        }
    ],
    description="Critical liability and indemnification risks"
)


# ============================================================================
# Dataset Factory Functions
# ============================================================================

def create_extraction_dataset() -> List[Dict[str, Any]]:
    """Create evaluation dataset for clause extraction."""
    examples = [
        SAMPLE_CHANGE_OF_CONTROL_MSA,
        SAMPLE_IP_ASSIGNMENT_NDA,
        SAMPLE_AMENDMENT_TERMINATION
    ]
    return [ex.to_dataset_format() for ex in examples]


def create_cross_reference_dataset() -> List[Dict[str, Any]]:
    """Create evaluation dataset for cross-reference analysis."""
    examples = [
        SAMPLE_PAYMENT_CONFLICT
    ]
    return [ex.to_dataset_format() for ex in examples]


def create_risk_flags_dataset() -> List[Dict[str, Any]]:
    """Create evaluation dataset for risk flag accuracy."""
    examples = [
        SAMPLE_RISK_FLAGS
    ]
    return [ex.to_dataset_format() for ex in examples]


# ============================================================================
# Benchmark Results (Expected Performance)
# ============================================================================

BENCHMARKS = {
    "extraction": {
        "f1_score_target": 0.94,
        "precision_target": 0.93,
        "recall_target": 0.95,
        "confidence_threshold": 0.85
    },
    "risk_flags": {
        "precision_target": 0.90,
        "recall_target": 0.97,
        "critical_flags_target": 0.98
    },
    "cross_reference": {
        "conflict_detection_recall": 0.85,
        "inconsistency_detection_recall": 0.80,
        "false_positive_rate": 0.05
    },
    "hallucination": {
        "hallucination_rate_target": 0.02,  # 2% max
        "grounding_score_target": 0.98
    }
}


# ============================================================================
# Evaluation Metrics Definition
# ============================================================================

EVALUATION_METRICS = {
    "extraction_accuracy": {
        "name": "Clause Extraction F1 Score",
        "metric_type": "f1",
        "target": BENCHMARKS["extraction"]["f1_score_target"],
        "dataset": "extraction_v1"
    },
    "risk_flag_precision": {
        "name": "Risk Flag Precision",
        "metric_type": "precision",
        "target": BENCHMARKS["risk_flags"]["precision_target"],
        "dataset": "risk_flags_v1"
    },
    "hallucination_detection": {
        "name": "Hallucination Rate",
        "metric_type": "rate",
        "target": BENCHMARKS["hallucination"]["hallucination_rate_target"],
        "dataset": "extraction_v1"
    },
    "conflict_detection": {
        "name": "Cross-Reference Conflict Recall",
        "metric_type": "recall",
        "target": BENCHMARKS["cross_reference"]["conflict_detection_recall"],
        "dataset": "cross_reference_v1"
    }
}


# ============================================================================
# Dataset Export & Import
# ============================================================================

def export_datasets_to_json(filepath: str) -> None:
    """Export all datasets to JSON for manual review or import."""
    datasets = {
        "extraction": create_extraction_dataset(),
        "cross_reference": create_cross_reference_dataset(),
        "risk_flags": create_risk_flags_dataset(),
        "benchmarks": BENCHMARKS,
        "metrics": EVALUATION_METRICS
    }

    with open(filepath, "w") as f:
        json.dump(datasets, f, indent=2, default=str)

    print(f"✓ Datasets exported to {filepath}")


def import_datasets_from_json(filepath: str) -> Dict[str, Any]:
    """Import datasets from JSON file."""
    with open(filepath, "r") as f:
        return json.load(f)


if __name__ == "__main__":
    # Export sample datasets
    export_datasets_to_json("/tmp/langsmith_evaluation_datasets.json")

    # Print summary
    print("\n=== Evaluation Dataset Summary ===")
    print(f"Extraction examples: {len(create_extraction_dataset())}")
    print(f"Cross-reference examples: {len(create_cross_reference_dataset())}")
    print(f"Risk flag examples: {len(create_risk_flags_dataset())}")
    print("\nBenchmarks:")
    for metric, targets in BENCHMARKS.items():
        print(f"  {metric}: {targets}")
