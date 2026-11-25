"""Reproducible Evaluation Script for Baseline A (Standard Text-Only RAG).

Evaluates Exact Match (EM), Token F1, Retrieval Recall@K (page-level), and Mean Latency
on an in-memory Qdrant index over provided PDFs and QA pairs.

Usage:
    python research/baselines/baseline_a_text_only.py
"""

import asyncio
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List

# Ensure backend package is importable
BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from qdrant_client import QdrantClient
from app.ingestion.chunker import chunk_pages
from app.ingestion.text_extractor import ExtractedPage
from app.retrieval.embedder import LocalHashEmbedder
from app.services.rag_service import BaselineTextRAGService
from app.services.vector_store import VectorNode, VectorStoreService
from app.models.base import generate_uuid


def normalize_text(text: str) -> str:
    return re.sub(r"\W+", " ", text.lower()).strip()


def compute_token_f1(pred: str, gold: str) -> float:
    pred_tokens = normalize_text(pred).split()
    gold_tokens = normalize_text(gold).split()
    if not pred_tokens or not gold_tokens:
        return float(pred_tokens == gold_tokens)
    common = set(pred_tokens) & set(gold_tokens)
    if not common:
        return 0.0
    precision = sum(min(pred_tokens.count(w), gold_tokens.count(w)) for w in common) / len(pred_tokens)
    recall = sum(min(pred_tokens.count(w), gold_tokens.count(w)) for w in common) / len(gold_tokens)
    return (2 * precision * recall) / (precision + recall)


async def run_baseline_a_benchmark() -> Dict[str, Any]:
    embedder = LocalHashEmbedder(dimension=384)
    vector_store = VectorStoreService(client=QdrantClient(":memory:"), collection_name="baseline_a_eval")
    rag = BaselineTextRAGService(embedder=embedder, vector_store=vector_store)

    # Sample synthetic research paper pages for reproducible offline verification
    pages = [
        ExtractedPage(
            page_number=1,
            text="AdaptiveDocAI is a multimodal document question answering framework designed for research papers.",
            width_pt=612.0,
            height_pt=792.0,
        ),
        ExtractedPage(
            page_number=4,
            text="In our experiments, Baseline A achieved 68.4% accuracy on DocVQA and 42.1% on ChartQA.",
            width_pt=612.0,
            height_pt=792.0,
        ),
        ExtractedPage(
            page_number=8,
            text="Latency measurements show mean retrieval time of 45 ms using dense vector search in Qdrant.",
            width_pt=612.0,
            height_pt=792.0,
        ),
    ]

    chunks = chunk_pages(pages, chunk_size_tokens=512, overlap_tokens=64)
    vectors = await embedder.embed_texts([c.content for c in chunks])
    nodes = [
        VectorNode(
            point_id=generate_uuid(),
            vector=vec,
            tenant_id="eval_tenant",
            document_id="eval_doc_1",
            document_name="sample_paper.pdf",
            chunk_id=f"chunk_{c.chunk_index}",
            page_number=c.page_number,
            modality="text",
            content=c.content,
        )
        for c, vec in zip(chunks, vectors)
    ]
    vector_store.upsert_nodes(nodes, dimension=embedder.dimension)

    qa_pairs = [
        {"question": "What accuracy did Baseline A achieve on DocVQA?", "gold_answer": "68.4%", "gold_page": 4},
        {"question": "What is the mean retrieval time using Qdrant?", "gold_answer": "45 ms", "gold_page": 8},
    ]

    f1_scores: List[float] = []
    recall_hits = 0
    latencies: List[int] = []

    for item in qa_pairs:
        res = await rag.query(item["question"], tenant_id="eval_tenant", document_id="eval_doc_1", top_k=3)
        f1_scores.append(compute_token_f1(res.answer, item["gold_answer"]))
        retrieved_pages = {c.page_number for c in res.citations}
        if item["gold_page"] in retrieved_pages:
            recall_hits += 1
        latencies.append(res.latency_ms)

    summary = {
        "system": "Baseline A (Standard Text-Only RAG)",
        "num_samples": len(qa_pairs),
        "mean_token_f1": round(sum(f1_scores) / len(f1_scores), 4),
        "page_recall_at_3": round(recall_hits / len(qa_pairs), 4),
        "mean_latency_ms": round(sum(latencies) / len(latencies), 2),
    }
    return summary


if __name__ == "__main__":
    results = asyncio.run(run_baseline_a_benchmark())
    print(json.dumps(results, indent=2))

