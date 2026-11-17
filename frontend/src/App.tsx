import { useEffect, useState } from "react";
import { api } from "./api/client";

type Ref = { id: string; name: string; initial_description: string; approved_description: string | null; media_ids: string };
type Proposal = { id: string; content: string; status: string; references: string };
type Generation = { id: string; kind: string; status: string; external_job_id: string | null };
type Asset = { id: string; kind: string; is_simulated: boolean };
type Scene = { id: string; order: number; title: string; narrative: string };
type Shot = { id: string; order: number; action: string; visual_intent: string };

const GEN_DEFAULTS: Record<string, Record<string, number>> = {
  image: { width: 1024, height: 1024, steps: 28 },
  video: { width: 864, height: 480, frames: 124 },
};

export default function App() {
  const [mode, setMode] = useState("…");
  const [projects, setProjects] = useState<any[]>([]);
  const [pid, setPid] = useState<string | null>(null);
  const [err, setErr] = useState("");

  const [refKind, setRefKind] = useState<"character" | "environment">("character");
  const [refs, setRefs] = useState<Ref[]>([]);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [shots, setShots] = useState<Record<string, Shot[]>>({});
  const [gens, setGens] = useState<Generation[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [genKind, setGenKind] = useState<"image" | "video" | "text">("image");

  async function refreshProjects() {
    setErr("");
    try {
      setMode((await api.config()).gateway_mode);
      setProjects(await api.listProjects());
    } catch (e) { setErr(String(e)); }
  }
  useEffect(() => { refreshProjects(); }, []);

  async function loadProject(id: string, kind: "character" | "environment") {
    setErr("");
    try {
      setRefs(await api.listReferences(id, kind));
      setProposals(await api.listProposals(id));
      setScenes(await api.listScenes(id));
      setGens(await api.listGenerations(id));
      setAssets(await api.listAssets(id));
      setShots({});
    } catch (e) { setErr(String(e)); }
  }

  function openProject(id: string) { setPid(id); loadProject(id, "character"); }

  async function refreshRefs() { if (pid) { setRefs(await api.listReferences(pid, refKind)); setAssets(await api.listAssets(pid)); } }

  async function createProject(name: string) { await api.createProject(name); refreshProjects(); }
  async function createRef(name: string, description: string) { if (!pid) return; await api.createReference(pid, refKind, name, description); refreshRefs(); }
  async function decide(proposalId: string, status: string) { if (!pid) return; await api.decideProposal(pid, proposalId, status); setProposals(await api.listProposals(pid)); refreshRefs(); }

  async function createScene(title: string, narrative: string) { if (!pid) return; await api.createScene(pid, title, narrative); setScenes(await api.listScenes(pid)); }
  async function createShot(sceneId: string, action: string, intent: string) { if (!pid) return; await api.createShot(pid, sceneId, action, intent); setShots({ ...shots, [sceneId]: await api.listShots(pid, sceneId) }); }
  async function toggleShots(sceneId: string) { if (!pid) return; setShots({ ...shots, [sceneId]: await api.listShots(pid, sceneId) }); }

  async function generate(request: Record<string, unknown>) {
    if (!pid) return;
    await api.createGeneration(pid, genKind, request);
    await new Promise(r => setTimeout(r, 1500));
    setGens(await api.listGenerations(pid));
    setAssets(await api.listAssets(pid));
  }

  return (
    <div style={{ fontFamily: "system-ui", maxWidth: 960, margin: "0 auto", padding: 16 }}>
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
            <h2>Références</h2>
            <select value={refKind} onChange={e => { const k = e.target.value as "character" | "environment"; setRefKind(k); loadProject(pid, k); }}>
              <option value="character">Personnages</option>
              <option value="environment">Environnements</option>
            </select>
            <form onSubmit={e => { e.preventDefault(); const f = new FormData(e.currentTarget); createRef(String(f.get("name")), String(f.get("description"))); (e.target as HTMLFormElement).reset(); }} style={{ display: "inline" }}>
              <input name="name" placeholder={`Nom (${refKind})`} />
              <input name="description" placeholder="Description" style={{ width: 260 }} />
              <button>Ajouter</button>
            </form>
            {refs.map(r => (
              <RefCard key={r.id} ref={r} kind={refKind} pid={pid} assets={assets.filter(a => (r.media_ids || "").split(",").includes(a.id))} onChanged={refreshRefs} />
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
            <h2>Scènes et plans</h2>
            <form onSubmit={e => { e.preventDefault(); const f = new FormData(e.currentTarget); createScene(String(f.get("title")), String(f.get("narrative"))); (e.target as HTMLFormElement).reset(); }}>
              <input name="title" placeholder="Titre de la scène" />
              <input name="narrative" placeholder="Description narrative" />
              <button>Ajouter une scène</button>
            </form>
            {scenes.map(s => (
              <div key={s.id} style={{ border: "1px solid #ddd", padding: 8, margin: 8 }}>
                <b>{s.title || `Scène ${s.order}`}</b>
                <p>{s.narrative}</p>
                <button onClick={() => toggleShots(s.id)}>Plans ({shots[s.id]?.length ?? "…"})</button>
                <form onSubmit={e => { e.preventDefault(); const f = new FormData(e.currentTarget); createShot(s.id, String(f.get("action")), String(f.get("intent"))); (e.target as HTMLFormElement).reset(); }} style={{ marginTop: 6 }}>
                  <input name="action" placeholder="Action" />
                  <input name="intent" placeholder="Intention visuelle" />
                  <button>Ajouter un plan</button>
                </form>
                {(shots[s.id] || []).map(sh => (
                  <div key={sh.id} style={{ marginLeft: 16, fontSize: 14 }}>#{sh.order} — {sh.action} <small>({sh.visual_intent})</small></div>
                ))}
              </div>
            ))}
          </section>

          <section>
            <h2>Générations</h2>
            <GenForm kind={genKind} setKind={setGenKind} onSubmit={generate} />
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

function RefCard({ ref, kind, pid, assets, onChanged }: {
  ref: Ref; kind: "character" | "environment"; pid: string; assets: Asset[];
  onChanged: () => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(ref.name);
  const [description, setDescription] = useState(ref.initial_description);

  async function save() {
    await api.updateReference(pid, kind, ref.id, { name, description });
    await onChanged();
  }
  async function importFile(file: File) {
    await api.importReference(pid, kind, ref.id, file);
    await onChanged();
  }
  async function analyze() {
    await api.analyzeReference(pid, kind, ref.id);
    await new Promise(r => setTimeout(r, 1500));
    await onChanged();
  }
  async function unlink(assetId: string) {
    await api.unlinkReferenceAsset(pid, kind, ref.id, assetId);
    await onChanged();
  }

  return (
    <div style={{ border: "1px solid #ccc", padding: 10, margin: 8, borderRadius: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <b>{ref.name}</b>
        <button onClick={() => setOpen(!open)}>{open ? "Fermer" : "Modifier"}</button>
      </div>
      {!open && <p style={{ fontSize: 14 }}>{ref.initial_description || "(pas de description)"}</p>}
      {open && (
        <div style={{ marginTop: 8 }}>
          <label>Nom<br /><input value={name} onChange={e => setName(e.target.value)} /></label><br />
          <label>Description<br /><textarea value={description} onChange={e => setDescription(e.target.value)} rows={3} style={{ width: "100%" }} /></label><br />
          <button onClick={save}>Enregistrer</button>

          <h4>Visuels</h4>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {assets.map(a => (
              <figure key={a.id} style={{ margin: 0, position: "relative" }}>
                <img src={api.assetUrl(a.id)} width={96} alt="visuel" />
                <button style={{ position: "absolute", top: 2, right: 2 }} onClick={() => unlink(a.id)}>✕</button>
              </figure>
            ))}
          </div>
          <input type="file" onChange={e => e.target.files && importFile(e.target.files[0])} />
          <button onClick={analyze}>Analyser (vision)</button>
          {ref.approved_description && <p><i>Approuvé : {ref.approved_description}</i></p>}
        </div>
      )}
    </div>
  );
}

function GenForm({ kind, setKind, onSubmit }: {
  kind: string;
  setKind: (k: "image" | "video" | "text") => void;
  onSubmit: (request: Record<string, unknown>) => void;
}) {
  return (
    <form onSubmit={e => {
      e.preventDefault();
      const f = new FormData(e.currentTarget);
      const request: Record<string, unknown> = { prompt: String(f.get("prompt")) };
      const d = GEN_DEFAULTS[kind] || {};
      for (const [k, v] of Object.entries(d)) request[k] = Number(f.get(k) || v);
      onSubmit(request);
      (e.target as HTMLFormElement).reset();
    }} style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
      <select value={kind} onChange={e => setKind(e.target.value as any)}>
        <option value="image">Image</option>
        <option value="video">Vidéo</option>
        <option value="text">Texte</option>
      </select>
      <input name="prompt" placeholder="Prompt" style={{ flex: 1, minWidth: 200 }} />
      {kind !== "text" && Object.entries(GEN_DEFAULTS[kind] || {}).map(([k, v]) => (
        <input key={k} name={k} defaultValue={v} style={{ width: 80 }} title={k} />
      ))}
      <button>Générer</button>
    </form>
  );
}
