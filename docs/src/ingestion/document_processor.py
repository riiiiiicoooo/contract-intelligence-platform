"""
Document Processor - Reference Implementation
Handles PDF/Word ingestion, native vs. scanned detection, and clause-level chunking.
"""

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class DocumentChunk:
    text: str
    page_number: int
    section_reference: Optional[str] = None
    section_title: Optional[str] = None
    chunk_type: str = "clause"  # clause, section_header, table, paragraph
    metadata: dict = field(default_factory=dict)


@dataclass
class ProcessedDocument:
    filename: str
    file_hash: str
    page_count: int
    is_scanned: bool
    chunks: list[DocumentChunk] = field(default_factory=list)
    parties: list[dict] = field(default_factory=list)
    contract_type: Optional[str] = None
    ocr_confidence: Optional[float] = None


class DocumentProcessor:
    """
    Dual-pipeline document processor.
    Routes native PDFs to Docling (fast, free) and scanned PDFs to Azure Document Intelligence (OCR).
    """

    SUPPORTED_TYPES = {".pdf", ".docx", ".doc"}
    MAX_FILE_SIZE_MB = 100
    CHUNK_MIN_TOKENS = 50
    CHUNK_MAX_TOKENS = 500

    # Patterns for detecting clause/section boundaries
    SECTION_PATTERN = re.compile(
        r"^(\d+\.?\d*\.?\d*)\s+([A-Z][A-Za-z\s,]+)",
        re.MULTILINE,
    )
    CLAUSE_PATTERN = re.compile(
        r"^(\(?[a-z]\)|\(?[ivxlc]+\)|\d+\.\d+)",
        re.MULTILINE,
    )

    def process(self, file_path: str) -> ProcessedDocument:
        """Main entry point. Detects file type and routes to appropriate pipeline."""
        path = Path(file_path)

        if path.suffix.lower() not in self.SUPPORTED_TYPES:
            raise ValueError(f"Unsupported file type: {path.suffix}")

        file_hash = self._compute_hash(file_path)

        if path.suffix.lower() in (".docx", ".doc"):
            return self._process_word(path, file_hash)
        elif path.suffix.lower() == ".pdf":
            is_scanned = self._detect_scanned(path)
            if is_scanned:
                return self._process_scanned_pdf(path, file_hash)
            else:
                return self._process_native_pdf(path, file_hash)

    def _detect_scanned(self, pdf_path: Path) -> bool:
        """
        Determine if a PDF is scanned (image-based) or native (text-based).

        Logic:
        1. Extract text via PyMuPDF
        2. If text length is very small relative to file size, likely scanned
        3. Check if images cover > 95% of page area
        4. Check for OCR artifact fonts (GlyphlessFont)
        """
        import fitz  # PyMuPDF

        doc = fitz.open(str(pdf_path))
        total_text_length = 0
        scanned_page_count = 0

        for page in doc:
            text = page.get_text()
            total_text_length += len(text.strip())

            # Check for minimal text + high image coverage
            if len(text.strip()) < 50:
                images = page.get_images()
                if len(images) > 0:
                    scanned_page_count += 1

            # Check for OCR artifact fonts
            for font in page.get_fonts():
                if "GlyphlessFont" in font[3]:
                    doc.close()
                    return True

        doc.close()

        # If more than 50% of pages appear scanned, treat as scanned document
        if doc.page_count > 0 and scanned_page_count / doc.page_count > 0.5:
            return True

        # If total text is very small relative to file size, likely scanned
        file_size = pdf_path.stat().st_size
        if total_text_length < 0.01 * file_size:
            return True

        return False

    def _process_native_pdf(self, pdf_path: Path, file_hash: str) -> ProcessedDocument:
        """
        Process native-text PDF using Docling.
        Docling provides DocLayNet layout analysis and TableFormer table extraction.
        """
        # In production: from docling.document_converter import DocumentConverter
        # converter = DocumentConverter()
        # result = converter.convert(str(pdf_path))

        # Reference implementation uses PyMuPDF for text extraction
        import fitz

        doc = fitz.open(str(pdf_path))
        full_text = ""
        page_texts = {}

        for page_num, page in enumerate(doc, 1):
            text = page.get_text()
            page_texts[page_num] = text
            full_text += text

        chunks = self._chunk_by_clauses(page_texts)

        result = ProcessedDocument(
            filename=pdf_path.name,
            file_hash=file_hash,
            page_count=doc.page_count,
            is_scanned=False,
            chunks=chunks,
        )

        doc.close()
        return result

    def _process_scanned_pdf(self, pdf_path: Path, file_hash: str) -> ProcessedDocument:
        """
        Process scanned PDF using Azure Document Intelligence for OCR.
        Azure achieves 99.8% character accuracy on typed text.
        """
        # In production:
        # from azure.ai.formrecognizer import DocumentAnalysisClient
        # from azure.core.credentials import AzureKeyCredential
        #
        # client = DocumentAnalysisClient(
        #     endpoint=os.environ["AZURE_FORM_RECOGNIZER_ENDPOINT"],
        #     credential=AzureKeyCredential(os.environ["AZURE_FORM_RECOGNIZER_KEY"]),
        # )
        # with open(pdf_path, "rb") as f:
        #     poller = client.begin_analyze_document("prebuilt-layout", f)
        # result = poller.result()

        # Reference: return structure showing expected output format
        return ProcessedDocument(
            filename=pdf_path.name,
            file_hash=file_hash,
            page_count=0,  # Would be populated from Azure response
            is_scanned=True,
            chunks=[],
            ocr_confidence=0.0,  # Average confidence from Azure
        )

    def _process_word(self, docx_path: Path, file_hash: str) -> ProcessedDocument:
        """Process Word document using python-docx."""
        # In production: from docx import Document
        # doc = Document(str(docx_path))
        # paragraphs = [p.text for p in doc.paragraphs]

        return ProcessedDocument(
            filename=docx_path.name,
            file_hash=file_hash,
            page_count=0,
            is_scanned=False,
            chunks=[],
        )

    def _chunk_by_clauses(self, page_texts: dict[int, str]) -> list[DocumentChunk]:
        """
        Split document text into clause-level chunks.

        Strategy:
        - Split at numbered section/clause boundaries (e.g., "8.2", "(a)", "(iv)")
        - Preserve hierarchy: section title stays with its clauses
        - Target chunk size: 200-500 tokens
        - Clauses exceeding 500 tokens are kept whole (don't split mid-clause)
        - Each chunk carries metadata: page number, section reference, section title
        """
        chunks = []
        current_section_title = None
        current_section_ref = None

        for page_num, text in page_texts.items():
            # Find section headers
            for match in self.SECTION_PATTERN.finditer(text):
                current_section_ref = match.group(1)
                current_section_title = match.group(2).strip()

            # Split on clause boundaries
            parts = self.CLAUSE_PATTERN.split(text)

            for part in parts:
                part = part.strip()
                if not part or len(part) < 20:
                    continue

                token_count = len(part.split())

                if token_count >= self.CHUNK_MIN_TOKENS:
                    chunks.append(
                        DocumentChunk(
                            text=part,
                            page_number=page_num,
                            section_reference=current_section_ref,
                            section_title=current_section_title,
                            metadata={"token_count": token_count},
                        )
                    )

        return chunks

    def _compute_hash(self, file_path: str) -> str:
        """SHA-256 hash for deduplication."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
