"""Frontière d'agent : état partagé + runtime. Compatible LangGraph.

Chaque agent est une *node* : une fonction `(state, runtime) -> state`.
Migrer vers LangGraph consistera à enregistrer ces mêmes fonctions comme nodes
d'un StateGraph — le contrat ne change pas.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, TypedDict

from sqlalchemy.orm import Session

from ..clients.interface import GenerationGatewayClient


class AgentState(TypedDict, total=False):
    """État partagé entre les agents (persisté en base par la tâche)."""
    project_id: str
    kind: str
    reference_id: str
    shot_id: str
    analysis: dict
    prompt: str
    reference_image: str | None
    request: dict


@dataclass
class AgentRuntime:
    """Dépendances injectées aux agents (jamais de service réel en test)."""
    db: Session
    gateway: GenerationGatewayClient


Agent = Callable[[AgentState, AgentRuntime], AgentState]
