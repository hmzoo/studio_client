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

# Schéma du prompt de génération construit à partir d'un plan.
SHOT_PROMPT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "prompt": {"type": "string", "description": "Prompt de génération, en anglais"},
        "reference_image": {"type": ["string", "null"],
                            "description": "URL du visuel de référence à utiliser, ou null"},
    },
    "required": ["prompt"],
    "additionalProperties": True,
}

SHOT_PROMPT_SYSTEM = (
    "Tu construis un prompt de génération d'image à partir d'un plan de tournage. "
    "Utilise l'action et l'intention visuelle, ainsi que les descriptions des références "
    "fournies (personnages, environnements). Écris un prompt visuel précis en anglais, "
    "et choisis éventuellement un visuel de référence parmi ceux proposés. "
    "Réponds en JSON conforme au schéma demandé."
)

# Amélioration d'une description de référence (texte seul).
IMPROVE_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "description": {"type": "string", "description": "Description enrichie et précise"},
        "key_traits": {"type": "array", "items": {"type": "string"}},
        "suggestions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["description"],
    "additionalProperties": True,
}

IMPROVE_SYSTEM = (
    "Tu améliores une description de personnage ou d'environnement fournie par un "
    "utilisateur. Rends-la précise, visuelle et complète (apparence, ambiance, détails), "
    "sans inventer d'éléments contradictoires avec la source. Réponds en JSON conforme "
    "au schéma demandé."
)


# Pilotage de l'orchestrateur par chat.
CHAT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "reply": {"type": "string", "description": "Réponse à l'utilisateur, en français, concise"},
        "action": {
            "type": ["object", "null"],
            "properties": {
                "type": {"type": "string", "enum": [
                    "generate_sequence", "analyze_reference", "improve_reference",
                    "generate_shot_image", "create_scene", "create_shot",
                    "create_reference", "none",
                ]},
                "scene_id": {"type": "string"},
                "shot_id": {"type": "string"},
                "kind": {"type": "string", "enum": ["character", "environment"]},
                "ref_id": {"type": "string"},
                "title": {"type": "string"},
                "narrative": {"type": "string"},
                "name": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["type"],
        },
    },
    "required": ["reply"],
    "additionalProperties": True,
}

CHAT_SYSTEM = (
    "Tu es l'orchestrateur du Studio : tu aides l'utilisateur à construire un projet "
    "vidéo (références, scènes, plans) et à lancer des générations. "
    "Tu réponds en français, de façon concise. Quand l'utilisateur demande une action "
    "(générer une séquence, analyser une référence, améliorer une description, générer "
    "l'image d'un plan, créer une scène/un plan/une référence), tu renvoies l'action "
    "correspondante avec ses paramètres en t'appuyant sur les identifiants du contexte. "
    "Si aucune action n'est nécessaire, mets action à null."
)
