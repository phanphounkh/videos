"""Smoke tests: the app boots and the error contract holds."""

from httpx import AsyncClient


async def test_health_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_ready_returns_checks(client: AsyncClient) -> None:
    response = await client.get("/api/health/ready")
    assert response.json()["checks"]["api"] == "ok"


async def test_unknown_route_uses_error_envelope(client: AsyncClient) -> None:
    response = await client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


async def test_openapi_lists_the_main_endpoints(client: AsyncClient) -> None:
    paths = (await client.get("/openapi.json")).json()["paths"]
    for expected in (
        "/api/auth/login",
        "/api/projects",
        "/api/projects/{project_id}/generate",
        "/api/projects/{project_id}/render",
        "/api/render-jobs/{job_id}",
        "/api/assets/upload",
    ):
        assert expected in paths
