"""Editor operations: settings, split, trim, restore (undo), media library, music."""

import shutil
import subprocess
from pathlib import Path

import pytest
from httpx import AsyncClient

NARRATION = "alpha beta gamma delta epsilon zeta eta theta"
HAS_FFMPEG = shutil.which("ffmpeg") is not None


async def _scene(client: AsyncClient, project_id: str, **fields) -> dict:
    body = {"narration": NARRATION, "duration": 8.0, "language": "en", **fields}
    response = await client.post(f"/api/projects/{project_id}/scenes", json=body)
    assert response.status_code == 201, response.text
    return response.json()


async def _timeline(client: AsyncClient, project_id: str) -> list[dict]:
    return (await client.get(f"/api/projects/{project_id}/scenes")).json()


def _snapshot(scenes: list[dict], project: dict | None = None) -> dict:
    return {
        "scenes": [
            {
                **{k: s[k] for k in (
                    "id", "narration", "visual_prompt", "on_screen_text", "duration",
                    "transition", "background_color", "language", "settings",
                    "image_asset_id", "video_asset_id", "audio_asset_id",
                )},
                "captions": [
                    {"text": c["text"], "start_time": c["start_time"],
                     "end_time": c["end_time"], "language": c["language"]}
                    for c in s["captions"]
                ],
            }
            for s in scenes
        ],
        "music_asset_id": (project or {}).get("music_asset_id"),
        "music": (project or {}).get("music", {}),
    }


def _layer(**extra) -> dict:
    return {"id": "l1", "type": "text", "text": "Hello", "x": 50, "y": 40, "font_size": 8,
            "rotation": 0, "color": "#ffffff", "background": None, "weight": 800,
            "animation": "pop", "start": 0, "end": 3, **extra}


# ------------------------------------------------------------------- settings
async def test_settings_patch_merges_and_keeps_generator_keys(
    auth_client: AsyncClient, project: dict
) -> None:
    scene = await _scene(auth_client, project["id"], settings={"mood": "hook"})
    response = await auth_client.patch(
        f"/api/scenes/{scene['id']}", json={"settings": {"layers": [_layer()], "voice_volume": 0.5}}
    )
    assert response.status_code == 200
    settings = response.json()["settings"]
    assert settings["mood"] == "hook"
    assert settings["voice_volume"] == 0.5
    assert settings["layers"][0]["text"] == "Hello"

    cleared = await auth_client.patch(
        f"/api/scenes/{scene['id']}", json={"settings": {"voice_volume": None}}
    )
    assert "voice_volume" not in cleared.json()["settings"]
    assert cleared.json()["settings"]["layers"]


@pytest.mark.parametrize(
    "bad",
    [
        {"layers": [_layer(x=900)]},
        {"layers": [_layer(color="red")]},
        {"layers": [_layer(start=3, end=1)]},
        {"layers": [_layer(animation="explode")]},
        {"layers": [_layer(text="")]},
        {"voice_volume": 3},
        {"clip_volume": -1},
        {"trim_start": -2},
        {"media_fit": "stretch"},
    ],
)
async def test_invalid_settings_are_rejected(
    auth_client: AsyncClient, project: dict, bad: dict
) -> None:
    scene = await _scene(auth_client, project["id"])
    response = await auth_client.patch(f"/api/scenes/{scene['id']}", json={"settings": bad})
    assert response.status_code == 422


# ----------------------------------------------------------------- split / trim
async def test_split_makes_two_scenes_that_add_up(auth_client: AsyncClient, project: dict) -> None:
    first = await _scene(auth_client, project["id"], on_screen_text="Key point",
                         transition="slide", duration=8.0)
    await _scene(auth_client, project["id"], narration="tail", duration=2.0)

    response = await auth_client.post(f"/api/scenes/{first['id']}/split", json={"at": 3.0})
    assert response.status_code == 200, response.text
    scenes = response.json()
    assert [s["scene_number"] for s in scenes] == [1, 2, 3]
    left, right = scenes[0], scenes[1]
    assert left["id"] == first["id"]
    assert left["duration"] == 3.0 and right["duration"] == 5.0
    assert left["on_screen_text"] == "Key point" and right["on_screen_text"] is None
    assert right["transition"] == "none"
    # Nothing was lost or invented: the words are the same, split in two.
    assert f"{left['narration']} {right['narration']}".split() == NARRATION.split()
    assert scenes[2]["narration"] == "tail"
    # timeline stays contiguous
    assert right["start_time"] == pytest.approx(3.0)
    assert scenes[2]["start_time"] == pytest.approx(8.0)


async def test_split_outside_the_scene_is_rejected(
    auth_client: AsyncClient, project: dict
) -> None:
    scene = await _scene(auth_client, project["id"], duration=4.0)
    for at in (0.05, 3.95, 9.0):
        response = await auth_client.post(f"/api/scenes/{scene['id']}/split", json={"at": at})
        assert response.status_code == 422, at
        assert response.json()["error"]["code"] == "INVALID_CUT"
    assert len(await _timeline(auth_client, project["id"])) == 1


async def test_split_keeps_speech_in_sync(auth_client: AsyncClient, project: dict) -> None:
    speech = {
        "narration": NARRATION,
        "words": [[w, i * 1.0, i * 1.0 + 1.0] for i, w in enumerate(NARRATION.split())],
        "mouth": list(range(80)),
        "fps": 10,
    }
    scene = await _scene(auth_client, project["id"], settings={"speech": speech})
    scenes = (await auth_client.post(f"/api/scenes/{scene['id']}/split", json={"at": 4.0})).json()
    right = scenes[1]
    assert right["settings"]["audio_start"] == 4.0
    assert right["settings"]["speech"]["narration"] == right["narration"]
    assert right["settings"]["speech"]["words"][0][1] == pytest.approx(0.0)
    assert len(right["settings"]["speech"]["mouth"]) == 40
    # captions follow the real word marks, so they cover the whole 4s
    assert right["captions"][-1]["end_time"] == pytest.approx(4.0, abs=0.6)


async def test_trim_keeps_the_window(auth_client: AsyncClient, project: dict) -> None:
    scene = await _scene(auth_client, project["id"], duration=8.0,
                         settings={"layers": [_layer(start=0, end=8)]})
    scenes = (
        await auth_client.post(f"/api/scenes/{scene['id']}/trim", json={"start": 2.0, "end": 6.0})
    ).json()
    assert len(scenes) == 1
    trimmed = scenes[0]
    assert trimmed["duration"] == 4.0
    assert trimmed["settings"]["audio_start"] == 2.0
    assert trimmed["settings"]["layers"][0]["start"] == 0 and trimmed["settings"]["layers"][0]["end"] == 4
    assert all(0 <= c["start_time"] < c["end_time"] <= 4.0 + 1e-6 for c in trimmed["captions"])


async def test_trim_rejects_bad_windows(auth_client: AsyncClient, project: dict) -> None:
    scene = await _scene(auth_client, project["id"], duration=5.0)
    for body in ({"start": 4.0, "end": 9.0}, {"start": 3.0, "end": 3.1}):
        response = await auth_client.post(f"/api/scenes/{scene['id']}/trim", json=body)
        assert response.status_code == 422
    assert (await auth_client.post(
        f"/api/scenes/{scene['id']}/trim", json={"start": 3.0, "end": 2.0})).status_code == 422


# ---------------------------------------------------------------- restore/undo
async def test_restore_undoes_split_delete_and_edits(
    auth_client: AsyncClient, project: dict
) -> None:
    a = await _scene(auth_client, project["id"], narration="first scene", duration=4.0)
    b = await _scene(auth_client, project["id"], narration="second scene", duration=6.0)
    before = await _timeline(auth_client, project["id"])
    snapshot = _snapshot(before)

    await auth_client.post(f"/api/scenes/{a['id']}/split", json={"at": 2.0})
    await auth_client.delete(f"/api/scenes/{b['id']}")
    await auth_client.patch(f"/api/scenes/{a['id']}", json={"on_screen_text": "changed"})
    assert len(await _timeline(auth_client, project["id"])) == 2

    response = await auth_client.put(f"/api/projects/{project['id']}/scenes/timeline", json=snapshot)
    assert response.status_code == 200, response.text
    after = response.json()
    assert [s["id"] for s in after] == [s["id"] for s in before]
    assert [s["scene_number"] for s in after] == [1, 2]
    for old, new in zip(before, after, strict=True):
        for key in ("narration", "duration", "on_screen_text", "transition", "start_time"):
            assert new[key] == old[key], key
        assert [(c["text"], c["start_time"], c["end_time"]) for c in new["captions"]] == [
            (c["text"], c["start_time"], c["end_time"]) for c in old["captions"]
        ]


async def test_restore_is_idempotent_and_can_redo(auth_client: AsyncClient, project: dict) -> None:
    await _scene(auth_client, project["id"], duration=4.0)
    snapshot = _snapshot(await _timeline(auth_client, project["id"]))
    url = f"/api/projects/{project['id']}/scenes/timeline"
    first = (await auth_client.put(url, json=snapshot)).json()
    second = (await auth_client.put(url, json=snapshot)).json()
    assert [s["id"] for s in first] == [s["id"] for s in second]
    assert len(second) == 1


async def test_restore_rejects_other_projects_scenes(
    auth_client: AsyncClient, project: dict
) -> None:
    other = (await auth_client.post("/api/projects", json={"title": "other"})).json()
    stolen = await _scene(auth_client, other["id"])
    snapshot = _snapshot(await _timeline(auth_client, other["id"]))
    assert stolen["id"] == snapshot["scenes"][0]["id"]
    response = await auth_client.put(
        f"/api/projects/{project['id']}/scenes/timeline", json=snapshot
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "SCENE_PROJECT_MISMATCH"
    assert len(await _timeline(auth_client, other["id"])) == 1  # untouched


async def test_restore_rejects_foreign_media(auth_client: AsyncClient, project: dict) -> None:
    await _scene(auth_client, project["id"])
    snapshot = _snapshot(await _timeline(auth_client, project["id"]))
    snapshot["scenes"][0]["image_asset_id"] = "00000000-0000-4000-8000-000000000000"
    response = await auth_client.put(
        f"/api/projects/{project['id']}/scenes/timeline", json=snapshot
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ASSET_NOT_FOUND"


async def test_restore_requires_the_owner(
    auth_client: AsyncClient, client: AsyncClient, project: dict
) -> None:
    await _scene(auth_client, project["id"])
    snapshot = _snapshot(await _timeline(auth_client, project["id"]))
    stranger = await client.post(
        "/api/auth/register", json={"email": "stranger@example.com", "password": "supersecret123"}
    )
    token = stranger.json()["access_token"]
    response = await client.put(
        f"/api/projects/{project['id']}/scenes/timeline",
        json=snapshot,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


# ------------------------------------------------------------- media + music
def _make_media(tmp_path: Path, name: str, args: list[str]) -> bytes:
    out = tmp_path / name
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args, str(out)], check=True)
    return out.read_bytes()


@pytest.fixture
def mp4(tmp_path: Path) -> bytes:
    if not HAS_FFMPEG:
        pytest.skip("ffmpeg not installed")
    return _make_media(tmp_path, "clip.mp4", [
        "-f", "lavfi", "-i", "testsrc=duration=2:size=64x64:rate=10",
        "-c:v", "libx264", "-pix_fmt", "yuv420p"])


@pytest.fixture
def mp3(tmp_path: Path) -> bytes:
    if not HAS_FFMPEG:
        pytest.skip("ffmpeg not installed")
    return _make_media(tmp_path, "song.mp3", ["-f", "lavfi", "-i", "sine=frequency=440:duration=3"])


async def test_video_upload_is_probed_and_attached(
    auth_client: AsyncClient, project: dict, mp4: bytes
) -> None:
    scene = await _scene(auth_client, project["id"])
    response = await auth_client.post(
        "/api/assets/upload",
        data={"project_id": project["id"], "scene_id": scene["id"]},
        files={"file": ("clip.mp4", mp4, "video/mp4")},
    )
    assert response.status_code == 201, response.text
    asset = response.json()
    assert asset["duration"] == pytest.approx(2.0, abs=0.2)
    assert (asset["width"], asset["height"]) == (64, 64)

    loaded = (await _timeline(auth_client, project["id"]))[0]
    assert loaded["video_asset_id"] == asset["id"]
    assert loaded["video_duration"] == pytest.approx(2.0, abs=0.2)


async def test_new_picture_replaces_a_clip_and_resets_the_trim(
    auth_client: AsyncClient, project: dict, mp4: bytes
) -> None:
    from tests.test_assets import PNG_1PX

    scene = await _scene(auth_client, project["id"], settings={"trim_start": 1.5})
    await auth_client.post(
        "/api/assets/upload", data={"project_id": project["id"], "scene_id": scene["id"]},
        files={"file": ("clip.mp4", mp4, "video/mp4")},
    )
    await auth_client.post(
        "/api/assets/upload", data={"project_id": project["id"], "scene_id": scene["id"]},
        files={"file": ("pic.png", PNG_1PX, "image/png")},
    )
    loaded = (await _timeline(auth_client, project["id"]))[0]
    assert loaded["video_asset_id"] is None and loaded["image_asset_id"]
    assert "trim_start" not in loaded["settings"]


async def test_scene_can_only_use_its_own_projects_media(
    auth_client: AsyncClient, project: dict
) -> None:
    from tests.test_assets import PNG_1PX

    other = (await auth_client.post("/api/projects", json={"title": "other"})).json()
    foreign = (await auth_client.post(
        "/api/assets/upload", data={"project_id": other["id"]},
        files={"file": ("pic.png", PNG_1PX, "image/png")},
    )).json()
    scene = await _scene(auth_client, project["id"])
    response = await auth_client.patch(
        f"/api/scenes/{scene['id']}", json={"image_asset_id": foreign["id"]}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ASSET_NOT_FOUND"


async def test_library_lists_uploads_and_a_scene_can_use_one(
    auth_client: AsyncClient, project: dict
) -> None:
    from tests.test_assets import PNG_1PX

    uploaded = (await auth_client.post(
        "/api/assets/upload", data={"project_id": project["id"]},
        files={"file": ("pic.png", PNG_1PX, "image/png")},
    )).json()
    library = (await auth_client.get(f"/api/projects/{project['id']}/assets")).json()
    assert [a["id"] for a in library] == [uploaded["id"]]

    scene = await _scene(auth_client, project["id"])
    patched = await auth_client.patch(
        f"/api/scenes/{scene['id']}", json={"image_asset_id": uploaded["id"]}
    )
    assert patched.json()["image_url"]
    removed = await auth_client.patch(f"/api/scenes/{scene['id']}", json={"image_asset_id": None})
    assert removed.json()["image_url"] is None


async def test_music_upload_settings_remove_and_restore(
    auth_client: AsyncClient, project: dict, mp3: bytes
) -> None:
    response = await auth_client.post(
        f"/api/projects/{project['id']}/music", files={"file": ("song.mp3", mp3, "audio/mpeg")}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["music_url"] and body["music_name"] == "song.mp3"
    assert body["music_duration"] == pytest.approx(3.0, abs=0.3)
    assert body["music"] == {"enabled": True, "volume": 1.0, "fade_in": 0.4,
                             "fade_out": 1.0, "duck": True}

    tuned = (await auth_client.patch(
        f"/api/projects/{project['id']}",
        json={"music": {"enabled": True, "volume": 0.3, "fade_in": 2, "fade_out": 2, "duck": False}},
    )).json()
    assert tuned["music"]["volume"] == 0.3 and tuned["music"]["duck"] is False
    assert tuned["music_url"] == body["music_url"]  # settings change keeps the track

    removed = (await auth_client.delete(f"/api/projects/{project['id']}/music")).json()
    assert removed["music_url"] is None

    # Undo of the removal: the snapshot taken while the track was set brings it back.
    await _scene(auth_client, project["id"])
    snapshot = _snapshot(await _timeline(auth_client, project["id"]), tuned)
    restored = await auth_client.put(
        f"/api/projects/{project['id']}/scenes/timeline", json=snapshot
    )
    assert restored.status_code == 200, restored.text
    again = (await auth_client.get(f"/api/projects/{project['id']}")).json()
    assert again["music_url"] == body["music_url"] and again["music"]["volume"] == 0.3


async def test_music_must_be_audio(auth_client: AsyncClient, project: dict) -> None:
    from tests.test_assets import PNG_1PX

    response = await auth_client.post(
        f"/api/projects/{project['id']}/music", files={"file": ("pic.png", PNG_1PX, "image/png")}
    )
    assert response.status_code == 422


async def test_music_settings_are_validated(auth_client: AsyncClient, project: dict) -> None:
    response = await auth_client.patch(
        f"/api/projects/{project['id']}", json={"music": {"volume": 5}}
    )
    assert response.status_code == 422


async def test_duplicating_a_project_copies_its_music(
    auth_client: AsyncClient, project: dict, mp3: bytes
) -> None:
    original = (await auth_client.post(
        f"/api/projects/{project['id']}/music", files={"file": ("song.mp3", mp3, "audio/mpeg")}
    )).json()
    copy = (await auth_client.post(f"/api/projects/{project['id']}/duplicate")).json()
    assert copy["music_url"] and copy["music_url"] != original["music_url"]
    await auth_client.delete(f"/api/projects/{project['id']}")
    survivor = (await auth_client.get(f"/api/projects/{copy['id']}")).json()
    assert survivor["music_url"] == copy["music_url"]


async def test_hevc_video_is_converted_to_h264(
    auth_client: AsyncClient, project: dict, tmp_path: Path
) -> None:
    if not HAS_FFMPEG:
        pytest.skip("ffmpeg not installed")
    try:
        hevc = _make_media(tmp_path, "phone.mp4", [
            "-f", "lavfi", "-i", "testsrc=duration=1:size=64x64:rate=10",
            "-c:v", "libx265", "-pix_fmt", "yuv420p", "-tag:v", "hvc1"])
    except subprocess.CalledProcessError:
        pytest.skip("this ffmpeg has no HEVC encoder")

    response = await auth_client.post(
        "/api/assets/upload", data={"project_id": project["id"]},
        files={"file": ("phone.mp4", hevc, "video/mp4")},
    )
    assert response.status_code == 201, response.text
    asset = response.json()
    assert asset["mime_type"] == "video/mp4"
    assert asset["duration"] == pytest.approx(1.0, abs=0.2)

    from app.services.media import probe_media
    from app.services.storage import get_storage

    stored = await get_storage().get_bytes(asset["storage_key"])
    assert (await probe_media(stored, ".mp4")).video_codec == "h264"


async def test_render_payload_carries_editor_settings(
    auth_client: AsyncClient, project: dict, session
) -> None:
    import uuid

    from sqlalchemy import select

    from app.models.project import Project
    from app.repositories.project_repository import ProjectRepository
    from app.services.render_payload import build_composition_payload

    await _scene(auth_client, project["id"], settings={
        "layers": [_layer(font_size=9.5)], "voice_volume": 0.4, "clip_volume": 0.7,
        "trim_start": 1.25, "audio_start": 2.5, "media_fit": "contain", "ken_burns": False})
    await auth_client.patch(f"/api/projects/{project['id']}",
                            json={"music": {"volume": 0.2, "fade_in": 1, "fade_out": 3,
                                            "duck": False, "enabled": True}})
    row = (await session.execute(
        select(Project).where(Project.id == uuid.UUID(project["id"])))).scalar_one()
    loaded = await ProjectRepository(session).get_for_owner(row.id, row.owner_id)
    payload = build_composition_payload(loaded)

    scene = payload["scenes"][0]
    assert scene["layers"][0]["fontSize"] == 9.5 and "font_size" not in scene["layers"][0]
    assert (scene["voiceVolume"], scene["clipVolume"]) == (0.4, 0.7)
    assert (scene["trimStart"], scene["audioStart"]) == (1.25, 2.5)
    assert (scene["mediaFit"], scene["kenBurns"]) == ("contain", False)
    assert (payload["project"]["musicVolume"], payload["project"]["musicFadeOut"],
            payload["project"]["musicDuck"]) == (0.2, 3, False)


# ------------------------------------------------------------------- captions
def _caps(*items: tuple[str, float, float]) -> dict:
    return {"captions": [{"text": t, "start_time": s, "end_time": e} for t, s, e in items]}


async def test_captions_can_be_edited_by_hand(auth_client: AsyncClient, project: dict) -> None:
    scene = await _scene(auth_client, project["id"], duration=8.0)
    response = await auth_client.put(
        f"/api/scenes/{scene['id']}/captions",
        json=_caps(("Second line", 3.0, 6.0), ("First line", 0.5, 2.5)),  # out of order on purpose
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert [(c["text"], c["start_time"], c["end_time"]) for c in body["captions"]] == [
        ("First line", 0.5, 2.5),
        ("Second line", 3.0, 6.0),
    ]
    assert body["settings"]["captions_edited"] is True


async def test_caption_end_is_clipped_to_the_scene(auth_client: AsyncClient, project: dict) -> None:
    scene = await _scene(auth_client, project["id"], duration=4.0)
    body = (await auth_client.put(
        f"/api/scenes/{scene['id']}/captions", json=_caps(("Long", 1.0, 99.0)))).json()
    assert body["captions"][0]["end_time"] == 4.0


@pytest.mark.parametrize(
    ("items", "code"),
    [
        ([("A", 0.0, 2.0), ("B", 1.0, 3.0)], "CAPTIONS_OVERLAP"),
        ([("  ", 0.0, 2.0)], "EMPTY_CAPTION"),
        ([("Late", 4.0, 5.0)], "CAPTION_OUT_OF_RANGE"),
        ([("x" * 301, 0.0, 2.0)], "CAPTION_TOO_LONG"),
        ([("Blink", 1.0, 1.05)], "CAPTION_TOO_SHORT"),
    ],
)
async def test_bad_captions_are_rejected_and_nothing_changes(
    auth_client: AsyncClient, project: dict, items: list, code: str
) -> None:
    scene = await _scene(auth_client, project["id"], duration=4.0)
    before = (await _timeline(auth_client, project["id"]))[0]["captions"]
    response = await auth_client.put(f"/api/scenes/{scene['id']}/captions", json=_caps(*items))
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == code
    after = (await _timeline(auth_client, project["id"]))[0]
    assert after["captions"] == before
    assert "captions_edited" not in after["settings"]


async def test_zero_length_caption_fails_validation(auth_client: AsyncClient, project: dict) -> None:
    scene = await _scene(auth_client, project["id"])
    response = await auth_client.put(
        f"/api/scenes/{scene['id']}/captions", json=_caps(("A", 2.0, 2.0)))
    assert response.status_code == 422


async def test_all_captions_can_be_removed(auth_client: AsyncClient, project: dict) -> None:
    scene = await _scene(auth_client, project["id"])
    body = (await auth_client.put(
        f"/api/scenes/{scene['id']}/captions", json={"captions": []})).json()
    assert body["captions"] == [] and body["settings"]["captions_edited"] is True


async def test_changing_the_length_keeps_edited_captions_and_clips_them(
    auth_client: AsyncClient, project: dict
) -> None:
    scene = await _scene(auth_client, project["id"], duration=8.0)
    await auth_client.put(
        f"/api/scenes/{scene['id']}/captions",
        json=_caps(("Keep", 0.0, 2.0), ("Clip", 3.0, 7.0), ("Drop", 7.2, 7.9)),
    )
    body = (await auth_client.patch(f"/api/scenes/{scene['id']}", json={"duration": 5.0})).json()
    assert [(c["text"], c["start_time"], c["end_time"]) for c in body["captions"]] == [
        ("Keep", 0.0, 2.0), ("Clip", 3.0, 5.0)]
    assert body["settings"]["captions_edited"] is True


async def test_changing_the_length_still_rebuilds_automatic_captions(
    auth_client: AsyncClient, project: dict
) -> None:
    scene = await _scene(auth_client, project["id"], duration=8.0)
    body = (await auth_client.patch(f"/api/scenes/{scene['id']}", json={"duration": 4.0})).json()
    assert body["captions"] and max(c["end_time"] for c in body["captions"]) <= 4.0 + 1e-6


async def test_new_narration_rebuilds_captions_and_clears_the_edit_flag(
    auth_client: AsyncClient, project: dict
) -> None:
    scene = await _scene(auth_client, project["id"], duration=8.0)
    await auth_client.put(f"/api/scenes/{scene['id']}/captions", json=_caps(("Mine", 1.0, 2.0)))
    body = (await auth_client.patch(
        f"/api/scenes/{scene['id']}", json={"narration": "brand new narration here"})).json()
    assert "captions_edited" not in body["settings"]
    assert " ".join(c["text"] for c in body["captions"]).replace("  ", " ").split() == [
        "brand", "new", "narration", "here"]


async def test_reset_returns_to_automatic_captions(auth_client: AsyncClient, project: dict) -> None:
    scene = await _scene(auth_client, project["id"], duration=8.0)
    await auth_client.put(f"/api/scenes/{scene['id']}/captions", json=_caps(("Mine", 1.0, 2.0)))
    body = (await auth_client.post(f"/api/scenes/{scene['id']}/captions/reset")).json()
    assert "captions_edited" not in body["settings"]
    assert " ".join(c["text"] for c in body["captions"]).split() == NARRATION.split()


async def test_edited_captions_survive_split_and_undo(
    auth_client: AsyncClient, project: dict
) -> None:
    scene = await _scene(auth_client, project["id"], duration=8.0)
    await auth_client.put(
        f"/api/scenes/{scene['id']}/captions", json=_caps(("Hello there", 0.5, 3.0), ("World", 5.0, 7.0)))
    snapshot = _snapshot(await _timeline(auth_client, project["id"]))
    scenes = (await auth_client.post(f"/api/scenes/{scene['id']}/split", json={"at": 4.0})).json()
    assert [c["text"] for c in scenes[0]["captions"]] == ["Hello there"]
    assert [(c["text"], c["start_time"]) for c in scenes[1]["captions"]] == [("World", 1.0)]
    assert scenes[0]["settings"]["captions_edited"] and scenes[1]["settings"]["captions_edited"]

    restored = (await auth_client.put(
        f"/api/projects/{project['id']}/scenes/timeline", json=snapshot)).json()
    assert [c["text"] for c in restored[0]["captions"]] == ["Hello there", "World"]
    assert restored[0]["settings"]["captions_edited"] is True


async def test_edited_caption_text_reaches_the_renderer(
    auth_client: AsyncClient, project: dict, session
) -> None:
    import uuid

    from sqlalchemy import select

    from app.models.project import Project
    from app.repositories.project_repository import ProjectRepository
    from app.services.render_payload import build_composition_payload

    scene = await _scene(auth_client, project["id"], duration=6.0)
    await auth_client.put(f"/api/scenes/{scene['id']}/captions", json=_caps(("Edited caption", 1.0, 4.0)))
    row = (await session.execute(
        select(Project).where(Project.id == uuid.UUID(project["id"])))).scalar_one()
    loaded = await ProjectRepository(session).get_for_owner(row.id, row.owner_id)
    payload = build_composition_payload(loaded)
    assert payload["scenes"][0]["captions"] == [{"text": "Edited caption", "start": 1.0, "end": 4.0}]


async def test_other_users_cannot_edit_captions(
    auth_client: AsyncClient, client: AsyncClient, project: dict
) -> None:
    scene = await _scene(auth_client, project["id"])
    stranger = await client.post(
        "/api/auth/register", json={"email": "cap-stranger@example.com", "password": "supersecret123"})
    response = await client.put(
        f"/api/scenes/{scene['id']}/captions", json=_caps(("Nope", 0.0, 1.0)),
        headers={"Authorization": f"Bearer {stranger.json()['access_token']}"})
    assert response.status_code == 404
