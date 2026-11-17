const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(BASE + path, init);
  if (!r.ok) throw new Error(await r.text());
  return r.json() as Promise<T>;
}

function json(method: string, body: unknown): RequestInit {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}

export const api = {
  config: () => req<{ gateway_mode: string; gateway_base_url_configured: boolean }>("/api/config"),

  // projets
  listProjects: () => req<any[]>("/api/projects"),
  createProject: (name: string) => req<any>("/api/projects", json("POST", { name })),
  listAssets: (pid: string) => req<any[]>(`/api/projects/${pid}/assets`),
  assetUrl: (id: string) => `${BASE}/api/assets/${id}/content`,

  // références (personnages / environnements)
  listReferences: (pid: string, kind: string) => req<any[]>(`/api/projects/${pid}/references?kind=${kind}`),
  createReference: (pid: string, kind: string, name: string, description: string = "") =>
    req<any>(`/api/projects/${pid}/references`, json("POST", { kind, name, description })),
  importReference: (pid: string, kind: string, rid: string, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return req<any>(`/api/projects/${pid}/references/${kind}/${rid}/import`, { method: "POST", body: fd });
  },
  analyzeReference: (pid: string, kind: string, rid: string) =>
    req<any>(`/api/projects/${pid}/references/${kind}/${rid}/analyze`, { method: "POST" }),
  getTask: (taskId: string) => req<any>(`/api/tasks/${taskId}`),
  updateReference: (pid: string, kind: string, rid: string, patch: { name?: string; description?: string }) =>
    req<any>(`/api/projects/${pid}/references/${kind}/${rid}`, json("PATCH", patch)),
  unlinkReferenceAsset: (pid: string, kind: string, rid: string, assetId: string) =>
    req<any>(`/api/projects/${pid}/references/${kind}/${rid}/assets/${assetId}`, { method: "DELETE" }),
  improveReference: (pid: string, kind: string, rid: string) =>
    req<any>(`/api/projects/${pid}/references/${kind}/${rid}/improve`, { method: "POST" }),
  generateReferenceVisual: (pid: string, kind: string, rid: string) =>
    req<any>(`/api/projects/${pid}/references/${kind}/${rid}/generate-visual`, { method: "POST" }),

  // complétions
  listProposals: (pid: string) => req<any[]>(`/api/projects/${pid}/completions`),
  decideProposal: (pid: string, proposalId: string, status: string) =>
    req<any>(`/api/projects/${pid}/completions/${proposalId}/decision`, json("POST", { status })),

  // storyboard (scènes / plans)
  listScenes: (pid: string) => req<any[]>(`/api/projects/${pid}/scenes`),
  createScene: (pid: string, title: string, narrative: string) =>
    req<any>(`/api/projects/${pid}/scenes`, json("POST", { title, narrative })),
  listShots: (pid: string, sceneId: string) => req<any[]>(`/api/projects/${pid}/scenes/${sceneId}/shots`),  createShot: (pid: string, sceneId: string, action: string, visualIntent: string,
               characterIds: string[] = [], environmentIds: string[] = [], mediaIds: string[] = []) =>
    req<any>(`/api/projects/${pid}/scenes/${sceneId}/shots`,
      json("POST", { action, visual_intent: visualIntent, character_ids: characterIds, environment_ids: environmentIds, media_ids: mediaIds })),
  generateShot: (pid: string, sceneId: string, shotId: string) =>
    req<any>(`/api/projects/${pid}/scenes/${sceneId}/shots/${shotId}/generate`, { method: "POST" }),
  deleteShot: (pid: string, sceneId: string, shotId: string) =>
    req<any>(`/api/projects/${pid}/scenes/${sceneId}/shots/${shotId}`, { method: "DELETE" }),
  generateSequence: (pid: string, sceneId: string) =>
    req<any>(`/api/projects/${pid}/scenes/${sceneId}/generate-sequence`, { method: "POST" }),
  chat: (pid: string, message: string) =>
    req<any>(`/api/projects/${pid}/chat`, { method: "POST", body: JSON.stringify({ message }) }),

  // générations
  createGeneration: (pid: string, kind: string, request: unknown) =>
    req<any>(`/api/projects/${pid}/generations`, json("POST", { kind, request })),
  listGenerations: (pid: string) => req<any[]>(`/api/projects/${pid}/generations`),
  getGeneration: (pid: string, id: string) => req<any>(`/api/projects/${pid}/generations/${id}`),
};
