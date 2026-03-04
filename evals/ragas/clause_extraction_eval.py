"""
RAGAS Evaluation Framework for Contract Clause Extraction
Evaluates the accuracy, completeness, and precision of contract clause extraction and classification.

This module measures:
- Extraction completeness: How many relevant clauses are identified
- Classification accuracy: How correctly clauses are categorized
- Risk flag precision: How accurately risk indicators are assigned
- F1 scores per clause type
"""

import json
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict

from ragas.metrics import faithfulness, answer_relevancy, context_recall
from datasets import Dataset


@dataclass
class ExtractionMetrics:
    """Metrics for clause extraction evaluation."""
    precision: float  # True positives / (True positives + False positives)
    recall: float     # True positives / (True positives + False negatives)
    f1_score: float   # Harmonic mean of precision and recall
    accuracy: float   # Correct classifications / Total items


class ContractExtractionEvaluator:
    """Evaluates contract clause extraction pipeline."""
    
    def __init__(self):
        """Initialize the contract extraction evaluator."""
        self.test_cases = self._load_test_cases()
        self.results = {}
        self.clause_types = [
            'change_of_control',
            'assignment',
            'termination',
            'indemnification',
            'confidentiality',
            'liability_limitation',
            'governing_law',
            'payment_terms',
            'deliverables',
            'intellectual_property'
        ]
    
    def _load_test_cases(self) -> List[Dict[str, Any]]:
        """
        Load contract test cases with extraction expectations.
        
        Returns:
            List of test case dictionaries
        """
        return [
            {
                "test_id": "EXTRACT_001",
                "contract_type": "Service Agreement",
                "excerpt": """
                This Service Agreement is entered into between Provider ("Service Provider")
                and Customer ("Client"). Service Provider shall provide software development
                services as outlined in Exhibit A. This agreement shall be governed by and
                construed in accordance with the laws of the State of Delaware, without regard
                to conflicts of law principles.
                """,
                "expected_clauses": {
                    "governing_law": {
                        "found": True,
                        "text": "governed by and construed in accordance with the laws of the State of Delaware",
                        "risk_level": "low"
                    },
                    "deliverables": {
                        "found": True,
                        "text": "software development services as outlined in Exhibit A",
                        "risk_level": "medium"
                    }
                },
                "expected_risk_flags": ["incomplete_exhibit_reference"],
                "challenge": "References external exhibit requiring cross-reference"
            },
            {
                "test_id": "EXTRACT_002",
                "contract_type": "NDA",
                "excerpt": """
                Confidential Information means all non-public information disclosed by one party
                to another regarding its business, technology, or operations. The receiving party
                agrees to maintain strict confidentiality and shall not disclose such information
                to third parties without prior written consent. This obligation shall survive
                termination of this Agreement for a period of three (3) years.
                """,
                "expected_clauses": {
                    "confidentiality": {
                        "found": True,
                        "text": "agrees to maintain strict confidentiality",
                        "risk_level": "high"
                    }
                },
                "expected_risk_flags": ["post_termination_obligations"],
                "challenge": "Contains survival clause with specific duration"
            },
            {
                "test_id": "EXTRACT_003",
                "contract_type": "Software License Agreement",
                "excerpt": """
                Licensee shall not assign, transfer, or sublicense the rights granted herein
                without the prior written consent of Licensor. Any unauthorized assignment shall
                be void. Licensor may terminate this license immediately upon material breach.
                Licensor's total liability shall not exceed the fees paid in the twelve (12)
                months preceding the claim.
                """,
                "expected_clauses": {
                    "assignment": {
                        "found": True,
                        "text": "shall not assign, transfer, or sublicense",
                        "risk_level": "high"
                    },
                    "termination": {
                        "found": True,
                        "text": "may terminate this license immediately upon material breach",
                        "risk_level": "high"
                    },
                    "liability_limitation": {
                        "found": True,
                        "text": "total liability shall not exceed the fees paid",
                        "risk_level": "high"
                    }
                },
                "expected_risk_flags": ["asymmetric_termination_rights", "capped_liability"],
                "challenge": "Multiple related clauses requiring careful extraction"
            },
            {
                "test_id": "EXTRACT_004",
                "contract_type": "M&A Purchase Agreement",
                "excerpt": """
                This Agreement shall be governed by Delaware law. The parties acknowledge that
                this transaction may constitute a Change of Control triggering certain obligations.
                In the event of Change of Control, Third-Party Consents may be required from
                major commercial partners as listed in Schedule 2.1(b). Failure to obtain such
                consents may result in specified termination rights and indemnification claims.
                """,
                "expected_clauses": {
                    "governing_law": {
                        "found": True,
                        "text": "governed by Delaware law",
                        "risk_level": "low"
                    },
                    "change_of_control": {
                        "found": True,
                        "text": "Change of Control triggering certain obligations",
                        "risk_level": "critical"
                    },
                    "indemnification": {
                        "found": True,
                        "text": "result in specified termination rights and indemnification claims",
                        "risk_level": "high"
                    }
                },
                "expected_risk_flags": ["change_of_control_trigger", "third_party_consents_required"],
                "challenge": "Critical change of control clause with cascading obligations"
            },
            {
                "test_id": "EXTRACT_005",
                "contract_type": "Employment Agreement",
                "excerpt": """
                Employee shall not disclose proprietary information or trade secrets belonging to
                Company. All work product, inventions, and intellectual property created during
                employment shall be the exclusive property of Company. Company retains the right
                to enforce these provisions through injunctive relief. This obligation survives
                termination for a period of five (5) years.
                """,
                "expected_clauses": {
                    "intellectual_property": {
                        "found": True,
                        "text": "All work product, inventions shall be exclusive property of Company",
                        "risk_level": "high"
                    },
                    "confidentiality": {
                        "found": True,
                        "text": "shall not disclose proprietary information",
                        "risk_level": "high"
                    }
                },
                "expected_risk_flags": ["injunctive_relief_clause", "extended_survival_period"],
                "challenge": "Long-term confidentiality obligations with broad IP scope"
            },
            {
                "test_id": "EXTRACT_006",
                "contract_type": "Supplier Agreement",
                "excerpt": """
                Supplier warrants that all deliverables shall comply with specifications in
                Exhibit A and applicable law. Supplier indemnifies Buyer against all claims
                arising from defective products. Buyer's sole remedy is replacement within
                30 days of discovery. Neither party's liability shall exceed contract value.
                Supplier assumes liability for third-party claims.
                """,
                "expected_clauses": {
                    "deliverables": {
                        "found": True,
                        "text": "shall comply with specifications in Exhibit A",
                        "risk_level": "medium"
                    },
                    "indemnification": {
                        "found": True,
                        "text": "indemnifies Buyer against all claims",
                        "risk_level": "high"
                    },
                    "liability_limitation": {
                        "found": True,
                        "text": "Neither party's liability shall exceed contract value",
                        "risk_level": "medium"
                    }
                },
                "expected_risk_flags": ["limited_remedies", "asymmetric_indemnification"],
                "challenge": "Unbalanced risk allocation with time-limited remedies"
            },
            {
                "test_id": "EXTRACT_007",
                "contract_type": "Lease Agreement",
                "excerpt": """
                Tenant shall not assign or sublet this lease without Landlord consent. Payment
                is due on the first of each month. Late payments incur a 5% penalty. Landlord
                may terminate for non-payment or material breach. Tenant indemnifies Landlord
                for all damages to the premises. Security deposit of $X,000 is required.
                """,
                "expected_clauses": {
                    "assignment": {
                        "found": True,
                        "text": "shall not assign or sublet",
                        "risk_level": "medium"
                    },
                    "payment_terms": {
                        "found": True,
                        "text": "Payment is due on the first of each month. Late payments incur 5% penalty",
                        "risk_level": "medium"
                    },
                    "termination": {
                        "found": True,
                        "text": "may terminate for non-payment or material breach",
                        "risk_level": "medium"
                    }
                },
                "expected_risk_flags": ["penalty_clause", "broad_termination_rights"],
                "challenge": "Monetary penalties and asymmetric termination rights"
            },
            {
                "test_id": "EXTRACT_008",
                "contract_type": "Consulting Agreement",
                "excerpt": """
                Consultant shall provide services on an independent contractor basis. Services
                are governed by Statement of Work attached as Exhibit B. All work product shall
                remain Consultant's property unless explicitly purchased. Consultant assumes
                liability only for gross negligence. Either party may terminate with 30 days notice.
                """,
                "expected_clauses": {
                    "deliverables": {
                        "found": True,
                        "text": "governed by Statement of Work attached as Exhibit B",
                        "risk_level": "high"
                    },
                    "intellectual_property": {
                        "found": True,
                        "text": "work product shall remain Consultant's property",
                        "risk_level": "high"
                    },
                    "termination": {
                        "found": True,
                        "text": "Either party may terminate with 30 days notice",
                        "risk_level": "low"
                    }
                },
                "expected_risk_flags": ["consultant_retains_ip", "limited_liability"],
                "challenge": "Unusual IP retention by consultant rather than client"
            },
            {
                "test_id": "EXTRACT_009",
                "contract_type": "Loan Agreement",
                "excerpt": """
                Principal amount: $X. Interest rate: 5% per annum. Repayment schedule in
                Schedule A. Borrower shall maintain insurance and comply with covenants.
                Lender may accelerate upon default. Borrower indemnifies Lender for all
                third-party claims. Personal guarantee by Principal as Exhibit C.
                """,
                "expected_clauses": {
                    "payment_terms": {
                        "found": True,
                        "text": "Interest rate: 5% per annum. Repayment schedule in Schedule A",
                        "risk_level": "critical"
                    },
                    "indemnification": {
                        "found": True,
                        "text": "indemnifies Lender for all third-party claims",
                        "risk_level": "high"
                    },
                    "termination": {
                        "found": True,
                        "text": "may accelerate upon default",
                        "risk_level": "high"
                    }
                },
                "expected_risk_flags": ["personal_guarantee", "acceleration_clause"],
                "challenge": "Complex financial terms with personal guarantee"
            },
            {
                "test_id": "EXTRACT_010",
                "contract_type": "Distribution Agreement",
                "excerpt": """
                Distributor has exclusive rights to distribute Products in Territory as defined
                in Exhibit A. Supplier warrants product quality and indemnifies against IP claims.
                Distributor indemnifies Supplier against sales liability. Either party may
                terminate with 60 days notice. Governing law: New York.
                """,
                "expected_clauses": {
                    "assignment": {
                        "found": True,
                        "text": "Distributor has exclusive rights to distribute",
                        "risk_level": "high"
                    },
                    "indemnification": {
                        "found": True,
                        "text": "indemnifies against IP claims",
                        "risk_level": "high"
                    },
                    "governing_law": {
                        "found": True,
                        "text": "Governing law: New York",
                        "risk_level": "low"
                    }
                },
                "expected_risk_flags": ["exclusive_distribution_rights", "mutual_indemnification"],
                "challenge": "Mutual indemnification obligations creating potential conflicts"
            }
        ]
    
    def calculate_metrics(
        self, 
        predicted: Dict[str, Any], 
        expected: Dict[str, Any]
    ) -> ExtractionMetrics:
        """
        Calculate precision, recall, F1 score for extraction.
        
        Args:
            predicted: Predicted clause extraction results
            expected: Expected clause extraction results
            
        Returns:
            ExtractionMetrics object with calculated scores
        """
        tp = 0  # True positives
        fp = 0  # False positives
        fn = 0  # False negatives
        
        # Check each clause type
        for clause_type in expected:
            if clause_type in predicted:
                if predicted[clause_type].get('found') == expected[clause_type].get('found'):
                    tp += 1
                else:
                    fp += 1
            else:
                fn += 1
        
        # Add false positives for predicted but not expected
        for clause_type in predicted:
            if clause_type not in expected:
                fp += 1
        
        # Calculate metrics
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        # Accuracy: correct predictions / total items
        total = tp + fp + fn
        accuracy = tp / total if total > 0 else 0.0
        
        return ExtractionMetrics(
            precision=precision,
            recall=recall,
            f1_score=f1,
            accuracy=accuracy
        )
    
    def run_evaluation(self) -> Dict[str, Any]:
        """
        Run extraction evaluation across all test cases.
        
        Returns:
            Comprehensive evaluation results
        """
        print("=" * 90)
        print("CONTRACT CLAUSE EXTRACTION EVALUATION")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Test Cases: {len(self.test_cases)}")
        print("=" * 90)
        
        aggregated_results = {
            'by_clause_type': defaultdict(lambda: {'tp': 0, 'fp': 0, 'fn': 0}),
            'by_contract_type': {},
            'overall': {}
        }
        
        total_tp, total_fp, total_fn = 0, 0, 0
        
        print(f"\n{'Test ID':<15} {'Contract Type':<25} {'Clauses Found':<15} {'Risk Flags':<15} {'Status':<10}")
        print("-" * 90)
        
        for test_case in self.test_cases:
            test_id = test_case['test_id']
            contract_type = test_case['contract_type']
            expected = test_case['expected_clauses']
            
            # Simulate extraction (in real scenario, this would be actual extraction output)
            predicted = self._simulate_extraction(test_case['excerpt'], expected)
            
            # Calculate metrics
            metrics = self.calculate_metrics(predicted, expected)
            
            # Update aggregates
            contract_type_key = contract_type
            if contract_type_key not in aggregated_results['by_contract_type']:
                aggregated_results['by_contract_type'][contract_type_key] = {
                    'tests': [],
                    'avg_f1': 0.0
                }
            
            aggregated_results['by_contract_type'][contract_type_key]['tests'].append({
                'test_id': test_id,
                'f1': metrics.f1_score
            })
            
            # Count correct extractions
            num_clauses = len(expected)
            risk_flags = len(test_case['expected_risk_flags'])
            
            status = "PASS" if metrics.f1_score >= 0.85 else "WARN" if metrics.f1_score >= 0.70 else "FAIL"
            
            print(f"{test_id:<15} {contract_type:<25} {num_clauses:<15} {risk_flags:<15} {status:<10}")
            
            # Store detailed results
            self.results[test_id] = {
                'metrics': {
                    'precision': metrics.precision,
                    'recall': metrics.recall,
                    'f1_score': metrics.f1_score,
                    'accuracy': metrics.accuracy
                },
                'challenge': test_case['challenge'],
                'expected_clauses': num_clauses,
                'risk_flags': risk_flags
            }
        
        print("-" * 90)
        
        return self.results
    
    def _simulate_extraction(
        self, 
        excerpt: str, 
        expected: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Simulate clause extraction output (in real scenario, this calls extraction model).
        
        Args:
            excerpt: Contract text excerpt
            expected: Expected extraction results
            
        Returns:
            Simulated extraction results
        """
        # In production, this would call the actual extraction pipeline
        # For now, we simulate with high accuracy for demonstration
        predicted = {}
        for clause_type, clause_info in expected.items():
            # Simulate 90% accuracy
            import random
            found = random.random() < 0.9 if clause_info.get('found') else random.random() < 0.1
            predicted[clause_type] = {
                'found': found,
                'risk_level': clause_info.get('risk_level') if found else None
            }
        return predicted
    
    def print_detailed_report(self):
        """Print detailed evaluation report with per-clause-type metrics."""
        if not self.results:
            print("\nNo evaluation results. Run evaluation first.")
            return
        
        print("\n" + "=" * 90)
        print("DETAILED EXTRACTION EVALUATION REPORT")
        print("=" * 90)
        
        # Per-test results
        print("\nPer-Test Results:")
        print("-" * 90)
        print(f"{'Test ID':<15} {'Precision':<12} {'Recall':<12} {'F1 Score':<12} {'Accuracy':<12} {'Status':<10}")
        print("-" * 90)
        
        f1_scores = []
        for test_id, result in sorted(self.results.items()):
            metrics = result['metrics']
            f1 = metrics['f1_score']
            f1_scores.append(f1)
            status = "PASS" if f1 >= 0.85 else "WARN" if f1 >= 0.70 else "FAIL"
            print(f"{test_id:<15} {metrics['precision']:<12.3f} {metrics['recall']:<12.3f} "
                  f"{f1:<12.3f} {metrics['accuracy']:<12.3f} {status:<10}")
        
        print("-" * 90)
        
        # Overall statistics
        if f1_scores:
            avg_f1 = sum(f1_scores) / len(f1_scores)
            max_f1 = max(f1_scores)
            min_f1 = min(f1_scores)
            
            print(f"\nOverall Statistics:")
            print(f"  Average F1 Score: {avg_f1:.3f}")
            print(f"  Max F1 Score:     {max_f1:.3f}")
            print(f"  Min F1 Score:     {min_f1:.3f}")
            print(f"  Pass Rate:        {(sum(1 for s in f1_scores if s >= 0.85) / len(f1_scores) * 100):.1f}%")
        
        # Recommendations
        print("\nRecommendations:")
        print("-" * 90)
        
        low_performers = [(tid, r) for tid, r in self.results.items() if r['metrics']['f1_score'] < 0.70]
        
        if low_performers:
            print(f"Address low-scoring tests ({len(low_performers)}):")
            for test_id, result in low_performers:
                print(f"  • {test_id}: Challenge - {result['challenge']}")
                print(f"    Current F1: {result['metrics']['f1_score']:.3f} (target: >= 0.85)")
        else:
            print("All tests performing well! Continue monitoring edge cases.")
        
        print("\n" + "=" * 90)


def main():
    """Main evaluation execution."""
    evaluator = ContractExtractionEvaluator()
    
    print("\nInitializing contract clause extraction evaluation...")
    results = evaluator.run_evaluation()
    
    # Print detailed report
    evaluator.print_detailed_report()
    
    print("\nEvaluation complete. Review results above.")


if __name__ == "__main__":
    main()
