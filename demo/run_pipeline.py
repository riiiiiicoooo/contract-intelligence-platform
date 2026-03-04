#!/usr/bin/env python3
"""
Demo Pipeline: Contract Intelligence Platform

Demonstrates the complete contract analysis pipeline:
1. Document ingestion (read sample contract text)
2. Classification (identify contract type)
3. Clause extraction (with pre-computed mock results)
4. Risk scoring (evaluate clause risks)
5. Cross-reference checking (identify conflicts)
6. Output risk matrix summary

Usage:
    python demo/run_pipeline.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Import workflow from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestration.analysis_workflow import (
    ContractAnalysisWorkflow,
    AnalysisState,
    ProcessingStatus,
    RiskLevel,
    ReviewStatus,
)


# ============================================================================
# SAMPLE CONTRACTS
# ============================================================================

SAMPLE_CONTRACT_1 = """
MASTER SERVICE AGREEMENT

This Master Service Agreement ("Agreement") is entered into effective March 1, 2024 ("Effective Date"),
between Acme Corporation, a Delaware corporation ("Client"), and Target Industries LLC, a New York
limited liability company ("Service Provider").

RECITALS

WHEREAS, Service Provider provides professional consulting and software development services;

WHEREAS, Client desires to engage Service Provider to provide services under this Agreement;

NOW, THEREFORE, in consideration of the mutual covenants:

SECTION 1: SERVICES
Service Provider shall provide consulting, architecture, and software development services as
detailed in Statements of Work ("SOWs") executed under this Agreement.

SECTION 3: PAYMENT TERMS
3.2 Invoices shall be due net thirty (30) days from receipt. Late payments accrue interest at
1.5% per month or the maximum lawful rate.

SECTION 5: TERMINATION
5.1 Either party may terminate this Agreement for convenience upon thirty (30) days written notice.
Upon termination, Client shall pay for all services through the termination date.

SECTION 8: ASSIGNMENT AND CHANGE OF CONTROL
Neither party may assign this Agreement without the other's prior written consent, except for
assignments to affiliates. In the event of a Change of Control of either party (meaning acquisition
of >50% voting securities, merger, or sale of substantially all assets), the non-changing party
may terminate this Agreement upon sixty (60) days written notice. Notwithstanding the foregoing,
a Change of Control shall not include acquisitions by employee stock plans or reorganizations
among entities under common control.

SECTION 10: LIMITATION OF LIABILITY
Neither party's aggregate liability shall exceed fees paid in the twelve (12) months preceding
the claim, except for: (a) indemnification obligations; (b) breach of confidentiality;
(c) gross negligence or willful misconduct.

SECTION 11: INDEMNIFICATION
Each party shall indemnify the other from third-party IP infringement claims, subject to
liability limitations in Section 10.

IN WITNESS WHEREOF, the parties execute this Agreement.
"""

SAMPLE_CONTRACT_2 = """
VENDOR SERVICES AGREEMENT

This Vendor Services Agreement ("Agreement") is entered into effective June 1, 2023 ("Effective Date"),
between Acme Corporation, a Delaware corporation ("Client"), and CloudTech Solutions Inc., a California
corporation ("Vendor").

This Agreement provides IT infrastructure services including cloud hosting, security monitoring, and
technical support.

TERM AND RENEWAL
This Agreement shall automatically renew for successive one-year terms unless either party provides
written notice of non-renewal at least one hundred twenty (120) days prior to expiration. Either party
may terminate for material breach upon thirty (30) days notice after opportunity to cure.

FEES AND PRICE ESCALATION
Base annual fee: $500,000. Vendor fees shall increase by 3% annually on each anniversary date unless
Client provides written objection within thirty (30) days of invoice.

CHANGE OF CONTROL
If Client undergoes a Change of Control, Client must notify Vendor within thirty (30) days. Vendor
may terminate this Agreement upon thirty (30) days notice, in which case final invoice shall include
termination fees equal to three (3) months of remaining annual fees.

LIMITATION OF LIABILITY
Neither party's liability shall exceed the total fees paid in the twelve (12) months preceding the claim.
This cap does not apply to indemnification obligations or breaches of confidentiality.

ASSIGNMENT
Client may not assign this Agreement without Vendor's prior written consent, except to an acquirer in
connection with a Change of Control, subject to Vendor's termination right above.
"""


# ============================================================================
# DEMO FUNCTIONS
# ============================================================================

def load_sample_contracts():
    """Load sample contracts from demo directory or use hardcoded samples."""
    contracts_dir = Path(__file__).parent / "sample_contracts"

    if contracts_dir.exists():
        # Try to load from files
        files = list(contracts_dir.glob("*.txt"))
        if len(files) >= 2:
            with open(files[0], "r") as f:
                contract_1 = f.read()
            with open(files[1], "r") as f:
                contract_2 = f.read()
            return contract_1, contract_2

    # Fallback to hardcoded samples
    return SAMPLE_CONTRACT_1, SAMPLE_CONTRACT_2


def run_single_contract_analysis(contract_text: str, contract_id: str):
    """
    Run full analysis pipeline on a single contract.

    Returns:
        AnalysisState: Final state with all analysis complete
    """
    print(f"\n{'='*80}")
    print(f"Processing Contract: {contract_id}")
    print(f"{'='*80}")

    # Initialize workflow
    workflow = ContractAnalysisWorkflow()

    # Create initial state
    state = AnalysisState(
        document_id=contract_id,
        deal_id="deal_demo_001",
        tenant_id="tenant_demo_001",
        raw_text=contract_text,
    )

    # Run pipeline
    print("\n[Stage 1/5] Document Classification...")
    state.processing_status = ProcessingStatus.CLASSIFYING

    print("\n[Stage 2/5] Clause Extraction...")
    state.processing_status = ProcessingStatus.EXTRACTING

    print("\n[Stage 3/5] Risk Scoring...")
    state.processing_status = ProcessingStatus.SCORING

    print("\n[Stage 4/5] Cross-Reference Check...")
    state.processing_status = ProcessingStatus.CROSS_REFERENCING

    print("\n[Stage 5/5] Human Review Routing...")
    state.processing_status = ProcessingStatus.ROUTING_REVIEW

    # Run the complete workflow
    final_state = workflow.run(state)

    return final_state


def print_analysis_summary(state: AnalysisState):
    """Pretty-print analysis results."""
    print(f"\n{'─'*80}")
    print(f"ANALYSIS RESULTS FOR: {state.document_id}")
    print(f"{'─'*80}")

    print(f"\nContract Classification:")
    if state.classification:
        print(f"  Type: {state.classification.contract_type}")
        print(f"  Parties: {', '.join(state.classification.party_names)}")
        print(f"  Effective Date: {state.classification.effective_date}")
        print(f"  Expiration Date: {state.classification.expiration_date}")
        print(f"  Governing Law: {state.classification.governing_law}")
        print(f"  Confidence: {state.classification.confidence:.1%}")

    print(f"\nClauses Extracted: {len(state.extracted_clauses)}")
    for clause in state.extracted_clauses:
        risk_indicator = "🔴" if clause.risk_level == "critical" else "🟠" if clause.risk_level == "high" else "🟡" if clause.risk_level == "medium" else "🟢"
        print(
            f"  {risk_indicator} [{clause.clause_type}] "
            f"Confidence: {clause.confidence:.0%} | "
            f"Risk: {clause.risk_level.upper()} ({clause.risk_score:.0f}) | "
            f"Status: {clause.review_status.value}"
        )
        print(f"      {clause.extracted_text[:80]}...")

    print(f"\nRisk Assessment:")
    critical = [c for c in state.extracted_clauses if c.risk_level == "critical"]
    high = [c for c in state.extracted_clauses if c.risk_level == "high"]
    medium = [c for c in state.extracted_clauses if c.risk_level == "medium"]
    low = [c for c in state.extracted_clauses if c.risk_level == "low"]

    print(f"  Critical: {len(critical)}")
    print(f"  High: {len(high)}")
    print(f"  Medium: {len(medium)}")
    print(f"  Low: {len(low)}")

    print(f"\nRisk Flags: {len(state.risk_flags)}")
    for flag in state.risk_flags:
        print(f"  [{flag.severity.upper()}] {flag.flag_type}: {flag.description}")

    print(f"\nHuman Review Routing:")
    print(f"  Requires Review: {state.requires_review}")
    if state.requires_review:
        print(f"  Reason: {state.review_reason}")
        print(f"  Low-Confidence Clauses: {len(state.low_confidence_clauses)}")

    print(f"\nProcessing Status: {state.processing_status.value}")
    if state.error_message:
        print(f"  ERROR: {state.error_message}")
    else:
        processing_time = (
            (state.processing_end_time - state.processing_start_time).total_seconds()
            if state.processing_end_time and state.processing_start_time
            else 0
        )
        print(f"  Processing Time: {processing_time:.2f}s")


def generate_risk_matrix(state1: AnalysisState, state2: AnalysisState):
    """Generate risk matrix summary across both contracts."""
    print(f"\n{'='*80}")
    print(f"DEAL RISK MATRIX SUMMARY")
    print(f"{'='*80}")

    all_clauses = state1.extracted_clauses + state2.extracted_clauses
    all_flags = state1.risk_flags + state2.risk_flags

    # Aggregate by risk level
    risk_breakdown = {
        "critical": len([c for c in all_clauses if c.risk_level == "critical"]),
        "high": len([c for c in all_clauses if c.risk_level == "high"]),
        "medium": len([c for c in all_clauses if c.risk_level == "medium"]),
        "low": len([c for c in all_clauses if c.risk_level == "low"]),
    }

    print(f"\nTotal Clauses Extracted: {len(all_clauses)}")
    print(f"\nRisk Distribution:")
    print(f"  🔴 Critical: {risk_breakdown['critical']} ({risk_breakdown['critical']/len(all_clauses)*100:.0f}%)")
    print(f"  🟠 High:     {risk_breakdown['high']} ({risk_breakdown['high']/len(all_clauses)*100:.0f}%)")
    print(f"  🟡 Medium:   {risk_breakdown['medium']} ({risk_breakdown['medium']/len(all_clauses)*100:.0f}%)")
    print(f"  🟢 Low:      {risk_breakdown['low']} ({risk_breakdown['low']/len(all_clauses)*100:.0f}%)")

    print(f"\nTop Risk Flags (by severity):")
    sorted_flags = sorted(all_flags, key=lambda f: ["critical", "high", "warning", "info"].index(f.severity))
    for flag in sorted_flags[:5]:
        print(f"  [{flag.severity.upper()}] {flag.flag_type}")
        print(f"      {flag.description}")
        print(f"      → {flag.recommendation}")

    # Confidence analysis
    avg_confidence = sum(c.confidence for c in all_clauses) / len(all_clauses)
    low_confidence = [c for c in all_clauses if c.confidence < 0.85]

    print(f"\nConfidence Analysis:")
    print(f"  Average Confidence: {avg_confidence:.1%}")
    print(f"  Low-Confidence (<85%): {len(low_confidence)}")
    print(f"  Requiring Review: {len([c for c in all_clauses if c.review_status == ReviewStatus.PENDING_REVIEW])}")

    print(f"\nClause Type Distribution:")
    clause_types = {}
    for clause in all_clauses:
        clause_types[clause.clause_type] = clause_types.get(clause.clause_type, 0) + 1

    for clause_type, count in sorted(clause_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  {clause_type}: {count}")

    # Summary recommendation
    critical_count = risk_breakdown["critical"]
    high_count = risk_breakdown["high"]

    print(f"\n{'─'*80}")
    if critical_count >= 2:
        print(f"🔴 DEAL RISK: CRITICAL")
        print(f"   {critical_count} critical-risk clauses must be negotiated before deal close")
    elif high_count >= 5 or critical_count > 0:
        print(f"🟠 DEAL RISK: HIGH")
        print(f"   {critical_count} critical and {high_count} high-risk items require attention")
    else:
        print(f"🟡 DEAL RISK: MODERATE")
        print(f"   Typical market risk profile for M&A transaction")


def export_json_report(state1: AnalysisState, state2: AnalysisState, output_file: str):
    """Export analysis results to JSON."""
    report = {
        "generated_at": datetime.utcnow().isoformat(),
        "contracts": [
            {
                "document_id": state1.document_id,
                "processing_status": state1.processing_status.value,
                "classification": {
                    "contract_type": state1.classification.contract_type if state1.classification else None,
                    "parties": state1.classification.party_names if state1.classification else [],
                    "governing_law": state1.classification.governing_law if state1.classification else None,
                } if state1.classification else None,
                "clauses_count": len(state1.extracted_clauses),
                "risk_summary": {
                    "critical": len([c for c in state1.extracted_clauses if c.risk_level == "critical"]),
                    "high": len([c for c in state1.extracted_clauses if c.risk_level == "high"]),
                    "medium": len([c for c in state1.extracted_clauses if c.risk_level == "medium"]),
                    "low": len([c for c in state1.extracted_clauses if c.risk_level == "low"]),
                },
                "clauses": [
                    {
                        "id": c.id,
                        "type": c.clause_type,
                        "confidence": c.confidence,
                        "risk_level": c.risk_level.value,
                        "risk_score": c.risk_score,
                        "review_status": c.review_status.value,
                    }
                    for c in state1.extracted_clauses
                ],
                "risk_flags": [
                    {
                        "flag_type": f.flag_type,
                        "severity": f.severity.value,
                        "description": f.description,
                        "recommendation": f.recommendation,
                    }
                    for f in state1.risk_flags
                ],
            },
            {
                "document_id": state2.document_id,
                "processing_status": state2.processing_status.value,
                "classification": {
                    "contract_type": state2.classification.contract_type if state2.classification else None,
                    "parties": state2.classification.party_names if state2.classification else [],
                    "governing_law": state2.classification.governing_law if state2.classification else None,
                } if state2.classification else None,
                "clauses_count": len(state2.extracted_clauses),
                "risk_summary": {
                    "critical": len([c for c in state2.extracted_clauses if c.risk_level == "critical"]),
                    "high": len([c for c in state2.extracted_clauses if c.risk_level == "high"]),
                    "medium": len([c for c in state2.extracted_clauses if c.risk_level == "medium"]),
                    "low": len([c for c in state2.extracted_clauses if c.risk_level == "low"]),
                },
                "clauses": [
                    {
                        "id": c.id,
                        "type": c.clause_type,
                        "confidence": c.confidence,
                        "risk_level": c.risk_level.value,
                        "risk_score": c.risk_score,
                        "review_status": c.review_status.value,
                    }
                    for c in state2.extracted_clauses
                ],
                "risk_flags": [
                    {
                        "flag_type": f.flag_type,
                        "severity": f.severity.value,
                        "description": f.description,
                        "recommendation": f.recommendation,
                    }
                    for f in state2.risk_flags
                ],
            },
        ],
    }

    with open(output_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n✓ Report exported to {output_file}")


def main():
    """Main demo execution."""
    print("\n" + "="*80)
    print("CONTRACT INTELLIGENCE PLATFORM - DEMO PIPELINE")
    print("="*80)
    print("\nThis demo processes 2 sample contracts through the complete analysis pipeline:")
    print("1. Classification")
    print("2. Clause Extraction")
    print("3. Risk Scoring")
    print("4. Cross-Reference Checking")
    print("5. Human Review Routing")

    # Load sample contracts
    print("\nLoading sample contracts...")
    contract_1, contract_2 = load_sample_contracts()

    # Process contract 1
    state_1 = run_single_contract_analysis(contract_1, "contract_msa_demo")
    print_analysis_summary(state_1)

    # Process contract 2
    state_2 = run_single_contract_analysis(contract_2, "contract_vendor_demo")
    print_analysis_summary(state_2)

    # Generate risk matrix
    generate_risk_matrix(state_1, state_2)

    # Export JSON report
    output_file = "demo_analysis_report.json"
    export_json_report(state_1, state_2, output_file)

    print(f"\n{'='*80}")
    print("DEMO COMPLETE")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
