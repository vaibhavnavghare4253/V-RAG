from dataclasses import dataclass
from typing import List
import fitz  # PyMuPDF


@dataclass
class ExtractedPage:
    """Represents raw text and geometry extracted from a single PDF page."""

    page_number: int
    text: str
    width_pt: float
    height_pt: float


def extract_text_from_pdf(pdf_bytes: bytes) -> List[ExtractedPage]:
    """Extract page-by-page text and page dimensions from PDF bytes using PyMuPDF."""
    if not pdf_bytes:
        raise ValueError("Cannot extract text from empty PDF bytes.")

    pages: List[ExtractedPage] = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for idx, page in enumerate(doc, start=1):
            rect = page.rect
            raw_text = page.get_text("text") or ""
            # Normalize excessive whitespace while preserving paragraph breaks
            cleaned = "\n".join(line.rstrip() for line in raw_text.splitlines()).strip()
            pages.append(
                ExtractedPage(
                    page_number=idx,
                    text=cleaned,
                    width_pt=float(rect.width),
                    height_pt=float(rect.height),
                )
            )
    return pages

