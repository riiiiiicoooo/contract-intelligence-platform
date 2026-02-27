"""
Contract Matrix Generator - Reference Implementation
Generates the Excel contract review matrix - the primary deliverable for M&A due diligence.
Rows = contracts, Columns = clause types, Cells = extracted text with RAG conditional formatting.
"""

from dataclasses import dataclass
from typing import Optional

# In production: import openpyxl
# from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
# from openpyxl.utils import get_column_letter


@dataclass
class MatrixConfig:
    deal_name: str
    deal_id: str
    template: str = "firm_default"
    include_risk_flags: bool = True
    include_clause_text: bool = True
    conditional_formatting: bool = True
    reviewed_only: bool = False


# Conditional formatting colors (RAG scheme)
RISK_COLORS = {
    "critical": "FF4444",  # Red
    "high": "FF8C00",      # Dark orange
    "medium": "FFD700",    # Amber/gold
    "low": "90EE90",       # Light green
    "none": "FFFFFF",      # White (no risk)
}

# Column order for clause types in the matrix
MATRIX_COLUMNS = [
    # Contract metadata columns
    "contract_name", "contract_type", "parties", "effective_date",
    "expiration_date", "governing_law",
    # P0 clause types (highest priority)
    "change_of_control", "assignment", "termination_convenience",
    "termination_cause", "indemnification", "limitation_of_liability",
    "payment_terms", "renewal_auto_renewal", "non_compete",
    "confidentiality", "ip_ownership", "force_majeure", "exclusivity",
    # P1 clause types
    "warranty_representations", "insurance_requirements", "audit_rights",
    "data_protection", "dispute_resolution", "most_favored_nation",
    "liquidated_damages", "survival_clauses",
]


class MatrixGenerator:
    """
    Generates the Excel contract matrix that deal teams deliver to clients.

    Structure:
    - Tab 1 "Contract Matrix": rows = contracts, columns = clause types
      Each cell contains clause summary + risk color coding
    - Tab 2 "Risk Flags": all risk flags with severity, description, recommendation
    - Tab 3 "Summary": aggregate statistics, risk breakdown, methodology

    Runs as Celery async task. Typical generation time: 20-60 seconds for 200 contracts.
    """

    def generate(self, config: MatrixConfig, contracts: list, clauses: list) -> str:
        """
        Generate Excel matrix and return file path.

        Args:
            config: Matrix configuration (template, formatting options)
            contracts: List of contract records with metadata
            clauses: List of extracted clauses across all contracts

        Returns:
            Path to generated .xlsx file
        """
        # In production:
        # wb = openpyxl.Workbook()
        # self._create_matrix_tab(wb, config, contracts, clauses)
        # self._create_risk_flags_tab(wb, config, clauses)
        # self._create_summary_tab(wb, config, contracts, clauses)
        # self._apply_branding(wb, config.template)
        #
        # output_path = f"/tmp/exports/{config.deal_id}_matrix.xlsx"
        # wb.save(output_path)
        # return output_path

        return f"/tmp/exports/{config.deal_id}_matrix.xlsx"

    def _create_matrix_tab(self, wb, config, contracts, clauses):
        """
        Build the main contract matrix tab.

        Layout:
        Row 1: Header row with column names
        Row 2+: One row per contract

        Columns A-F: Contract metadata (name, type, parties, dates, governing law)
        Columns G+: One column per clause type

        Each clause cell contains:
        - Clause summary text (first 200 chars if include_clause_text)
        - Background color based on risk level (RAG formatting)
        - "Not found" in gray if clause type wasn't extracted for this contract
        """
        # ws = wb.active
        # ws.title = "Contract Matrix"

        # Build clause lookup: {contract_id: {clause_type: clause}}
        clause_lookup = {}
        for clause in clauses:
            contract_id = clause.get("contract_id")
            clause_type = clause.get("clause_type")
            if contract_id not in clause_lookup:
                clause_lookup[contract_id] = {}
            clause_lookup[contract_id][clause_type] = clause

        # Write headers
        # for col_idx, col_name in enumerate(MATRIX_COLUMNS, 1):
        #     cell = ws.cell(row=1, column=col_idx, value=col_name.replace("_", " ").title())
        #     cell.font = Font(bold=True, color="FFFFFF")
        #     cell.fill = PatternFill(start_color="2F5496", fill_type="solid")

        # Write contract rows
        for row_idx, contract in enumerate(contracts, 2):
            contract_id = contract.get("id")

            # Metadata columns
            metadata_values = [
                contract.get("filename", ""),
                contract.get("contract_type", ""),
                self._format_parties(contract.get("parties", [])),
                str(contract.get("effective_date", "")),
                str(contract.get("expiration_date", "")),
                contract.get("governing_law", ""),
            ]

            # Clause columns
            for clause_type in MATRIX_COLUMNS[6:]:  # Skip metadata columns
                contract_clauses = clause_lookup.get(contract_id, {})
                clause = contract_clauses.get(clause_type)

                if clause:
                    text = clause.get("extracted_text", "")
                    if config.include_clause_text:
                        cell_value = text[:200] + "..." if len(text) > 200 else text
                    else:
                        cell_value = clause.get("risk_level", "").upper()

                    risk_level = clause.get("risk_level", "none")
                    # Apply conditional formatting
                    # if config.conditional_formatting:
                    #     cell.fill = PatternFill(
                    #         start_color=RISK_COLORS.get(risk_level, "FFFFFF"),
                    #         fill_type="solid"
                    #     )
                else:
                    cell_value = "Not found"
                    # Gray out missing clauses
                    # cell.font = Font(color="999999", italic=True)

    def _create_risk_flags_tab(self, wb, config, clauses):
        """
        Dedicated tab listing all risk flags across the deal.

        Columns: Contract, Clause Type, Risk Level, Description, Recommendation
        Sorted by severity (critical first), then by contract name.
        """
        # ws = wb.create_sheet("Risk Flags")
        # headers = ["Contract", "Clause Type", "Severity", "Description", "Recommendation"]
        pass

    def _create_summary_tab(self, wb, config, contracts, clauses):
        """
        Summary statistics tab.

        Contents:
        - Deal name, generation date, methodology
        - Total contracts, total clauses extracted
        - Risk breakdown (critical/high/medium/low counts)
        - Top risk categories with counts
        - Review completion percentage
        - Confidence score distribution
        """
        # ws = wb.create_sheet("Summary")
        pass

    def _apply_branding(self, wb, template: str):
        """
        Apply firm-specific branding to the workbook.

        Supported templates:
        - firm_default: Standard blue header, Calibri font
        - firm_dark: Dark theme, suitable for print
        - custom: Per-tenant configured colors and fonts
        """
        pass

    def _format_parties(self, parties: list) -> str:
        """Format party list for display in matrix cell."""
        if not parties:
            return ""
        return " / ".join(
            f"{p.get('name', '')} ({p.get('role', '')})" for p in parties
        )
