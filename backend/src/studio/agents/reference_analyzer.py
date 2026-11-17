"""Agent d'analyse de référence : vision → description structurée + complétions."""
from __future__ import annotations

import json

from jsonschema import Draft202012Validator

from ..agents.prompts import ANALYSIS_PROMPT, ANALYSIS_SCHEMA, ANALYSIS_SYSTEM_PROMPT
from ..clients.interface import TextRequest
from ..domain.models import Asset, Character, CompletionProposal, Environment
from .base import AgentRuntime, AgentState

_REF_MODELS = {"character": Character, "environment": Environment}


def analyze_reference(state: AgentState, rt: AgentRuntime) -> AgentState:
    db = rt.db
    project_id = state["project_id"]
    kind = state["kind"]
    ref_id = state["reference_id"]

    model = _REF_MODELS[kind]
    ref = db.get(model, ref_id)
    if ref is None or ref.project_id != project_id:
        raise ValueError("référence introuvable")

    assets = db.query(Asset).filter(Asset.id.in_([i for i in (ref.media_ids or "").split(",") if i])).all()
    images = [a.external_url for a in assets if a.external_url]

    result = rt.gateway.generate_text(TextRequest(
        prompt=ANALYSIS_PROMPT,
        system=ANALYSIS_SYSTEM_PROMPT,
        images=images or None,
        response_format={"type": "json_schema", "schema": ANALYSIS_SCHEMA},
        temperature=0.3,
        max_tokens=2000,
    ))
    if result.schema_valid is not True or result.data is None:
        raise RuntimeError("réponse structurée invalide de la passerelle")
    # revalidation locale (défense en profondeur)
    Draft202012Validator(ANALYSIS_SCHEMA).validate(result.data)

    data = result.data
    proposal = CompletionProposal(
        project_id=project_id,
        subject_type=kind,
        subject_id=ref_id,
        content=(data.get("description") or ""),
        references=json.dumps({
            "key_traits": data.get("key_traits", []),
            "missing_views": data.get("missing_views", []),
            "suggestions": data.get("suggestions", []),
        }, ensure_ascii=False),
        status="pending",
    )
    db.add(proposal)
    db.commit()

    state["analysis"] = data
    return state
