"""Services applicatifs : logique métier (sans logique d'agents)."""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from .. import storage
from ..agents.prompts import CHAT_SCHEMA, CHAT_SYSTEM
from ..clients import get_gateway
from ..clients.interface import (
    GatewayError,
    ImageRequest,
    TextRequest,
    VideoRequest,
)
from ..domain.models import (
    Asset,
    Character,
    CompletionProposal,
    Environment,
    Generation,
    Project,
    Scene,
    Shot,
    Task,
)


def _gateway():
    return get_gateway()


# --------------------------------------------------------------------------- #
# Projets
# --------------------------------------------------------------------------- #
def create_project(db: Session, name: str, description: str) -> Project:
    p = Project(name=name, description=description)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def list_projects(db: Session) -> list[Project]:
    return db.query(Project).order_by(Project.created_at.desc()).all()


def get_project(db: Session, project_id: str) -> Project:
    p = db.get(Project, project_id)
    if p is None:
        raise ValueError("projet introuvable")
    return p


# --------------------------------------------------------------------------- #
# Références (personnages / environnements)
# --------------------------------------------------------------------------- #
_REF_MODELS = {"character": Character, "environment": Environment}


def create_reference(db: Session, project_id: str, kind: str, name: str, description: str):
    get_project(db, project_id)
    model = _REF_MODELS[kind]
    ref = model(project_id=project_id, name=name, initial_description=description)
    db.add(ref)
    db.commit()
    db.refresh(ref)
    return ref


def list_references(db: Session, project_id: str, kind: str):
    model = _REF_MODELS[kind]
    return db.query(model).filter(model.project_id == project_id).all()


def get_reference(db: Session, project_id: str, kind: str, ref_id: str):
    model = _REF_MODELS[kind]
    ref = db.get(model, ref_id)
    if ref is None or ref.project_id != project_id:
        raise ValueError("référence introuvable")
    return ref


def update_reference(db: Session, project_id: str, kind: str, ref_id: str,
                     name: str | None = None, description: str | None = None):
    ref = get_reference(db, project_id, kind, ref_id)
    if name is not None:
        ref.name = name
    if description is not None:
        ref.initial_description = description
    db.add(ref)
    db.commit()
    db.refresh(ref)
    return ref


def unlink_reference_asset(db: Session, project_id: str, kind: str, ref_id: str, asset_id: str):
    """Retire un média de la référence (ne supprime pas l'asset de la médiathèque)."""
    ref = get_reference(db, project_id, kind, ref_id)
    ids = [i for i in (ref.media_ids or "").split(",") if i and i != asset_id]
    ref.media_ids = ",".join(ids)
    db.add(ref)
    db.commit()
    db.refresh(ref)
    return ref


def _link_media(db: Session, ref, asset_id: str) -> None:
    ids = [i for i in (ref.media_ids or "").split(",") if i]
    if asset_id not in ids:
        ids.append(asset_id)
    ref.media_ids = ",".join(ids)
    db.add(ref)


def import_reference_image(db: Session, project_id: str, kind: str, ref_id: str,
                           filename: str, data: bytes) -> Asset:
    """Copie locale + import dans la passerelle + lien à la référence."""
    ref = get_reference(db, project_id, kind, ref_id)
    ext = ("." + filename.rsplit(".", 1)[-1]) if "." in filename else ".png"
    local_rel = storage.save_media(data, ext, project_id)
    try:
        meta = _gateway().upload_asset(filename, data)
    except GatewayError as e:
        raise RuntimeError(f"import passerelle échoué : {e}") from e
    asset = Asset(
        project_id=project_id, kind="image", origin="gateway",
        local_path=local_rel, mime_type=meta.mime_type, width=meta.width, height=meta.height,
        external_id=meta.asset_id, external_url=meta.url,
        is_simulated=getattr(_gateway(), "simulated", False),
    )
    db.add(asset)
    db.flush()
    _link_media(db, ref, asset.id)
    db.commit()
    db.refresh(asset)
    return asset


# --------------------------------------------------------------------------- #
# Analyse vision (tâche worker)
# --------------------------------------------------------------------------- #
def request_analysis(db: Session, project_id: str, kind: str, ref_id: str) -> Task:
    get_reference(db, project_id, kind, ref_id)
    task = Task(kind="analyze_reference", status="pending",
                payload=json.dumps({"project_id": project_id, "kind": kind, "ref_id": ref_id}))
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def _run_analysis(db: Session, task: Task) -> None:
    """L'analyse vit désormais dans agents.reference_analyzer — gardé pour compatibilité."""
    from ..agents.base import AgentRuntime
    from ..agents.reference_analyzer import analyze_reference
    payload = json.loads(task.payload)
    state = {"project_id": payload["project_id"], "kind": payload["kind"], "reference_id": payload["ref_id"]}
    analyze_reference(state, AgentRuntime(db=db, gateway=_gateway()))


# --------------------------------------------------------------------------- #
# Complétions : approbation / rejet
# --------------------------------------------------------------------------- #
def decide_proposal(db: Session, project_id: str, proposal_id: str, status: str, comment: str) -> CompletionProposal:
    p = db.get(CompletionProposal, proposal_id)
    if p is None or p.project_id != project_id:
        raise ValueError("proposition introuvable")
    p.status = status
    p.validation_comment = comment
    if status == "approved":
        ref = get_reference(db, project_id, p.subject_type, p.subject_id)
        # Approbation explicite uniquement : aucune écriture silencieuse.
        ref.approved_description = p.content
        db.add(ref)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def list_proposals(db: Session, project_id: str) -> list[CompletionProposal]:
    return db.query(CompletionProposal).filter(CompletionProposal.project_id == project_id).all()


# --------------------------------------------------------------------------- #
# Générations
# --------------------------------------------------------------------------- #
def _resolve_request_refs(db: Session, kind: str, request: dict) -> dict:
    """Résout les identifiants d'assets locaux vers leurs URLs externes."""
    def r(v):
        if isinstance(v, str):
            a = db.get(Asset, v)
            if a is not None and a.external_url:
                return a.external_url
        return v
    out = dict(request)
    if kind == "image" and "image" in out:
        out["image"] = r(out["image"])
    if kind == "video" and "refs" in out:
        out["refs"] = [r(x) for x in out["refs"]]
    if kind == "text" and "images" in out:
        out["images"] = [r(x) for x in out["images"]]
    return out


def request_generation(db: Session, project_id: str, kind: str, request: dict) -> Generation:
    get_project(db, project_id)
    if kind == "video" and not (request.get("refs") or []):
        raise ValueError("la génération vidéo nécessite au moins une image de référence (Ref2V)")
    snapshot = _resolve_request_refs(db, kind, request)
    gen = Generation(
        project_id=project_id, kind=kind, status="pending",
        request_snapshot=json.dumps(snapshot, ensure_ascii=False),
    )
    db.add(gen)
    db.flush()
    task = Task(kind=f"generate_{kind}", status="pending",
                payload=json.dumps({"project_id": project_id, "generation_id": gen.id}))
    db.add(task)
    db.commit()
    db.refresh(gen)
    return gen


def request_shot_generation(db: Session, project_id: str, shot_id: str, kind: str = "image") -> Task:
    """Génération pilotée par un plan : l'agent construit le prompt en tâche de fond."""
    if db.get(Shot, shot_id) is None:
        raise ValueError("plan introuvable")
    task = Task(kind="generate_shot", status="pending",
                payload=json.dumps({"project_id": project_id, "shot_id": shot_id, "kind": kind}))
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def request_sequence(db: Session, project_id: str, scene_id: str) -> Task:
    """Génère la suite des plans vidéo d'une scène, dans l'ordre (un instantané des plans)."""
    shots = db.query(Shot).filter(Shot.scene_id == scene_id).order_by(Shot.order).all()
    if not shots:
        raise ValueError("la scène n'a pas encore de plan")
    task = Task(kind="run_sequence", status="pending",
                payload=json.dumps({"project_id": project_id, "scene_id": scene_id,
                                    "shots": [s.id for s in shots], "current": -1, "results": []}))
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def request_improve_reference(db: Session, project_id: str, kind: str, ref_id: str) -> Task:
    """Amélioration de la description d'une référence (agent)."""
    get_reference(db, project_id, kind, ref_id)
    task = Task(kind="improve_reference", status="pending",
                payload=json.dumps({"project_id": project_id, "kind": kind, "ref_id": ref_id}))
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def request_reference_visual(db: Session, project_id: str, kind: str, ref_id: str) -> Generation:
    """Génère un visuel depuis la description de la référence (lié à la référence)."""
    ref = get_reference(db, project_id, kind, ref_id)
    prompt = (ref.approved_description or ref.initial_description or ref.name).strip()
    gen = Generation(
        project_id=project_id, kind="image", status="pending",
        request_snapshot=json.dumps({"prompt": prompt, "width": 1024, "height": 1024, "steps": 28}, ensure_ascii=False),
        reference_kind=kind, reference_id=ref_id,
    )
    db.add(gen)
    db.flush()
    task = Task(kind="generate_image", status="pending",
                payload=json.dumps({"project_id": project_id, "generation_id": gen.id}))
    db.add(task)
    db.commit()
    db.refresh(gen)
    return gen


def list_generations(db: Session, project_id: str) -> list[Generation]:
    return db.query(Generation).filter(Generation.project_id == project_id).order_by(Generation.created_at.desc()).all()


def list_assets(db: Session, project_id: str) -> list[Asset]:
    return db.query(Asset).filter(Asset.project_id == project_id).order_by(Asset.created_at).all()


# --------------------------------------------------------------------------- #
# Storyboard (scènes / plans)
# --------------------------------------------------------------------------- #
def create_scene(db: Session, project_id: str, title: str = "", narrative: str = "", order: int = 0) -> Scene:
    get_project(db, project_id)
    s = Scene(project_id=project_id, title=title, narrative=narrative, order=order)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def list_scenes(db: Session, project_id: str) -> list[Scene]:
    return db.query(Scene).filter(Scene.project_id == project_id).order_by(Scene.order).all()


def create_shot(db: Session, scene_id: str, action: str = "", visual_intent: str = "", order: int = 0,
                character_ids: list[str] | None = None, environment_ids: list[str] | None = None,
                media_ids: list[str] | None = None) -> Shot:
    if db.get(Scene, scene_id) is None:
        raise ValueError("scène introuvable")
    sh = Shot(
        scene_id=scene_id, action=action, visual_intent=visual_intent, order=order,
        character_ids=",".join(character_ids or []),
        environment_ids=",".join(environment_ids or []),
        media_ids=",".join(media_ids or []),
    )
    db.add(sh)
    db.commit()
    db.refresh(sh)
    return sh


def list_shots(db: Session, scene_id: str) -> list[Shot]:
    return db.query(Shot).filter(Shot.scene_id == scene_id).order_by(Shot.order).all()


def delete_shot(db: Session, shot_id: str) -> None:
    sh = db.get(Shot, shot_id)
    if sh is None:
        raise ValueError("plan introuvable")
    db.delete(sh)
    db.commit()


def chat_orchestrator(db: Session, project_id: str, message: str) -> dict:
    """Pilotage de l'orchestrateur par chat : réponse + exécution d'une action."""
    get_project(db, project_id)
    summary = _project_summary(db, project_id)
    result = _gateway().generate_text(TextRequest(
        prompt=f"État du projet :\n{summary}\n\nMessage de l'utilisateur : {message}",
        system=CHAT_SYSTEM,
        response_format={"type": "json_schema", "schema": CHAT_SCHEMA},
        temperature=0.4,
        max_tokens=1200,
    ))
    data = result.data if getattr(result, "schema_valid", False) else None
    reply = (data or {}).get("reply") if data else (result.text or "Je n'ai pas pu traiter la demande.")
    action = (data or {}).get("action") if data else None
    outcome = _execute_chat_action(db, project_id, action)
    return {"reply": reply, "action": action, "outcome": outcome}


def _project_summary(db: Session, project_id: str) -> str:
    chars = db.query(Character).filter(Character.project_id == project_id).order_by(Character.created_at).all()
    envs = db.query(Environment).filter(Environment.project_id == project_id).order_by(Environment.created_at).all()
    scenes = db.query(Scene).filter(Scene.project_id == project_id).order_by(Scene.order).all()
    scene_ids = [s.id for s in scenes]
    shots = db.query(Shot).filter(Shot.scene_id.in_(scene_ids)).order_by(Shot.order).all() if scene_ids else []
    pending = db.query(CompletionProposal).filter(
        CompletionProposal.project_id == project_id, CompletionProposal.status == "pending").count()
    lines = [f"Personnages : {', '.join(f'{c.name} (id={c.id})' for c in chars) or 'aucun'}",
             f"Environnements : {', '.join(f'{e.name} (id={e.id})' for e in envs) or 'aucun'}"]
    for s in scenes:
        ss = [sh for sh in shots if sh.scene_id == s.id]
        lines.append(f"Scène id={s.id} ordre={s.order} « {s.title} » : {len(ss)} plan(s)")
        for sh in ss:
            lines.append(f"  plan id={sh.id} ordre={sh.order} : {sh.action} — {sh.visual_intent}")
    if pending:
        lines.append(f"Propositions en attente : {pending}")
    return "\n".join(lines)


def _execute_chat_action(db: Session, project_id: str, action: dict | None) -> dict | None:
    if not action:
        return None
    t = action.get("type")
    if t in (None, "none"):
        return None
    try:
        if t == "generate_sequence":
            task = request_sequence(db, project_id, action["scene_id"])
            return {"task_id": task.id, "kind": task.kind}
        if t == "analyze_reference":
            task = request_analysis(db, project_id, action.get("kind", "character"), action["ref_id"])
            return {"task_id": task.id, "kind": task.kind}
        if t == "improve_reference":
            task = request_improve_reference(db, project_id, action.get("kind", "character"), action["ref_id"])
            return {"task_id": task.id, "kind": task.kind}
        if t == "generate_shot_image":
            task = request_shot_generation(db, project_id, action["shot_id"], "image")
            return {"task_id": task.id, "kind": task.kind}
        if t == "create_scene":
            sc = create_scene(db, project_id, action.get("title", ""), action.get("narrative", ""), 0)
            return {"scene_id": sc.id}
        if t == "create_shot":
            sh = create_shot(db, action["scene_id"], action.get("action", ""), action.get("visual_intent", ""), 0, [], [], [])
            return {"shot_id": sh.id, "scene_id": sh.scene_id}
        if t == "create_reference":
            ref = create_reference(db, project_id, action.get("kind", "character"), action.get("name", ""), action.get("description", ""))
            return {"ref_id": ref.id}
        return {"error": f"action inconnue : {t}"}
    except (ValueError, KeyError) as e:
        return {"error": str(e)}
