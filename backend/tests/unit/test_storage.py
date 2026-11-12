import pytest
from app.services.storage import LocalStorageService


@pytest.mark.asyncio
async def test_local_storage_lifecycle(temp_storage_dir):
    service = LocalStorageService(base_dir=temp_storage_dir)
    file_bytes = b"%PDF-1.4 Mock PDF content for testing"
    rel_path = "subfolder/test_doc.pdf"

    # Save
    saved_path = await service.save_file(file_bytes, rel_path, content_type="application/pdf")
    assert saved_path == rel_path

    # Exists
    exists = await service.file_exists(rel_path)
    assert exists is True

    # Get
    content = await service.get_file(rel_path)
    assert content == file_bytes

    # Delete
    deleted = await service.delete_file(rel_path)
    assert deleted is True

    # Exists after deletion
    assert await service.file_exists(rel_path) is False


@pytest.mark.asyncio
async def test_local_storage_path_traversal_prevention(temp_storage_dir):
    service = LocalStorageService(base_dir=temp_storage_dir)
    malicious_path = "../../etc/passwd"

    with pytest.raises(ValueError, match="Illegal file path traversal"):
        await service.save_file(b"attack", malicious_path)

