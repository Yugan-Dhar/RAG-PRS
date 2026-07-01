import io
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import engine, Base

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(autouse=True)
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def test_create_assessment():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/assess",
            files={"file": ("router.txt", io.BytesIO(b"router supports ssh and rbac"), "text/plain")},
            data={"standard_id": "ITSAR", "framework_id": "ITSAR-ROUTER"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert "id" in data


async def test_get_assessment_report_not_found():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/reports/does-not-exist")
    assert res.status_code == 404
