from dataclasses import dataclass
from typing import List

from app.ingestion.text_extractor import ExtractedPage


@dataclass
class TextChunk:
    """Represents a token-bounded text chunk with page provenance."""

    page_number: int
    chunk_index: int
    content: str
    token_count: int


def chunk_pages(
    pages: List[ExtractedPage],
    chunk_size_tokens: int = 512,
    overlap_tokens: int = 64,
) -> List[TextChunk]:
    """Split extracted PDF pages into overlapping word-based chunks, preserving page numbers.

    Uses whitespace tokenization as a fast, dependency-free proxy for token count.
    """
    if chunk_size_tokens <= 0:
        raise ValueError("chunk_size_tokens must be positive.")
    if overlap_tokens < 0 or overlap_tokens >= chunk_size_tokens:
        raise ValueError("overlap_tokens must be >= 0 and < chunk_size_tokens.")

    chunks: List[TextChunk] = []
    global_idx = 0
    step = chunk_size_tokens - overlap_tokens

    for page in pages:
        if not page.text:
            continue
        words = page.text.split()
        if not words:
            continue

        start = 0
        while start < len(words):
            window = words[start : start + chunk_size_tokens]
            chunk_text = " ".join(window)
            chunks.append(
                TextChunk(
                    page_number=page.page_number,
                    chunk_index=global_idx,
                    content=chunk_text,
                    token_count=len(window),
                )
            )
            global_idx += 1
            if start + chunk_size_tokens >= len(words):
                break
            start += step

    return chunks

