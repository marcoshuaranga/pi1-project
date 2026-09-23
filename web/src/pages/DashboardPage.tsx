import { useEffect, useState } from "react";
import { api } from "../api";
import { useJobRun } from "../useJobRun";

export default function DashboardPage() {
  const [dashboard, setDashboard] = useState<Record<string, unknown> | null>(null);
  const [evaluacion, setEvaluacion] = useState<Record<string, unknown> | null>(null);
  const [searchQ, setSearchQ] = useState("");
  const [searchResults, setSearchResults] = useState<unknown[]>([]);
  const [articulos, setArticulos] = useState<unknown[]>([]);
  const [error, setError] = useState("");
  const jobRun = useJobRun();

  const refresh = async () => {
    const [dash, evalMetrics, arts] = await Promise.all([
      api.getDashboard().catch(() => null),
      api.getEvaluacion().catch(() => null),
      api.listArticulos().catch(() => []),
    ]);
    if (dash) setDashboard(dash);
    if (evalMetrics) setEvaluacion(evalMetrics);
    setArticulos(arts);
  };

  useEffect(() => {
    refresh();
    return () => jobRun.cancel();
  }, []);

  const handleRecompute = async () => {
    setError("");
    try {
      const done = await jobRun.run(() => api.enqueueEvaluacion(), "Encolando evaluación…");
      if (!done) return; // cancelled by a newer run or unmount
      if (done.success === false) {
        throw new Error(done.error || "La evaluación falló en el worker");
      }
      await refresh();
    } catch (e) {
      setError(String(e));
    }
  };

  const handleSearch = async () => {
    const res = await api.searchKedb(searchQ);
    setSearchResults(res.results);
  };

  const cobertura = dashboard?.cobertura_kedb as Record<string, unknown> | undefined;

  return (
    <div className="max-w-5xl mx-auto p-4">
      <div className="navbar page-header bg-neutral text-neutral-content rounded-lg mb-4 px-4 shadow">
        <span className="text-lg font-bold">Tablero del Coordinador (HU15)</span>
      </div>

      {jobRun.status && (
        <div className="alert alert-info mb-4 text-sm">
          <span>{jobRun.status}</span>
        </div>
      )}
      {error && (
        <div className="alert alert-error mb-4 text-sm">
          <span>{error}</span>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4 items-start">
        <div className="stat bg-base-100 shadow rounded-lg self-start">
          <div className="stat-title">Artículos KEDB</div>
          <div className="stat-value text-primary text-3xl">
            {(cobertura?.total_articulos as number) ?? "—"}
          </div>
        </div>
        <div className="stat bg-base-100 shadow rounded-lg self-start">
          <div className="stat-title">Validados</div>
          <div className="stat-value text-success text-3xl">
            {(cobertura?.validados as number) ?? "—"}
          </div>
        </div>
        <div className="stat bg-base-100 shadow rounded-lg self-start">
          <div className="stat-title">Tickets procesados</div>
          <div className="stat-value text-3xl">
            {(dashboard?.tickets_procesados as number) ?? "—"}
          </div>
        </div>
      </div>

      <div className="card bg-base-100 shadow mb-4">
        <div className="card-body gap-3 p-4 !flex-none">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <h3 className="card-title text-sm">Métricas de evaluación (C9)</h3>
            <button
              className="btn btn-sm btn-outline"
              onClick={handleRecompute}
              disabled={jobRun.busy}
            >
              {jobRun.busy ? (
                <>
                  <span className="loading loading-spinner loading-xs" />
                  Recalculando…
                </>
              ) : (
                "Recalcular (worker)"
              )}
            </button>
          </div>
          {evaluacion ? (
            <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
              <span>
                F1 macro: <strong>{evaluacion.f1_macro as number}</strong>
              </span>
              <span>
                Recall@5: <strong>{evaluacion.recall_at_5 as number}</strong>
              </span>
              <span>Muestra: {evaluacion.muestra_tickets as number} tickets</span>
            </div>
          ) : (
            <p className="text-sm opacity-70">Sin caché aún. Usa recalcular para encolar el job.</p>
          )}
        </div>
      </div>

      <div className="card bg-base-100 shadow mb-4">
        <div className="card-body gap-3 p-4 !flex-none">
          <h3 className="card-title text-sm">Búsqueda directa KEDB (HU16)</h3>
          <div className="flex gap-2 flex-wrap">
            <input
              className="input input-bordered flex-1 min-w-[12rem]"
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              placeholder="Buscar en KEDB..."
            />
            <button className="btn btn-primary" onClick={handleSearch}>
              Buscar
            </button>
          </div>
          {searchResults.length > 0 && (
            <ul className="mt-1 space-y-2 text-sm">
              {searchResults.map((r: unknown, i) => {
                const item = r as {
                  titulo?: string;
                  score: number;
                  articulo_o_ticket_id: string;
                };
                return (
                  <li key={i} className="border-b pb-2">
                    {item.titulo || item.articulo_o_ticket_id} — similitud{" "}
                    {(item.score * 100).toFixed(0)}%
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>

      <div className="card bg-base-100 shadow">
        <div className="card-body gap-3 p-4 !flex-none">
          <h3 className="card-title text-sm">Gestión ciclo de vida (HU17)</h3>
          <div className="overflow-x-auto">
            <table className="table table-sm">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Título</th>
                  <th>Estado</th>
                  <th>Categoría</th>
                </tr>
              </thead>
              <tbody>
                {(
                  articulos as {
                    articulo_id: string;
                    titulo: string;
                    estado: string;
                    categoria: string;
                  }[]
                ).map((a) => (
                  <tr key={a.articulo_id}>
                    <td className="font-mono text-xs whitespace-nowrap">{a.articulo_id}</td>
                    <td className="max-w-[14rem]">
                      <span className="line-clamp-2">{a.titulo}</span>
                    </td>
                    <td>
                      <span className="badge badge-sm">{a.estado}</span>
                    </td>
                    <td className="text-xs max-w-[12rem]">
                      <span className="line-clamp-2 whitespace-normal">{a.categoria}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
