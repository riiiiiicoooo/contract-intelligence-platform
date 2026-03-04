import React from "react";
import {
  Body,
  Button,
  Container,
  Head,
  Hr,
  Html,
  Img,
  Link,
  Preview,
  Row,
  Section,
  Text,
} from "@react-email/components";

interface ExtractionCompleteEmailProps {
  contractName: string;
  extractionId: string;
  contractType: string;
  clausesExtracted: number;
  criticalFlagsCount: number;
  highFlagsCount: number;
  mediumFlagsCount: number;
  avgConfidence: number;
  dealName: string;
  dealId: string;
  analyzeUrl: string;
  userName: string;
}

const baseUrl = process.env.VERCEL_URL
  ? `https://${process.env.VERCEL_URL}`
  : "https://app.contract-intelligence.app";

export const ExtractionCompleteEmail: React.FC<ExtractionCompleteEmailProps> = ({
  contractName,
  extractionId,
  contractType,
  clausesExtracted,
  criticalFlagsCount,
  highFlagsCount,
  mediumFlagsCount,
  avgConfidence,
  dealName,
  dealId,
  analyzeUrl,
  userName,
}) => (
  <Html>
    <Head />
    <Preview>Contract extraction complete: {contractName}</Preview>
    <Body style={main}>
      <Container style={container}>
        {/* Header */}
        <Section style={headerSection}>
          <Row>
            <Text style={logo}>📋 Contract Intelligence</Text>
          </Row>
          <Text style={headerText}>Extraction Complete</Text>
        </Section>

        <Hr style={divider} />

        {/* Main Content */}
        <Section style={content}>
          <Text style={greeting}>Hi {userName},</Text>

          <Text style={bodyText}>
            Extraction is complete for <strong>{contractName}</strong> in{" "}
            <strong>{dealName}</strong>. Here's a summary of what we found:
          </Text>

          {/* Contract Summary Card */}
          <Section style={summaryCard}>
            <Row style={summaryRow}>
              <Text style={summaryLabel}>Contract Name</Text>
              <Text style={summaryValue}>{contractName}</Text>
            </Row>
            <Row style={summaryRow}>
              <Text style={summaryLabel}>Type</Text>
              <Text style={summaryValue}>{contractType.toUpperCase()}</Text>
            </Row>
            <Row style={summaryRow}>
              <Text style={summaryLabel}>Clauses Extracted</Text>
              <Text style={summaryValue}>{clausesExtracted}</Text>
            </Row>
            <Row style={summaryRow}>
              <Text style={summaryLabel}>Extraction Confidence</Text>
              <Text style={summaryValue}>{(avgConfidence * 100).toFixed(1)}%</Text>
            </Row>
          </Section>

          {/* Risk Flags Section */}
          <Text style={sectionHeading}>Risk Flags Found:</Text>

          <Section style={flagsContainer}>
            {criticalFlagsCount > 0 && (
              <Row style={flagRow}>
                <Text style={flagLabel}>🔴 Critical</Text>
                <Text style={flagCount}>{criticalFlagsCount}</Text>
              </Row>
            )}
            {highFlagsCount > 0 && (
              <Row style={flagRow}>
                <Text style={flagLabel}>🟠 High</Text>
                <Text style={flagCount}>{highFlagsCount}</Text>
              </Row>
            )}
            {mediumFlagsCount > 0 && (
              <Row style={flagRow}>
                <Text style={flagLabel}>🟡 Medium</Text>
                <Text style={flagCount}>{mediumFlagsCount}</Text>
              </Row>
            )}
            {criticalFlagsCount === 0 && highFlagsCount === 0 && mediumFlagsCount === 0 && (
              <Text style={noFlagsText}>✓ No significant risks detected</Text>
            )}
          </Section>

          <Hr style={divider} />

          {/* Call to Action */}
          <Text style={ctaText}>Review the detailed extraction and risk analysis:</Text>

          <Section style={ctaSection}>
            <Button style={button} href={analyzeUrl}>
              Review Extraction
            </Button>
          </Section>

          {/* Next Steps */}
          <Section style={nextSteps}>
            <Text style={nextStepsHeading}>Next Steps:</Text>
            <Text style={nextStepsItem}>
              1. Review extracted clauses and confirm accuracy
            </Text>
            <Text style={nextStepsItem}>
              2. Address any critical or high-risk flags
            </Text>
            <Text style={nextStepsItem}>
              3. Run cross-contract analysis when all documents are extracted
            </Text>
            <Text style={nextStepsItem}>
              4. Generate deal matrix and risk report for stakeholders
            </Text>
          </Section>

          <Hr style={divider} />

          {/* Footer */}
          <Section style={footer}>
            <Text style={footerText}>
              <strong>Extraction ID:</strong> {extractionId}
            </Text>
            <Text style={footerText}>
              <strong>Timestamp:</strong>{" "}
              {new Date().toLocaleString("en-US", {
                timeZone: "America/New_York",
              })}
            </Text>
            <Text style={footerText}>
              Questions? <Link href="mailto:support@contract-intelligence.app">
                Contact support
              </Link>
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
  padding: "24px",
  textAlign: "center" as const,
};

const logo = {
  fontSize: "20px",
  fontWeight: "bold" as const,
  margin: "0 0 12px 0",
  color: "#ffffff",
};

const headerText = {
  fontSize: "28px",
  fontWeight: "bold" as const,
  margin: "0",
  color: "#ffffff",
};

const content = {
  padding: "32px",
};

const greeting = {
  fontSize: "16px",
  fontWeight: "600" as const,
  marginBottom: "16px",
  color: "#1f2937",
};

const bodyText = {
  fontSize: "14px",
  lineHeight: "1.6",
  color: "#4b5563",
  marginBottom: "24px",
};

const summaryCard = {
  backgroundColor: "#f9fafb",
  border: "1px solid #e5e7eb",
  borderRadius: "6px",
  padding: "16px",
  marginBottom: "24px",
};

const summaryRow = {
  display: "flex" as const,
  justifyContent: "space-between" as const,
  paddingBottom: "12px",
  borderBottom: "1px solid #e5e7eb",
  marginBottom: "12px",
};

const summaryLabel = {
  fontSize: "13px",
  fontWeight: "600" as const,
  color: "#6b7280",
  margin: "0",
};

const summaryValue = {
  fontSize: "13px",
  fontWeight: "600" as const,
  color: "#1f2937",
  margin: "0",
};

const sectionHeading = {
  fontSize: "14px",
  fontWeight: "600" as const,
  color: "#1f2937",
  marginBottom: "12px",
  marginTop: "20px",
};

const flagsContainer = {
  backgroundColor: "#fef3c7",
  border: "1px solid #fcd34d",
  borderRadius: "6px",
  padding: "12px",
  marginBottom: "24px",
};

const flagRow = {
  display: "flex" as const,
  justifyContent: "space-between" as const,
  paddingBottom: "8px",
  marginBottom: "8px",
};

const flagLabel = {
  fontSize: "13px",
  fontWeight: "600" as const,
  color: "#1f2937",
  margin: "0",
};

const flagCount = {
  fontSize: "13px",
  fontWeight: "bold" as const,
  color: "#d97706",
  margin: "0",
};

const noFlagsText = {
  fontSize: "13px",
  color: "#059669",
  fontWeight: "600" as const,
  margin: "0",
};

const divider = {
  borderColor: "#e5e7eb",
  margin: "24px 0",
};

const ctaText = {
  fontSize: "14px",
  color: "#4b5563",
  marginBottom: "16px",
  textAlign: "center" as const,
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

const nextSteps = {
  backgroundColor: "#eff6ff",
  border: "1px solid #bfdbfe",
  borderRadius: "6px",
  padding: "16px",
  marginBottom: "24px",
};

const nextStepsHeading = {
  fontSize: "14px",
  fontWeight: "600" as const,
  color: "#1f2937",
  marginBottom: "12px",
  margin: "0 0 12px 0",
};

const nextStepsItem = {
  fontSize: "13px",
  color: "#4b5563",
  margin: "0 0 8px 0",
  lineHeight: "1.5",
};

const footer = {
  backgroundColor: "#f9fafb",
  padding: "16px",
  borderTop: "1px solid #e5e7eb",
};

const footerText = {
  fontSize: "12px",
  color: "#6b7280",
  margin: "0 0 8px 0",
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

export default ExtractionCompleteEmail;
