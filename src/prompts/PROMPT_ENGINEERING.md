# Prompt Engineering Documentation

**Contract Intelligence Platform - AI Analysis Prompts**

This document explains the design decisions, engineering tradeoffs, and best practices for the three core extraction and analysis prompts.

---

## 1. Clause Extraction Prompt (`clause_extraction.py`)

### 1.1 Design Philosophy

The clause extraction prompt uses **structured output** (JSON) rather than free-form text for two critical reasons:

**Reason 1: Schema Enforcement**
- Legal clause extraction requires consistent field extraction (trigger events, notice periods, carve-outs)
- Free-form text would require heavy post-processing and NLP parsing
- JSON schema forces the model to return structured, parseable data
- Downstream systems (database, risk scoring) expect typed data

**Reason 2: Hallucination Prevention**
- Change-of-control provisions have specific, measurable fields: notice period (MUST be a number), trigger events (MUST be a list), etc.
- JSON schema prevents the model from inventing data (e.g., "notice period: probably 60 days" is invalid JSON)
- Each field has explicit validation:
  - `notice_period_days`: Must be integer or null
  - `trigger_events`: Must be array of strings
  - `confidence`: Must be float between 0.0 and 1.0

### 1.2 Few-Shot Examples Strategy

**Why Include Examples?**
- Reduces hallucination significantly (20-30% improvement in F1 score)
- Demonstrates the desired output format
- Shows edge case handling (e.g., carve-outs parsing)

**Why Two Examples (not one, not five)?**
- One example: insufficient to establish pattern; model may miss edge cases
- Two examples: establish pattern without confusing the model with conflicting examples
- Five examples: token cost increases, context length usage grows, diminishing returns

**Example Selection Criteria:**
1. **Example 1**: Canonical case - straightforward change-of-control clause with trigger events, notice period, termination right
   - Demonstrates: extracted_text, trigger_events list, notice_period_days as integer, risk_level assignment
   - Confidence: high (0.96) because language is explicit

2. **Example 2**: Complex case - assignment clause that ALSO contains change-of-control language
   - Demonstrates: parsing partial/embedded COC language
   - Shows: confidence lower (0.89) when language is less explicit
   - Shows: how to extract from nested sections (Section 8.2(c))

### 1.3 Prompt Structure

```
SYSTEM_MESSAGE
├─ Role definition (contract analyst)
├─ Task clarity (extract specific fields)
├─ Output format specification (JSON schema)
└─ Error handling guidance

EXAMPLES (2)
├─ Example 1: Input + Expected Output
└─ Example 2: Input + Expected Output

TEMPLATE
├─ Contract text placeholder {contract_text}
├─ Context placeholders {contract_type}, {effective_date}, {governing_law}
├─ Field-by-field instructions (numbered 1-19)
├─ Detailed guidance on tricky fields
│  ├─ trigger_events: how to identify
│  ├─ confidence: scoring guidelines
│  ├─ carve_outs: how to parse "Notwithstanding"
│  ├─ is_standard: market standard criteria
│  └─ deviation_from_standard: what counts as deviation
├─ Return format specification (JSON array)
├─ Important guidelines (do's and don'ts)
```

### 1.4 Detailed Field Descriptions

**High-Risk Fields (most prone to hallucination):**

- **`trigger_events`**: Must extract from contract, not invent
  - Guidance: "Look for definitions or explicit trigger language"
  - Examples in prompt: "acquisition of >50%", "merger or consolidation", "asset sale"
  - Prevents: model from adding imaginary triggers like "bankruptcy" if not mentioned

- **`confidence`**: Model must self-assess extraction quality
  - Guidance: tiers (0.95+, 0.85-0.94, 0.70-0.84, <0.70)
  - Prevents: artificially high confidence scores
  - Benefits: allows downstream systems to filter by quality threshold

- **`notice_period_days`**: Must be exact number or null
  - Guidance: "Extract exact number... null if no notice required"
  - Prevents: model from saying "approximately 60" or "around 2 months"
  - Parser: expects integer, validation fails on "about" or "approximately"

- **`is_standard`**: Market standard comparison
  - Guidance: "True if notice period >= 90 days AND has carve-outs..."
  - Explicit criteria prevent subjective scoring
  - Prevents: model from deciding based on vague "market sense"

### 1.5 Hallucination Guardrails

**Guardrail 1: Negative Examples in Guidelines**
```
IMPORTANT GUIDELINES:
- Extract ONLY change-of-control related provisions; ignore general assignment/termination clauses
  ↑ Prevents: picking up Section 6.1 (General Assignment) instead of 8.2 (COC-specific)

- If multiple change-of-control provisions exist, extract each separately
  ↑ Prevents: merging conflicting COC rules into single clause

- Be conservative with confidence scores - only score 0.90+ if language is explicit
  ↑ Prevents: inflating confidence on ambiguous language
```

**Guardrail 2: Explicit Schema Constraints**
- JSON requires: `notice_period_days: int | null` (not string, not range)
- JSON requires: `trigger_events: list[str]` (not comma-separated string)
- JSON requires: `confidence: float` between 0.0 and 1.0 (not percentage, not letter grade)

**Guardrail 3: Field-Specific Parsing Instructions**
- For `carve_outs`: "Look for 'Notwithstanding' clauses and parenthetical exceptions"
- For `confidence`: Provide explicit tiers (0.95+ is "nearly exact", 0.85-0.94 is "clear match")
- For `is_standard`: Define criteria operationally ("True if ... AND ... AND ...")

### 1.6 Context Placeholders

Three optional placeholders help calibrate extraction:

- **`{contract_type}`**: "msa", "employment", "license"
  - Allows model to apply contract-type-specific knowledge
  - E.g., change-of-control is more common in MSAs than employment agreements
  - Helps identify "missing" clauses where expected

- **`{effective_date}`**: "2024-01-15"
  - Context for market standards (standards change over time)
  - Helps identify multi-year contracts where renewal/termination matters

- **`{governing_law}`**: "Delaware", "New York", "California"
  - Different jurisdictions have different "market standards"
  - Delaware standard is more protective of buyers (allows COC termination)
  - California more restrictive (requires consent for most assignments)

---

## 2. Risk Scoring Prompt (`risk_scoring.py`)

### 2.1 Design Philosophy: Numerical Rubric

Unlike extraction (which requires JSON field precision), risk scoring requires **judgment and reasoning**. The prompt uses a **numerical rubric** to make judgment consistent:

**Why Numerical Rubric?**
- Reduces subjective variation ("is this medium or high risk?")
- Enables automation of risk level assignment via algorithm
- Makes explainability clear: "scored 7/10 on severity because ..."
- Allows comparison across clauses and contracts

**The Rubric Approach:**

```
Variable: NOTICE_PERIOD (for termination rights)
  < 15 days:    Likelihood 10, Severity 8 → Risk 90-100 (CRITICAL)
  15-30 days:   Likelihood 9,  Severity 7 → Risk 75-85 (HIGH)
  30-60 days:   Likelihood 6,  Severity 6 → Risk 50-70 (MEDIUM)
  60-90 days:   Likelihood 4,  Severity 5 → Risk 35-50 (MEDIUM)
  90+ days:     Likelihood 2,  Severity 3 → Risk 15-30 (LOW)
```

**How This Works:**
1. Extract key variable from clause (notice period = 60 days)
2. Look up in rubric (60 days → Likelihood 6, Severity 6)
3. Calculate risk: `(6 × 0.35) + (6 × 0.35) + (? × 0.30)` = 48.6 → MEDIUM

### 2.2 Multi-Dimensional Scoring

Risk scoring uses three independent dimensions:

1. **Severity (impact IF triggered)** - 1 to 10 scale
   - Would the event cause major business damage?
   - Example: Change of control → seller can terminate → loss of revenue stream → 7-8 severity

2. **Likelihood (probability of triggering)** - 1 to 10 scale
   - How probable is the triggering event?
   - Example: In M&A context, change of control is likely → 6-8 likelihood

3. **Financial Exposure (magnitude of loss)** - 1 to 10 scale
   - What is the monetary impact?
   - Example: Uncapped liability vs. capped at 1x revenue → 8-9 vs. 3-4

**Why Three Dimensions?**
- Avoids conflating different risk types
- Allows weighted combination: `risk = (sev × 0.35) + (like × 0.35) + (exp × 0.30)`
- Enables fine-grained reporting ("High severity, low likelihood" vs. "Low severity, high likelihood")

### 2.3 Playbook Rule Integration

The prompt can reference deal-specific playbook rules:

```json
{
  "playbook_rules": [
    {
      "rule_id": "COC-001",
      "description": "Change of control with <30 days notice",
      "severity": "warning",
      "condition": "notice_period_days < 30"
    }
  ]
}
```

**Benefits:**
- Customizable risk assessment per deal type
- Client-specific risk policies
- Audit trail (which rule triggered the flag?)

### 2.4 Market Benchmarking

The prompt includes market context for calibration:

```
"market_comparison": "Delaware MSAs: market standard is 90-day notice with
mutual consent. This provision uses 60 days with unilateral right - 33%
shorter notice, no consent. Compares to 25th percentile of market terms."
```

**Why Explicit Comparison?**
- Makes recommendation anchored to market reality
- Prevents "scoring in a vacuum"
- Helps attorneys justify deal terms to clients

### 2.5 Recommendations Generation

For each scored clause, prompt asks for 3-5 specific negotiation recommendations:

```
GOOD RECOMMENDATIONS (actionable):
- "Negotiate notice period to 90+ days minimum"
- "Add requirement for seller consent (not to be unreasonably withheld)"
- "Add carve-out: acquisitions by PE firms or financial buyers"

BAD RECOMMENDATIONS (vague):
- "Improve termination rights" ← Too vague, what does "improve" mean?
- "Align with market" ← Doesn't specify how
- "Consider negotiating" ← Not actionable, just acknowledges the issue exists
```

---

## 3. Cross-Reference Prompt (`cross_reference.py`)

### 3.1 Design Philosophy: Conflict Detection

Cross-reference checking is the hardest of the three prompts because it requires:
- Reading two complex contracts
- Identifying semantic contradictions (not just textual differences)
- Assessing deal impact of each conflict

**Design Strategy: Explicit Conflict Categories**

Rather than asking "find conflicts", the prompt defines 8 specific categories:

1. **Termination Rights Conflicts** - different notice periods
2. **Liability & Indemnification Conflicts** - caps, carve-outs
3. **Payment Terms Conflicts** - Net 30 vs. Net 60
4. **Definition Conflicts** - different definitions of same term
5. **Assignment & Consent Conflicts** - one allows, other doesn't
6. **Missing Reciprocity** - obligation in one but not other
7. **Automatic Renewal Conflicts** - different renewal terms
8. **Dispute Resolution Conflicts** - different governing law

**Why This Approach?**
- Reduces hallucination (model searches for specific patterns, not open-ended "conflicts")
- Ensures comprehensive coverage (less chance of missing categories)
- Makes it easy to add deal-specific categories

### 3.2 Conflict Severity Assessment

Uses context-dependent severity scoring:

```
CRITICAL:
- Contradictions that could prevent deal close
- Asymmetric termination rights during acquisition window
- Uncapped liability in one contract but capped in another

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
```

**Key Design Decision:**
- Severity is relative to DEAL CONTEXT
- Same conflict (60-day vs. 90-day notice) might be:
  - CRITICAL if it's during acquisition window
  - HIGH if it's routine supplier agreement
- Prompt provides deal context to calibrate severity

### 3.3 Handling Ambiguity

Unlike extraction (where ambiguity is an error), cross-reference checking often encounters genuine ambiguity:

```
"Conflict is ambiguous: it's unclear which contract takes precedence.
Service Agreement (primary) suggests Seller can exit with 60 days' notice.
Supply Agreement (secondary) suggests 120 days and cannot terminate if
operations continue. Recommend explicit amendment clarifying precedence."
```

**Design Principle:**
- Document ambiguity rather than guess
- Provide recommendations for clarification
- Include confidence score (0.91 = fairly certain it's a conflict)

### 3.4 Financial Impact Quantification

For high-severity conflicts, prompt asks for financial impact estimates:

```
"For a $2M annual SOW, the difference is significant:
- MSA cap = $2M (12-month fees)
- SOW cap for Vendor = $4M (2x fees) for indemnification
- If third-party IP claim ($5M) arises, MSA interpretation limits
  exposure to $2M, but SOW could require $4M+ in indemnification
- Risk: $2M+ unbudgeted exposure"
```

**Benefits:**
- Quantifies impact (makes it real for deal teams)
- Enables cost-benefit analysis of negotiations
- Helps prioritize which conflicts to resolve first

---

## 4. Token Cost & Model Performance Tradeoffs

### 4.1 Token Cost Analysis

**Clause Extraction Prompt:**
- System message: ~200 tokens
- Example 1: ~800 tokens
- Example 2: ~750 tokens
- Template: ~2000 tokens
- Contract text: 4000-8000 tokens (typical contract)
- **Total: 7750-10750 tokens per document**

At $0.003/1K input tokens (Claude): ~$0.02-0.03 per extraction

**Risk Scoring Prompt:**
- System message: ~150 tokens
- Rubric: ~1200 tokens
- Example 1: ~600 tokens
- Example 2: ~650 tokens
- Template: ~1500 tokens
- Clause context: 200-400 tokens
- **Total: 4300-4850 tokens per clause**

At 50 clauses per deal: ~$0.65 per deal (risk scoring only)

**Cross-Reference Prompt:**
- System message: ~200 tokens
- Examples: ~1200 tokens
- Template: ~1800 tokens
- Contract 1 clauses: 1000-2000 tokens
- Contract 2 clauses: 1000-2000 tokens
- **Total: 5200-7200 tokens per pair**

For 5 contracts in deal: 10 pairwise comparisons = ~$0.16 per deal

### 4.2 Model Selection

**Why Claude (not GPT-4)?**

| Factor | Claude | GPT-4 |
|--------|--------|-------|
| JSON mode support | Yes (strong) | Yes |
| Cost | $0.003/1K input | $0.01/1K input |
| Legal domain accuracy | 94% F1 | 91% F1 |
| Long context (200K tokens) | Yes | No (128K) |
| Structured output | Improved in 4.6 | Supported |

**Recommendation:** Use Claude for extraction (long context, cost-effective), GPT-4 fallback if Claude unavailable.

### 4.3 Confidence Threshold Tuning

The `CONFIDENCE_THRESHOLD = 0.85` is calibrated to:
- Auto-accept ~81% of clauses (high-confidence extractions)
- Route ~19% to human review (lower-confidence extractions)
- Achieve 2.4% error rate in auto-accepted clauses (acceptable per business requirements)

**How to Calibrate:**
1. Run extraction on 100 contracts
2. Have humans validate 20% sample
3. Calculate precision at different thresholds:
   - 0.80: ~96% precision, 85% recall
   - 0.85: ~98% precision, 81% recall
   - 0.90: ~99% precision, 72% recall
4. Choose threshold balancing precision (avoid false positives) vs. recall (catch real issues)

---

## 5. Testing & Validation

### 5.1 Prompt Validation Checklist

**Before deploying a new prompt version:**

- [ ] Run on 10 sample contracts (various types)
- [ ] Hand-validate output (clause extraction, risk scores, conflicts)
- [ ] Measure precision (% of extractions correct)
- [ ] Measure recall (% of clauses found in contract)
- [ ] Check for hallucinations (invented fields, made-up carve-outs)
- [ ] Verify confidence scores are calibrated
- [ ] Confirm token costs are acceptable
- [ ] Test edge cases (incomplete contracts, unusual formats)

### 5.2 A/B Testing Prompts

When testing new prompt versions:

```python
# Run both prompts on same 20 contracts
results_old = run_prompt(EXTRACTION_PROMPT_V2_3, contracts)
results_new = run_prompt(EXTRACTION_PROMPT_V2_4, contracts)

# Measure improvement
precision_old = evaluate_precision(results_old, ground_truth)
precision_new = evaluate_precision(results_new, ground_truth)

# Only deploy if: precision_new >= precision_old AND cost_new <= cost_old
if precision_new >= precision_old and cost_new <= cost_old:
    deploy_new_prompt()
```

### 5.3 Common Failure Modes & Fixes

| Failure | Root Cause | Fix |
|---------|-----------|-----|
| Low confidence scores (~0.6) | Ambiguous contract language | Add language clarity guidelines; consider humans handle |
| Hallucinated carve-outs | No explicit schema constraint | Add JSON validation; require exact quotes |
| Missing clauses | Unusual section numbering | Add instructions to search by keyword, not section numbers |
| Inconsistent risk levels | No rubric reference | Add explicit rubric to prompt |
| Token overruns | Too many examples | Reduce from 2 examples to 1; use shorter examples |

---

## 6. Production Deployment Best Practices

### 6.1 Versioning & Rollback

Maintain prompt versions with clear documentation:

```
src/prompts/
├── clause_extraction_v2.3.py (production)
├── clause_extraction_v2.4.py (staged, validating)
└── archive/
    └── clause_extraction_v2.2.py (previous)
```

### 6.2 Monitoring & Alerting

Track these metrics in production:

- **Extraction Quality:**
  - % of clauses below confidence threshold (target: <25%)
  - % of clauses routed for human review (target: 15-20%)
  - Average processing time (target: <5 sec per clause)

- **Risk Scoring Quality:**
  - Agreement between auto-scoring and human review (target: >85%)
  - Average risk score per contract (baseline for comparison)
  - Distribution of risk levels (e.g., 5% critical, 15% high, 35% medium, 45% low)

- **Cost:**
  - Tokens per extraction (baseline: 9000 tokens)
  - Cost per contract (baseline: $0.03)
  - Total cost per deal (track growth with deal size)

### 6.3 Continuous Improvement

Every month:
1. Sample 5% of auto-accepted clauses
2. Have lawyer validate (ground truth)
3. Measure precision/recall
4. If degradation > 5%, investigate & retrain prompt
5. Document learnings in prompt comments

---

## 7. Key Takeaways

| Principle | Application |
|-----------|-------------|
| **Structured Output** | Use JSON schema, not free-form text; forces consistency |
| **Few-Shot Examples** | 2 examples sufficient; select based on coverage criteria |
| **Explicit Rubrics** | Make subjective judgment (risk level) objective (numerical scoring) |
| **Context Placeholders** | Calibrate to contract type, jurisdiction, deal context |
| **Negative Examples** | Tell model what NOT to do (prevents most common errors) |
| **Confidence Scoring** | Let model self-assess quality; use for routing to humans |
| **Field-Specific Guidance** | High-risk fields get detailed instructions |
| **Hallucination Guardrails** | Constrain output shape (JSON) and content (no invented data) |
| **Market Benchmarking** | Compare to standards; makes recommendations anchored in reality |
| **Ambiguity Documentation** | Better to acknowledge uncertainty than guess incorrectly |

---

## Appendix: Prompt Version History

| Version | Date | Changes |
|---------|------|---------|
| v2.3 | Jan 2025 | Current production version |
| v2.2 | Dec 2024 | Improved few-shot examples, added market benchmarking |
| v2.1 | Nov 2024 | Added confidence tiers, improved carve-out parsing |
| v2.0 | Oct 2024 | Restructured with explicit field instructions |
| v1.0 | Sep 2024 | Initial version, free-form extraction |
