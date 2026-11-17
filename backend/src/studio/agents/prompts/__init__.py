"""Agents : prompts et schémas (les agents spécialisés arrivent plus tard)."""
from __future__ import annotations

# Schéma JSON défini par le Studio pour l'analyse vision d'une référence.
ANALYSIS_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "description": {"type": "string", "description": "Description factuelle du sujet"},
        "key_traits": {"type": "array", "items": {"type": "string"}, "description": "Traits caractéristiques observés"},
        "missing_views": {"type": "array", "items": {"type": "string"}, "description": "Vues/éléments manquants"},
        "suggestions": {"type": "array", "items": {"type": "string"}, "description": "Propositions de complétion"},
    },
    "required": ["description"],
    "additionalProperties": True,
}

ANALYSIS_SYSTEM_PROMPT = (
    "Tu analyses une image de référence. Distingue strictement les observations "
    "factuelles des suppositions. Réponds en JSON conforme au schéma demandé."
)

ANALYSIS_PROMPT = (
    "Décris les caractéristiques visibles de cette référence, puis propose des "
    "complétions utiles (vues manquantes, détails à confirmer)."
)
