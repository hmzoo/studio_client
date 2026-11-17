"""Tests d'intégration : storyboard (scènes/plans) et fiches de références."""
_TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080600000"
    "01f15c4890000000d49444154789c626000000000ffff030000060005"
    "57bfabd40000000049454e44ae426082"
)


def _create_project(client, name="S"):
    r = client.post("/api/projects", json={"name": name})
    assert r.status_code == 200
    return r.json()["id"]


def _create_character(client, pid, name="P"):
    r = client.post(f"/api/projects/{pid}/references", json={"kind": "character", "name": name, "description": "init"})
    assert r.status_code == 200
    return r.json()["id"]


def test_scenes_and_shots_crud(client):
    pid = _create_project(client)
    r = client.post(f"/api/projects/{pid}/scenes", json={"title": "S1", "narrative": "narration"})
    assert r.status_code == 200
    scene_id = r.json()["id"]

    r = client.post(f"/api/projects/{pid}/scenes/{scene_id}/shots",
                    json={"action": "plan large", "visual_intent": "décor",
                          "character_ids": ["c1"], "media_ids": ["m1"]})
    assert r.status_code == 200
    shot = r.json()
    assert shot["character_ids"] == "c1"
    assert shot["media_ids"] == "m1"
    assert shot["environment_ids"] == ""

    scenes = client.get(f"/api/projects/{pid}/scenes").json()
    assert scenes[0]["title"] == "S1"
    shots = client.get(f"/api/projects/{pid}/scenes/{scene_id}/shots").json()
    assert len(shots) == 1


def test_reference_update(client):
    pid = _create_project(client)
    rid = _create_character(client, pid)
    r = client.patch(f"/api/projects/{pid}/references/character/{rid}",
                     json={"name": "Nouveau nom", "description": "nouvelle description"})
    assert r.status_code == 200
    assert r.json()["name"] == "Nouveau nom"
    assert r.json()["initial_description"] == "nouvelle description"
    # l'approbation n'est pas touchée par une édition de la fiche
    assert r.json()["approved_description"] is None


def test_reference_unlink_asset(client):
    pid = _create_project(client)
    rid = _create_character(client, pid)
    r = client.post(f"/api/projects/{pid}/references/character/{rid}/import",
                    files={"file": ("r.png", _TINY_PNG, "image/png")})
    assert r.status_code == 200
    ref = client.get(f"/api/projects/{pid}/references?kind=character").json()[0]
    asset_id = ref["media_ids"].split(",")[0]

    r = client.delete(f"/api/projects/{pid}/references/character/{rid}/assets/{asset_id}")
    assert r.status_code == 200
    assert r.json()["media_ids"] == ""

    # l'asset reste dans la médiathèque
    assets = client.get(f"/api/projects/{pid}/assets").json()
    assert any(a["id"] == asset_id for a in assets)
