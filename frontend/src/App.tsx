import { useEffect, useState } from "react";
import { api } from "./api/client";

type Ref = { id: string; name: string; initial_description: string; approved_description: string | null };
type Proposal = { id: string; content: string; status: string; references: string };
type Generation = { id: string; kind: string; status: string; external_job_id: string | null };
type Asset = { id: string; kind: string; is_simulated: boolean };

export default function App() {
  const [mode, setMode] = useState<string>("…");
  const [projects, setProjects] = useState<any[]>([]);
  const [pid, setPid] = useState<string | null>(null);
  const [refs, setRefs] = useState<Ref[]>([]);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [gens, setGens] = useState<Generation[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [err, setErr] = useState<string>("");

  async function refresh() {
    setErr("");
    try {
      const cfg = await api.config();
      setMode(cfg.gateway_mode);
      setProjects(await api.listProjects());
    } catch (e) { setErr(String(e)); }
  }

  async function openProject(id: string) {
    setPid(id);
    setErr("");
    try {
      setRefs(await api.listReferences(id, "character"));
      setProposals(await api.listProposals(id));
      setGens(await api.listGenerations(id));
      setAssets(await api.listAssets(id));
    } catch (e) { setErr(String(e)); }
  }

  useEffect(() => { refresh(); }, []);

  async function createProject(name: string) {
    await api.createProject(name);
    refresh();
  }

  async function createRef(name: string) {
    if (!pid) return;
    await api.createReference(pid, "character", name);
    setRefs(await api.listReferences(pid, "character"));
  }

  async function importFile(rid: string, file: File) {
    if (!pid) return;
    await api.importReference(pid, "character", rid, file);
    setAssets(await api.listAssets(pid));
  }

  async function analyze(rid: string) {
    if (!pid) return;
    await api.analyzeReference(pid, "character", rid);
    await new Promise(r => setTimeout(r, 1500)); // laisse le worker traiter
    setProposals(await api.listProposals(pid));
    setRefs(await api.listReferences(pid, "character"));
  }

  async function decide(proposalId: string, status: string) {
    if (!pid) return;
    await api.decideProposal(pid, proposalId, status);
    setProposals(await api.listProposals(pid));
    setRefs(await api.listReferences(pid, "character"));
  }

  async function generate(prompt: string) {
    if (!pid) return;
    await api.createGeneration(pid, "image", prompt);
    await new Promise(r => setTimeout(r, 1500)); // laisse le worker traiter
    setGens(await api.listGenerations(pid));
    setAssets(await api.listAssets(pid));
  }

  return (
    <div style={{ fontFamily: "system-ui", maxWidth: 900, margin: "0 auto", padding: 16 }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1>Studio</h1>
        <span style={{ padding: "2px 10px", borderRadius: 8, background: mode === "fake" ? "#fff3cd" : "#d1e7dd" }}>
          passerelle : {mode}
        </span>
      </header>
      {err && <p style={{ color: "red" }}>Erreur : {err}</p>}

      {!pid ? (
        <section>
          <h2>Projets</h2>
          <form onSubmit={e => { e.preventDefault(); const f = new FormData(e.currentTarget); createProject(String(f.get("name"))); (e.target as HTMLFormElement).reset(); }}>
            <input name="name" placeholder="Nom du projet" />
            <button>Créer</button>
          </form>
          <ul>{projects.map(p => <li key={p.id}><button onClick={() => openProject(p.id)}>{p.name}</button></li>)}</ul>
        </section>
      ) : (
        <div>
          <button onClick={() => setPid(null)}>← Projets</button>

          <section>
            <h2>Références — personnages</h2>
            <form onSubmit={e => { e.preventDefault(); const f = new FormData(e.currentTarget); createRef(String(f.get("name"))); (e.target as HTMLFormElement).reset(); }}>
              <input name="name" placeholder="Nom du personnage" />
              <button>Ajouter</button>
            </form>
            {refs.map(r => (
              <div key={r.id} style={{ border: "1px solid #ddd", padding: 8, margin: 8 }}>
                <b>{r.name}</b>
                {r.approved_description && <p><i>Approuvé : {r.approved_description}</i></p>}
                <input type="file" onChange={e => e.target.files && importFile(r.id, e.target.files[0])} />
                <button onClick={() => analyze(r.id)}>Analyser (vision)</button>
              </div>
            ))}
          </section>

          <section>
            <h2>Complétions proposées</h2>
            {proposals.map(p => (
              <div key={p.id} style={{ border: "1px solid #ddd", padding: 8, margin: 8 }}>
                <p>{p.content}</p>
                <small>{p.references}</small>
                <p>statut : {p.status}</p>
                {p.status === "pending" && (<>
                  <button onClick={() => decide(p.id, "approved")}>Approuver</button>
                  <button onClick={() => decide(p.id, "rejected")}>Rejeter</button>
                </>)}
              </div>
            ))}
            {!proposals.length && <p>Aucune proposition.</p>}
          </section>

          <section>
            <h2>Générations (image)</h2>
            <form onSubmit={e => { e.preventDefault(); const f = new FormData(e.currentTarget); generate(String(f.get("prompt"))); (e.target as HTMLFormElement).reset(); }}>
              <input name="prompt" placeholder="Prompt d'image" />
              <button>Générer</button>
            </form>
            <ul>{gens.map(g => <li key={g.id}>{g.kind} — {g.status}{g.external_job_id ? ` (job ${g.external_job_id})` : ""}</li>)}</ul>
          </section>

          <section>
            <h2>Médiathèque</h2>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {assets.map(a => (
                <figure key={a.id} style={{ margin: 0 }}>
                  <img src={api.assetUrl(a.id)} width={120} alt={a.kind} />
                  <figcaption style={{ fontSize: 11 }}>{a.kind}{a.is_simulated ? " · simulé" : ""}</figcaption>
                </figure>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
