# Studio Client

Application de création de vidéos par itérations. Le Studio gère les références
(personnages, environnements), le scénario (scènes/plans — fondations), les
complétions proposées, les demandes de génération, les validations humaines et
l'historique. Les générations (texte/vision, images, vidéos) sont exécutées par
une **API externe** via un client dédié (`GenerationGatewayClient`).

Le Studio est une application **distincte** de l'API de génération : il ne
réimplémente aucun moteur et n'appelle jamais directement les fournisseurs.

## Stack

- Backend : Python, FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL
- Worker : même code, dépile une file de tâches persistée en PostgreSQL
- Frontend : TypeScript, React, Vite
- Tests : pytest (aucun service réel)
- Lancement : Docker Compose, stockage local des médias sur volume

## Lancement (Docker Compose)

```bash
cp .env.example .env          # par défaut GENERATION_GATEWAY_MODE=fake
docker compose up --build
```

- Frontend : http://localhost:5173
- API : http://localhost:8000 (docs OpenAPI sur /docs)
- Worker : service séparé, consomme la file de tâches

## Migrations de base

La migration initiale est générée dans `backend/migrations/versions/`.

```bash
cd backend
pip install -e .[dev]
alembic upgrade head            # applique les migrations
# pour générer une nouvelle migration :
# DATABASE_URL=sqlite:////tmp/mig.db alembic revision --autogenerate -m "..."
```

En Docker Compose, le backend exécute `alembic upgrade head` automatiquement au
démarrage (voir le `CMD` du Dockerfile). Pour la démo locale, le backend crée
aussi le schéma au démarrage (`Base.metadata.create_all`) — idempotent.

## Tests

```bash
cd backend
pip install -e .[dev]
pytest -q
```

Les tests utilisent SQLite + la passerelle `fake` ; aucun service réel ni
génération payante n'est déclenché.

## Configuration (variables d'environnement)

Voir `.env.example`. Secrets côté backend uniquement (jamais exposés au frontend,
aux logs ni au dépôt).

- `GENERATION_GATEWAY_MODE=fake|http`
- `GENERATION_API_BASE_URL`, `GENERATION_API_KEY`, `GENERATION_API_AUTH_HEADER`, `GENERATION_API_AUTH_SCHEME`
- délais (`GENERATION_CONNECT_TIMEOUT`, `GENERATION_READ_TIMEOUT`, `GENERATION_POLL_INTERVAL`, `GENERATION_MAX_TRACK_SECONDS`)
- `TRUSTED_MEDIA_ORIGINS` (origines autorisées pour télécharger les médias)

## Parcours de démonstration (fake)

1. Créer un projet.
2. Créer un personnage.
3. Importer une image de référence (copie locale + import passerelle).
4. Lancer l'analyse vision structurée (tâche worker).
5. Voir la description et les complétions proposées.
6. Approuver ou rejeter.
7. Demander une génération d'image.
8. Suivre la tâche et voir le résultat dans la médiathèque.

Voir `docs/architecture.md` et `docs/api-integration.md`.
