import os
import shutil
import tempfile
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_db, get_storage_service
from app.core.config import settings
from app.core.database import Base
from app.core.security import create_access_token
from app.main import app
from app.models.user import Organization, User, UserRole
from app.services.storage import LocalStorageService, StorageService

# Use in-memory SQLite for high-speed, isolated async testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a fresh in-memory database for each test function."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
def temp_storage_dir():
    """Create a temporary directory for file storage during testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def mock_storage(temp_storage_dir) -> StorageService:
    return LocalStorageService(base_dir=temp_storage_dir)


@pytest_asyncio.fixture(scope="function")
async def client(test_db: AsyncSession, mock_storage: StorageService) -> AsyncGenerator[AsyncClient, None]:
    """Test client overriding database and storage dependencies."""
    async def override_get_db():
        yield test_db

    def override_storage():
        return mock_storage

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage_service] = override_storage

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def test_user_and_token(test_db: AsyncSession):
    """Fixture providing a seeded test user and valid JWT token."""
    from app.core.security import get_password_hash

    org = Organization(name="Test University Lab", tier="enterprise")
    test_db.add(org)
    await test_db.flush()

    user = User(
        organization_id=org.id,
        email="researcher@lab.ac.in",
        hashed_password=get_password_hash("ResearchPass123!"),
        full_name="Dr. Research Scientist",
        role=UserRole.ADMIN,
        is_active=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)

    token = create_access_token(
        subject=user.id,
        extra_claims={"org_id": org.id, "role": user.role.value},
    )

    return {
        "user": user,
        "org": org,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }

