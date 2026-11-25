import fitz
import numpy as np
import pytest
from qdrant_client import QdrantClient

from app.generation.llm_provider import MockLLMProvider
from app.ingestion.chunker import chunk_pages
from app.ingestion.text_extractor import extract_text_from_pdf
from app.retrieval.embedder import LocalHashEmbedder
from app.services.vector_store import VectorNode, VectorStoreService


def _make_sample_pdf(page_texts: list[str]) -> bytes:
    doc = fitz.open()
    for text in page_texts:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    return doc.tobytes()


def test_extract_text_and_chunk_pages():
    pdf_bytes = _make_sample_pdf([
        "Page one introduces AdaptiveDocAI architecture and vector indexing.",
        "Page two reports that the proposed model achieved 94.2% accuracy on DocVQA.",
    ])
    pages = extract_text_from_pdf(pdf_bytes)
    assert len(pages) == 2
    assert pages[0].page_number == 1
    assert "AdaptiveDocAI" in pages[0].text
    assert pages[1].page_number == 2
    assert "94.2%" in pages[1].text

    chunks = chunk_pages(pages, chunk_size_tokens=6, overlap_tokens=2)
    assert len(chunks) >= 3
    assert chunks[0].page_number == 1
    assert any(c.page_number == 2 and "94.2%" in c.content for c in chunks)


@pytest.mark.asyncio
async def test_local_hash_embedder_similarity():
    embedder = LocalHashEmbedder(dimension=384)
    vecs = await embedder.embed_texts([
        "The proposed model achieved 94.2% accuracy on DocVQA.",
        "The weather tomorrow will be sunny with light winds.",
        "What accuracy did the proposed model achieve on DocVQA?",
    ])
    assert len(vecs) == 3
    assert len(vecs[0]) == 384

    sim_relevant = float(np.dot(vecs[0], vecs[2]))
    sim_irrelevant = float(np.dot(vecs[1], vecs[2]))
    assert sim_relevant > sim_irrelevant


@pytest.mark.asyncio
async def test_vector_store_tenant_isolation_and_delete():
    store = VectorStoreService(client=QdrantClient(":memory:"), collection_name="test_nodes")
    embedder = LocalHashEmbedder(dimension=384)
    vecs = await embedder.embed_texts(["Quantum computing uses qubits."])

    store.upsert_nodes(
        [
            VectorNode(
                point_id="11111111-1111-1111-1111-111111111111",
                vector=vecs[0],
                tenant_id="tenant_a",
                document_id="doc_1",
                document_name="quantum.pdf",
                chunk_id="c1",
                page_number=1,
                modality="text",
                content="Quantum computing uses qubits.",
            )
        ],
        dimension=384,
    )

    q_vec = await embedder.embed_query("qubits")
    hits_a = store.search(q_vec, tenant_id="tenant_a", top_k=3)
    hits_b = store.search(q_vec, tenant_id="tenant_b", top_k=3)
    assert len(hits_a) == 1
    assert len(hits_b) == 0

    store.delete_by_document("doc_1", "tenant_a")
    assert len(store.search(q_vec, tenant_id="tenant_a", top_k=3)) == 0


@pytest.mark.asyncio
async def test_mock_llm_provider_citations():
    llm = MockLLMProvider()
    prompt = (
        "Retrieved Evidence:\n\n"
        "[Evidence 1 | paper.pdf | Page 4]\n"
        "The baseline achieved 68.4% accuracy.\n\n"
        "Question: What accuracy did the baseline achieve?\nAnswer:"
    )
    resp = await llm.generate("System", prompt)
    assert "68.4%" in resp.content
    assert "[Source: paper.pdf, Page 4]" in resp.content

