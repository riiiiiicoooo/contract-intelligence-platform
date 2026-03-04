# AI Evaluation Framework - Contract Intelligence Platform

Comprehensive evaluation suite for the Contract Intelligence Platform's clause extraction, classification, and risk assessment pipeline.

## Overview

The evaluation framework consists of three integrated components:

1. **RAGAS Framework** - Evaluates clause extraction completeness and accuracy
2. **Promptfoo** - Tests clause extraction prompt against adversarial inputs
3. **Braintrust** - End-to-end pipeline tracing and cost/performance monitoring

## Directory Structure

```
evals/
├── ragas/
│   ├── clause_extraction_eval.py    # RAGAS evaluation for extraction
│   └── README.md
├── promptfoo/
│   ├── promptfooconfig.yaml         # Promptfoo test configuration
│   └── results.json                 # Test results (generated)
├── braintrust/
│   ├── eval_pipeline.py             # End-to-end pipeline evaluation
│   ├── pipeline_results.json        # Pipeline results (generated)
│   └── README.md
└── README.md
```

## RAGAS Evaluation

### Overview

RAGAS evaluation measures the quality of clause extraction by comparing against 10 test contracts with different characteristics.

### Running RAGAS Evaluation

```bash
# Install dependencies
pip install ragas datasets anthropic

# Run evaluation
cd evals/ragas
python clause_extraction_eval.py
```

### Key Metrics

1. **Precision**: True positives / (True positives + False positives)
   - Measures how many identified clauses are actually correct
   - Target: >= 0.85

2. **Recall**: True positives / (True positives + False negatives)
   - Measures how many actual clauses are identified
   - Target: >= 0.80

3. **F1 Score**: Harmonic mean of precision and recall
   - Overall extraction quality metric
   - Target: >= 0.85

4. **Accuracy**: Correct classifications / Total items
   - Measures classification correctness
   - Target: >= 0.80

### Test Cases

The framework includes 10 contract test cases:

1. **Service Agreement** - Basic services with governing law
2. **NDA** - Confidentiality with survival clauses
3. **Software License** - Assignment restrictions, termination, liability caps
4. **M&A Purchase Agreement** - Change of control with cascading obligations
5. **Employment Agreement** - IP ownership and confidentiality
6. **Supplier Agreement** - Deliverables, indemnification, liability
7. **Lease Agreement** - Assignment, payment, termination
8. **Consulting Agreement** - SOW reference, IP retention, limited liability
9. **Loan Agreement** - Payment terms, acceleration, personal guarantee
10. **Distribution Agreement** - Exclusive rights, mutual indemnification

### Interpreting Results

Example output:

```
Test ID         Precision     Recall        F1 Score      Accuracy      Status
========================================================================
EXTRACT_001     0.900         0.857         0.878         0.875         PASS
EXTRACT_002     0.875         0.800         0.836         0.800         PASS
...
========================================================================
Average F1 Score: 0.848
Pass Rate: 100%
```

## Promptfoo Evaluation

### Overview

Promptfoo tests the clause extraction prompt against 20+ test cases including adversarial inputs.

### Running Promptfoo Evaluation

```bash
# Install Promptfoo
npm install -g promptfoo

# Set API keys
export ANTHROPIC_API_KEY="your_key"
export OPENAI_API_KEY="your_key"

# Run tests
cd evals/promptfoo
promptfoo eval

# View results
promptfoo view
```

### Test Categories

1. **Functional Tests** (8 tests)
   - Basic clause extraction
   - Confidentiality and survival
   - Assignment restrictions
   - Termination and liability
   - Change of control
   - IP ownership

2. **Accuracy Tests** (3 tests)
   - Clause classification
   - Risk level assignment
   - Risk flag identification

3. **Red Team Tests** (9 tests)
   - Hallucination prevention
   - Fabricated terms
   - Incomplete exhibits
   - Ambiguous clauses
   - Contradictory terms
   - Confidential information handling
   - Compounded risks
   - Obfuscated language

4. **Edge Cases** (2 tests)
   - Mixed contract types
   - Regulatory compliance clauses

### Assertion Types

- **contains**: Check if output includes specific text
- **javascript**: Custom validation logic
- **llm-rubric**: LLM-based quality evaluation

## Braintrust Evaluation

### Overview

Braintrust integration provides end-to-end pipeline tracing and cost/performance monitoring.

### Running Braintrust Evaluation

```bash
# Install dependencies (note: Braintrust integration optional)
pip install anthropic

# Run pipeline evaluation
cd evals/braintrust
python eval_pipeline.py
```

### Pipeline Stages

The evaluation traces 4 pipeline stages:

1. **Ingest Stage**
   - Loads and preprocesses contract document
   - Fixed cost: $0.01
   - Expected latency: <100ms

2. **Extract Stage**
   - Extracts clauses using language model
   - Cost: $0.05 base + variable per contract size
   - Expected latency: 500-2000ms
   - Accounts for model API calls

3. **Score Stage**
   - Assigns risk levels and confidence scores
   - Fixed cost: $0.02
   - Expected latency: <200ms

4. **Verify Stage**
   - Quality assurance and accuracy verification
   - Fixed cost: $0.01
   - Expected latency: <100ms

### Key Metrics

- **Cost per extraction**: Total USD cost for full pipeline
- **Latency per stage**: Time taken for each stage
- **Success rate**: Percentage of successful extractions
- **Cost breakdown**: Percentage by stage

### Sample Output

```
Pipeline Summary:
===================================================
Total Contracts Processed: 5
Successful Extractions:    5/5 (100%)
Total Cost:                $0.4123
Average Cost per Contract: $0.0825
Average Duration:          1542.34ms

Cost Breakdown by Stage:
  Ingest:    $0.0500  (12.1%)
  Extract:   $0.2500  (60.6%)
  Score:     $0.1000  (24.2%)
  Verify:    $0.0123  (3.0%)
```

## Integration with CI/CD

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

cd evals/ragas
python clause_extraction_eval.py | grep -q "PASS" || exit 1
```

### CI/CD Pipeline

```yaml
# Example GitHub Actions workflow
name: Evaluate Contract Intelligence

on: [push, pull_request]

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install ragas datasets anthropic
          npm install -g promptfoo
      
      - name: Run RAGAS evaluation
        run: python evals/ragas/clause_extraction_eval.py
      
      - name: Run Promptfoo tests
        run: promptfoo eval --output results.json
        working-directory: evals/promptfoo
      
      - name: Check results
        run: |
          grep -q "PASS" ragas_results.txt || exit 1
          grep -q "pass_rate.*100" promptfoo_results.json || exit 1
```

## Best Practices

### RAGAS Evaluation

1. **Run regularly**: Test after prompt changes or model updates
2. **Track metrics over time**: Monitor F1 score trends
3. **Analyze failures**: Understand why specific contracts fail
4. **Expand test set**: Add production contracts periodically
5. **Document baselines**: Record baseline scores for comparison

### Promptfoo Testing

1. **Test multiple providers**: Compare Claude vs GPT-4
2. **Expand red team tests**: Add domain-specific adversarial cases
3. **Monitor regressions**: Ensure new prompts maintain quality
4. **Review failed assertions**: Understand assertion failures
5. **Iterate on prompts**: Use failures to guide refinement

### Braintrust Pipeline

1. **Monitor costs**: Track cost trends per contract type
2. **Identify bottlenecks**: Find slow pipeline stages
3. **Set budgets**: Establish maximum acceptable costs
4. **Alert on anomalies**: Set up alerts for cost/latency spikes
5. **Optimize stages**: Focus improvements on costly stages

## Troubleshooting

### Common Issues

**Issue**: RAGAS evaluation slow
```bash
Solution: Reduce test case count for quick feedback, run full suite in CI/CD only
```

**Issue**: Promptfoo tests timeout
```bash
Solution: Increase timeout in promptfooconfig.yaml, check API rate limits
```

**Issue**: Braintrust authentication fails
```bash
Solution: Set BRAINTRUST_API_KEY environment variable with valid token
```

**Issue**: False positives in red team tests
```bash
Solution: Review assertions, adjust llm-rubric criteria, test with multiple models
```

## Cost Optimization

To reduce per-contract costs:

1. **Batch processing**: Process multiple contracts in one API call
2. **Caching**: Cache extraction results for identical clauses
3. **Sampling**: Use rule-based extraction for simple contracts
4. **Model selection**: Use smaller/cheaper models for simple clauses

Estimated cost reduction: 30-50% through optimization.

## References

- [RAGAS Documentation](https://github.com/explodinggradients/ragas)
- [Promptfoo Documentation](https://www.promptfoo.dev/)
- [Braintrust Documentation](https://www.braintrust.dev/)
- [Contract Intelligence Platform Guide](../README.md)

## Support

For issues or questions:
1. Check troubleshooting section
2. Review official documentation for RAGAS/Promptfoo
3. Analyze specific test failures
4. Consult with data science team
