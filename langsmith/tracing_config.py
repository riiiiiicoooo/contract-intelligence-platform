"""
LangSmith Integration for Contract Intelligence Platform

Provides distributed tracing, cost tracking, and custom evaluators for:
- Clause extraction accuracy (F1 score benchmarks)
- Risk flag precision and recall
- Hallucination detection
- Cross-reference conflict detection

Uses @traceable decorator pattern for all pipeline stages.
"""

import os
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from langsmith import Client, evaluate, EvaluationResult, run_on_dataset
from langsmith.schemas import Example, Run
from langsmith.evaluation import evaluate as ls_evaluate, EvaluationResult
from langchain_core.traceable_context import trace_as_chain_group


# ============================================================================
# Configuration
# ============================================================================

class Environment(str, Enum):
    """Deployment environments for LangSmith projects."""
    DEVELOPMENT = "dev"
    STAGING = "staging"
    PRODUCTION = "prod"


@dataclass
class LangSmithConfig:
    """LangSmith configuration per environment."""
    api_key: str
    environment: Environment
    project_name_prefix: str = "contract-intelligence"
    enable_tracing: bool = True
    batch_size: int = 10

    @property
    def project_name(self) -> str:
        """Generate project name with environment suffix."""
        return f"{self.project_name_prefix}-{self.environment.value}"

    @classmethod
    def from_env(cls) -> "LangSmithConfig":
        """Load configuration from environment variables."""
        api_key = os.getenv("LANGSMITH_API_KEY", "")
        env_str = os.getenv("ENVIRONMENT", "dev").lower()

        try:
            environment = Environment(env_str)
        except ValueError:
            environment = Environment.DEVELOPMENT

        return cls(
            api_key=api_key,
            environment=environment,
            enable_tracing=os.getenv("LANGSMITH_TRACING_ENABLED", "true").lower() == "true"
        )


# Initialize global config
config = LangSmithConfig.from_env()
client = Client(api_key=config.api_key) if config.api_key else None


# ============================================================================
# Decorators & Traceable Functions
# ============================================================================

def traceable(name: str = None, tags: List[str] = None):
    """
    Decorator for tracing individual pipeline stages.

    Usage:
        @traceable(name="clause_extraction", tags=["extraction"])
        def extract_clauses(text: str, contract_type: str) -> dict:
            ...
    """
    def decorator(func):
        async_func = hasattr(func, '__aenter__')

        def sync_wrapper(*args, **kwargs):
            if not config.enable_tracing or not client:
                return func(*args, **kwargs)

            from langsmith.run_trees import RunTree

            run_name = name or func.__name__
            with trace_as_chain_group(run_name, tags=tags or []):
                result = func(*args, **kwargs)
            return result

        async def async_wrapper(*args, **kwargs):
            if not config.enable_tracing or not client:
                return await func(*args, **kwargs)

            from langsmith.run_trees import RunTree

            run_name = name or func.__name__
            with trace_as_chain_group(run_name, tags=tags or []):
                result = await func(*args, **kwargs)
            return result

        # Return appropriate wrapper
        if async_func:
            return async_wrapper
        return sync_wrapper

    return decorator


# ============================================================================
# Pipeline Stage Wrappers
# ============================================================================

@traceable(name="document_classification", tags=["ingestion", "classification"])
def trace_document_classification(
    filename: str,
    mime_type: str,
    page_count: int,
    is_scanned: bool
) -> Dict[str, Any]:
    """
    Trace document type classification stage.

    Args:
        filename: Original filename
        mime_type: Document MIME type
        page_count: Number of pages detected
        is_scanned: Whether document is scanned (requires OCR)

    Returns:
        Classification metadata with confidence
    """
    return {
        "filename": filename,
        "mime_type": mime_type,
        "page_count": page_count,
        "is_scanned": is_scanned,
        "timestamp": datetime.utcnow().isoformat()
    }


@traceable(name="clause_extraction", tags=["analysis", "extraction"])
def trace_clause_extraction(
    contract_id: str,
    contract_type: str,
    extracted_clauses: List[Dict[str, Any]],
    token_count_input: int,
    token_count_output: int,
    latency_ms: int,
    model_id: str
) -> Dict[str, Any]:
    """
    Trace clause extraction stage with cost tracking.

    Args:
        contract_id: Unique contract identifier
        contract_type: Type of contract (msa, nda, etc.)
        extracted_clauses: List of extracted clause dictionaries
        token_count_input: LLM input tokens consumed
        token_count_output: LLM output tokens generated
        latency_ms: API latency in milliseconds
        model_id: Model used (e.g., claude-3-5-sonnet-20241022)

    Returns:
        Extraction results with cost metrics
    """
    # Calculate costs (example rates per 1M tokens)
    input_cost = (token_count_input / 1_000_000) * 3.0  # $3 per 1M input tokens
    output_cost = (token_count_output / 1_000_000) * 15.0  # $15 per 1M output tokens
    total_cost = input_cost + output_cost

    return {
        "contract_id": contract_id,
        "contract_type": contract_type,
        "num_clauses_extracted": len(extracted_clauses),
        "avg_confidence": sum(c.get("confidence", 0) for c in extracted_clauses) / len(extracted_clauses) if extracted_clauses else 0,
        "tokens": {
            "input": token_count_input,
            "output": token_count_output,
            "total": token_count_input + token_count_output
        },
        "cost": {
            "input_usd": round(input_cost, 4),
            "output_usd": round(output_cost, 4),
            "total_usd": round(total_cost, 4)
        },
        "latency_ms": latency_ms,
        "model": model_id,
        "timestamp": datetime.utcnow().isoformat()
    }


@traceable(name="risk_scoring", tags=["analysis", "risk"])
def trace_risk_scoring(
    contract_id: str,
    clauses_scored: List[Dict[str, Any]],
    critical_flags: int,
    high_flags: int,
    medium_flags: int,
    low_flags: int
) -> Dict[str, Any]:
    """
    Trace risk scoring stage.

    Args:
        contract_id: Contract being scored
        clauses_scored: List of clauses with risk scores
        critical_flags: Count of critical severity flags
        high_flags: Count of high severity flags
        medium_flags: Count of medium severity flags
        low_flags: Count of low severity flags

    Returns:
        Risk scoring summary
    """
    total_flags = critical_flags + high_flags + medium_flags + low_flags

    return {
        "contract_id": contract_id,
        "clauses_scored": len(clauses_scored),
        "risk_flags": {
            "critical": critical_flags,
            "high": high_flags,
            "medium": medium_flags,
            "low": low_flags,
            "total": total_flags
        },
        "risk_distribution": {
            "critical_pct": (critical_flags / total_flags * 100) if total_flags > 0 else 0,
            "high_pct": (high_flags / total_flags * 100) if total_flags > 0 else 0,
            "medium_pct": (medium_flags / total_flags * 100) if total_flags > 0 else 0,
            "low_pct": (low_flags / total_flags * 100) if total_flags > 0 else 0
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@traceable(name="cross_reference_analysis", tags=["analysis", "cross-reference"])
def trace_cross_reference_analysis(
    deal_id: str,
    contracts_analyzed: int,
    conflicts_found: List[Dict[str, Any]],
    inconsistencies_found: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Trace cross-contract reference analysis stage.

    Args:
        deal_id: Deal being analyzed
        contracts_analyzed: Number of contracts processed
        conflicts_found: List of identified conflicts
        inconsistencies_found: List of inconsistencies across contracts

    Returns:
        Cross-reference analysis summary
    """
    return {
        "deal_id": deal_id,
        "contracts_analyzed": contracts_analyzed,
        "conflicts": {
            "total": len(conflicts_found),
            "details": conflicts_found
        },
        "inconsistencies": {
            "total": len(inconsistencies_found),
            "details": inconsistencies_found
        },
        "risk_level": "critical" if len(conflicts_found) > 0 else "medium" if len(inconsistencies_found) > 0 else "low",
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================================
# Custom Evaluators
# ============================================================================

def extract_accuracy_evaluator(run: Run, example: Example) -> EvaluationResult:
    """
    Evaluate extraction accuracy by comparing against ground truth.

    Metrics:
    - Precision: correctly extracted clauses / total extracted
    - Recall: correctly extracted clauses / total ground truth clauses
    - F1: harmonic mean of precision and recall
    """
    predictions = run.outputs or {}
    expected = example.outputs or {}

    predicted_clauses = set(c.get("clause_type") for c in predictions.get("clauses", []))
    expected_clauses = set(c.get("clause_type") for c in expected.get("clauses", []))

    true_positives = len(predicted_clauses & expected_clauses)
    false_positives = len(predicted_clauses - expected_clauses)
    false_negatives = len(expected_clauses - predicted_clauses)

    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    # Score is F1 >= 0.94 for this task
    score = f1
    passes = score >= 0.94

    return EvaluationResult(
        key="extract_accuracy_f1",
        score=score,
        value=score,
        comment=f"F1={f1:.3f} (P={precision:.3f}, R={recall:.3f})",
        passes=passes
    )


def hallucination_detection_evaluator(run: Run, example: Example) -> EvaluationResult:
    """
    Detect hallucinations in extracted clauses.

    Flags extractions that:
    - Extract text not present in source document
    - Invent clause types not mentioned
    - Create false cross-references
    """
    predictions = run.outputs or {}
    expected = example.outputs or {}

    predicted_text = predictions.get("extracted_text", "")
    source_text = example.inputs.get("source_text", "")

    # Check if predicted text appears in source (simple heuristic)
    text_found = predicted_text.lower() in source_text.lower()

    hallucination_detected = not text_found
    score = 0 if hallucination_detected else 1

    return EvaluationResult(
        key="hallucination_detection",
        score=score,
        value=score,
        comment="Hallucination detected" if hallucination_detected else "Text grounded in source",
        passes=not hallucination_detected
    )


def risk_flag_precision_evaluator(run: Run, example: Example) -> EvaluationResult:
    """
    Evaluate risk flag precision (correct flags / total flags raised).

    Penalizes both false positives and incorrect severity ratings.
    """
    predictions = run.outputs or {}
    expected = example.outputs or {}

    predicted_flags = predictions.get("risk_flags", [])
    expected_flags = expected.get("risk_flags", [])

    # Simple matching: count flags with correct severity
    correct = sum(1 for p in predicted_flags
                  if any(e["severity"] == p.get("severity") for e in expected_flags))

    precision = correct / len(predicted_flags) if predicted_flags else 1.0
    score = precision
    passes = score >= 0.90  # Allow 90%+ precision

    return EvaluationResult(
        key="risk_flag_precision",
        score=score,
        value=score,
        comment=f"Precision={precision:.1%} ({correct}/{len(predicted_flags)} correct)",
        passes=passes
    )


def conflict_detection_evaluator(run: Run, example: Example) -> EvaluationResult:
    """
    Evaluate cross-reference conflict detection recall.

    Measures: detected conflicts / total conflicts present
    """
    predictions = run.outputs or {}
    expected = example.outputs or {}

    predicted_conflicts = len(predictions.get("conflicts", []))
    expected_conflicts = len(expected.get("conflicts", []))

    if expected_conflicts == 0:
        return EvaluationResult(
            key="conflict_detection_recall",
            score=1.0,
            value=1.0,
            comment="No conflicts to detect",
            passes=True
        )

    # Recall: what fraction of expected conflicts were found?
    recall = predicted_conflicts / expected_conflicts if expected_conflicts > 0 else 1.0
    score = recall
    passes = score >= 0.85  # 85%+ recall target

    return EvaluationResult(
        key="conflict_detection_recall",
        score=score,
        value=score,
        comment=f"Recall={recall:.1%} ({predicted_conflicts}/{expected_conflicts} detected)",
        passes=passes
    )


# ============================================================================
# Dataset Management
# ============================================================================

def get_or_create_evaluation_dataset(dataset_name: str, examples: List[Dict[str, Any]]) -> str:
    """
    Get or create an evaluation dataset in LangSmith.

    Args:
        dataset_name: Name of dataset (e.g., "extraction_v1_dev")
        examples: List of example inputs/outputs for evaluation

    Returns:
        Dataset ID for use with evaluate()
    """
    if not client:
        return ""

    try:
        # Try to get existing dataset
        dataset = client.read_dataset(dataset_name=dataset_name)
        return dataset.id
    except:
        pass

    # Create new dataset
    dataset = client.create_dataset(
        dataset_name=dataset_name,
        description=f"Evaluation dataset for {dataset_name}"
    )

    # Upload examples
    for example in examples:
        client.create_example(
            inputs=example.get("inputs", {}),
            outputs=example.get("outputs", {}),
            dataset_id=dataset.id
        )

    return dataset.id


# ============================================================================
# Evaluation Runner
# ============================================================================

def run_evaluation(
    dataset_name: str,
    test_fn,
    evaluators: List,
    description: str = ""
) -> Optional[str]:
    """
    Run evaluations on a dataset.

    Args:
        dataset_name: Name of dataset to evaluate on
        test_fn: Function that takes (input) and returns output for evaluation
        evaluators: List of evaluator functions
        description: Optional evaluation description

    Returns:
        Evaluation ID if successful
    """
    if not client:
        print("LangSmith client not configured. Skipping evaluation.")
        return None

    try:
        # Run evaluation
        result = ls_evaluate(
            data=dataset_name,
            predicts=test_fn,
            evaluators=evaluators,
            experiment_prefix=f"{config.project_name}_eval",
            num_repetitions=1,
            metadata={
                "environment": config.environment.value,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        print(f"Evaluation completed: {result}")
        return result.get("experiment_id")

    except Exception as e:
        print(f"Evaluation failed: {e}")
        return None


# ============================================================================
# Cost Tracking
# ============================================================================

@dataclass
class ExtractionMetrics:
    """Metrics for a single extraction job."""
    contract_id: str
    contract_type: str
    num_clauses: int
    tokens_input: int
    tokens_output: int
    latency_ms: int
    model: str
    extraction_f1: float = 1.0
    risk_flags_raised: int = 0

    @property
    def cost_usd(self) -> float:
        """Calculate cost in USD for this extraction."""
        # Example pricing (update with actual rates)
        input_cost = (self.tokens_input / 1_000_000) * 3.0
        output_cost = (self.tokens_output / 1_000_000) * 15.0
        return input_cost + output_cost

    @property
    def cost_per_contract(self) -> float:
        """Cost per contract processed."""
        return self.cost_usd

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "contract_id": self.contract_id,
            "contract_type": self.contract_type,
            "num_clauses": self.num_clauses,
            "tokens": {
                "input": self.tokens_input,
                "output": self.tokens_output
            },
            "latency_ms": self.latency_ms,
            "model": self.model,
            "metrics": {
                "extraction_f1": self.extraction_f1,
                "risk_flags": self.risk_flags_raised
            },
            "cost": {
                "usd": round(self.cost_usd, 4),
                "per_contract": round(self.cost_per_contract, 4)
            }
        }


def log_extraction_metrics(metrics: ExtractionMetrics) -> None:
    """Log extraction metrics to LangSmith."""
    if not client:
        return

    client.create_run(
        name="extraction_metric",
        inputs={"contract_id": metrics.contract_id},
        outputs=metrics.to_dict(),
        run_type="chain"
    )


# ============================================================================
# Initialization & Health Check
# ============================================================================

def init_langsmith() -> bool:
    """Initialize LangSmith and verify connectivity."""
    global client, config

    if not config.api_key:
        print("⚠️  LANGSMITH_API_KEY not set. Tracing disabled.")
        return False

    try:
        # Test connectivity
        projects = client.list_projects(limit=1)
        print(f"✓ LangSmith connected. Current project: {config.project_name}")
        return True
    except Exception as e:
        print(f"✗ LangSmith connection failed: {e}")
        return False


if __name__ == "__main__":
    init_langsmith()
