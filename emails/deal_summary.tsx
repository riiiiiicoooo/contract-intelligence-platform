import React from "react";
import {
  Body,
  Button,
  Container,
  Head,
  Hr,
  Html,
  Link,
  Preview,
  Row,
  Section,
  Text,
} from "@react-email/components";

interface DealProgressItem {
  name: string;
  status: "completed" | "in_progress" | "pending";
  clauses_extracted?: number;
}

interface RiskSummary {
  critical: number;
  high: number;
  medium: number;
  low: number;
}

interface DealSummaryEmailProps {
  dealName: string;
  dealId: string;
  partnersName: string;
  weekStartDate: string;
  weekEndDate: string;
  contractsProcessed: number;
  contractsRemaining: number;
  totalContractCount: number;
  riskMatrix: RiskSummary;
  recentContracts: DealProgressItem[];
  pendingReviews: number;
  actionItems: Array<{
    title: string;
    priority: "high" | "medium" | "low";
    dueDate: string;
  }>;
  dashboardUrl: string;
}

const baseUrl = process.env.VERCEL_URL
  ? `https://${process.env.VERCEL_URL}`
  : "https://app.contract-intelligence.app";

export const DealSummaryEmail: React.FC<DealSummaryEmailProps> = ({
  dealName,
  dealId,
  partnersName,
  weekStartDate,
  weekEndDate,
  contractsProcessed,
  contractsRemaining,
  totalContractCount,
  riskMatrix,
  recentContracts,
  pendingReviews,
  actionItems,
  dashboardUrl,
}) => (
  <Html>
    <Head />
    <Preview>Weekly Deal Summary: {dealName}</Preview>
    <Body style={main}>
      <Container style={container}>
        {/* Header */}
        <Section style={headerSection}>
          <Text style={headerTitle}>📊 Weekly Deal Digest</Text>
          <Text style={headerSubtitle}>
            {weekStartDate} - {weekEndDate}
          </Text>
        </Section>

        {/* Main Content */}
        <Section style={content}>
          <Text style={greeting}>Hi {partnersName},</Text>

          <Text style={bodyText}>
            Here's your weekly progress update on <strong>{dealName}</strong>:
          </Text>

          <Hr style={divider} />

          {/* Progress Metrics */}
          <Text style={sectionHeading}>Deal Progress</Text>

          <Section style={progressCard}>
            <Row style={progressRow}>
              <Text style={progressLabel}>Contracts Processed</Text>
              <Text style={progressValue}>
                {contractsProcessed} of {totalContractCount}
              </Text>
            </Row>
            <Row style={progressRow}>
              <Text style={progressLabel}>Remaining</Text>
              <Text style={progressValue}>{contractsRemaining}</Text>
            </Row>
            <Row style={progressRow}>
              <Text style={progressLabel}>Completion</Text>
              <Text style={progressValue}>
                {((contractsProcessed / totalContractCount) * 100).toFixed(0)}%
              </Text>
            </Row>
          </Section>

          {/* Risk Matrix */}
          <Text style={sectionHeading}>Risk Matrix Summary</Text>

          <Section style={riskMatrixCard}>
            <Row style={riskMatrixRow}>
              <Section style={riskCell}>
                <Text style={riskCellLabel}>🔴 Critical</Text>
                <Text style={riskCellValue}>{riskMatrix.critical}</Text>
              </Section>
              <Section style={riskCell}>
                <Text style={riskCellLabel}>🟠 High</Text>
                <Text style={riskCellValue}>{riskMatrix.high}</Text>
              </Section>
              <Section style={riskCell}>
                <Text style={riskCellLabel}>🟡 Medium</Text>
                <Text style={riskCellValue}>{riskMatrix.medium}</Text>
              </Section>
              <Section style={riskCell}>
                <Text style={riskCellLabel}>🟢 Low</Text>
                <Text style={riskCellValue}>{riskMatrix.low}</Text>
              </Section>
            </Row>
          </Section>

          <Hr style={divider} />

          {/* Recent Processing */}
          <Text style={sectionHeading}>Recent Contract Processing</Text>

          <Section style={contractsList}>
            {recentContracts.map((contract, idx) => (
              <Row key={idx} style={contractRow}>
                <Text style={contractName}>{contract.name}</Text>
                <Text style={getStatusStyle(contract.status)}>
                  {contract.status === "completed"
                    ? `✓ ${contract.clauses_extracted} clauses`
                    : contract.status === "in_progress"
                    ? "⏳ In Progress"
                    : "⏹️ Pending"}
                </Text>
              </Row>
            ))}
          </Section>

          <Hr style={divider} />

          {/* Pending Reviews */}
          {pendingReviews > 0 && (
            <>
              <Section style={alertCard}>
                <Text style={alertHeading}>⚠️ Action Required</Text>
                <Text style={alertText}>
                  {pendingReviews} extraction{pendingReviews > 1 ? "s" : ""} pending analyst
                  review (confidence &lt; 0.85).
                </Text>
              </Section>

              <Hr style={divider} />
            </>
          )}

          {/* Action Items */}
          {actionItems.length > 0 && (
            <>
              <Text style={sectionHeading}>Action Items</Text>

              <Section style={actionItemsContainer}>
                {actionItems.map((item, idx) => (
                  <Row key={idx} style={actionItemRow}>
                    <Text style={getActionItemPriorityStyle(item.priority)}>
                      {item.priority === "high"
                        ? "🔴"
                        : item.priority === "medium"
                        ? "🟡"
                        : "🟢"}
                    </Text>
                    <Text style={actionItemText}>{item.title}</Text>
                    <Text style={actionItemDate}>Due: {item.dueDate}</Text>
                  </Row>
                ))}
              </Section>

              <Hr style={divider} />
            </>
          )}

          {/* CTA */}
          <Section style={ctaSection}>
            <Button style={button} href={dashboardUrl}>
              View Full Deal Dashboard
            </Button>
          </Section>

          {/* Stats Footer */}
          <Section style={statsFooter}>
            <Text style={statsText}>
              This week: <strong>{contractsProcessed}</strong> contracts processed |{" "}
              <strong>{riskMatrix.critical + riskMatrix.high}</strong> high-risk flags |{" "}
              <strong>{pendingReviews}</strong> pending reviews
            </Text>
          </Section>
        </Section>

        {/* Copyright */}
        <Section style={copyright}>
          <Text style={copyrightText}>
            © {new Date().getFullYear()} Contract Intelligence Platform. All rights reserved.
          </Text>
          <Text style={disclaimer}>
            This message contains attorney work product and confidential information.
            If you received this email in error, please delete it immediately.
          </Text>
        </Section>
      </Container>
    </Body>
  </Html>
);

// ============================================================================
// Helper function to get status style
// ============================================================================

function getStatusStyle(status: string): React.CSSProperties {
  const baseStyle: React.CSSProperties = {
    fontSize: "12px",
    fontWeight: "600" as const,
    margin: "0",
  };

  if (status === "completed") {
    return { ...baseStyle, color: "#059669" };
  } else if (status === "in_progress") {
    return { ...baseStyle, color: "#2563eb" };
  }
  return { ...baseStyle, color: "#d97706" };
}

function getActionItemPriorityStyle(_priority: string): React.CSSProperties {
  return {
    fontSize: "14px",
    fontWeight: "bold" as const,
    margin: "0 8px 0 0",
  };
}

// ============================================================================
// Styles
// ============================================================================

const main = {
  backgroundColor: "#f3f4f6",
  fontFamily: '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Ubuntu,sans-serif',
};

const container = {
  maxWidth: "600px",
  margin: "0 auto",
  backgroundColor: "#ffffff",
  borderRadius: "8px",
  overflow: "hidden",
  boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
};

const headerSection = {
  backgroundColor: "#1f2937",
  color: "#ffffff",
  padding: "32px 24px",
  textAlign: "center" as const,
};

const headerTitle = {
  fontSize: "24px",
  fontWeight: "bold" as const,
  margin: "0 0 8px 0",
  color: "#ffffff",
};

const headerSubtitle = {
  fontSize: "14px",
  color: "#d1d5db",
  margin: "0",
};

const content = {
  padding: "32px",
};

const greeting = {
  fontSize: "16px",
  fontWeight: "600" as const,
  marginBottom: "12px",
  color: "#1f2937",
};

const bodyText = {
  fontSize: "14px",
  lineHeight: "1.6",
  color: "#4b5563",
  marginBottom: "24px",
};

const sectionHeading = {
  fontSize: "14px",
  fontWeight: "bold" as const,
  color: "#1f2937",
  marginBottom: "12px",
  marginTop: "20px",
};

const progressCard = {
  backgroundColor: "#f0f9ff",
  border: "1px solid #bfdbfe",
  borderRadius: "6px",
  padding: "16px",
  marginBottom: "24px",
};

const progressRow = {
  display: "flex" as const,
  justifyContent: "space-between" as const,
  paddingBottom: "12px",
  marginBottom: "12px",
  borderBottom: "1px solid #bfdbfe",
};

const progressLabel = {
  fontSize: "13px",
  fontWeight: "600" as const,
  color: "#1f2937",
  margin: "0",
};

const progressValue = {
  fontSize: "13px",
  fontWeight: "bold" as const,
  color: "#2563eb",
  margin: "0",
};

const riskMatrixCard = {
  backgroundColor: "#fff7ed",
  border: "1px solid #fed7aa",
  borderRadius: "6px",
  padding: "16px",
  marginBottom: "24px",
};

const riskMatrixRow = {
  display: "flex" as const,
  justifyContent: "space-around" as const,
};

const riskCell = {
  textAlign: "center" as const,
  flex: 1,
};

const riskCellLabel = {
  fontSize: "12px",
  fontWeight: "600" as const,
  color: "#6b7280",
  margin: "0 0 8px 0",
};

const riskCellValue = {
  fontSize: "18px",
  fontWeight: "bold" as const,
  color: "#1f2937",
  margin: "0",
};

const contractsList = {
  backgroundColor: "#f9fafb",
  border: "1px solid #e5e7eb",
  borderRadius: "6px",
  padding: "12px",
  marginBottom: "24px",
};

const contractRow = {
  display: "flex" as const,
  justifyContent: "space-between" as const,
  paddingBottom: "8px",
  marginBottom: "8px",
  paddingBottom: "8px",
  borderBottom: "1px solid #e5e7eb",
};

const contractName = {
  fontSize: "13px",
  fontWeight: "600" as const,
  color: "#1f2937",
  margin: "0",
};

const alertCard = {
  backgroundColor: "#fef2f2",
  border: "1px solid #fecaca",
  borderRadius: "6px",
  padding: "12px",
  marginBottom: "24px",
};

const alertHeading = {
  fontSize: "13px",
  fontWeight: "bold" as const,
  color: "#991b1b",
  margin: "0 0 8px 0",
};

const alertText = {
  fontSize: "13px",
  color: "#7f1d1d",
  margin: "0",
  lineHeight: "1.5",
};

const actionItemsContainer = {
  backgroundColor: "#f9fafb",
  border: "1px solid #e5e7eb",
  borderRadius: "6px",
  padding: "12px",
  marginBottom: "24px",
};

const actionItemRow = {
  display: "flex" as const,
  alignItems: "center" as const,
  paddingBottom: "8px",
  marginBottom: "8px",
  borderBottom: "1px solid #e5e7eb",
};

const actionItemText = {
  fontSize: "13px",
  fontWeight: "600" as const,
  color: "#1f2937",
  margin: "0",
  flex: 1,
};

const actionItemDate = {
  fontSize: "12px",
  color: "#6b7280",
  margin: "0",
};

const divider = {
  borderColor: "#e5e7eb",
  margin: "24px 0",
};

const ctaSection = {
  textAlign: "center" as const,
  marginBottom: "24px",
};

const button = {
  backgroundColor: "#2563eb",
  color: "#ffffff",
  padding: "12px 32px",
  fontSize: "14px",
  fontWeight: "600" as const,
  borderRadius: "6px",
  textDecoration: "none",
  display: "inline-block" as const,
};

const statsFooter = {
  backgroundColor: "#f3f4f6",
  padding: "12px",
  borderTop: "1px solid #e5e7eb",
  textAlign: "center" as const,
};

const statsText = {
  fontSize: "12px",
  color: "#4b5563",
  margin: "0",
  lineHeight: "1.5",
};

const copyright = {
  padding: "16px 32px",
  backgroundColor: "#f3f4f6",
  textAlign: "center" as const,
};

const copyrightText = {
  fontSize: "11px",
  color: "#9ca3af",
  margin: "0 0 8px 0",
};

const disclaimer = {
  fontSize: "10px",
  color: "#d1d5db",
  fontStyle: "italic" as const,
  margin: "0",
};

export default DealSummaryEmail;
