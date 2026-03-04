/**
 * Contract Intelligence Platform - Dashboard Component
 *
 * A React component providing three integrated views for M&A contract analysis:
 * 1. Deal Dashboard - contract portfolio with status indicators and risk scores
 * 2. Contract Viewer - split-pane text + clauses with confidence highlighting
 * 3. Risk Matrix - clause-level risk visualization across deal
 *
 * Built with Next.js, shadcn/ui, and Recharts for visualizations.
 */

"use client";

import React, { useState } from "react";
import {
  BarChart,
  Bar,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
  LineChart,
  Line,
  PieChart,
  Pie,
} from "recharts";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription } from "@/components/ui/alert";

// ============================================================================
// SYNTHETIC DATA: M&A DEAL WITH 5 CONTRACTS
// ============================================================================

const DEAL_DATA = {
  id: "deal_proj_atlas",
  name: "Project Atlas - Acme Corp Acquisition",
  target_company: "Acme Corporation",
  deal_type: "m_and_a",
  status: "reviewing",
  deal_value: "$150M-$200M",
  created_at: "2025-01-10",
  contracts: [
    {
      id: "contract_msa_001",
      filename: "Master_Service_Agreement_Acme_2024.pdf",
      contract_type: "msa",
      page_count: 42,
      processing_status: "reviewed",
      risk_summary: {
        critical: 1,
        high: 3,
        medium: 7,
        low: 8,
      },
      status_color: "success",
      clauses_count: 19,
      parties: ["Acme Corporation", "Target Corp"],
      effective_date: "2024-03-01",
      expiration_date: "2027-02-28",
      governing_law: "Delaware",
    },
    {
      id: "contract_sow_001",
      filename: "Statement_of_Work_2024_Q1_Q2.pdf",
      contract_type: "sow",
      page_count: 28,
      processing_status: "reviewed",
      risk_summary: {
        critical: 0,
        high: 2,
        medium: 5,
        low: 12,
      },
      status_color: "success",
      clauses_count: 19,
      parties: ["Acme Corporation", "Target Corp"],
      effective_date: "2024-01-01",
      expiration_date: "2024-06-30",
      governing_law: "New York",
    },
    {
      id: "contract_vendor_001",
      filename: "Vendor_Agreement_IT_Services.pdf",
      contract_type: "vendor",
      page_count: 15,
      processing_status: "review_pending",
      risk_summary: {
        critical: 0,
        high: 1,
        medium: 3,
        low: 5,
      },
      status_color: "warning",
      clauses_count: 9,
      parties: ["Acme Corporation", "CloudTech Solutions"],
      effective_date: "2023-06-01",
      expiration_date: "2025-05-31",
      governing_law: "Delaware",
    },
    {
      id: "contract_nda_001",
      filename: "NDA_Mutual_Standard.pdf",
      contract_type: "nda",
      page_count: 8,
      processing_status: "reviewed",
      risk_summary: {
        critical: 0,
        high: 0,
        medium: 1,
        low: 4,
      },
      status_color: "success",
      clauses_count: 5,
      parties: ["Acme Corporation", "Various Partners"],
      effective_date: "2023-01-01",
      expiration_date: "2025-12-31",
      governing_law: "Delaware",
    },
    {
      id: "contract_lease_001",
      filename: "Real_Estate_Lease_HQ.pdf",
      contract_type: "lease",
      page_count: 35,
      processing_status: "extracted",
      risk_summary: {
        critical: 1,
        high: 2,
        medium: 6,
        low: 10,
      },
      status_color: "warning",
      clauses_count: 19,
      parties: ["Property Management LLC", "Acme Corporation"],
      effective_date: "2020-01-15",
      expiration_date: "2030-01-14",
      governing_law: "California",
    },
  ],
};

// Clause data with risk scores
const CLAUSE_DATA = [
  {
    id: "clause_001",
    contract_id: "contract_msa_001",
    clause_type: "change_of_control",
    extracted_text:
      "In the event of a Change of Control of either party, the non-affected party shall have the right to terminate this Agreement upon sixty (60) days written notice.",
    page_number: 12,
    section_reference: "Section 14.2(b)",
    confidence: 0.94,
    risk_level: "high",
    risk_score: 78,
    review_status: "auto_accepted",
  },
  {
    id: "clause_002",
    contract_id: "contract_msa_001",
    clause_type: "limitation_of_liability",
    extracted_text:
      "Neither party's aggregate liability under this Agreement shall exceed the total fees paid in the twelve (12) months preceding the claim.",
    page_number: 18,
    section_reference: "Section 10.1",
    confidence: 0.88,
    risk_level: "medium",
    risk_score: 42,
    review_status: "auto_accepted",
  },
  {
    id: "clause_003",
    contract_id: "contract_msa_001",
    clause_type: "payment_terms",
    extracted_text:
      "Invoices shall be due net thirty (30) days from receipt. Late payments accrue interest at 1.5% per month.",
    page_number: 5,
    section_reference: "Section 3.2",
    confidence: 0.97,
    risk_level: "low",
    risk_score: 15,
    review_status: "auto_accepted",
  },
  {
    id: "clause_004",
    contract_id: "contract_msa_001",
    clause_type: "termination_convenience",
    extracted_text:
      "Either party may terminate this Agreement without cause upon thirty (30) days written notice to the other party.",
    page_number: 8,
    section_reference: "Section 5.1(a)",
    confidence: 0.82,
    risk_level: "medium",
    risk_score: 58,
    review_status: "pending_review",
  },
  {
    id: "clause_005",
    contract_id: "contract_sow_001",
    clause_type: "assignment",
    extracted_text:
      "Neither party may assign this SOW without prior written consent of the other party, not to be unreasonably withheld.",
    page_number: 3,
    section_reference: "Section 2.1",
    confidence: 0.91,
    risk_level: "low",
    risk_score: 25,
    review_status: "auto_accepted",
  },
  {
    id: "clause_006",
    contract_id: "contract_sow_001",
    clause_type: "indemnification",
    extracted_text:
      "Vendor indemnifies Client for IP infringement claims. Indemnification is subject to the liability limitations in Section 3.",
    page_number: 11,
    section_reference: "Section 8.2",
    confidence: 0.85,
    risk_level: "medium",
    risk_score: 48,
    review_status: "auto_accepted",
  },
  {
    id: "clause_007",
    contract_id: "contract_vendor_001",
    clause_type: "auto_renewal",
    extracted_text:
      "This Agreement shall automatically renew for successive one-year terms unless either party provides written notice of non-renewal at least ninety (90) days prior to expiration.",
    page_number: 2,
    section_reference: "Section 1.3",
    confidence: 0.93,
    risk_level: "high",
    risk_score: 72,
    review_status: "auto_accepted",
  },
  {
    id: "clause_008",
    contract_id: "contract_lease_001",
    clause_type: "termination_cause",
    extracted_text:
      "Landlord may terminate this Lease for material non-payment of rent, with fifteen (15) days to cure after notice.",
    page_number: 22,
    section_reference: "Section 18.1",
    confidence: 0.89,
    risk_level: "critical",
    risk_score: 92,
    review_status: "pending_review",
  },
];

// Risk flags across contracts
const RISK_FLAGS = [
  {
    id: "flag_001",
    clause_id: "clause_001",
    flag_type: "change_of_control_trigger",
    severity: "critical",
    description:
      "Change of control triggers termination right for counterparty with only 60 days notice",
    recommendation:
      "Negotiate for consent requirement or extend notice to 90+ days",
  },
  {
    id: "flag_002",
    clause_id: "clause_004",
    flag_type: "short_notice_period",
    severity: "warning",
    description:
      "30-day termination notice is below market standard (60-90 days typical)",
    recommendation: "Extend notice period to minimum 60 days",
  },
  {
    id: "flag_003",
    clause_id: "clause_007",
    flag_type: "auto_renewal_trap",
    severity: "critical",
    description:
      "Auto-renewal with 90-day notice requirement could cause renewal beyond intended deal period",
    recommendation:
      "Modify to manual renewal or align renewal date with post-acquisition transition plan",
  },
  {
    id: "flag_004",
    clause_id: "clause_008",
    flag_type: "short_cure_period",
    severity: "high",
    description:
      "15-day cure period for rent payment is aggressive; market standard is 30 days",
    recommendation:
      "Negotiate for 30-day cure period to align with target's cash management practices",
  },
];

// ============================================================================
// COLOR UTILITIES
// ============================================================================

const getRiskColor = (risk_level) => {
  switch (risk_level) {
    case "critical":
      return "#dc2626";
    case "high":
      return "#ea580c";
    case "medium":
      return "#eab308";
    case "low":
      return "#16a34a";
    default:
      return "#6b7280";
  }
};

const getConfidenceColor = (confidence) => {
  if (confidence >= 0.9) return "#22c55e";
  if (confidence >= 0.8) return "#3b82f6";
  if (confidence >= 0.7) return "#f59e0b";
  return "#ef4444";
};

const getStatusBadgeColor = (status) => {
  switch (status) {
    case "reviewed":
    case "success":
      return "bg-green-100 text-green-800";
    case "review_pending":
    case "warning":
      return "bg-yellow-100 text-yellow-800";
    case "extracted":
      return "bg-blue-100 text-blue-800";
    case "processing":
      return "bg-purple-100 text-purple-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
};

// ============================================================================
// VIEW 1: DEAL DASHBOARD
// ============================================================================

function DealDashboard() {
  const contracts = DEAL_DATA.contracts;

  // Calculate aggregate metrics
  const total_contracts = contracts.length;
  const total_clauses = CLAUSE_DATA.length;
  const total_critical = CLAUSE_DATA.filter(
    (c) => c.risk_level === "critical"
  ).length;
  const total_high = CLAUSE_DATA.filter((c) => c.risk_level === "high").length;
  const reviewed = contracts.filter(
    (c) => c.processing_status === "reviewed"
  ).length;
  const completion_pct = Math.round((reviewed / total_contracts) * 100);

  // Data for risk distribution chart
  const risk_distribution = [
    {
      name: "Critical",
      value: total_critical,
      fill: "#dc2626",
    },
    {
      name: "High",
      value: total_high,
      fill: "#ea580c",
    },
    {
      name: "Medium",
      value: CLAUSE_DATA.filter((c) => c.risk_level === "medium").length,
      fill: "#eab308",
    },
    {
      name: "Low",
      value: CLAUSE_DATA.filter((c) => c.risk_level === "low").length,
      fill: "#16a34a",
    },
  ];

  // Data for contract status chart
  const contract_status = contracts.map((c) => ({
    filename: c.filename.replace(".pdf", "").slice(0, 15),
    clauses: c.clauses_count,
    critical: c.risk_summary.critical,
    high: c.risk_summary.high,
    medium: c.risk_summary.medium,
    low: c.risk_summary.low,
  }));

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">
              Total Contracts
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{total_contracts}</div>
            <p className="text-xs text-gray-500 mt-1">{reviewed} reviewed</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">
              Total Clauses
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{total_clauses}</div>
            <p className="text-xs text-gray-500 mt-1">extracted & analyzed</p>
          </CardContent>
        </Card>

        <Card className="border-red-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-red-600">
              Critical Flags
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{total_critical}</div>
            <p className="text-xs text-gray-500 mt-1">require immediate attention</p>
          </CardContent>
        </Card>

        <Card className="border-orange-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-orange-600">
              High Risk
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{total_high}</div>
            <p className="text-xs text-gray-500 mt-1">should be negotiated</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">
              Review Progress
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{completion_pct}%</div>
            <Progress value={completion_pct} className="mt-2" />
          </CardContent>
        </Card>
      </div>

      {/* Risk Distribution */}
      <Card>
        <CardHeader>
          <CardTitle>Risk Distribution</CardTitle>
          <CardDescription>
            Clause risk levels across all {total_contracts} contracts
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={risk_distribution}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                {risk_distribution.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Contract Summary Table */}
      <Card>
        <CardHeader>
          <CardTitle>Contract Portfolio</CardTitle>
          <CardDescription>
            Status of {total_contracts} contracts in deal
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {contracts.map((contract) => (
              <div
                key={contract.id}
                className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50"
              >
                <div className="flex-1">
                  <div className="font-medium text-sm">
                    {contract.filename}
                  </div>
                  <div className="flex gap-3 text-xs text-gray-600 mt-1">
                    <span>{contract.page_count} pages</span>
                    <span>•</span>
                    <span>{contract.clauses_count} clauses</span>
                    <span>•</span>
                    <Badge variant="outline" className="text-xs">
                      {contract.contract_type.toUpperCase()}
                    </Badge>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="flex gap-1">
                    {contract.risk_summary.critical > 0 && (
                      <Badge variant="destructive" className="text-xs">
                        {contract.risk_summary.critical} Critical
                      </Badge>
                    )}
                    {contract.risk_summary.high > 0 && (
                      <Badge
                        variant="secondary"
                        className="text-xs bg-orange-100 text-orange-800"
                      >
                        {contract.risk_summary.high} High
                      </Badge>
                    )}
                  </div>

                  <Badge className={`${getStatusBadgeColor(contract.status_color)} text-xs`}>
                    {contract.processing_status === "reviewed"
                      ? "✓ Reviewed"
                      : "Pending"}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ============================================================================
// VIEW 2: CONTRACT VIEWER (SPLIT PANE)
// ============================================================================

function ContractViewer() {
  const [selectedContractId, setSelectedContractId] = useState(
    "contract_msa_001"
  );
  const contract = DEAL_DATA.contracts.find((c) => c.id === selectedContractId);
  const clauses = CLAUSE_DATA.filter((c) => c.contract_id === selectedContractId);

  const contractText = `MASTER SERVICE AGREEMENT

This Master Service Agreement ("Agreement") is entered into as of March 1, 2024 ("Effective Date"),
between Acme Corporation, a Delaware corporation ("Client"), and Target Corporation, a New York
corporation ("Vendor").

RECITALS

WHEREAS, Vendor provides professional services in the areas of software development and
IT consulting;

WHEREAS, Client desires to engage Vendor to provide such services under the terms and conditions
set forth herein;

NOW, THEREFORE, in consideration of the mutual covenants and agreements contained herein,
the parties agree as follows:

SECTION 1: SERVICES
1.1 Scope of Services. Vendor shall provide software development, system integration, and
IT consulting services as further described in Statements of Work ("SOWs") to be executed
pursuant to this Agreement.

SECTION 3: PAYMENT TERMS
3.2 Invoicing. Invoices shall be due net thirty (30) days from receipt. Late payments accrue
interest at 1.5% per month or the maximum rate allowed by law, whichever is less.

SECTION 5: TERMINATION
5.1(a) Termination for Convenience. Either party may terminate this Agreement without cause
upon thirty (30) days written notice to the other party. Upon such termination, Client shall
pay Vendor for all services performed through the effective date of termination.

SECTION 10: LIMITATION OF LIABILITY
10.1 Aggregate Cap. Neither party's aggregate liability under this Agreement shall be limited
to the total fees paid by Client in the twelve (12) months immediately preceding the date of
the claim, except for: (a) indemnification obligations; (b) breach of confidentiality;
(c) gross negligence or willful misconduct.

SECTION 14: ASSIGNMENT AND CHANGE OF CONTROL
14.2(b) Change of Control. In the event of a Change of Control of either party, the non-affected
party shall have the right to terminate this Agreement upon sixty (60) days written notice.
"Change of Control" means: (i) acquisition of >50% voting securities; (ii) merger where party
does not own >50% post-transaction; (iii) sale of substantially all assets. Notwithstanding the
foregoing, a Change of Control shall not include acquisitions of securities by employee stock
ownership plans or reorganizations among entities under common control.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the Effective Date.

ACME CORPORATION                    TARGET CORPORATION
By: ____________________           By: ____________________
Name: John Smith                    Name: Jane Doe
Title: CEO                         Title: VP Business Development
Date: January 15, 2024             Date: January 15, 2024`;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Select Contract</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
            {DEAL_DATA.contracts.map((c) => (
              <button
                key={c.id}
                onClick={() => setSelectedContractId(c.id)}
                className={`text-xs p-2 rounded border text-center ${
                  selectedContractId === c.id
                    ? "bg-blue-100 border-blue-300"
                    : "hover:bg-gray-100"
                }`}
              >
                {c.contract_type.toUpperCase()}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {contract && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">{contract.filename}</CardTitle>
            <CardDescription>
              {contract.clauses_count} clauses extracted • Pages{" "}
              {contract.page_count}
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 h-[600px]">
        {/* LEFT PANE: Contract Text */}
        <Card className="flex flex-col">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Original Contract Text</CardTitle>
          </CardHeader>
          <CardContent className="flex-1 overflow-y-auto">
            <pre className="text-xs whitespace-pre-wrap font-mono leading-relaxed text-gray-700">
              {contractText}
            </pre>
          </CardContent>
        </Card>

        {/* RIGHT PANE: Extracted Clauses */}
        <Card className="flex flex-col">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Extracted Clauses</CardTitle>
            <CardDescription>{clauses.length} clauses</CardDescription>
          </CardHeader>
          <CardContent className="flex-1 overflow-y-auto space-y-3">
            {clauses.map((clause) => (
              <div
                key={clause.id}
                className="p-3 border rounded-lg bg-gray-50 hover:bg-gray-100"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-xs text-gray-900">
                      {clause.clause_type.replace(/_/g, " ").toUpperCase()}
                    </div>
                    <div className="text-xs text-gray-600 mt-1 line-clamp-2">
                      {clause.extracted_text}
                    </div>
                    <div className="flex gap-2 mt-2 flex-wrap">
                      <Badge
                        variant="outline"
                        className="text-xs"
                        style={{
                          backgroundColor: getConfidenceColor(clause.confidence),
                          color: "white",
                          border: "none",
                        }}
                      >
                        {Math.round(clause.confidence * 100)}% conf
                      </Badge>
                      <Badge
                        variant="outline"
                        className="text-xs"
                        style={{
                          backgroundColor: getRiskColor(clause.risk_level),
                          color: "white",
                          border: "none",
                        }}
                      >
                        Risk: {clause.risk_level}
                      </Badge>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ============================================================================
// VIEW 3: RISK MATRIX
// ============================================================================

function RiskMatrix() {
  // Prepare data for scatter plot: confidence vs risk_score
  const scatterData = CLAUSE_DATA.map((clause) => ({
    ...clause,
    x: clause.confidence * 100,
    y: clause.risk_score,
    fill: getRiskColor(clause.risk_level),
  }));

  // Clause type distribution
  const clauseTypes = {};
  CLAUSE_DATA.forEach((clause) => {
    clauseTypes[clause.clause_type] =
      (clauseTypes[clause.clause_type] || 0) + 1;
  });

  const typeDistribution = Object.entries(clauseTypes)
    .map(([type, count]) => ({
      name: type.replace(/_/g, " "),
      value: count,
    }))
    .sort((a, b) => b.value - a.value);

  return (
    <div className="space-y-6">
      {/* Risk Flags Alert */}
      {RISK_FLAGS.filter((f) => f.severity === "critical").length > 0 && (
        <Alert className="border-red-200 bg-red-50">
          <AlertDescription className="text-red-800 text-sm">
            <strong>
              {RISK_FLAGS.filter((f) => f.severity === "critical").length}{" "}
              Critical Issues Identified
            </strong>
            - Review and address these items before deal close
          </AlertDescription>
        </Alert>
      )}

      {/* Scatter: Confidence vs Risk Score */}
      <Card>
        <CardHeader>
          <CardTitle>Confidence vs. Risk Score Matrix</CardTitle>
          <CardDescription>
            Each point = one extracted clause. High-risk, low-confidence clauses
            (upper-left) require review.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={400}>
            <ScatterChart
              margin={{ top: 20, right: 20, bottom: 20, left: 20 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                type="number"
                dataKey="x"
                name="Confidence (%)"
                domain={[0, 100]}
              />
              <YAxis type="number" dataKey="y" name="Risk Score" domain={[0, 100]} />
              <Tooltip
                cursor={{ strokeDasharray: "3 3" }}
                content={({ active, payload }) => {
                  if (active && payload && payload[0]) {
                    const data = payload[0].payload;
                    return (
                      <div className="bg-white p-2 border rounded text-xs">
                        <p className="font-semibold">{data.clause_type}</p>
                        <p>Confidence: {Math.round(data.x)}%</p>
                        <p>Risk: {data.y}</p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Scatter
                name="Clauses"
                data={scatterData}
                shape="circle"
                fill="#3b82f6"
              >
                {scatterData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Clause Type Distribution */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Clauses by Type</CardTitle>
            <CardDescription>
              Distribution across {typeDistribution.length} clause types
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={typeDistribution}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={(entry) => `${entry.name}: ${entry.value}`}
                  outerRadius={80}
                  fill="#3b82f6"
                  dataKey="value"
                >
                  {typeDistribution.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={
                        [
                          "#3b82f6",
                          "#8b5cf6",
                          "#ec4899",
                          "#f59e0b",
                          "#10b981",
                          "#06b6d4",
                        ][index % 6]
                      }
                    />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Critical & High Risk Flags */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Risk Flags Summary</CardTitle>
            <CardDescription>
              {RISK_FLAGS.length} total flags identified
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {RISK_FLAGS.sort((a, b) => {
                const order = { critical: 0, high: 1, warning: 2, info: 3 };
                return order[a.severity] - order[b.severity];
              }).map((flag) => (
                <div
                  key={flag.id}
                  className="p-2 border rounded-lg text-xs space-y-1"
                  style={{
                    backgroundColor:
                      flag.severity === "critical"
                        ? "#fee2e2"
                        : flag.severity === "high"
                        ? "#fef3c7"
                        : "#f3f4f6",
                    borderColor:
                      flag.severity === "critical"
                        ? "#fca5a5"
                        : flag.severity === "high"
                        ? "#fcd34d"
                        : "#d1d5db",
                  }}
                >
                  <div className="font-semibold flex items-center gap-2">
                    <Badge
                      variant="outline"
                      className="text-xs"
                      style={{
                        backgroundColor: getRiskColor(flag.severity),
                        color: "white",
                        border: "none",
                      }}
                    >
                      {flag.severity.toUpperCase()}
                    </Badge>
                    {flag.flag_type.replace(/_/g, " ")}
                  </div>
                  <p>{flag.description}</p>
                  <p className="text-gray-600">✓ {flag.recommendation}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ============================================================================
// MAIN DASHBOARD COMPONENT
// ============================================================================

export function ContractDashboard() {
  return (
    <div className="w-full max-w-7xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">Contract Intelligence Dashboard</h1>
        <p className="text-gray-600">
          {DEAL_DATA.name} • {DEAL_DATA.deal_type.toUpperCase()} •{" "}
          {DEAL_DATA.deal_value}
        </p>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="dashboard" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="dashboard">Deal Dashboard</TabsTrigger>
          <TabsTrigger value="viewer">Contract Viewer</TabsTrigger>
          <TabsTrigger value="matrix">Risk Matrix</TabsTrigger>
        </TabsList>

        <TabsContent value="dashboard" className="space-y-4">
          <DealDashboard />
        </TabsContent>

        <TabsContent value="viewer" className="space-y-4">
          <ContractViewer />
        </TabsContent>

        <TabsContent value="matrix" className="space-y-4">
          <RiskMatrix />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default ContractDashboard;
