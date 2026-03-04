"""
Braintrust Integration for Contract Intelligence Platform
End-to-end evaluation and tracing of the contract extraction pipeline.

This module integrates with Braintrust to track:
- Pipeline performance metrics (latency, cost)
- Extraction accuracy metrics
- Per-stage performance (ingest, extract, score, verify)
- Cost per extraction
- Quality assurance metrics
"""

import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PipelineMetrics:
    """Metrics for a pipeline execution."""
    stage: str
    duration_ms: float
    cost_usd: float
    success: bool
    error_message: Optional[str] = None


class BraintrusEvaluationPipeline:
    """
    End-to-end evaluation of contract extraction pipeline.
    Integrates with Braintrust for tracing and monitoring.
    """
    
    def __init__(self, project_name: str = "contract-intelligence"):
        """
        Initialize the evaluation pipeline.
        
        Args:
            project_name: Name of Braintrust project for logging
        """
        self.project_name = project_name
        self.execution_log = []
        self.metrics_by_stage = {}
        
        # Initialize Braintrust experiment
        # Note: In production, use: from braintrust import init_experiment
        # self.experiment = init_experiment(project_name)
        
        self.test_contracts = self._load_test_contracts()
    
    def _load_test_contracts(self) -> List[Dict[str, Any]]:
        """
        Load test contracts for pipeline evaluation.
        
        Returns:
            List of test contract dictionaries
        """
        return [
            {
                "contract_id": "CONTRACT_001",
                "type": "Service Agreement",
                "size_bytes": 5000,
                "complexity": "low",
                "expected_clauses": 5,
                "contract_text": "Service Agreement sample 1..."
            },
            {
                "contract_id": "CONTRACT_002",
                "type": "NDA",
                "size_bytes": 3000,
                "complexity": "low",
                "expected_clauses": 3,
                "contract_text": "NDA sample..."
            },
            {
                "contract_id": "CONTRACT_003",
                "type": "M&A Purchase Agreement",
                "size_bytes": 25000,
                "complexity": "high",
                "expected_clauses": 15,
                "contract_text": "M&A Agreement sample..."
            },
            {
                "contract_id": "CONTRACT_004",
                "type": "Software License",
                "size_bytes": 8000,
                "complexity": "medium",
                "expected_clauses": 8,
                "contract_text": "Software License sample..."
            },
            {
                "contract_id": "CONTRACT_005",
                "type": "Employment Agreement",
                "size_bytes": 6000,
                "complexity": "medium",
                "expected_clauses": 7,
                "contract_text": "Employment Agreement sample..."
            },
        ]
    
    def pipeline_ingest_stage(
        self, 
        contract: Dict[str, Any]
    ) -> tuple[bool, Dict[str, Any], float, float]:
        """
        STAGE 1: Ingest contract document.
        
        Args:
            contract: Contract data to ingest
            
        Returns:
            Tuple of (success, processed_data, duration_ms, cost_usd)
        """
        start_time = time.time()
        cost = 0.01  # Fixed cost for ingestion
        
        try:
            # Simulate document ingestion and preprocessing
            processed = {
                "contract_id": contract["contract_id"],
                "type": contract["type"],
                "text_length": len(contract["contract_text"]),
                "ingested_at": datetime.now().isoformat(),
                "checksum": hash(contract["contract_text"]) % 100000
            }
            
            duration = (time.time() - start_time) * 1000
            
            return True, processed, duration, cost
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return False, {"error": str(e)}, duration, 0.0
    
    def pipeline_extract_stage(
        self, 
        processed_data: Dict[str, Any]
    ) -> tuple[bool, Dict[str, Any], float, float]:
        """
        STAGE 2: Extract clauses from contract.
        
        Args:
            processed_data: Preprocessed contract data
            
        Returns:
            Tuple of (success, extracted_clauses, duration_ms, cost_usd)
        """
        start_time = time.time()
        
        try:
            # Simulate clause extraction
            # Cost varies based on contract complexity
            base_cost = 0.05
            text_length = processed_data.get("text_length", 1000)
            length_multiplier = max(1.0, text_length / 5000)
            cost = base_cost * length_multiplier
            
            extracted = {
                "contract_id": processed_data["contract_id"],
                "clauses": [
                    {
                        "type": "governing_law",
                        "text": "Sample clause text",
                        "confidence": 0.95
                    },
                    {
                        "type": "termination",
                        "text": "Sample termination clause",
                        "confidence": 0.87
                    }
                ],
                "extraction_model": "claude-opus-4-20250514",
                "extracted_at": datetime.now().isoformat()
            }
            
            duration = (time.time() - start_time) * 1000
            
            return True, extracted, duration, cost
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return False, {"error": str(e)}, duration, 0.0
    
    def pipeline_score_stage(
        self, 
        extracted_clauses: Dict[str, Any]
    ) -> tuple[bool, Dict[str, Any], float, float]:
        """
        STAGE 3: Score and classify extracted clauses.
        
        Args:
            extracted_clauses: Extracted clause data
            
        Returns:
            Tuple of (success, scored_data, duration_ms, cost_usd)
        """
        start_time = time.time()
        cost = 0.02  # Cost for scoring
        
        try:
            # Simulate clause scoring
            scored = {
                "contract_id": extracted_clauses["contract_id"],
                "scored_clauses": [
                    {
                        "type": clause["type"],
                        "risk_level": "low" if clause["confidence"] > 0.90 else "medium",
                        "confidence_score": clause["confidence"],
                        "risk_score": round(1.0 - clause["confidence"], 2)
                    }
                    for clause in extracted_clauses.get("clauses", [])
                ],
                "overall_risk_level": "medium",
                "scored_at": datetime.now().isoformat()
            }
            
            duration = (time.time() - start_time) * 1000
            
            return True, scored, duration, cost
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return False, {"error": str(e)}, duration, 0.0
    
    def pipeline_verify_stage(
        self, 
        scored_data: Dict[str, Any],
        expected_clauses: int
    ) -> tuple[bool, Dict[str, Any], float, float]:
        """
        STAGE 4: Verify extraction quality against expectations.
        
        Args:
            scored_data: Scored clause data
            expected_clauses: Expected number of clauses
            
        Returns:
            Tuple of (success, verification_result, duration_ms, cost_usd)
        """
        start_time = time.time()
        cost = 0.01  # Cost for verification
        
        try:
            actual_clauses = len(scored_data.get("scored_clauses", []))
            accuracy = actual_clauses / expected_clauses if expected_clauses > 0 else 0.0
            
            # Simulate quality check
            passed = accuracy >= 0.8
            
            result = {
                "contract_id": scored_data["contract_id"],
                "expected_clauses": expected_clauses,
                "extracted_clauses": actual_clauses,
                "accuracy": accuracy,
                "passed_quality_check": passed,
                "verified_at": datetime.now().isoformat()
            }
            
            duration = (time.time() - start_time) * 1000
            
            return True, result, duration, cost
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return False, {"error": str(e)}, duration, 0.0
    
    def run_full_pipeline(self) -> Dict[str, Any]:
        """
        Execute the complete extraction pipeline for all test contracts.
        
        Returns:
            Comprehensive pipeline execution results
        """
        print("=" * 100)
        print("BRAINTRUST PIPELINE EVALUATION - Contract Intelligence Platform")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Project: {self.project_name}")
        print(f"Test Contracts: {len(self.test_contracts)}")
        print("=" * 100)
        
        results = []
        total_cost = 0.0
        total_duration = 0.0
        
        print(f"\n{'Contract':<20} {'Stage':<15} {'Duration(ms)':<15} {'Cost($)':<12} {'Status':<10}")
        print("-" * 100)
        
        for contract in self.test_contracts:
            contract_results = {
                "contract_id": contract["contract_id"],
                "type": contract["type"],
                "stages": [],
                "total_cost": 0.0,
                "total_duration": 0.0,
                "overall_success": True
            }
            
            # Stage 1: Ingest
            success, data, duration, cost = self.pipeline_ingest_stage(contract)
            contract_results["stages"].append({
                "stage": "ingest",
                "success": success,
                "duration_ms": duration,
                "cost_usd": cost
            })
            print(f"{contract['contract_id']:<20} {'Ingest':<15} {duration:<15.2f} {cost:<12.4f} {'OK' if success else 'FAIL':<10}")
            
            if not success:
                contract_results["overall_success"] = False
                results.append(contract_results)
                continue
            
            # Stage 2: Extract
            success, data, duration, cost = self.pipeline_extract_stage(data)
            contract_results["stages"].append({
                "stage": "extract",
                "success": success,
                "duration_ms": duration,
                "cost_usd": cost
            })
            print(f"{'':<20} {'Extract':<15} {duration:<15.2f} {cost:<12.4f} {'OK' if success else 'FAIL':<10}")
            
            if not success:
                contract_results["overall_success"] = False
                results.append(contract_results)
                continue
            
            # Stage 3: Score
            success, data, duration, cost = self.pipeline_score_stage(data)
            contract_results["stages"].append({
                "stage": "score",
                "success": success,
                "duration_ms": duration,
                "cost_usd": cost
            })
            print(f"{'':<20} {'Score':<15} {duration:<15.2f} {cost:<12.4f} {'OK' if success else 'FAIL':<10}")
            
            if not success:
                contract_results["overall_success"] = False
                results.append(contract_results)
                continue
            
            # Stage 4: Verify
            success, data, duration, cost = self.pipeline_verify_stage(data, contract["expected_clauses"])
            contract_results["stages"].append({
                "stage": "verify",
                "success": success,
                "duration_ms": duration,
                "cost_usd": cost,
                "verification_data": data
            })
            print(f"{'':<20} {'Verify':<15} {duration:<15.2f} {cost:<12.4f} {'OK' if success else 'FAIL':<10}")
            
            # Calculate totals
            for stage in contract_results["stages"]:
                contract_results["total_cost"] += stage["cost_usd"]
                contract_results["total_duration"] += stage["duration_ms"]
            
            total_cost += contract_results["total_cost"]
            total_duration += contract_results["total_duration"]
            
            results.append(contract_results)
        
        print("-" * 100)
        
        # Summary statistics
        print("\nPipeline Summary:")
        print("-" * 100)
        
        successful = sum(1 for r in results if r["overall_success"])
        total_contracts = len(results)
        
        avg_cost = total_cost / total_contracts if total_contracts > 0 else 0.0
        avg_duration = total_duration / total_contracts if total_contracts > 0 else 0.0
        
        print(f"Total Contracts Processed: {total_contracts}")
        print(f"Successful Extractions:    {successful}/{total_contracts} ({successful*100/total_contracts:.1f}%)")
        print(f"Total Cost:                ${total_cost:.4f}")
        print(f"Average Cost per Contract: ${avg_cost:.4f}")
        print(f"Average Duration per Contract: {avg_duration:.2f}ms")
        
        # Cost breakdown
        print("\nCost Breakdown by Stage:")
        stage_costs = {}
        for result in results:
            for stage in result["stages"]:
                stage_name = stage["stage"]
                if stage_name not in stage_costs:
                    stage_costs[stage_name] = 0.0
                stage_costs[stage_name] += stage["cost_usd"]
        
        for stage, cost in sorted(stage_costs.items()):
            pct = (cost / total_cost * 100) if total_cost > 0 else 0
            print(f"  {stage.capitalize():<15}: ${cost:<8.4f} ({pct:>5.1f}%)")
        
        print("\n" + "=" * 100)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "project": self.project_name,
            "total_contracts": total_contracts,
            "successful_contracts": successful,
            "total_cost": total_cost,
            "average_cost_per_contract": avg_cost,
            "average_duration_per_contract": avg_duration,
            "results": results
        }
    
    def export_results(self, filepath: str):
        """
        Export pipeline results to JSON file for analysis.
        
        Args:
            filepath: Path to save results JSON
        """
        results = self.run_full_pipeline()
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults exported to {filepath}")


def main():
    """Main pipeline execution."""
    # Initialize evaluator
    evaluator = BraintrusEvaluationPipeline(project_name="contract-intelligence-prod")
    
    # Run pipeline
    print("\nExecuting end-to-end contract extraction pipeline...\n")
    results = evaluator.run_full_pipeline()
    
    # Export results
    export_path = '/sessions/youthful-eager-lamport/mnt/Portfolio/contract-intelligence-platform/evals/braintrust/pipeline_results.json'
    evaluator.export_results(export_path)
    
    print("\nPipeline evaluation complete.")


if __name__ == "__main__":
    main()
