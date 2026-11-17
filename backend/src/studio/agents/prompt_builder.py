"""Agent de construction du prompt de génération à partir d'un plan."""
from __future__ import annotations

from jsonschema import Draft202012Validator

from ..agents.prompts import SHOT_PROMPT_SCHEMA, SHOT_PROMPT_SYSTEM
from ..clients.interface import TextRequest
from ..domain.models import Asset, Character, Environment, Shot
from .base import AgentRuntime, AgentState


def build_shot_prompt(state: AgentState, rt: AgentRuntime) -> AgentState:
    db = rt.db
    shot = db.get(Shot, state["shot_id"])
    if shot is None:
        raise ValueError("plan introuvable")

    def summarize(model, ids_csv: str) -> list[str]:
        ids = [i for i in (ids_csv or "").split(",") if i]
        if not ids:
            return []
        return [f"{o.name}: {o.approved_description or o.initial_description or '(sans description)'}"
                for o in db.query(model).filter(model.id.in_(ids)).all()]

    chars = summarize(Character, shot.character_ids)
    envs = summarize(Environment, shot.environment_ids)
    media_ids = [i for i in (shot.media_ids or "").split(",") if i]
    meds = [a.external_url for a in db.query(Asset).filter(Asset.id.in_(media_ids)).all() if a.external_url] if media_ids else []

    user = (
        f"Plan : action = {shot.action or '(non précisée)'} ; "
        f"intention visuelle = {shot.visual_intent or '(non précisée)'}.\n"
        f"Personnages : {chars or 'aucun'}.\n"
        f"Environnements : {envs or 'aucun'}.\n"
        f"Visuels de référence disponibles : {meds or 'aucun'}."
    )

    result = rt.gateway.generate_text(TextRequest(
        prompt=user,
        system=SHOT_PROMPT_SYSTEM,
        response_format={"type": "json_schema", "schema": SHOT_PROMPT_SCHEMA},
        temperature=0.5,
        max_tokens=800,
    ))
    if result.schema_valid is not True or result.data is None:
        raise RuntimeError("réponse structurée invalide (prompt de plan)")
    Draft202012Validator(SHOT_PROMPT_SCHEMA).validate(result.data)

    data = result.data
    state["prompt"] = (data.get("prompt") or "").strip()
    state["reference_image"] = data.get("reference_image")
    return state
