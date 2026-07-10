import { useEffect, useState } from "react";
import { api, KedbDoc } from "../api";

export default function DocsPage() {
  const [docs, setDocs] = useState<KedbDoc[]>([]);
  const [selected, setSelected] = useState<KedbDoc | null>(null);
  const [markdown, setMarkdown] = useState("");
  const [filtro, setFiltro] = useState<"todos" | "validado" | "borrador">("todos");
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const estado = filtro === "todos" ? undefined : filtro;
      const list = await api.listDocs(estado);
      setDocs(list);
      if (list.length && !selected) {
        await openDoc(list[0]);
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
    const res = await api.exportDocs();
    setMsg(`Exportados ${res.exported} artículos a Markdown.`);
    await load();
  };

  useEffect(() => {
    load();
  }, [filtro]);

  return (
    <div className="max-w-6xl mx-auto p-4">
      <div className="navbar bg-accent text-accent-content rounded-lg mb-4 px-4 shadow">
        <span className="text-lg font-bold">Live Docs — KEDB</span>
        <span className="ml-4 badge badge-ghost">{docs.length} artículos</span>
        <div className="ml-auto flex gap-2">
          <select
            className="select select-sm select-bordered text-base-content"
            value={filtro}
            onChange={(e) => setFiltro(e.target.value as typeof filtro)}
          >
            <option value="todos">Todos</option>
            <option value="validado">Validados</option>
            <option value="borrador">Borradores</option>
          </select>
          <button className="btn btn-sm btn-neutral" onClick={exportAll}>
            Sync SQLite → MD
          </button>
        </div>
      </div>

      <p className="text-sm text-base-content/70 mb-4">
        Archivos en <code>data/kedb/articles/*.md</code> — visibles en el host y en esta vista.
      </p>

      {msg && <div className="alert alert-success mb-4 text-sm">{msg}</div>}

      {loading ? (
        <span className="loading loading-spinner" />
      ) : docs.length === 0 ? (
        <div className="alert">
          No hay Markdown aún. Pulsa <strong>Sync SQLite → MD</strong> o aprueba artículos en Experto.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="card bg-base-100 shadow">
            <div className="card-body p-3">
              <ul className="menu menu-sm">
                {docs.map((d) => (
                  <li key={d.articulo_id}>
                    <button
                      className={selected?.articulo_id === d.articulo_id ? "active" : ""}
                      onClick={() => openDoc(d)}
                    >
                      <span className="truncate">{d.titulo}</span>
                      <span className="badge badge-xs">{d.estado}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="lg:col-span-2 card bg-base-100 shadow">
            <div className="card-body">
              {selected && (
                <>
                  <div className="flex items-center gap-2">
                    <h2 className="card-title text-base">{selected.titulo}</h2>
                    <span className="badge badge-sm">{selected.estado}</span>
                    <span className="font-mono text-xs opacity-60">{selected.filename}</span>
                  </div>
                  <div className="divider my-1" />
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
