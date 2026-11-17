# Intégration avec l'API de génération

Tous les appels vers l'API externe passent par `GenerationGatewayClient`
(`src/studio/clients/`). Deux implémentations : `HttpGenerationGatewayClient` et
`FakeGenerationGatewayClient`, sélectionnées par `GENERATION_GATEWAY_MODE`.

## Normalisation

Le client HTTP normalise les réponses de l'API externe :

- une soumission asynchrone peut renvoyer `job_id` sous **200 ou 202** : les deux
  sont acceptés et produisent un `JobRef` ;
- une réponse finale directe (image/vidéo) produit un `GenerationOutcome.direct` ;
- les URLs relatives des médias sont résolues contre `GENERATION_API_BASE_URL` ;
- un état externe inconnu est **conservé et signalé** (jamais interprété comme
  succès ou échec) ;
- les erreurs sont normalisées (`GatewayError`).

## Hypothèses sur l'API à confirmer

1. Le champ `result` d'un job réutilise le schéma de réponse synchrone
   (`images` / `video`), comme décrit dans `docs/contracts/openapi.json`.
2. `saved_to` et `avi_path` sont des informations du serveur externe — **jamais**
   utilisés comme chemins locaux du Studio. Seuls `url` (résolu) sert au
   téléchargement.
3. Les références de génération sont passées par `url` (résultat de l'import
   `POST /api/v1/assets`), pas par `asset_id` brut.
4. L'idempotence externe n'est pas supposée disponible : le Studio gère sa propre
   reprise (job_id enregistré dès réception, `needs_reconciliation` sinon).

## Contrat

- `docs/contracts/openapi.json` — copie du schéma OpenAPI de l'API externe.
- Toute divergence entre ce contrat et le code du client est à signaler.
