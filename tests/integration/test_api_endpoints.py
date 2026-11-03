"""
Integration tests for Coordinator API endpoints: Authentication, API Keys, Jobs, and Catalogs.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from coordinator.database import Base, get_db
from coordinator.main import app

# Test SQLite In-Memory Engine
test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    echo=False,
    future=True,
)
_test_session_factory = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db():
    async with _test_session_factory() as session:
        yield session


# Override FastAPI DB dependency
app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(autouse=True)
async def init_test_db():
    """Create all tables before each test and drop them after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_auth_and_api_key_flow() -> None:
    """Test full user registration, login, and API key authentication flow."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Register User
        reg_resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "researcher@example.com",
                "password": "SecurePassword123!",
                "full_name": "AI Researcher",
                "role": "user",
            },
        )
        assert reg_resp.status_code == 201
        user_data = reg_resp.json()
        assert user_data["email"] == "researcher@example.com"
        assert user_data["balance_credits"] == 10.0

        # 2. Login
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "researcher@example.com",
                "password": "SecurePassword123!",
            },
        )
        assert login_resp.status_code == 200
        token_data = login_resp.json()
        assert "access_token" in token_data
        token = token_data["access_token"]

        # 3. Authenticated Profile Query
        me_resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == "researcher@example.com"

        # 4. Create API Key
        key_resp = await client.post(
            "/api/v1/auth/api-keys",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "cli-laptop", "expires_days": 30},
        )
        assert key_resp.status_code == 201
        key_data = key_resp.json()
        assert "raw_key" in key_data
        raw_key = key_data["raw_key"]
        assert raw_key.startswith("cld_live_")

        # 5. Access Protected Endpoint via X-API-Key Header
        jobs_resp = await client.get(
            "/api/v1/jobs",
            headers={"X-API-Key": raw_key},
        )
        assert jobs_resp.status_code == 200
        assert jobs_resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_job_submission_and_query() -> None:
    """Test submitting inference and training jobs and inspecting status."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register and login
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "submitter@example.com",
                "password": "Password123!",
                "role": "user",
            },
        )
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "submitter@example.com", "password": "Password123!"},
        )
        token = login.json()["access_token"]

        # Submit text inference job
        submit_resp = await client.post(
            "/api/v1/jobs/inference/text",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "model_name": "meta-llama/Llama-3-8B-Instruct",
                "prompt": "Explain decentralized physical infrastructure networks (DePIN).",
                "max_tokens": 256,
                "temperature": 0.7,
                "min_vram_mb": 16384,
            },
        )
        assert submit_resp.status_code == 201
        job_data = submit_resp.json()
        assert job_data["type"] == "inference_text"
        assert job_data["status"] == "pending"
        job_id = job_data["id"]

        # Query job details
        detail_resp = await client.get(
            f"/api/v1/jobs/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["id"] == job_id
        assert "events" in detail
        assert len(detail["events"]) >= 1
        assert detail["events"][0]["event_type"] == "submitted"


@pytest.mark.asyncio
async def test_model_manifest_and_dataset_catalog() -> None:
    """Test cataloging models and datasets."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/register",
            json={"email": "catalog@example.com", "password": "Password123!"},
        )
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "catalog@example.com", "password": "Password123!"},
        )
        token = login.json()["access_token"]

        # Create Model Manifest
        model_resp = await client.post(
            "/api/v1/artifacts/models",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "mistral-7b-instruct-v0.2",
                "description": "Mistral 7B Instruct Safetensors bundle",
                "architecture": "MistralForCausalLM",
                "framework": "transformers",
                "format": "safetensors",
                "default_vram_required_mb": 16384,
                "is_public": True,
            },
        )
        assert model_resp.status_code == 201
        assert model_resp.json()["name"] == "mistral-7b-instruct-v0.2"

        # List models
        list_resp = await client.get(
            "/api/v1/artifacts/models",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1
