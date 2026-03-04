/**
 * Trigger.dev Job: Batch Deal Analysis
 *
 * Process all contracts in a deal room:
 * 1. Fan-out: Extract all contracts in parallel
 * 2. Fan-in: Aggregate results and perform cross-deal analysis
 * 3. Generate deal risk matrix
 * 4. Identify portfolio-level patterns
 *
 * Features:
 * - Parallel contract processing (up to 10 concurrently)
 * - Portfolio risk aggregation
 * - Pattern detection across contracts
 * - Generate summary metrics for dashboard
 */

import { task, logger, runs } from "@trigger.dev/sdk/v3";
import type { Run } from "@trigger.dev/sdk/v3";

// ============================================================================
// Types
// ============================================================================

interface DealAnalysisPayload {
  deal_id: string;
  tenant_id: string;
  contract_ids: string[];
}

interface ContractSummary {
  contract_id: string;
  filename: string;
  contract_type: string;
  clause_count: number;
  critical_flags: number;
  high_flags: number;
  medium_flags: number;
  avg_confidence: number;
}

interface PortfolioPattern {
  pattern_type: string;
  affected_contracts: string[];
  severity: "low" | "medium" | "high" | "critical";
  description: string;
}

interface DealAnalysisResult {
  deal_id: string;
  analysis_timestamp: string;
  contracts_analyzed: number;
  contract_summaries: ContractSummary[];
  portfolio_patterns: PortfolioPattern[];
  risk_matrix: Record<string, unknown>;
  metrics: {
    total_clauses: number;
    total_critical_flags: number;
    total_high_flags: number;
    avg_extraction_confidence: number;
    processing_duration_ms: number;
  };
}

// ============================================================================
// Fan-Out: Trigger Contract Extraction for All Contracts
// ============================================================================

async function fanOutContractExtractions(contractIds: string[]): Promise<string[]> {
  const run = await logger.log("Fanning out contract extractions", {
    contract_count: contractIds.length,
  });

  const runIds: string[] = [];

  // Process contracts in batches of 10 for parallelism
  const batchSize = 10;
  for (let i = 0; i < contractIds.length; i += batchSize) {
    const batch = contractIds.slice(i, i + batchSize);

    const promises = batch.map(async (contractId) => {
      try {
        // Trigger extraction task
        const extractRun = await runs.trigger("contract-extraction", {
          contract_id: contractId,
          file_path: ``, // Will be fetched from DB
          contract_type: "", // Will be fetched from DB
          deal_id: "", // Will be set by caller
          tenant_id: "", // Will be set by caller
        });

        return extractRun.id;
      } catch (error) {
        logger.error("Failed to trigger extraction", {
          contract_id: contractId,
          error,
        });
        return null;
      }
    });

    const results = await Promise.all(promises);
    runIds.push(...results.filter((id) => id !== null) as string[]);
  }

  logger.log("Fan-out completed", { triggered_runs: runIds.length });

  return runIds;
}

// ============================================================================
// Fan-In: Aggregate Results
// ============================================================================

async function fanInResults(
  runIds: string[]
): Promise<{ contractSummaries: ContractSummary[]; extractionResults: Record<string, unknown>[] }> {
  const run = await logger.log("Waiting for extraction results", {
    run_count: runIds.length,
  });

  const contractSummaries: ContractSummary[] = [];
  const extractionResults: Record<string, unknown>[] = [];

  // Poll for completion of all runs
  const completedRuns = await Promise.all(
    runIds.map((runId) => waitForRun(runId))
  );

  // Process completed runs
  for (const completedRun of completedRuns) {
    if (completedRun && completedRun.output) {
      const result = completedRun.output as Record<string, unknown>;
      const clauses = (result.clauses as Record<string, unknown>[]) || [];
      const flags = (result.risk_flags as Record<string, unknown>[]) || [];

      // Build contract summary
      const summary: ContractSummary = {
        contract_id: result.contract_id as string,
        filename: result.filename as string || "Unknown",
        contract_type: result.contract_type as string || "other",
        clause_count: clauses.length,
        critical_flags: flags.filter((f) => f.severity === "critical").length,
        high_flags: flags.filter((f) => f.severity === "high").length,
        medium_flags: flags.filter((f) => f.severity === "medium").length,
        avg_confidence:
          clauses.length > 0
            ? clauses.reduce((sum, c) => sum + ((c.confidence as number) || 0), 0) / clauses.length
            : 0,
      };

      contractSummaries.push(summary);
      extractionResults.push(result);
    }
  }

  logger.log("Fan-in completed", {
    successful_extractions: contractSummaries.length,
    failed_extractions: runIds.length - contractSummaries.length,
  });

  return { contractSummaries, extractionResults };
}

// ============================================================================
// Portfolio Analysis
// ============================================================================

async function analyzePortfolioPatterns(
  contractSummaries: ContractSummary[],
  extractionResults: Record<string, unknown>[]
): Promise<PortfolioPattern[]> {
  const run = await logger.log("Analyzing portfolio patterns", {
    contract_count: contractSummaries.length,
  });

  const patterns: PortfolioPattern[] = [];

  // Pattern 1: High-risk contract concentration
  const highRiskContracts = contractSummaries.filter(
    (c) => c.critical_flags + c.high_flags > 5
  );
  if (highRiskContracts.length > 0) {
    patterns.push({
      pattern_type: "high_risk_concentration",
      affected_contracts: highRiskContracts.map((c) => c.contract_id),
      severity: "high",
      description: `${highRiskContracts.length} contracts have high risk flag concentration`,
    });
  }

  // Pattern 2: Low confidence extraction (may need manual review)
  const lowConfidenceContracts = contractSummaries.filter(
    (c) => c.avg_confidence < 0.85
  );
  if (lowConfidenceContracts.length > 0) {
    patterns.push({
      pattern_type: "low_extraction_confidence",
      affected_contracts: lowConfidenceContracts.map((c) => c.contract_id),
      severity: "medium",
      description: `${lowConfidenceContracts.length} contracts have low extraction confidence (< 0.85)`,
    });
  }

  // Pattern 3: Missing standard clauses
  const contractsByType: Record<string, ContractSummary[]> = {};
  contractSummaries.forEach((c) => {
    if (!contractsByType[c.contract_type]) {
      contractsByType[c.contract_type] = [];
    }
    contractsByType[c.contract_type].push(c);
  });

  for (const [type, contracts] of Object.entries(contractsByType)) {
    const avgClauses =
      contracts.reduce((sum, c) => sum + c.clause_count, 0) / contracts.length;
    const belowAverage = contracts.filter((c) => c.clause_count < avgClauses * 0.7);

    if (belowAverage.length > 0) {
      patterns.push({
        pattern_type: "missing_standard_clauses",
        affected_contracts: belowAverage.map((c) => c.contract_id),
        severity: "medium",
        description: `${belowAverage.length} ${type} contracts have fewer clauses than typical`,
      });
    }
  }

  // Pattern 4: Cross-contract term conflicts
  const termConflicts = await detectTermConflicts(extractionResults);
  if (termConflicts.length > 0) {
    patterns.push(...termConflicts);
  }

  logger.log("Portfolio analysis completed", { patterns_found: patterns.length });

  return patterns;
}

// ============================================================================
// Risk Matrix Generation
// ============================================================================

function generateRiskMatrix(
  contractSummaries: ContractSummary[]
): Record<string, unknown> {
  const matrix = {
    critical: contractSummaries.filter((c) => c.critical_flags > 0),
    high: contractSummaries.filter((c) => c.high_flags > 0 && c.critical_flags === 0),
    medium: contractSummaries.filter((c) => c.medium_flags > 0 && c.high_flags === 0 && c.critical_flags === 0),
    low: contractSummaries.filter(
      (c) => c.critical_flags === 0 && c.high_flags === 0 && c.medium_flags === 0
    ),
  };

  return {
    total_contracts: contractSummaries.length,
    risk_distribution: {
      critical: matrix.critical.length,
      high: (matrix.high as Record<string, unknown>[]).length,
      medium: (matrix.medium as Record<string, unknown>[]).length,
      low: (matrix.low as Record<string, unknown>[]).length,
    },
    contracts_by_risk: matrix,
  };
}

// ============================================================================
// Cross-Contract Conflict Detection
// ============================================================================

async function detectTermConflicts(
  extractionResults: Record<string, unknown>[]
): Promise<PortfolioPattern[]> {
  const conflicts: PortfolioPattern[] = [];

  // Check for payment term conflicts
  const paymentTerms: Record<string, string[]> = {};
  extractionResults.forEach((result) => {
    const clauses = (result.clauses as Record<string, unknown>[]) || [];
    clauses
      .filter((c) => c.clause_type === "payment_terms")
      .forEach((clause) => {
        const contractId = result.contract_id as string;
        const text = (clause.extracted_text as string) || "";
        if (!paymentTerms[contractId]) {
          paymentTerms[contractId] = [];
        }
        paymentTerms[contractId].push(text);
      });
  });

  // Simple conflict detection: check if Net 30 vs Net 15
  const net30Contracts = Object.entries(paymentTerms)
    .filter(([, terms]) => terms.some((t) => t.includes("Net 30")))
    .map(([id]) => id);
  const net15Contracts = Object.entries(paymentTerms)
    .filter(([, terms]) => terms.some((t) => t.includes("Net 15")))
    .map(([id]) => id);

  if (net30Contracts.length > 0 && net15Contracts.length > 0) {
    conflicts.push({
      pattern_type: "payment_term_conflict",
      affected_contracts: [...net30Contracts, ...net15Contracts],
      severity: "high",
      description: "Inconsistent payment terms across contracts (Net 30 vs Net 15)",
    });
  }

  return conflicts;
}

// ============================================================================
// Save Deal Analysis Results
// ============================================================================

async function saveDealAnalysisResults(
  dealId: string,
  tenantId: string,
  result: DealAnalysisResult
): Promise<void> {
  const run = await logger.log("Saving deal analysis results", {
    deal_id: dealId,
  });

  try {
    // Save deal metrics to database
    await fetch(`https://api.contract-intelligence.app/v1/deals/${dealId}/analysis`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${process.env.API_KEY}`,
      },
      body: JSON.stringify({
        tenant_id: tenantId,
        contracts_analyzed: result.contracts_analyzed,
        total_clauses: result.metrics.total_clauses,
        critical_flags: result.metrics.total_critical_flags,
        high_flags: result.metrics.total_high_flags,
        avg_confidence: result.metrics.avg_extraction_confidence,
        patterns: result.portfolio_patterns,
        risk_matrix: result.risk_matrix,
        analyzed_at: result.analysis_timestamp,
      }),
    });

    logger.log("Deal analysis results saved", {
      patterns_saved: result.portfolio_patterns.length,
    });
  } catch (error) {
    logger.error("Failed to save deal analysis results", { error, deal_id: dealId });
    throw error;
  }
}

// ============================================================================
// Helper: Wait for Run Completion
// ============================================================================

async function waitForRun(runId: string, maxRetries = 30): Promise<Run | null> {
  let retries = 0;

  while (retries < maxRetries) {
    try {
      const run = await runs.retrieve(runId);

      if (run.status === "COMPLETED") {
        return run;
      } else if (run.status === "FAILED") {
        logger.warn("Run failed", { run_id: runId });
        return null;
      }

      // Wait before retrying
      await new Promise((resolve) => setTimeout(resolve, 2000));
      retries++;
    } catch (error) {
      logger.error("Error retrieving run", { run_id: runId, error });
      retries++;
    }
  }

  logger.error("Run timeout", { run_id: runId });
  return null;
}

// ============================================================================
// Main Task
// ============================================================================

export const dealAnalysisTask = task<DealAnalysisPayload, DealAnalysisResult>({
  id: "deal-analysis",
  run: async (payload) => {
    const startTime = Date.now();

    logger.log("Starting deal analysis", {
      deal_id: payload.deal_id,
      contract_count: payload.contract_ids.length,
    });

    try {
      // Step 1: Fan-out extractions
      const runIds = await fanOutContractExtractions(payload.contract_ids);

      // Step 2: Fan-in results
      const { contractSummaries, extractionResults } = await fanInResults(runIds);

      // Step 3: Portfolio analysis
      const portfolioPatterns = await analyzePortfolioPatterns(
        contractSummaries,
        extractionResults
      );

      // Step 4: Generate risk matrix
      const riskMatrix = generateRiskMatrix(contractSummaries);

      // Aggregate metrics
      const totalClauses = contractSummaries.reduce((sum, c) => sum + c.clause_count, 0);
      const totalCriticalFlags = contractSummaries.reduce((sum, c) => sum + c.critical_flags, 0);
      const totalHighFlags = contractSummaries.reduce((sum, c) => sum + c.high_flags, 0);
      const avgConfidence =
        contractSummaries.length > 0
          ? contractSummaries.reduce((sum, c) => sum + c.avg_confidence, 0) /
            contractSummaries.length
          : 0;

      // Build result
      const result: DealAnalysisResult = {
        deal_id: payload.deal_id,
        analysis_timestamp: new Date().toISOString(),
        contracts_analyzed: contractSummaries.length,
        contract_summaries: contractSummaries,
        portfolio_patterns: portfolioPatterns,
        risk_matrix: riskMatrix,
        metrics: {
          total_clauses: totalClauses,
          total_critical_flags: totalCriticalFlags,
          total_high_flags: totalHighFlags,
          avg_extraction_confidence: avgConfidence,
          processing_duration_ms: Date.now() - startTime,
        },
      };

      // Step 5: Save results
      await saveDealAnalysisResults(payload.deal_id, payload.tenant_id, result);

      logger.log("Deal analysis completed successfully", {
        duration_ms: result.metrics.processing_duration_ms,
        patterns_found: result.portfolio_patterns.length,
      });

      return result;
    } catch (error) {
      logger.error("Deal analysis failed", { error, payload });
      throw error;
    }
  },
});
