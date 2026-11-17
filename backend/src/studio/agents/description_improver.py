"""Agent d'amélioration de description (référence texte seule)."""
from __future__ import annotations

import json

from jsonschema import Draft202012Validator

from ..agents.prompts import IMPROVE_SCHEMA, IMPROVE_SYSTEM
from ..clients.interface import TextRequest
from ..domain.models import Character, CompletionProposal, Environment
from .base import AgentRuntime, AgentState

_REF_MODELS = {"character": Character, "environment": Environment}


def improve_reference_description(state: AgentState, rt: AgentRuntime) -> AgentState:
    db = rt.db
    project_id = state["project_id"]
    kind = state["kind"]
    ref_id = state["reference_id"]

    ref = db.get(_REF_MODELS[kind], ref_id)
    if ref is None or ref.project_id != project_id:
        raise ValueError("référence introuvable")

    source = ref.initial_description or ref.name
    user = f"Référence « {ref.name} » : {source or '(aucune description)'}. Améliore cette description."

    result = rt.gateway.generate_text(TextRequest(
        prompt=user,
        system=IMPROVE_SYSTEM,
        response_format={"type": "json_schema", "schema": IMPROVE_SCHEMA},
        temperature=0.5,
        max_tokens=1200,
    ))
    if result.schema_valid is not True or result.data is None:
        raise RuntimeError("réponse structurée invalide (amélioration)")
    Draft202012Validator(IMPROVE_SCHEMA).validate(result.data)

    data = result.data
    proposal = CompletionProposal(
        project_id=project_id,
        subject_type=kind,
        subject_id=ref_id,
        content=(data.get("description") or ""),
        references=json.dumps({
            "key_traits": data.get("key_traits", []),
            "suggestions": data.get("suggestions", []),
        }, ensure_ascii=False),
        status="pending",
    )
    db.add(proposal)
    db.commit()

    state["analysis"] = data
    return state
