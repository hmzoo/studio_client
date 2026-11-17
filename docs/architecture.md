# Architecture

Monolithe modulaire : un backend API, un worker (même code), un frontend, PostgreSQL.

## Composants

- `src/studio/api/` — routes REST (projets, références, complétions, générations, assets, tâches).
- `src/studio/application/services.py` — logique métier (sans logique d'agents).
- `src/studio/orchestration/workflow.py` — workflow explicite à états persistés (frontière prête pour LangGraph).
- `src/studio/workers/worker.py` — dépile la file `tasks` (PostgreSQL) ; les traitements longs ne dépendent pas d'une requête HTTP.
- `src/studio/clients/` — `GenerationGatewayClient` (interface + `http` + `fake`).
- `src/studio/storage/media.py` — stockage local des médias (volume), chemins sécurisés.
- `src/studio/domain/models.py` — entités : Project, Character, Environment, Scene, Shot, Asset, CompletionProposal, Generation, Task.

## Modèle de données (résumé)

- **Project** — nom, description.
- **Character / Environment** — description initiale, description approuvée (écrite uniquement par approbation explicite).
- **Scene / Shot** — fondations du storyboard (ordre, action, intention visuelle, liens).
- **Asset** — identifiant local, type, provenance, chemin local, MIME, identifiant/URL externes.
- **CompletionProposal** — pending / approved / rejected, commentaire de validation.
- **Generation** — instantané de la demande, état local, job_id externe, résultat, erreur normalisée, génération précédente.
- **Task** — travail du worker, état, tentatives, reprise.

Distinctions : identifiants locaux (uuid) vs externes (`job_id`, `asset_id`), tâche applicative vs tentative créative.

## Sécurité / fiabilité

- Secrets uniquement côté backend (variables d'environnement).
- Chemins locaux résolus sans échappement du répertoire de stockage.
- Téléchargements limités aux origines de confiance (`TRUSTED_MEDIA_ORIGINS`), redirections contrôlées.
- Aucune génération automatique : toute génération résulte d'une action explicite.
- Timeout de soumission → `needs_reconciliation` (pas de relance aveugle) ; job connu → reprise du suivi.
