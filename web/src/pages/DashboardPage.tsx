import { useEffect, useState } from "react";
import { api } from "../api";

export default function DashboardPage() {
  const [dashboard, setDashboard] = useState<Record<string, unknown> | null>(null);
  const [evaluacion, setEvaluacion] = useState<Record<string, unknown> | null>(null);
  const [searchQ, setSearchQ] = useState("");
  const [searchResults, setSearchResults] = useState<unknown[]>([]);
  const [articulos, setArticulos] = useState<unknown[]>([]);

  useEffect(() => {
    api.getDashboard().then(setDashboard).catch(() => {});
    api.getEvaluacion().then(setEvaluacion).catch(() => {});
    api.listArticulos().then(setArticulos).catch(() => {});
  }, []);

  const handleSearch = async () => {
    const res = await api.searchKedb(searchQ);
    setSearchResults(res.results);
  };

  const cobertura = dashboard?.cobertura_kedb as Record<string, unknown> | undefined;

  return (
    <div className="max-w-5xl mx-auto p-4">
      <div className="navbar bg-neutral text-neutral-content rounded-lg mb-4 px-4 shadow">
        <span className="text-lg font-bold">Tablero del Coordinador (HU15)</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        <div className="stat bg-base-100 shadow rounded-lg">
          <div className="stat-title">Artículos KEDB</div>
          <div className="stat-value text-primary">{cobertura?.total_articulos as number ?? "—"}</div>
        </div>
        <div className="stat bg-base-100 shadow rounded-lg">
          <div className="stat-title">Validados</div>
          <div className="stat-value text-success">{cobertura?.validados as number ?? "—"}</div>
        </div>
        <div className="stat bg-base-100 shadow rounded-lg">
          <div className="stat-title">Tickets procesados</div>
          <div className="stat-value">{dashboard?.tickets_procesados as number ?? "—"}</div>
        </div>
      </div>

      {evaluacion && (
        <div className="card bg-base-100 shadow mb-4">
          <div className="card-body">
            <h3 className="card-title text-sm">Métricas de evaluación (C9)</h3>
            <div className="flex gap-6 text-sm">
              <span>F1 macro: <strong>{evaluacion.f1_macro as number}</strong></span>
              <span>Recall@5: <strong>{evaluacion.recall_at_5 as number}</strong></span>
              <span>Muestra: {evaluacion.muestra_tickets as number} tickets</span>
            </div>
          </div>
        </div>
      )}

      <div className="card bg-base-100 shadow mb-4">
        <div className="card-body">
          <h3 className="card-title text-sm">Búsqueda directa KEDB (HU16)</h3>
          <div className="flex gap-2">
            <input
              className="input input-bordered flex-1"
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              placeholder="Buscar en KEDB..."
            />
            <button className="btn btn-primary" onClick={handleSearch}>
              Buscar
            </button>
          </div>
          {searchResults.length > 0 && (
            <ul className="mt-3 space-y-2 text-sm">
              {searchResults.map((r: unknown, i) => {
                const item = r as { titulo?: string; score: number; articulo_o_ticket_id: string };
                return (
                  <li key={i} className="border-b pb-2">
                    {item.titulo || item.articulo_o_ticket_id} — similitud {(item.score * 100).toFixed(0)}%
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>

      <div className="card bg-base-100 shadow">
        <div className="card-body">
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
                {(articulos as { articulo_id: string; titulo: string; estado: string; categoria: string }[]).map((a) => (
                  <tr key={a.articulo_id}>
                    <td className="font-mono text-xs">{a.articulo_id}</td>
                    <td>{a.titulo.slice(0, 50)}</td>
                    <td><span className="badge badge-sm">{a.estado}</span></td>
                    <td className="text-xs">{a.categoria.slice(0, 30)}</td>
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
