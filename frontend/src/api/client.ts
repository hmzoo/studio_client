const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(BASE + path, init);
  if (!r.ok) throw new Error(await r.text());
  return r.json() as Promise<T>;
}

export const api = {
  config: () => req<{ gateway_mode: string; gateway_base_url_configured: boolean }>("/api/config"),
  listProjects: () => req<any[]>("/api/projects"),
  createProject: (name: string) => req<any>("/api/projects", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name }) }),
  listReferences: (pid: string, kind: string) => req<any[]>(`/api/projects/${pid}/references?kind=${kind}`),
  createReference: (pid: string, kind: string, name: string) => req<any>(`/api/projects/${pid}/references`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ kind, name }) }),
  importReference: (pid: string, kind: string, rid: string, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return req<any>(`/api/projects/${pid}/references/${kind}/${rid}/import`, { method: "POST", body: fd });
  },
  analyzeReference: (pid: string, kind: string, rid: string) => req<any>(`/api/projects/${pid}/references/${kind}/${rid}/analyze`, { method: "POST" }),
  listProposals: (pid: string) => req<any[]>(`/api/projects/${pid}/completions`),
  decideProposal: (pid: string, proposalId: string, status: string) => req<any>(`/api/projects/${pid}/completions/${proposalId}/decision`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status }) }),
  createGeneration: (pid: string, kind: string, prompt: string) => req<any>(`/api/projects/${pid}/generations`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ kind, request: { prompt, width: 512, height: 512 } }) }),
  listGenerations: (pid: string) => req<any[]>(`/api/projects/${pid}/generations`),
  listAssets: (pid: string) => req<any[]>(`/api/projects/${pid}/assets`),
  assetUrl: (id: string) => `${BASE}/api/assets/${id}/content`,
};
