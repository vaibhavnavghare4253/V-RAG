import io
import fitz
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token, get_password_hash
from app.models.trace import RetrievalTrace
from app.models.user import Organization, User, UserRole


def _build_pdf_bytes(pages: list[str]) -> bytes:
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    return doc.tobytes()


@pytest.mark.asyncio
async def test_e2e_pdf_upload_ingestion_and_rag_query(client: AsyncClient, test_db, test_user_and_token):
    headers = test_user_and_token["headers"]
    pdf_bytes = _build_pdf_bytes([
        "Abstract: This paper presents AdaptiveDocAI for multimodal document understanding.",
        "Section 4 Results: Our proposed model achieved 94.2% accuracy on ChartQA benchmark.",
    ])

    files = {"file": ("adaptive_paper.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    up_res = await client.post("/api/v1/documents/upload", headers=headers, files=files)
    assert up_res.status_code == 202
    doc_id = up_res.json()["document_id"]

    # BackgroundTasks runs before client returns in ASGITransport; verify indexed status
    detail_res = await client.get(f"/api/v1/documents/{doc_id}", headers=headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["status"] == "indexed"
    assert detail["page_count"] == 2
    assert detail["latest_job"]["status"] == "completed"

    # Query the indexed document via Baseline A RAG
    q_res = await client.post(
        "/api/v1/chat/query",
        headers=headers,
        json={"document_id": doc_id, "query": "What accuracy did the proposed model achieve on ChartQA?"},
    )
    assert q_res.status_code == 200
    q_data = q_res.json()
    assert q_data["decision"] == "ANSWER"
    assert "94.2%" in q_data["answer"]
    assert len(q_data["citations"]) >= 1
    assert q_data["citations"][0]["page_number"] == 2
    assert q_data["citations"][0]["document_name"] == "adaptive_paper.pdf"

    # Verify RetrievalTrace persisted in database
    trace_stmt = select(RetrievalTrace).where(RetrievalTrace.message_id == q_data["message_id"])
    trace = (await test_db.execute(trace_stmt)).scalar_one_or_none()
    assert trace is not None
    assert trace.intent_category == "TEXT_BASELINE_A"
    assert trace.selected_modalities == ["text"]

    # Tenant isolation: another org must NOT retrieve Org 1's indexed chunks
    org2 = Organization(name="Isolated Org 2", tier="standard")
    test_db.add(org2)
    await test_db.flush()
    user2 = User(
        organization_id=org2.id,
        email="user2@isolated.org",
        hashed_password=get_password_hash("Pass1234!"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    test_db.add(user2)
    await test_db.commit()
    token2 = create_access_token(subject=user2.id, extra_claims={"org_id": org2.id, "role": "admin"})

    q_res2 = await client.post(
        "/api/v1/chat/query",
        headers={"Authorization": f"Bearer {token2}"},
        json={"query": "What accuracy did the proposed model achieve on ChartQA?"},
    )
    assert q_res2.status_code == 200
    assert q_res2.json()["citations"] == []

