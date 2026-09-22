import { useEffect, useState } from "react";
import { api, KedbDoc } from "../api";

export default function DocsPage() {
  const [docs, setDocs] = useState<KedbDoc[]>([]);
  const [selected, setSelected] = useState<KedbDoc | null>(null);
  const [markdown, setMarkdown] = useState("");
  const [filtro, setFiltro] = useState<"validado" | "todos" | "borrador">("validado");
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const list = await api.listDocs(filtro);
      setDocs(list);
      if (list.length) {
        const still = selected && list.find((d) => d.articulo_id === selected.articulo_id);
        await openDoc(still || list[0]);
      } else {
        setSelected(null);
        setMarkdown("");
      }
    } finally {
      setLoading(false);
    }
  };

  const openDoc = async (doc: KedbDoc) => {
    setSelected(doc);
    const res = await api.getDoc(doc.articulo_id);
    setMarkdown(res.markdown);
  };

  const exportAll = async () => {
    const res = await api.exportDocs(true);
    setMsg(`Publicados ${res.exported} artículos validados → Markdown.`);
    await load();
  };

  useEffect(() => {
    load();
  }, [filtro]);

  return (
    <div className="max-w-6xl mx-auto p-4">
      <div className="navbar page-header bg-accent text-accent-content rounded-lg mb-4 px-4 shadow">
        <div className="page-header-title">
          <span className="text-lg font-bold">Live Docs — KEDB</span>
          <span className="badge badge-ghost">{docs.length} artículos</span>
        </div>
        <div className="page-header-actions">
          <select
            className="select select-sm select-bordered text-base-content"
            value={filtro}
            onChange={(e) => setFiltro(e.target.value as typeof filtro)}
          >
            <option value="validado">Validados (live)</option>
            <option value="todos">Todos los .md</option>
            <option value="borrador">Borradores (si hay .md)</option>
          </select>
          <button className="btn btn-sm btn-neutral" onClick={exportAll}>
            Publicar validados → MD
          </button>
        </div>
      </div>

      <p className="text-sm text-base-content/70 mb-4">
        Live docs = proyección Markdown de artículos <strong>validados</strong>.
        SQLite sigue siendo la fuente de verdad. Archivos en <code>data/kedb/articles/*.md</code>.
      </p>

      {msg && <div className="alert alert-success mb-4 text-sm">{msg}</div>}

      {loading ? (
        <span className="loading loading-spinner" />
      ) : docs.length === 0 ? (
        <div className="alert">
          No hay docs publicados. Aprueba un artículo en Experto o pulsa{" "}
          <strong>Publicar validados → MD</strong>.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-start">
          <div className="card bg-base-100 shadow self-start w-full">
            <div className="card-body gap-2 p-3 !flex-none">
              <ul className="menu menu-sm w-full">
                {docs.map((d) => (
                  <li key={d.articulo_id}>
                    <button
                      type="button"
                      className={selected?.articulo_id === d.articulo_id ? "active" : ""}
                      onClick={() => openDoc(d)}
                    >
                      <span className="truncate flex-1 text-left">{d.titulo}</span>
                      <span className="badge badge-xs shrink-0">{d.estado}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="lg:col-span-2 card bg-base-100 shadow self-start w-full">
            <div className="card-body gap-3 p-4 !flex-none">
              {selected && (
                <>
                  <div className="flex flex-wrap items-start gap-2">
                    <h2 className="card-title text-base leading-snug flex-1 min-w-0">
                      {selected.titulo}
                    </h2>
                    <span className="badge badge-sm shrink-0">{selected.estado}</span>
                    <span className="font-mono text-xs opacity-60 w-full sm:w-auto">
                      {selected.filename}
                    </span>
                  </div>
                  <div className="divider my-0" />
                  <pre className="whitespace-pre-wrap text-sm bg-base-200 p-4 rounded-lg overflow-auto max-h-[70vh]">
                    {markdown}
                  </pre>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
