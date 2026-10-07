"""Asset upload validation and security."""

import io

from httpx import AsyncClient

from app.api.routes.assets import safe_filename

PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000a49444154789c6300010000050001"
    "0d0a2db40000000049454e44ae426082"
)


def test_safe_filename_strips_paths_and_unsafe_characters() -> None:
    assert safe_filename("../../etc/passwd") == "passwd"
    assert safe_filename("my photo!.png") == "my_photo_.png"
    assert safe_filename("/absolute/path/a.png") == "a.png"
    assert safe_filename("") == "upload"
    assert len(safe_filename("x" * 500)) <= 120


async def test_rejects_disallowed_mime_type(auth_client: AsyncClient, project: dict) -> None:
    response = await auth_client.post(
        "/api/assets/upload",
        data={"project_id": project["id"]},
        files={"file": ("evil.sh", io.BytesIO(b"#!/bin/sh\nrm -rf /"), "application/x-sh")},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


async def test_rejects_an_empty_file(auth_client: AsyncClient, project: dict) -> None:
    response = await auth_client.post(
        "/api/assets/upload",
        data={"project_id": project["id"]},
        files={"file": ("empty.png", io.BytesIO(b""), "image/png")},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "EMPTY_FILE"


async def test_rejects_a_file_over_the_size_limit(
    auth_client: AsyncClient, project: dict, monkeypatch
) -> None:
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "max_upload_size_mb", 1)

    response = await auth_client.post(
        "/api/assets/upload",
        data={"project_id": project["id"]},
        files={"file": ("big.png", io.BytesIO(b"x" * (2 * 1024 * 1024)), "image/png")},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"


async def test_upload_requires_project_ownership(auth_client: AsyncClient) -> None:
    import uuid

    response = await auth_client.post(
        "/api/assets/upload",
        data={"project_id": str(uuid.uuid4())},
        files={"file": ("a.png", io.BytesIO(PNG_1PX), "image/png")},
    )
    assert response.status_code == 404
