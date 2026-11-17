"""Tests d'intégration du parcours (fake gateway + worker synchrone)."""
import json
from unittest.mock import MagicMock, patch

from studio.application import services
from studio.orchestration import workflow
from studio.workers.worker import run_worker_once

_TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080600000"
    "01f15c4890000000d49444154789c626000000000ffff030000060005"
    "57bfabd40000000049454e44ae426082"
)


def _create_project(client, name="Demo"):
    r = client.post("/api/projects", json={"name": name})
    assert r.status_code == 200
    return r.json()["id"]


def _create_character(client, pid):
    r = client.post(f"/api/projects/{pid}/references",
                    json={"kind": "character", "name": "Personnage", "description": ""})
    assert r.status_code == 200
    return r.json()["id"]


def _import_and_analyze(client, pid, rid):
    r = client.post(f"/api/projects/{pid}/references/character/{rid}/import",
                    files={"file": ("ref.png", _TINY_PNG, "image/png")})
    assert r.status_code == 200
    r = client.post(f"/api/projects/{pid}/references/character/{rid}/analyze")
    assert r.status_code == 200
    return r.json()["id"]


def test_full_path(client):
    pid = _create_project(client)
    rid = _create_character(client, pid)
    task_id = _import_and_analyze(client, pid, rid)

    run_worker_once()
    assert client.get(f"/api/tasks/{task_id}").json()["status"] == "succeeded"

    proposals = client.get(f"/api/projects/{pid}/completions").json()
    assert len(proposals) == 1
    prop = proposals[0]
    assert prop["status"] == "pending"

    r = client.post(f"/api/projects/{pid}/completions/{prop['id']}/decision",
                    json={"status": "approved", "comment": "ok"})
    assert r.status_code == 200

    ref = client.get(f"/api/projects/{pid}/references?kind=character").json()[0]
    assert ref["approved_description"] == prop["content"]

    r = client.post(f"/api/projects/{pid}/generations",
                    json={"kind": "image", "request": {"prompt": "a fox", "width": 512, "height": 512}})
    assert r.status_code == 200
    gen_id = r.json()["id"]

    run_worker_once()
    gen = client.get(f"/api/projects/{pid}/generations/{gen_id}").json()
    assert gen["status"] == "succeeded"
    assert gen["external_job_id"]

    assets = client.get(f"/api/projects/{pid}/assets").json()
    assert any(a["kind"] == "image" and a["origin"] == "gateway" for a in assets)


def test_approval_without_silent_overwrite(client):
    pid = _create_project(client)
    rid = _create_character(client, pid)
    _import_and_analyze(client, pid, rid)
    run_worker_once()
    prop = client.get(f"/api/projects/{pid}/completions").json()[0]

    # rejet : ne doit pas écrire la description approuvée
    client.post(f"/api/projects/{pid}/completions/{prop['id']}/decision", json={"status": "rejected", "comment": ""})
    ref = client.get(f"/api/projects/{pid}/references?kind=character").json()[0]
    assert ref["approved_description"] is None

    # approbation explicite : écrit la description
    client.post(f"/api/projects/{pid}/completions/{prop['id']}/decision", json={"status": "approved", "comment": ""})
    ref = client.get(f"/api/projects/{pid}/references?kind=character").json()[0]
    assert ref["approved_description"] == prop["content"]


def test_invalid_structured_response_fails_task(client):
    pid = _create_project(client)
    rid = _create_character(client, pid)
    task_id = _import_and_analyze(client, pid, rid)

    bad = MagicMock()
    bad.simulated = True
    bad.generate_text.return_value.schema_valid = False
    bad.generate_text.return_value.data = None
    with patch.object(services, "get_gateway", return_value=bad):
        run_worker_once()
    assert client.get(f"/api/tasks/{task_id}").json()["status"] == "failed"
    assert client.get(f"/api/projects/{pid}/completions").json() == []


def test_submit_timeout_no_resubmit(client):
    pid = _create_project(client)
    r = client.post(f"/api/projects/{pid}/generations", json={"kind": "image", "request": {"prompt": "x"}})
    gen_id = r.json()["id"]

    gw = MagicMock()
    gw.simulated = True
    gw.generate_image.side_effect = Exception("timeout")
    with patch.object(workflow, "get_gateway", return_value=gw):
        run_worker_once()
        run_worker_once()

    gen = client.get(f"/api/projects/{pid}/generations/{gen_id}").json()
    assert gen["status"] == "needs_reconciliation"
    assert gen["external_job_id"] is None
    assert gw.generate_image.call_count == 1  # aucune relance aveugle


def test_resume_tracking_known_job(client):
    pid = _create_project(client)
    r = client.post(f"/api/projects/{pid}/generations", json={"kind": "image", "request": {"prompt": "x"}})
    gen_id = r.json()["id"]

    state = {"n": 0}
    gw = MagicMock()
    gw.simulated = True
    gw.generate_image.return_value = type("O", (), {"job": type("J", (), {"job_id": "job_1", "status": "queued"})(), "direct": None})()
    gw.get_job.side_effect = [
        type("S", (), {"status": "running", "result": None, "error": None, "kind": "image"})(),
        type("S", (), {"status": "succeeded", "result": {"images": [{"url": "fake://media/x.png"}]},
                              "error": None, "kind": "image"})(),
    ]
    gw.download_media.return_value = _TINY_PNG
    with patch.object(workflow, "get_gateway", return_value=gw):
        run_worker_once()  # soumission + 1er suivi (running)
        run_worker_once()  # reprise du suivi (succeeded)

    gen = client.get(f"/api/projects/{pid}/generations/{gen_id}").json()
    assert gen["status"] == "succeeded"
    assert gen["external_job_id"] == "job_1"
    # la reprise a consulté le job connu, sans nouvelle soumission
    assert gw.get_job.call_count == 2


def test_unknown_external_state(client):
    pid = _create_project(client)
    r = client.post(f"/api/projects/{pid}/generations", json={"kind": "image", "request": {"prompt": "x"}})
    gen_id = r.json()["id"]

    gw = MagicMock()
    gw.simulated = True
    gw.generate_image.return_value = type("O", (), {"job": type("J", (), {"job_id": "j", "status": "queued"})(), "direct": None})()
    gw.get_job.return_value = type("S", (), {"status": "weird_state", "result": None, "error": None})()
    with patch.object(workflow, "get_gateway", return_value=gw):
        run_worker_once()

    gen = client.get(f"/api/projects/{pid}/generations/{gen_id}").json()
    assert gen["status"] == "needs_reconciliation"
