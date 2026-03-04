"""
Contract Intelligence Platform - MCP Server
Model Context Protocol implementation for contract analysis, semantic search,
risk assessment, and clause comparison. Integrates with document processing
and legal AI models for contract intelligence.
"""

import json
import os
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
import logging
from enum import Enum

from mcp.server import Server, Tool
from mcp.types import TextContent

# External API clients
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP Server
server = Server("contract-intelligence-platform")


class ContractAnalysisType(str, Enum):
    """Types of contract analysis available."""
    FULL_EXTRACTION = "full_extraction"  # Extract all clauses and key terms
    RISK_ASSESSMENT = "risk_assessment"  # Identify risk flags
    COMMERCIAL_SUMMARY = "commercial_summary"  # Extract commercial terms
    LEGAL_REVIEW = "legal_review"  # Legal compliance check


class RiskLevel(str, Enum):
    """Risk severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ContractProcessor:
    """
    Main contract processing engine using AI-powered document analysis.
    Handles file uploads, OCR, text extraction, and clause identification.
    """
    
    def __init__(self, processing_api_url: str, api_key: str):
        self.processing_api_url = processing_api_url
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=300.0,  # 5 minute timeout for document processing
        )
    
    async def analyze_contract(
        self,
        file_path: str,
        analysis_type: ContractAnalysisType = ContractAnalysisType.FULL_EXTRACTION,
    ) -> Dict[str, Any]:
        """
        Upload and analyze a contract document.
        
        Supports: PDF, DOCX, TXT, images (JPG, PNG with OCR)
        Returns: Extracted clauses, metadata, risk flags, key terms
        """
        try:
            # Read file (in production, could stream large files)
            with open(file_path, "rb") as f:
                file_content = f.read()
            
            # Upload to contract processor
            files = {"document": (os.path.basename(file_path), file_content)}
            data = {"analysis_type": analysis_type.value}
            
            response = await self.client.post(
                f"{self.processing_api_url}/analyze",
                files=files,
                data=data,
            )
            response.raise_for_status()
            
            result = response.json()
            
            logger.info(f"Contract analyzed: {file_path}, clauses found: {len(result.get('clauses', []))}")
            
            return result
        except Exception as e:
            logger.error(f"Contract analysis failed: {str(e)}")
            raise
    
    async def search_contracts(
        self,
        query: str,
        tenant_id: str,
        doc_types: Optional[List[str]] = None,
        date_range: Optional[Dict[str, str]] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search across contract corpus.
        
        Returns ranked list of relevant contracts and specific clauses.
        Supports filtering by document type and date range.
        """
        try:
            search_payload = {
                "query": query,
                "tenant_id": tenant_id,
                "top_k": min(top_k, 50),
            }
            
            if doc_types:
                search_payload["doc_types"] = doc_types
            
            if date_range:
                search_payload["date_range"] = date_range
            
            response = await self.client.post(
                f"{self.processing_api_url}/search",
                json=search_payload,
            )
            response.raise_for_status()
            
            results = response.json().get("results", [])
            logger.info(f"Contract search found {len(results)} results for: {query}")
            
            return results
        except Exception as e:
            logger.error(f"Contract search failed: {str(e)}")
            return []
    
    async def extract_clauses(
        self,
        contract_id: str,
        clause_types: Optional[List[str]] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract specific clauses from an indexed contract.
        
        Clause types: payment_terms, termination, liability_limits,
        indemnification, confidentiality, ip_rights, renewal, etc.
        """
        try:
            payload = {"contract_id": contract_id}
            if clause_types:
                payload["clause_types"] = clause_types
            
            response = await self.client.post(
                f"{self.processing_api_url}/extract_clauses",
                json=payload,
            )
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            logger.error(f"Clause extraction failed: {str(e)}")
            return {}


class RiskAssessment:
    """
    Legal risk assessment engine using rule-based and ML-based detection.
    Identifies problematic clauses, missing terms, and legal risks.
    """
    
    # Risk rules database - in production, loaded from database
    RISK_RULES = {
        "unlimited_liability": {
            "level": RiskLevel.HIGH,
            "description": "Contract contains unlimited liability clause",
            "search_terms": ["unlimited liability", "no cap on damages"],
        },
        "unilateral_termination": {
            "level": RiskLevel.MEDIUM,
            "description": "Termination rights are unilateral and not mutual",
            "search_terms": ["may terminate at any time", "termination without cause"],
        },
        "auto_renewal": {
            "level": RiskLevel.MEDIUM,
            "description": "Auto-renewal clause with short notice period for cancellation",
            "search_terms": ["automatically renews", "unless notice given"],
        },
        "indemnity_no_control": {
            "level": RiskLevel.HIGH,
            "description": "Indemnity obligation for third-party claims we don't control",
            "search_terms": ["indemnify for", "third party claims"],
        },
        "broad_ip_assignment": {
            "level": RiskLevel.HIGH,
            "description": "Broad intellectual property assignment clause",
            "search_terms": ["assign all ip", "work made for hire"],
        },
    }
    
    @staticmethod
    def assess_risks(extracted_content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Identify risks in extracted contract content.
        
        Returns list of risk flags with severity and remediation suggestions.
        """
        risks = []
        
        # Check against risk rules
        for rule_id, rule in RiskAssessment.RISK_RULES.items():
            if any(
                term.lower() in extracted_content.get("full_text", "").lower()
                for term in rule["search_terms"]
            ):
                risks.append({
                    "rule_id": rule_id,
                    "level": rule["level"].value,
                    "description": rule["description"],
                    "remediation": RiskAssessment._get_remediation(rule_id),
                })
        
        # ML-based risk detection (in production, calls model)
        if extracted_content.get("payment_terms_missing"):
            risks.append({
                "rule_id": "missing_payment_terms",
                "level": RiskLevel.MEDIUM.value,
                "description": "Contract missing clear payment terms and conditions",
                "remediation": "Add detailed payment schedule, methods, and currency",
            })
        
        return sorted(risks, key=lambda x: ["critical", "high", "medium", "low", "info"].index(x["level"]))
    
    @staticmethod
    def _get_remediation(rule_id: str) -> str:
        """Get remediation suggestion for a specific risk."""
        remediation_map = {
            "unlimited_liability": "Add cap on liability equal to 12 months of fees or contract value",
            "unilateral_termination": "Change to mutual termination rights with notice period (e.g., 60 days)",
            "auto_renewal": "Add requirement for 90+ days notice before auto-renewal",
            "indemnity_no_control": "Limit indemnity to claims arising from our negligence only",
            "broad_ip_assignment": "Carve out pre-existing IP and limit to scope of work",
            "missing_payment_terms": "Define payment schedule, methods (ACH/check/card), and currency",
        }
        return remediation_map.get(rule_id, "Review with legal team")


class ContractComparison:
    """Compare terms across multiple contracts for consistency and anomalies."""
    
    @staticmethod
    def compare_clauses(
        clause_type: str,
        contracts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Compare specific clause types across contracts.
        
        Returns comparison table with key terms, variations, and anomalies.
        """
        comparison = {
            "clause_type": clause_type,
            "contract_count": len(contracts),
            "clauses": [],
            "variations": [],
            "outliers": [],
        }
        
        for contract in contracts:
            clauses = contract.get("clauses", {}).get(clause_type, [])
            if clauses:
                for clause in clauses:
                    comparison["clauses"].append({
                        "contract_id": contract.get("contract_id"),
                        "contract_name": contract.get("contract_name"),
                        "content": clause.get("content", ""),
                        "key_terms": clause.get("key_terms", {}),
                    })
        
        # Identify variations and outliers
        comparison["variations"] = ContractComparison._find_variations(comparison["clauses"])
        comparison["outliers"] = ContractComparison._find_outliers(comparison["clauses"])
        
        return comparison
    
    @staticmethod
    def _find_variations(clauses: List[Dict[str, Any]]) -> List[str]:
        """Find significant variations in clause terms."""
        if not clauses or len(clauses) < 2:
            return []
        
        variations = []
        # In production, uses more sophisticated comparison
        variation_count = {}
        for clause in clauses:
            key_terms = str(clause.get("key_terms", {}))
            variation_count[key_terms] = variation_count.get(key_terms, 0) + 1
        
        if len(variation_count) > 1:
            variations.append(f"Found {len(variation_count)} different versions of this clause")
        
        return variations
    
    @staticmethod
    def _find_outliers(clauses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify anomalous clauses compared to others."""
        return []  # Simplified for example


# Global client
contract_processor = None


@server.list_tools()
def list_tools():
    """Register all contract analysis tools."""
    return [
        Tool(
            name="analyze_contract",
            description=(
                "Upload and analyze a contract document. Performs clause extraction, "
                "risk assessment, and key term identification. Supports PDF, DOCX, TXT, "
                "and image formats (with OCR)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Local file path to contract document (PDF, DOCX, TXT, JPG, PNG)",
                    },
                    "analysis_type": {
                        "type": "string",
                        "enum": ["full_extraction", "risk_assessment", "commercial_summary", "legal_review"],
                        "description": "Type of analysis to perform",
                        "default": "full_extraction",
                    },
                    "tenant_id": {
                        "type": "string",
                        "description": "Tenant identifier",
                    },
                },
                "required": ["file_path", "tenant_id"],
            },
        ),
        Tool(
            name="search_contracts",
            description=(
                "Semantic search across contract corpus. Find contracts and specific "
                "clauses by natural language query. Supports filtering by document type "
                "and date range."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query (e.g., 'termination for convenience' or 'IP ownership of custom software')",
                    },
                    "tenant_id": {
                        "type": "string",
                        "description": "Tenant identifier",
                    },
                    "doc_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional: filter by document type (e.g., ['vendor', 'client', 'partnership'])",
                    },
                    "date_range": {
                        "type": "object",
                        "properties": {
                            "start": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                            "end": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                        },
                        "description": "Optional: filter by signed date range",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results (default: 10, max: 50)",
                        "default": 10,
                    },
                },
                "required": ["query", "tenant_id"],
            },
        ),
        Tool(
            name="get_risk_summary",
            description=(
                "Get risk assessment summary for a deal. Identifies problematic clauses, "
                "missing terms, and legal risks with severity levels and remediation suggestions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "deal_id": {
                        "type": "string",
                        "description": "Deal identifier (aggregates all contracts in deal)",
                    },
                    "tenant_id": {
                        "type": "string",
                        "description": "Tenant identifier",
                    },
                    "focus_areas": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional: focus on specific risk areas (e.g., ['liability', 'ip_rights', 'termination'])",
                    },
                },
                "required": ["deal_id", "tenant_id"],
            },
        ),
        Tool(
            name="compare_clauses",
            description=(
                "Compare specific clause types across multiple contracts. "
                "Identifies variations and anomalies to ensure consistency across agreements."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "clause_type": {
                        "type": "string",
                        "enum": [
                            "payment_terms", "termination", "liability_limits",
                            "indemnification", "confidentiality", "ip_rights", "renewal"
                        ],
                        "description": "Type of clause to compare",
                    },
                    "contract_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Contract IDs to compare",
                    },
                    "tenant_id": {
                        "type": "string",
                        "description": "Tenant identifier",
                    },
                },
                "required": ["clause_type", "contract_ids", "tenant_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool invocations."""
    
    if name == "analyze_contract":
        return await _analyze_contract(arguments)
    elif name == "search_contracts":
        return await _search_contracts(arguments)
    elif name == "get_risk_summary":
        return await _get_risk_summary(arguments)
    elif name == "compare_clauses":
        return await _compare_clauses(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")


async def _analyze_contract(args: Dict[str, Any]) -> List[TextContent]:
    """Analyze contract and return extracted clauses and risks."""
    try:
        file_path = args["file_path"]
        analysis_type = ContractAnalysisType(args.get("analysis_type", "full_extraction"))
        
        # Analyze contract
        analysis = await contract_processor.analyze_contract(file_path, analysis_type)
        
        # Assess risks
        risks = RiskAssessment.assess_risks(analysis)
        
        result = {
            "file_path": file_path,
            "analysis_type": analysis_type.value,
            "clauses": analysis.get("clauses", {}),
            "key_terms": analysis.get("key_terms", {}),
            "risks": risks,
            "summary": analysis.get("summary", ""),
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as e:
        logger.error(f"Contract analysis failed: {str(e)}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def _search_contracts(args: Dict[str, Any]) -> List[TextContent]:
    """Search contracts by semantic query."""
    try:
        results = await contract_processor.search_contracts(
            query=args["query"],
            tenant_id=args["tenant_id"],
            doc_types=args.get("doc_types"),
            date_range=args.get("date_range"),
            top_k=args.get("top_k", 10),
        )
        
        return [
            TextContent(
                type="text",
                text=json.dumps({
                    "query": args["query"],
                    "result_count": len(results),
                    "results": results,
                    "timestamp": datetime.utcnow().isoformat(),
                }, indent=2),
            )
        ]
    except Exception as e:
        logger.error(f"Contract search failed: {str(e)}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def _get_risk_summary(args: Dict[str, Any]) -> List[TextContent]:
    """Get risk summary for a deal."""
    try:
        deal_id = args["deal_id"]
        
        # In production, would fetch all contracts for deal from database
        # Then assess combined risks
        risks = [
            {
                "rule_id": "unlimited_liability",
                "level": "high",
                "description": "Contract contains unlimited liability clause in MSA",
                "remediation": "Add cap on liability equal to 12 months of fees",
                "contract_id": "CTR-001",
            },
            {
                "rule_id": "auto_renewal",
                "level": "medium",
                "description": "Auto-renewal with 30-day notice period",
                "remediation": "Increase notice period to 90 days",
                "contract_id": "CTR-002",
            },
        ]
        
        return [
            TextContent(
                type="text",
                text=json.dumps({
                    "deal_id": deal_id,
                    "risk_count": len(risks),
                    "critical_risks": len([r for r in risks if r["level"] == "critical"]),
                    "high_risks": len([r for r in risks if r["level"] == "high"]),
                    "risks": sorted(risks, key=lambda x: ["critical", "high", "medium", "low"].index(x["level"])),
                    "timestamp": datetime.utcnow().isoformat(),
                }, indent=2),
            )
        ]
    except Exception as e:
        logger.error(f"Risk assessment failed: {str(e)}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def _compare_clauses(args: Dict[str, Any]) -> List[TextContent]:
    """Compare clauses across contracts."""
    try:
        clause_type = args["clause_type"]
        contract_ids = args["contract_ids"]
        
        # In production, would fetch contracts from database
        mock_contracts = [
            {
                "contract_id": cid,
                "contract_name": f"Contract {cid}",
                "clauses": {
                    clause_type: [
                        {
                            "content": f"Sample {clause_type} clause for {cid}",
                            "key_terms": {"duration": "12 months", "amount": "$100k"},
                        }
                    ]
                },
            }
            for cid in contract_ids
        ]
        
        comparison = ContractComparison.compare_clauses(clause_type, mock_contracts)
        
        return [TextContent(type="text", text=json.dumps(comparison, indent=2))]
    except Exception as e:
        logger.error(f"Clause comparison failed: {str(e)}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


def initialize_mcp_server():
    """Initialize contract processor client."""
    global contract_processor
    
    contract_processor = ContractProcessor(
        processing_api_url=os.getenv("CONTRACT_PROCESSOR_URL", "http://localhost:8000"),
        api_key=os.getenv("CONTRACT_PROCESSOR_API_KEY", ""),
    )
    
    logger.info("Contract Intelligence Platform MCP server initialized")


if __name__ == "__main__":
    initialize_mcp_server()
    server.run()
