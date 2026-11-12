import io
import pytest
from httpx import AsyncClient
from app.core.security import create_access_token
from app.core.security import get_password_hash
from app.models.user import Organization, User, UserRole


@pytest.mark.asyncio
async def test_upload_pdf_success(client: AsyncClient, test_user_and_token):
    headers = test_user_and_token["headers"]
    fake_pdf = io.BytesIO(b"%PDF-1.4 Mock research paper content with tables and charts.")
    files = {"file": ("research_paper.pdf", fake_pdf, "application/pdf")}

    response = await client.post("/api/v1/documents/upload", headers=headers, files=files)
    assert response.status_code == 202
    data = response.json()
    assert "document_id" in data
    assert "job_id" in data
    assert data["filename"] == "research_paper.pdf"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_upload_non_pdf_fails(client: AsyncClient, test_user_and_token):
    headers = test_user_and_token["headers"]
    fake_txt = io.BytesIO(b"Plain text file")
    files = {"file": ("data.txt", fake_txt, "text/plain")}

    response = await client.post("/api/v1/documents/upload", headers=headers, files=files)
    assert response.status_code == 400
    assert "Only PDF files are supported" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_duplicate_pdf_conflict(client: AsyncClient, test_user_and_token):
    headers = test_user_and_token["headers"]
    pdf_content = b"%PDF-1.4 Same exact content duplicated."

    f1 = {"file": ("paper1.pdf", io.BytesIO(pdf_content), "application/pdf")}
    r1 = await client.post("/api/v1/documents/upload", headers=headers, files=f1)
    assert r1.status_code == 202

    f2 = {"file": ("paper2.pdf", io.BytesIO(pdf_content), "application/pdf")}
    r2 = await client.post("/api/v1/documents/upload", headers=headers, files=f2)
    assert r2.status_code == 409
    assert "identical document" in r2.json()["detail"]


@pytest.mark.asyncio
async def test_list_and_get_document(client: AsyncClient, test_user_and_token):
    headers = test_user_and_token["headers"]
    # Upload one document
    f = {"file": ("doc_list_test.pdf", io.BytesIO(b"%PDF-1.4 Unique Doc 123"), "application/pdf")}
    upload_res = await client.post("/api/v1/documents/upload", headers=headers, files=f)
    doc_id = upload_res.json()["document_id"]

    # List documents
    list_res = await client.get("/api/v1/documents", headers=headers)
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(d["id"] == doc_id for d in list_data["items"])

    # Get single document detail
    detail_res = await client.get(f"/api/v1/documents/{doc_id}", headers=headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == doc_id
    assert detail["latest_job"] is not None

    # Get document status
    status_res = await client.get(f"/api/v1/documents/{doc_id}/status", headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_delete_document(client: AsyncClient, test_user_and_token):
    headers = test_user_and_token["headers"]
    f = {"file": ("to_delete.pdf", io.BytesIO(b"%PDF-1.4 To Delete Content"), "application/pdf")}
    upload_res = await client.post("/api/v1/documents/upload", headers=headers, files=f)
    doc_id = upload_res.json()["document_id"]

    # Delete
    del_res = await client.delete(f"/api/v1/documents/{doc_id}", headers=headers)
    assert del_res.status_code == 204

    # Verify not found after delete
    check_res = await client.get(f"/api/v1/documents/{doc_id}", headers=headers)
    assert check_res.status_code == 404


@pytest.mark.asyncio
async def test_tenant_isolation_boundary(client: AsyncClient, test_db, test_user_and_token):
    headers_org1 = test_user_and_token["headers"]

    # Create Org 2 and User 2
    org2 = Organization(name="Competitor Research Org", tier="standard")
    test_db.add(org2)
    await test_db.flush()

    user2 = User(
        organization_id=org2.id,
        email="other@competitor.com",
        hashed_password=get_password_hash("Password123!"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    test_db.add(user2)
    await test_db.commit()
    await test_db.refresh(user2)

    token2 = create_access_token(
        subject=user2.id,
        extra_claims={"org_id": org2.id, "role": user2.role.value},
    )
    headers_org2 = {"Authorization": f"Bearer {token2}"}

    # Org 1 uploads a private document
    f = {"file": ("org1_secret.pdf", io.BytesIO(b"%PDF-1.4 Org 1 Proprietary"), "application/pdf")}
    up_res = await client.post("/api/v1/documents/upload", headers=headers_org1, files=f)
    org1_doc_id = up_res.json()["document_id"]

    # Org 2 attempts to fetch Org 1's document -> must be 404 Not Found
    leak_res = await client.get(f"/api/v1/documents/{org1_doc_id}", headers=headers_org2)
    assert leak_res.status_code == 404

    # Org 2 list documents should NOT include Org 1's document
    list_res = await client.get("/api/v1/documents", headers=headers_org2)
    assert list_res.status_code == 200
    assert not any(d["id"] == org1_doc_id for d in list_res.json()["items"])

