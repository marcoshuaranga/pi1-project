import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, KedbArticulo, Solucion } from "../api";
import { useFeature } from "../featureFlags";
import { formatPorcentaje, mensajeDeError } from "../lib/operador";
import {
  accionesDe,
  claseBadgeEstado,
  confirmacionDe,
  explicarEvidencia,
  FILTROS_VACIOS,
  FiltrosTablero,
  hayFiltros,
  queryDeFiltros,
  validarRango,
} from "../lib/tablero";
import { useJobRun } from "../useJobRun";

const MIN_BUSQUEDA = 2; // HU16 CA3: debe coincidir con `min_length` de GET /kedb/buscar

export default function DashboardPage() {
  const tableroOn = useFeature("e05_tablero_coordinador"); // HU15
  const busquedaOn = useFeature("e02_busqueda_kedb"); // HU16
  const cicloVidaOn = useFeature("e03_ciclo_vida"); // HU17
  const [dashboard, setDashboard] = useState<Record<string, unknown> | null>(null);
  const [evaluacion, setEvaluacion] = useState<Record<string, unknown> | null>(null);
  const [articulos, setArticulos] = useState<KedbArticulo[]>([]);
  // Errores de carga por sección: un fallo ya no se disfraza de "—" (HU15 CA2).
  const [dashError, setDashError] = useState("");
  const [evalError, setEvalError] = useState("");
  const [artError, setArtError] = useState("");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [aviso, setAviso] = useState("");
  const jobRun = useJobRun();

  // HU15: el borrador del formulario se aplica al pulsar "Aplicar", no en cada tecla.
  const [borrador, setBorrador] = useState<FiltrosTablero>(FILTROS_VACIOS);
  const [filtros, setFiltros] = useState<FiltrosTablero>(FILTROS_VACIOS);
  const errorRango = validarRango(borrador.desde, borrador.hasta);

  // HU16
  const [searchQ, setSearchQ] = useState("");
  const [searchResults, setSearchResults] = useState<Solucion[] | null>(null);
  const [searchError, setSearchError] = useState("");
  const [buscando, setBuscando] = useState(false);

  const [cambiando, setCambiando] = useState<string | null>(null);

  const categorias = useMemo(
    () => [...new Set(articulos.map((a) => a.categoria))].sort((a, b) => a.localeCompare(b)),
    [articulos]
  );

  const refresh = async (aplicados: FiltrosTablero = filtros) => {
    setCargando(true);
    const [dash, evalMetrics, arts] = await Promise.allSettled([
      tableroOn ? api.getDashboard(queryDeFiltros(aplicados)) : Promise.resolve(null),
      tableroOn ? api.getEvaluacion() : Promise.resolve(null),
      cicloVidaOn || tableroOn ? api.listArticulos() : Promise.resolve([] as KedbArticulo[]),
    ]);
    if (dash.status === "fulfilled") {
      setDashboard(dash.value);
      setDashError("");
    } else {
      setDashError(mensajeDeError(dash.reason));
    }
    if (evalMetrics.status === "fulfilled") {
      setEvaluacion(evalMetrics.value);
      setEvalError("");
    } else {
      setEvalError(mensajeDeError(evalMetrics.reason));
    }
    if (arts.status === "fulfilled") {
      setArticulos(arts.value);
      setArtError("");
    } else {
      setArtError(mensajeDeError(arts.reason));
    }
    setCargando(false);
  };

  useEffect(() => {
    refresh();
    return () => jobRun.cancel();
    // Se recarga cuando llegan los flags del servidor (ADR-0011).
  }, [tableroOn, cicloVidaOn]);

  const aplicarFiltros = async () => {
    if (errorRango) return; // CA3: no se envía un rango inválido
    setFiltros(borrador);
    await refresh(borrador);
  };

  const limpiarFiltros = async () => {
    setBorrador(FILTROS_VACIOS);
    setFiltros(FILTROS_VACIOS);
    await refresh(FILTROS_VACIOS);
  };

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
      setError(mensajeDeError(e));
    }
  };

  const termino = searchQ.trim();
  const busquedaInvalida = termino.length < MIN_BUSQUEDA;

  const handleSearch = async () => {
    if (busquedaInvalida) {
      // HU16 CA3: se pide un término válido antes de ejecutar la búsqueda.
      setSearchError(`Escribe al menos ${MIN_BUSQUEDA} caracteres para buscar.`);
      setSearchResults(null);
      return;
    }
    setSearchError("");
    setBuscando(true);
    try {
      const res = await api.searchKedb(termino);
      setSearchResults(res.results);
    } catch (e) {
      setSearchResults(null);
      setSearchError(mensajeDeError(e));
    } finally {
      setBuscando(false);
    }
  };

  const cambiarEstado = async (a: KedbArticulo, destino: string) => {
    const mensaje = confirmacionDe(destino, a.titulo);
    if (mensaje && !window.confirm(mensaje)) return;
    setError("");
    setAviso("");
    setCambiando(a.articulo_id);
    try {
      const actualizado = await api.cambiarEstadoArticulo(a.articulo_id, destino);
      setArticulos((lista) => lista.map((x) => (x.articulo_id === a.articulo_id ? actualizado : x)));
      setAviso(`«${a.titulo}» pasó a ${actualizado.estado}.`);
      if (tableroOn) await refresh();
    } catch (e) {
      setError(mensajeDeError(e));
    } finally {
      setCambiando(null);
    }
  };

  const cobertura = dashboard?.cobertura_kedb as Record<string, unknown> | undefined;
  const sinDatos = dashboard?.sin_datos === true;
  const tipoEvidencia = String(evaluacion?.tipo_evidencia ?? "proxy");

  return (
    <div className="max-w-5xl mx-auto p-4">
      <div className="navbar page-header page-header-coordinador rounded-lg mb-4 px-4 shadow">
        <h1 className="text-lg font-bold">
          {tableroOn ? "Tablero del Coordinador (HU15)" : "Gestión de conocimiento KEDB"}
        </h1>
      </div>

      <div aria-live="polite" role="status">
        {jobRun.status && (
          <div className="alert alert-info mb-4 text-sm">
            <span>{jobRun.status}</span>
          </div>
        )}
        {aviso && (
          <div className="alert alert-success mb-4 text-sm">
            <span>{aviso}</span>
          </div>
        )}
      </div>
      {error && (
        <div role="alert" className="alert alert-error mb-4 text-sm">
          <span>{error}</span>
        </div>
      )}

      {tableroOn && (
        <>
          <form
            className="card bg-base-100 shadow mb-4"
            aria-labelledby="filtros-titulo"
            onSubmit={(e) => {
              e.preventDefault();
              void aplicarFiltros();
            }}
          >
            <div className="card-body gap-3 p-4 !flex-none">
              <h2 id="filtros-titulo" className="card-title text-sm">
                Filtros
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <label className="form-control">
                  <span className="label-text text-xs mb-1">Categoría</span>
                  <select
                    className="select select-sm select-bordered"
                    aria-label="Filtrar por categoría"
                    value={borrador.categoria}
                    onChange={(e) => setBorrador({ ...borrador, categoria: e.target.value })}
                  >
                    <option value="">Todas</option>
                    {categorias.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="form-control">
                  <span className="label-text text-xs mb-1">Desde</span>
                  <input
                    type="date"
                    aria-label="Fecha de inicio"
                    className="input input-sm input-bordered"
                    value={borrador.desde}
                    max={borrador.hasta || undefined}
                    aria-invalid={errorRango ? true : undefined}
                    aria-describedby={errorRango ? "rango-error" : undefined}
                    onChange={(e) => setBorrador({ ...borrador, desde: e.target.value })}
                  />
                </label>
                <label className="form-control">
                  <span className="label-text text-xs mb-1">Hasta</span>
                  <input
                    type="date"
                    aria-label="Fecha de fin"
                    className="input input-sm input-bordered"
                    value={borrador.hasta}
                    min={borrador.desde || undefined}
                    aria-invalid={errorRango ? true : undefined}
                    aria-describedby={errorRango ? "rango-error" : undefined}
                    onChange={(e) => setBorrador({ ...borrador, hasta: e.target.value })}
                  />
                </label>
              </div>
              {errorRango && (
                <p id="rango-error" role="alert" className="text-xs text-error">
                  {errorRango}
                </p>
              )}
              <div className="flex gap-2">
                <button type="submit" className="btn btn-sm btn-primary" disabled={Boolean(errorRango) || cargando}>
                  Aplicar
                </button>
                <button
                  type="button"
                  className="btn btn-sm btn-ghost"
                  onClick={() => void limpiarFiltros()}
                  disabled={!hayFiltros(borrador) && !hayFiltros(filtros)}
                >
                  Limpiar
                </button>
              </div>
            </div>
          </form>

          {dashError && (
            <div role="alert" className="alert alert-error mb-4 text-sm flex-wrap">
              <span>No se pudo cargar el tablero: {dashError}</span>
              <button className="btn btn-xs" onClick={() => void refresh()}>
                Reintentar
              </button>
            </div>
          )}

          {sinDatos ? (
            <div className="card bg-base-100 shadow mb-4" role="status">
              <div className="card-body items-center text-center gap-2 p-6">
                <p className="font-semibold">Sin datos para estos filtros</p>
                <p className="text-sm opacity-70">
                  No hay artículos KEDB que cumplan la categoría y el rango de fechas elegidos.
                </p>
                <button className="btn btn-sm btn-outline" onClick={() => void limpiarFiltros()}>
                  Limpiar filtros
                </button>
              </div>
            </div>
          ) : (
            <div
              className={`grid grid-cols-1 md:grid-cols-3 gap-4 mb-4 items-start ${cargando ? "opacity-60" : ""}`}
              aria-busy={cargando}
            >
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
                  {(dashboard?.tickets_procesados as number)?.toLocaleString("es-PE") ?? "—"}
                </div>
              </div>
            </div>
          )}

          <section className="card bg-base-100 shadow mb-4" aria-labelledby="evaluacion-titulo">
            <div className="card-body gap-3 p-4 !flex-none">
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <h2 id="evaluacion-titulo" className="card-title text-sm">
                  Métricas de evaluación (C9)
                </h2>
                <button className="btn btn-sm btn-outline" onClick={handleRecompute} disabled={jobRun.busy}>
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
              {evalError && (
                <div role="alert" className="alert alert-warning text-sm py-2">
                  <span>No se pudieron cargar las métricas: {evalError}</span>
                </div>
              )}
              {evaluacion ? (
                <div className="space-y-2 text-sm">
                  <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
                    <span title="Promedio del F1 de las categorías del clasificador (0 a 1; más alto es mejor).">
                      F1 macro: <strong>{evaluacion.f1_macro as number}</strong>
                    </span>
                    <span title="Proporción de consultas en que una solución útil aparece entre las 5 primeras sugeridas (0 a 1).">
                      Recall@5: <strong>{evaluacion.recall_at_5 as number}</strong>
                    </span>
                    <span>Muestra: {evaluacion.muestra_tickets as number} tickets</span>
                    <span
                      className={`badge badge-sm ${tipoEvidencia === "medido" ? "badge-success" : "badge-warning"}`}
                      title={explicarEvidencia(tipoEvidencia)}
                    >
                      {tipoEvidencia}
                    </span>
                  </div>
                  <p className="text-xs opacity-70">{explicarEvidencia(tipoEvidencia)}</p>
                  <p className="text-xs opacity-70">
                    Dataset: {String(evaluacion.dataset ?? "desconocido")}
                    {evaluacion.metodo ? ` · ${String(evaluacion.metodo)}` : ""}
                  </p>
                </div>
              ) : (
                !evalError && (
                  <p className="text-sm opacity-70">Sin caché aún. Usa recalcular para encolar el job.</p>
                )
              )}
            </div>
          </section>
        </>
      )}

      {busquedaOn && (
        <section className="card bg-base-100 shadow mb-4" aria-labelledby="busqueda-titulo">
          <div className="card-body gap-3 p-4 !flex-none">
            <h2 id="busqueda-titulo" className="card-title text-sm">
              Búsqueda directa KEDB (HU16)
            </h2>
            <form
              className="flex gap-2 flex-wrap"
              role="search"
              onSubmit={(e) => {
                e.preventDefault();
                void handleSearch();
              }}
            >
              <input
                type="search"
                className="input input-bordered flex-1 min-w-[12rem]"
                value={searchQ}
                onChange={(e) => setSearchQ(e.target.value)}
                placeholder="Buscar en KEDB..."
                aria-label="Término de búsqueda en la KEDB"
                aria-invalid={searchError ? true : undefined}
                aria-describedby={searchError ? "busqueda-error" : undefined}
              />
              <button type="submit" className="btn btn-primary" disabled={buscando}>
                {buscando ? <span className="loading loading-spinner loading-xs" /> : "Buscar"}
              </button>
            </form>
            <div aria-live="polite">
              {searchError && (
                <p id="busqueda-error" role="alert" className="text-xs text-error">
                  {searchError}
                </p>
              )}
              {searchResults !== null && searchResults.length === 0 && (
                <p className="text-sm opacity-70">No se encontraron resultados para «{termino}».</p>
              )}
              {searchResults !== null && searchResults.length > 0 && (
                <ul className="mt-1 space-y-2 text-sm" aria-label="Resultados de la búsqueda">
                  {searchResults.map((r) => (
                    <li key={r.articulo_o_ticket_id} className="border-b pb-2">
                      {r.titulo || r.articulo_o_ticket_id} — similitud {formatPorcentaje(r.score)}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </section>
      )}

      {cicloVidaOn && (
        <section className="card bg-base-100 shadow" aria-labelledby="ciclo-titulo">
          <div className="card-body gap-3 p-4 !flex-none">
            <h2 id="ciclo-titulo" className="card-title text-sm">
              Gestión ciclo de vida (HU17)
            </h2>
            {artError && (
              <div role="alert" className="alert alert-error text-sm flex-wrap">
                <span>No se pudo cargar el listado: {artError}</span>
                <button className="btn btn-xs" onClick={() => void refresh()}>
                  Reintentar
                </button>
              </div>
            )}
            {!artError && !cargando && articulos.length === 0 && (
              <p className="text-sm opacity-70">Aún no hay artículos KEDB.</p>
            )}
            {articulos.length > 0 && (
              <div className="overflow-x-auto">
                <table className="table table-sm">
                  <caption className="sr-only">
                    Artículos KEDB con su estado y las acciones de ciclo de vida disponibles
                  </caption>
                  <thead>
                    <tr>
                      <th scope="col">ID</th>
                      <th scope="col">Título</th>
                      <th scope="col">Estado</th>
                      <th scope="col">Categoría</th>
                      <th scope="col">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {articulos.map((a) => {
                      const acciones = accionesDe(a.estado);
                      return (
                        <tr key={a.articulo_id}>
                          <td className="font-mono text-xs whitespace-nowrap">{a.articulo_id}</td>
                          <td className="max-w-[14rem]">
                            <span className="line-clamp-2">{a.titulo}</span>
                          </td>
                          <td>
                            <span className={`badge badge-sm ${claseBadgeEstado(a.estado)}`}>{a.estado}</span>
                          </td>
                          <td className="text-xs max-w-[12rem]">
                            <span className="line-clamp-2 whitespace-normal">{a.categoria}</span>
                          </td>
                          <td>
                            <div className="flex flex-wrap gap-1">
                              {acciones.map(({ destino, etiqueta }) => (
                                <button
                                  key={destino}
                                  className="btn btn-xs btn-outline"
                                  disabled={cambiando === a.articulo_id}
                                  aria-label={`${etiqueta}: ${a.titulo}`}
                                  onClick={() => void cambiarEstado(a, destino)}
                                >
                                  {etiqueta}
                                </button>
                              ))}
                              {a.estado === "borrador" && (
                                <Link className="link link-primary text-xs" to="/experto">
                                  Validar en Experto
                                </Link>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
