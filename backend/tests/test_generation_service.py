"""Generation pipeline with FAKE providers injected through the interfaces.

No network, no API keys, no object storage: this is what the provider
abstractions are for. The storage backend is replaced with an in-memory dict.
"""

import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import AsyncClient

from app.core.exceptions import ProviderError
from app.schemas.generation import GeneratedScene, GeneratedScript
from app.services.ai import base as ai_base
from app.services.ai.base import AudioResult, ImageResult
from app.services.storage.base import StorageBackend, StoredObject


class FakeStorage(StorageBackend):
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def ensure_ready(self) -> None:
        return None

    async def put_bytes(self, key: str, data: bytes, mime_type: str) -> StoredObject:
        self.objects[key] = data
        return StoredObject(key, len(data), mime_type, f"http://fake/{key}")

    async def get_bytes(self, key: str) -> bytes:
        return self.objects[key]

    async def delete(self, key: str) -> None:
        self.objects.pop(key, None)

    async def exists(self, key: str) -> bool:
        return key in self.objects

    async def presigned_url(self, key: str, expires_in: int = 3600) -> str:
        return f"http://fake/{key}?signed=1"


class FakeLLM(ai_base.LLMProvider):
    name = "fake-llm"

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    async def generate_script(self, request: ai_base.ScriptRequest) -> GeneratedScript:
        if self.fail:
            raise ProviderError("provider exploded", code="LLM_PROVIDER_ERROR")
        return GeneratedScript(
            title="Fake Script",
            description="desc",
            language=request.language,
            estimated_duration=10,
            scenes=[
                GeneratedScene(
                    scene_number=1,
                    narration="First sentence here. Second sentence here.",
                    visual_prompt="a chart",
                    on_screen_text="Intro",
                    duration=5,
                ),
                GeneratedScene(
                    scene_number=2,
                    narration="Another scene narration.",
                    visual_prompt="a diagram",
                    on_screen_text="Next",
                    duration=5,
                ),
            ],
        )


class FakeImages(ai_base.ImageProvider):
    name = "fake-image"
    calls = 0

    async def generate_image(
        self, prompt: str, width: int, height: int, *, style: str | None = None
    ) -> ImageResult:
        FakeImages.calls += 1
        return ImageResult(b"PNGDATA", "image/png", width, height, self.name)


class FakeTTS(ai_base.TTSProvider):
    name = "fake-tts"

    def supports_language(self, language: str) -> bool:
        return True

    async def generate(self, text: str, language: str, voice: str) -> AudioResult:
        # Deliberately longer than the scene, to test duration reconciliation.
        return AudioResult(b"MP3DATA", "audio/mpeg", 6.25, self.name, voice)


@pytest.fixture
async def fakes(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[FakeStorage]:
    storage = FakeStorage()
    import app.services.generation_service as gen

    monkeypatch.setattr(gen, "get_storage", lambda: storage)
    monkeypatch.setattr(gen, "get_llm_provider", lambda: FakeLLM())
    monkeypatch.setattr(gen, "get_image_provider", lambda: FakeImages())
    monkeypatch.setattr(gen, "get_tts_provider", lambda language="en": FakeTTS())
    yield storage


async def test_generate_creates_scenes_and_captions(
    auth_client: AsyncClient, project: dict, fakes: FakeStorage
) -> None:
    response = await auth_client.post(
        f"/api/projects/{project['id']}/generate",
        json={"prompt": "explain testing", "duration": 10, "language": "en",
              "style": "educational", "generate_media": False},
    )
    assert response.status_code == 202, response.text
    assert response.json()["scene_count"] == 2
    assert response.json()["status"] == "ready"

    scenes = (await auth_client.get(f"/api/projects/{project['id']}/scenes")).json()
    assert [s["scene_number"] for s in scenes] == [1, 2]
    # Captions are derived from narration immediately, before any audio exists.
    assert scenes[0]["captions"]
    assert scenes[0]["captions"][0]["start_time"] == 0.0


async def test_generate_replaces_a_previous_script(
    auth_client: AsyncClient, project: dict, fakes: FakeStorage
) -> None:
    body = {"prompt": "first", "duration": 10, "language": "en", "style": "educational",
            "generate_media": False}
    await auth_client.post(f"/api/projects/{project['id']}/generate", json=body)
    await auth_client.post(f"/api/projects/{project['id']}/generate", json=body)

    scenes = (await auth_client.get(f"/api/projects/{project['id']}/scenes")).json()
    assert len(scenes) == 2  # not 4: generation replaces the timeline


async def test_llm_failure_marks_the_project_failed(
    auth_client: AsyncClient, project: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.services.generation_service as gen

    monkeypatch.setattr(gen, "get_llm_provider", lambda: FakeLLM(fail=True))
    response = await auth_client.post(
        f"/api/projects/{project['id']}/generate",
        json={"prompt": "boom", "duration": 10, "language": "en", "style": "educational",
              "generate_media": False},
    )
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "LLM_PROVIDER_ERROR"

    # The project must not be stuck in "generating" forever.
    project_after = (await auth_client.get(f"/api/projects/{project['id']}")).json()
    assert project_after["status"] == "failed"
    assert project_after["error_message"]


async def test_scene_image_is_stored_and_attached(
    auth_client: AsyncClient, project: dict, fakes: FakeStorage
) -> None:
    generated = await auth_client.post(
        f"/api/projects/{project['id']}/generate",
        json={"prompt": "explain testing", "duration": 10, "language": "en", "style": "educational",
              "generate_media": False},
    )
    assert generated.status_code == 202, generated.text
    scene = (await auth_client.get(f"/api/projects/{project['id']}/scenes")).json()[0]

    response = await auth_client.post(f"/api/scenes/{scene['id']}/generate-image")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"

    # The bytes went to storage under the documented key layout...
    key = f"projects/{project['id']}/scenes/{scene['id']}/image.png"
    assert fakes.objects[key] == b"PNGDATA"
    # ...and the scene now exposes a URL.
    refreshed = (await auth_client.get(f"/api/scenes/{scene['id']}")).json()
    assert refreshed["image_url"]


async def test_regenerating_an_image_reuses_the_same_key(
    auth_client: AsyncClient, project: dict, fakes: FakeStorage
) -> None:
    await auth_client.post(
        f"/api/projects/{project['id']}/generate",
        json={"prompt": "explain testing", "duration": 10, "language": "en", "style": "educational",
              "generate_media": False},
    )
    scene = (await auth_client.get(f"/api/projects/{project['id']}/scenes")).json()[0]

    await auth_client.post(f"/api/scenes/{scene['id']}/generate-image")
    before = len(fakes.objects)
    await auth_client.post(f"/api/scenes/{scene['id']}/generate-image")
    assert len(fakes.objects) == before  # overwritten, not duplicated


async def test_voice_extends_a_too_short_scene_and_retimes_captions(
    auth_client: AsyncClient, project: dict, fakes: FakeStorage
) -> None:
    await auth_client.post(
        f"/api/projects/{project['id']}/generate",
        json={"prompt": "explain testing", "duration": 10, "language": "en", "style": "educational",
              "generate_media": False},
    )
    scene = (await auth_client.get(f"/api/projects/{project['id']}/scenes")).json()[0]
    assert scene["duration"] == 5

    assert (await auth_client.post(f"/api/scenes/{scene['id']}/generate-voice")).status_code == 200

    refreshed = (await auth_client.get(f"/api/scenes/{scene['id']}")).json()
    # FakeTTS returns 6.25s of audio for a 5s scene: the scene must grow, or the
    # narration would be cut off in the render.
    assert refreshed["duration"] == 6.25
    assert refreshed["audio_url"]
    # Captions were re-timed against the real audio length.
    assert refreshed["captions"][-1]["end_time"] == 6.25


async def test_generation_requires_ownership(
    client: AsyncClient, auth_client: AsyncClient, project: dict, fakes: FakeStorage
) -> None:
    other = await client.post(
        "/api/auth/register",
        json={"email": f"o{uuid.uuid4().hex[:8]}@example.com", "password": "supersecret123"},
    )
    headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    response = await client.post(
        f"/api/projects/{project['id']}/generate",
        json={"prompt": "steal", "duration": 10, "language": "en", "style": "educational",
              "generate_media": False},
        headers=headers,
    )
    assert response.status_code == 404
