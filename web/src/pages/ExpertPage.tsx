import { useEffect, useRef, useState } from "react";
import { api, KedbArticulo, pollJob } from "../api";

export default function ExpertPage() {
  const [pendientes, setPendientes] = useState<KedbArticulo[]>([]);
  const [selected, setSelected] = useState<KedbArticulo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [jobStatus, setJobStatus] = useState("");
  const [generating, setGenerating] = useState(false);
  const pollAbort = useRef<AbortController | null>(null);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const list = await api.getPendientes();
      setPendientes(list);
      setSelected((prev) => {
        if (!list.length) return null;
        if (prev && list.some((a) => a.articulo_id === prev.articulo_id)) return prev;
        return list[0];
      });
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    return () => pollAbort.current?.abort();
  }, []);

  const handleGenerate = async () => {
    setError("");
    setMsg("");
    setGenerating(true);
    setJobStatus("Encolando generación KEDB…");
    pollAbort.current?.abort();
    pollAbort.current = new AbortController();
    try {
      const enqueued = await api.enqueueKedbGenerate(10);
      setJobStatus(`Job ${enqueued.job_id} en cola — consultando cada 5s…`);
      const done = await pollJob(enqueued.job_id, {
        signal: pollAbort.current.signal,
        onStatus: (job) => setJobStatus(`Job ${job.job_id}: ${job.status}`),
      });
      if (done.success === false) {
        throw new Error(done.error || "La generación falló en el worker");
      }
      const generated =
        done.result && typeof done.result === "object" && "generated" in done.result
          ? Number((done.result as { generated: number }).generated)
          : undefined;
      setMsg(
        generated != null
          ? `Generación lista: ${generated} artículo(s).`
          : "Generación KEDB completada."
      );
      setJobStatus("");
      await load();
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") return;
      setError(String(e));
      setJobStatus("");
    } finally {
      setGenerating(false);
    }
  };

  const handleApprove = async () => {
    if (!selected) return;
    try {
      const updated = await api.approveArticulo(selected.articulo_id);
      setSelected(updated);
      setMsg("Artículo aprobado — disponible para RAG y Live Docs.");
      await load();
    } catch (e) {
      setError(String(e));
    }
  };

  const handleReject = async () => {
    if (!selected) return;
    try {
      await api.rejectArticulo(selected.articulo_id);
      setMsg("Artículo rechazado.");
      setSelected(null);
      await load();
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <div className="max-w-5xl mx-auto p-4">
      <div className="navbar bg-secondary text-secondary-content rounded-lg mb-4 px-4 shadow">
        <span className="text-lg font-bold">Validación KEDB — Experto Técnico</span>
        <span className="ml-4 badge badge-warning">{pendientes.length} pendientes</span>
        <div className="ml-auto">
          <button
            className="btn btn-sm btn-primary"
            onClick={handleGenerate}
            disabled={generating}
          >
            {generating ? (
              <>
                <span className="loading loading-spinner loading-xs" />
                Generando…
              </>
            ) : (
              "Generar borradores (worker)"
            )}
          </button>
        </div>
      </div>

      {jobStatus && (
        <div className="alert alert-info mb-4 text-sm">
          <span>{jobStatus}</span>
        </div>
      )}

      {error && (
        <div className="alert alert-error mb-4 text-sm">
          <span>{error}</span>
          <button className="btn btn-sm" onClick={load}>
            Reintentar
          </button>
        </div>
      )}

      {loading && pendientes.length === 0 ? (
        <div className="flex items-center gap-2 text-sm">
          <span className="loading loading-spinner" />
          Cargando pendientes desde la API…
        </div>
      ) : pendientes.length === 0 && !error ? (
        <div className="alert alert-info">
          No hay artículos pendientes. Usa &quot;Generar borradores&quot; (poll cada 5s) o{" "}
          <code>POST /kedb/seed-demo</code>.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="col-span-1">
            <div className="card bg-base-100 shadow">
              <div className="card-body p-4">
                <h3 className="font-semibold text-sm">Pendientes (HU14)</h3>
                <ul className="menu menu-sm">
                  {pendientes.map((a) => (
                    <li key={a.articulo_id}>
                      <button
                        className={selected?.articulo_id === a.articulo_id ? "active" : ""}
                        onClick={() => setSelected(a)}
                      >
                        {a.titulo.slice(0, 40)}...
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>

          {selected && (
            <div className="col-span-2 card bg-base-100 shadow">
              <div className="card-body">
                <h2 className="card-title">{selected.titulo}</h2>
                <span className="badge">{selected.estado}</span>
                <div className="divider my-1" />

                <section>
                  <h4 className="font-semibold text-sm">Síntoma</h4>
                  <p className="text-sm">{selected.sintoma}</p>
                </section>
                <section className="mt-3">
                  <h4 className="font-semibold text-sm">Causa probable</h4>
                  <p className="text-sm">{selected.causa}</p>
                </section>
                <section className="mt-3">
                  <h4 className="font-semibold text-sm">Solución</h4>
                  <p className="text-sm whitespace-pre-line">{selected.solucion}</p>
                </section>
                <section className="mt-3">
                  <h4 className="font-semibold text-sm">Trazabilidad N:1 (HU09)</h4>
                  <p className="text-sm mt-1">
                    <span className="badge badge-primary badge-lg">
                      {selected.tickets_fuente.length} tickets fuente
                    </span>
                  </p>
                  <p className="text-xs font-mono text-base-content/70 mt-2">
                    {selected.tickets_fuente.slice(0, 20).join(", ")}
                    {selected.tickets_fuente.length > 20 &&
                      ` ... (+${selected.tickets_fuente.length - 20} más)`}
                  </p>
                </section>

                <div className="card-actions justify-end mt-4">
                  <button className="btn btn-error btn-sm" onClick={handleReject}>
                    Rechazar
                  </button>
                  <button className="btn btn-success btn-sm" onClick={handleApprove}>
                    Aprobar (HU10)
                  </button>
                </div>
                {msg && <p className="text-success text-sm mt-2">{msg}</p>}
              </div>
            </div>
          )}
        </div>
      )}

      {msg && pendientes.length === 0 && !selected && (
        <p className="text-success text-sm mt-2">{msg}</p>
      )}
    </div>
  );
}
