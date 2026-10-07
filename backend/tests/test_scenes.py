"""Scene CRUD, ordering and timeline arithmetic."""

from httpx import AsyncClient


async def _add(client: AsyncClient, project_id: str, text: str, duration: float = 5.0) -> dict:
    response = await client.post(
        f"/api/projects/{project_id}/scenes", json={"narration": text, "duration": duration}
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_scenes_are_numbered_and_timed(auth_client: AsyncClient, project: dict) -> None:
    await _add(auth_client, project["id"], "first", 3)
    await _add(auth_client, project["id"], "second", 4)

    scenes = (await auth_client.get(f"/api/projects/{project['id']}/scenes")).json()
    assert [s["scene_number"] for s in scenes] == [1, 2]
    # start_time is derived from the durations before it, never stored twice.
    assert [s["start_time"] for s in scenes] == [0.0, 3.0]


async def test_insert_in_the_middle_shifts_the_rest(
    auth_client: AsyncClient, project: dict
) -> None:
    await _add(auth_client, project["id"], "a")
    await _add(auth_client, project["id"], "b")
    await auth_client.post(
        f"/api/projects/{project['id']}/scenes",
        json={"narration": "inserted", "duration": 2, "scene_number": 1},
    )

    scenes = (await auth_client.get(f"/api/projects/{project['id']}/scenes")).json()
    assert [s["narration"] for s in scenes] == ["inserted", "a", "b"]
    assert [s["scene_number"] for s in scenes] == [1, 2, 3]


async def test_reorder_requires_every_scene_id(auth_client: AsyncClient, project: dict) -> None:
    first = await _add(auth_client, project["id"], "a")
    await _add(auth_client, project["id"], "b")

    bad = await auth_client.post(
        f"/api/projects/{project['id']}/scenes/reorder", json={"scene_ids": [first["id"]]}
    )
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "INVALID_SCENE_ORDER"


async def test_reorder_rewrites_numbers_and_times(auth_client: AsyncClient, project: dict) -> None:
    a = await _add(auth_client, project["id"], "a", 3)
    b = await _add(auth_client, project["id"], "b", 4)

    reordered = await auth_client.post(
        f"/api/projects/{project['id']}/scenes/reorder", json={"scene_ids": [b["id"], a["id"]]}
    )
    assert [s["narration"] for s in reordered.json()] == ["b", "a"]
    assert [s["start_time"] for s in reordered.json()] == [0.0, 4.0]


async def test_delete_renumbers_remaining_scenes(auth_client: AsyncClient, project: dict) -> None:
    a = await _add(auth_client, project["id"], "a")
    await _add(auth_client, project["id"], "b")
    await _add(auth_client, project["id"], "c")

    assert (await auth_client.delete(f"/api/scenes/{a['id']}")).status_code == 204
    scenes = (await auth_client.get(f"/api/projects/{project['id']}/scenes")).json()
    assert [s["scene_number"] for s in scenes] == [1, 2]


async def test_duplicate_scene_lands_next_to_the_original(
    auth_client: AsyncClient, project: dict
) -> None:
    a = await _add(auth_client, project["id"], "a")
    await _add(auth_client, project["id"], "b")

    copy = await auth_client.post(f"/api/scenes/{a['id']}/duplicate")
    assert copy.status_code == 201
    assert copy.json()["scene_number"] == 2


async def test_khmer_narration_survives_the_round_trip(
    auth_client: AsyncClient, project: dict
) -> None:
    khmer = "បង្កើតវីដេអូ ១ នាទី អំពីប្រវត្តិសាស្ត្រអង្គរវត្ត"
    scene = await _add(auth_client, project["id"], khmer)
    assert scene["narration"] == khmer
