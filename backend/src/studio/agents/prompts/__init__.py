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
        "reply": {"type": "string", "description": "Ta réponse en français : ce que tu fais ou demandes"},
        "action": {
            "type": ["object", "null"],
            "properties": {
                "type": {"type": "string", "enum": [
                    "generate_sequence", "analyze_reference", "improve_reference",
                    "generate_reference_visual", "generate_shot_image", "create_scene",
                    "create_shot", "create_reference", "none",
                ]},
                "scene_id": {"type": "string"},
                "shot_id": {"type": "string"},
                "kind": {"type": "string", "enum": ["character", "environment"]},
                "ref_id": {"type": "string"},
                "title": {"type": "string"},
                "narrative": {"type": "string"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "visual_intent": {"type": "string"},
            },
            "required": ["type"],
        },
    },
    "required": ["reply"],
    "additionalProperties": True,
}

CHAT_SYSTEM = (
    "Tu es l'orchestrateur du Studio : tu aides l'utilisateur à construire un projet "
    "vidéo et à lancer des générations. Réponds TOUJOURS en JSON avec deux champs :\n"
    "- \"reply\" : ta réponse en français, une phrase claire ;\n"
    "- \"action\" : null si tu ne lances rien, sinon un objet avec un \"type\" parmi :\n"
    "  generate_sequence(scene_id), generate_reference_visual(kind, ref_id), "
    "generate_shot_image(shot_id), analyze_reference(kind, ref_id), "
    "improve_reference(kind, ref_id), create_scene(title, narrative), "
    "create_shot(scene_id, action, visual_intent), create_reference(kind, name, description).\n"
    "Utilise les identifiants (id) présents dans le contexte. Si un élément manque, "
    "explique-le dans reply et mets action à null.\n"
    "Exemple : « génère des images pour la forêt » → "
    '{"reply": "Je génère un visuel pour la forêt.", '
    '"action": {"type": "generate_reference_visual", "kind": "environment", "ref_id": "<id_forêt>"}}.'
)
