"""Workflow applicatif explicite, à états persistés.

Frontière d'orchestration : la boucle est ici un simple dispatch de tâches.
Une migration vers LangGraph remplacera `process_task` sans toucher au métier.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict

from sqlalchemy.orm import Session

from .. import storage
from ..agents.base import AgentRuntime
from ..agents.description_improver import improve_reference_description
from ..agents.prompt_builder import build_shot_prompt
from ..application.services import _run_analysis
from ..clients import get_gateway
from ..clients.interface import GatewayError, ImageRequest, TextRequest, VideoRequest
from ..config import settings
from ..domain.models import Asset, Character, Environment, Generation, Shot, Task


def process_task(db: Session, task: Task) -> None:
    if task.kind == "analyze_reference":
        _run_analysis(db, task)
        task.status = "succeeded"
        return
    if task.kind == "improve_reference":
        _run_improve_reference(db, task)
        task.status = "succeeded"
        return
    if task.kind == "run_sequence":
        _process_sequence(db, task)
        return
    if task.kind == "generate_shot":
        _process_generate_shot(db, task)
        return
    if task.kind.startswith("generate_"):
        _process_generation(db, task)
        return
    task.status = "failed"
    task.last_error = f"type de tâche inconnu : {task.kind}"


def _run_improve_reference(db: Session, task: Task) -> None:
    payload = json.loads(task.payload)
    rt = AgentRuntime(db=db, gateway=get_gateway())
    improve_reference_description(
        {"project_id": payload["project_id"], "kind": payload["kind"], "reference_id": payload["ref_id"]},
        rt,
    )


def _process_generate_shot(db: Session, task: Task) -> None:
    """L'agent construit le prompt du plan, puis on génère (soumission + suivi)."""
    payload = json.loads(task.payload)
    rt = AgentRuntime(db=db, gateway=get_gateway())
    state = build_shot_prompt({"project_id": payload["project_id"], "shot_id": payload["shot_id"]}, rt)

    kind = payload.get("kind", "image")
    request: dict = {"prompt": state.get("prompt") or ""}
    if state.get("reference_image"):
        request["image"] = state["reference_image"]
    if kind == "video":
        request.setdefault("width", 864)
        request.setdefault("height", 480)
        request.setdefault("frames", 124)
    else:
        request.setdefault("width", 1024)
        request.setdefault("height", 1024)
        request.setdefault("steps", 28)

    gen = Generation(project_id=payload["project_id"], kind=kind, status="pending",
                     request_snapshot=json.dumps(request, ensure_ascii=False))
    db.add(gen)
    db.flush()
    # le plan est résolu : la tâche devient une simple tâche de génération
    task.kind = f"generate_{kind}"
    task.payload = json.dumps({"project_id": payload["project_id"], "generation_id": gen.id})
    db.commit()
    _process_generation(db, task)


def _process_generation(db: Session, task: Task) -> None:
    payload = json.loads(task.payload)
    gen = db.get(Generation, payload["generation_id"])
    if gen is None:
        task.status = "failed"
        task.last_error = "génération introuvable"
        return
    gw = get_gateway()
    snapshot = json.loads(gen.request_snapshot or "{}")
    kind = gen.kind

    # --- phase soumission (une seule fois, jamais de relance aveugle) --------
    if not gen.external_job_id and gen.status == "pending":
        try:
            if kind == "image":
                outcome = gw.generate_image(ImageRequest(**snapshot), async_exec=True)
            elif kind == "video":
                outcome = gw.generate_video(VideoRequest(**snapshot), async_exec=True)
            elif kind == "text":
                result = gw.generate_text(TextRequest(**snapshot))
                gen.status = "succeeded"
                gen.result = json.dumps({"text": result.text, "model": result.model,
                                         "data": result.data, "schema_valid": result.schema_valid},
                                        ensure_ascii=False, default=str)
                task.status = "succeeded"
                return
            else:
                raise ValueError(f"kind inconnu : {kind}")
        except Exception as e:  # noqa: BLE001 — on ne sait pas si la demande a été acceptée
            gen.status = "needs_reconciliation"
            gen.error = json.dumps({"code": "submission_timeout", "message": str(e)[:300]}, ensure_ascii=False)
            task.status = "needs_reconciliation"
            return

        if outcome.job is not None:
            gen.external_job_id = outcome.job.job_id
            gen.status = "running"
        else:
            _finalize_direct(db, gen, outcome.direct)
            task.status = "succeeded"
            return

    # --- phase suivi (job_id connu) ------------------------------------------
    try:
        status = gw.get_job(gen.external_job_id)
    except GatewayError as e:
        gen.status = "needs_reconciliation"
        gen.error = json.dumps({"code": "track_failed", "message": str(e)[:300]}, ensure_ascii=False)
        task.status = "needs_reconciliation"
        return

    if status.status == "succeeded":
        _finalize_job(db, gen, status.result)
        task.status = "succeeded"
        return
    if status.status == "failed":
        gen.status = "failed"
        gen.error = json.dumps(status.error or {"code": "generation_failed"}, ensure_ascii=False, default=str)
        task.status = "failed"
        return
    if status.status == "needs_reconciliation":
        gen.status = "needs_reconciliation"
        task.status = "needs_reconciliation"
        return
    if status.status in ("queued", "running"):
        # toujours en cours : on reprend la consultation plus tard (bornée dans le temps)
        elapsed = time.time() - (gen.created_at.timestamp() if gen.created_at else time.time())
        if elapsed > settings.generation_max_track_seconds:
            gen.status = "needs_reconciliation"
            task.status = "needs_reconciliation"
            return
        task.status = "pending"  # nouvelle passe de suivi, SANS nouvelle soumission
        return
    # état inconnu : conservé et signalé, jamais interprété comme succès/échec
    gen.status = "needs_reconciliation"
    gen.error = json.dumps({"code": "unknown_external_state", "message": f"état externe inconnu : {status.status}"},
                           ensure_ascii=False)
    task.status = "needs_reconciliation"


def _finalize_direct(db: Session, gen: Generation, direct) -> None:
    if direct is None:
        gen.status = "failed"
        gen.error = json.dumps({"code": "generation_failed", "message": "résultat direct vide"})
        return
    raw = asdict(direct) if hasattr(direct, "__dataclass_fields__") else direct
    _download_result(db, gen, raw)


def _finalize_job(db: Session, gen: Generation, result) -> None:
    _download_result(db, gen, result or {})


def _download_result(db: Session, gen: Generation, result) -> None:
    gw = get_gateway()
    urls: list[tuple[str, str, str]] = []
    if isinstance(result, dict):
        for i in result.get("images", []) or []:
            if isinstance(i, dict) and i.get("url"):
                urls.append((i["url"], "image", ".png"))
        v = result.get("video")
        if isinstance(v, dict) and v.get("url"):
            urls.append((v["url"], "video", ".mp4"))
    created: list[Asset] = []
    for url, kind, ext in urls:
        try:
            data = gw.download_media(url)
        except GatewayError:
            continue
        rel = storage.save_media(data, ext, gen.project_id)
        asset = Asset(project_id=gen.project_id, kind=kind, origin="gateway", local_path=rel,
                      mime_type="image/png" if kind == "image" else "video/mp4",
                      external_url=url, is_simulated=getattr(gw, "simulated", False))
        db.add(asset)
        created.append(asset)
    db.flush()
    # si la génération est liée à une référence, on y attache les visuels produits
    if gen.reference_id and gen.reference_kind:
        ref_model = {"character": Character, "environment": Environment}.get(gen.reference_kind)
        if ref_model:
            ref = db.get(ref_model, gen.reference_id)
            if ref is not None:
                ids = [i for i in (ref.media_ids or "").split(",") if i]
                for a in created:
                    if a.id not in ids:
                        ids.append(a.id)
                ref.media_ids = ",".join(ids)
                db.add(ref)
    gen.result = json.dumps(result, ensure_ascii=False, default=str)
    gen.status = "succeeded"


def _process_sequence(db: Session, task: Task) -> None:
    """Génère la suite des plans vidéo d'une scène, dans l'ordre."""
    payload = json.loads(task.payload)
    project_id = payload["project_id"]
    shot_ids = payload["shots"]
    results: list[dict] = []
    prev_refs: list[str] = []
    for i, shot_id in enumerate(shot_ids):
        payload["current"] = i
        payload["results"] = results
        task.payload = json.dumps(payload, ensure_ascii=False)
        db.commit()

        shot = db.get(Shot, shot_id)
        if shot is None:
            results.append({"shot_id": shot_id, "status": "failed", "error": "plan introuvable"})
            continue
        rt = AgentRuntime(db=db, gateway=get_gateway())
        st = build_shot_prompt({"project_id": project_id, "shot_id": shot_id}, rt)
        prompt = st.get("prompt") or shot.action or shot.visual_intent or ""
        refs = _shot_refs(db, shot) or prev_refs
        if not refs:
            key = _generate_keyframe(db, project_id, shot, prompt)
            if key is None:
                results.append({"shot_id": shot_id, "status": "failed",
                                "error": "échec de génération automatique du keyframe"})
                continue
            refs = [key]
        request: dict = {"prompt": prompt, "width": 864, "height": 480, "frames": 124, "refs": refs[:3]}
        gen = Generation(project_id=project_id, kind="video", status="pending",
                         request_snapshot=json.dumps(request, ensure_ascii=False))
        db.add(gen)
        db.flush()
        _generate_blocking(db, gen)
        if gen.status == "succeeded":
            _link_clip_to_shot(db, shot, gen)
            prev_refs = refs
        results.append({"shot_id": shot_id, "generation_id": gen.id, "status": gen.status,
                        "error": (json.loads(gen.error or "{}") or {}).get("message") if gen.error else None})

    # agrégation des clips produits en une vidéo finale
    clip_urls = []
    for r in results:
        if r.get("status") == "succeeded" and r.get("generation_id"):
            g = db.get(Generation, r["generation_id"])
            if g is not None:
                url = _gen_video_url(g)
                if url:
                    clip_urls.append(url)
    final_video = None
    if len(clip_urls) >= 2:
        try:
            gw = get_gateway()
            vr = gw.concat_videos(clip_urls)
            data = gw.download_media(vr.video.url)
            rel = storage.save_media(data, ".mp4", project_id)
            asset = Asset(project_id=project_id, kind="video", origin="gateway", local_path=rel,
                          mime_type="video/mp4", external_url=vr.video.url,
                          is_simulated=getattr(gw, "simulated", False))
            db.add(asset)
            db.flush()
            final_video = {"asset_id": asset.id, "url": vr.video.url}
        except Exception as e:  # noqa: BLE001
            final_video = {"error": str(e)[:200]}
    elif len(clip_urls) == 1:
        final_video = {"url": clip_urls[0]}
    payload["final_video"] = final_video

    payload["results"] = results
    task.payload = json.dumps(payload, ensure_ascii=False)
    task.status = "succeeded"


def _generate_blocking(db: Session, gen: Generation) -> None:
    """Soumet puis attend la fin d'une génération (utilisé par la séquence)."""
    gw = get_gateway()
    snapshot = json.loads(gen.request_snapshot or "{}")
    if gen.kind == "image":
        outcome = gw.generate_image(ImageRequest(**snapshot), async_exec=True)
    elif gen.kind == "video":
        outcome = gw.generate_video(VideoRequest(**snapshot), async_exec=True)
    else:
        gen.status = "failed"
        gen.error = json.dumps({"code": "unsupported_kind", "message": f"kind non géré en séquence : {gen.kind}"})
        db.commit()
        return

    if outcome.job is None:
        _finalize_direct(db, gen, outcome.direct)
        db.commit()
        return
    gen.external_job_id = outcome.job.job_id
    gen.status = "running"
    db.commit()

    deadline = time.time() + settings.generation_max_track_seconds
    while time.time() < deadline:
        try:
            st = gw.get_job(gen.external_job_id)
        except GatewayError as e:
            gen.status = "needs_reconciliation"
            gen.error = json.dumps({"code": "track_failed", "message": str(e)[:300]}, ensure_ascii=False)
            db.commit()
            return
        if st.status == "succeeded":
            _finalize_job(db, gen, st.result)
            db.commit()
            return
        if st.status == "failed":
            gen.status = "failed"
            gen.error = json.dumps(st.error or {"code": "generation_failed"}, ensure_ascii=False, default=str)
            db.commit()
            return
        if st.status not in ("queued", "running"):
            gen.status = "needs_reconciliation"
            gen.error = json.dumps({"code": "unknown_external_state",
                                    "message": f"état externe inconnu : {st.status}"}, ensure_ascii=False)
            db.commit()
            return
        time.sleep(settings.generation_poll_interval)
    gen.status = "needs_reconciliation"
    gen.error = json.dumps({"code": "track_timeout", "message": "délai de suivi dépassé"}, ensure_ascii=False)
    db.commit()


def _shot_refs(db: Session, shot: Shot) -> list[str]:
    ids = [i for i in (shot.media_ids or "").split(",") if i]
    if not ids:
        return []
    return [a.external_url for a in db.query(Asset).filter(Asset.id.in_(ids)).all() if a.external_url]


def _link_clip_to_shot(db: Session, shot: Shot, gen: Generation) -> None:
    url = None
    try:
        res = json.loads(gen.result or "{}")
        url = (res.get("video") or {}).get("url")
    except Exception:  # noqa: BLE001
        url = None
    if not url:
        return
    asset = db.query(Asset).filter(Asset.external_url == url, Asset.project_id == gen.project_id).first()
    if asset is None:
        return
    ids = [i for i in (shot.media_ids or "").split(",") if i]
    if asset.id not in ids:
        ids.append(asset.id)
    shot.media_ids = ",".join(ids)
    db.add(shot)


def _result_image_urls(gen: Generation) -> list[str]:
    try:
        res = json.loads(gen.result or "{}")
        return [i.get("url") for i in (res.get("images") or [])
                if isinstance(i, dict) and i.get("url")]
    except Exception:  # noqa: BLE001
        return []


def _gen_video_url(gen: Generation) -> str | None:
    try:
        res = json.loads(gen.result or "{}")
        return (res.get("video") or {}).get("url")
    except Exception:  # noqa: BLE001
        return None


def _generate_keyframe(db: Session, project_id: str, shot: Shot, prompt: str) -> str | None:
    """Génère un keyframe (image) pour un plan sans visuel de référence."""
    req = {"prompt": prompt, "width": 1024, "height": 1024, "steps": 28}
    gen = Generation(project_id=project_id, kind="image", status="pending",
                     request_snapshot=json.dumps(req, ensure_ascii=False))
    db.add(gen)
    db.flush()
    _generate_blocking(db, gen)
    if gen.status != "succeeded":
        return None
    urls = _result_image_urls(gen)
    if not urls:
        return None
    assets = db.query(Asset).filter(Asset.external_url.in_(urls),
                                    Asset.project_id == project_id).all()
    ids = [i for i in (shot.media_ids or "").split(",") if i]
    for a in assets:
        if a.id not in ids:
            ids.append(a.id)
    shot.media_ids = ",".join(ids)
    db.add(shot)
    return urls[0]
