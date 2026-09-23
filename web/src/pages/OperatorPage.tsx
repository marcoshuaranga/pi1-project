import { useEffect, useState } from "react";
import { api, Solucion } from "../api";
import { Link } from "react-router-dom";
import { STEPS, usePipelineSession } from "./usePipelineSession";

const FACTOR_LABELS: Record<string, string> = {
  impacto_servicio_ciudadano: "Impacto servicio ciudadano",
  recurrencia_historica: "Recurrencia histórica",
  sla_asociado: "SLA asociado",
  criticidad_solicitante: "Criticidad solicitante",
  tipo_incidencia: "Tipo de incidencia",
};

const PREVIEW_CHARS = 110;

function SolucionCard({
  solucion,
  expanded,
  onToggle,
  onFeedback,
  feedbackState,
  feedbackBusy,
}: {
  solucion: Solucion;
  expanded: boolean;
  onToggle: () => void;
  onFeedback: (util: boolean) => void;
  feedbackState: "util" | "no_util" | null;
  feedbackBusy: boolean;
}) {
  const texto = solucion.solucion?.trim() ?? "";
  const preview =
    texto.length > PREVIEW_CHARS ? `${texto.slice(0, PREVIEW_CHARS).trimEnd()}…` : texto;
  const voted = feedbackState !== null;

  return (
    <div
      className={`border rounded-lg p-3 text-sm transition-colors ${
        expanded ? "border-success/50 bg-success/5" : "border-base-300"
      }`}
    >
      <div className="flex justify-between items-center gap-2">
        <span className="badge badge-ghost badge-sm">{solucion.tipo}</span>
        <span className="text-xs font-mono shrink-0">
          similitud {(solucion.score * 100).toFixed(0)}%
        </span>
      </div>
      <p className="font-medium mt-1">{solucion.titulo || solucion.articulo_o_ticket_id}</p>

      {texto && (
        <div className="mt-2">
          {!expanded ? (
            <div className="rounded-md bg-base-200/60 overflow-hidden">
              <div className="px-3 pt-2 pb-1">
                <p className="text-[10px] uppercase tracking-wide text-base-content/50 mb-1">
                  Solución · vista previa
                </p>
                <p className="text-sm text-base-content/70 leading-relaxed line-clamp-2">
                  {preview}
                </p>
              </div>
              <button
                type="button"
                onClick={onToggle}
                className="w-full flex items-center justify-center gap-1.5 border-t border-base-300/70 bg-base-200/80 px-3 py-2 text-xs font-semibold text-success hover:bg-success/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-success/40"
                aria-expanded={false}
              >
                Ampliar detalle
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className="w-3.5 h-3.5"
                  aria-hidden
                >
                  <path
                    fillRule="evenodd"
                    d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z"
                    clipRule="evenodd"
                  />
                </svg>
              </button>
            </div>
          ) : (
            <div className="rounded-md border border-success/30 bg-base-100 overflow-hidden">
              <div className="flex items-center justify-between gap-2 px-3 pt-2">
                <p className="text-[10px] uppercase tracking-wide text-base-content/50">
                  Solución · detalle
                </p>
                <button
                  type="button"
                  onClick={onToggle}
                  className="btn btn-ghost btn-xs text-base-content/60"
                  aria-expanded={true}
                >
                  Ocultar
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    className="w-3.5 h-3.5"
                    aria-hidden
                  >
                    <path
                      fillRule="evenodd"
                      d="M14.78 11.78a.75.75 0 0 1-1.06 0L10 8.06l-3.72 3.72a.75.75 0 1 1-1.06-1.06l4.25-4.25a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06Z"
                      clipRule="evenodd"
                    />
                  </svg>
                </button>
              </div>
              <p className="px-3 pb-3 pt-1 text-sm text-base-content/80 whitespace-pre-wrap break-words leading-relaxed">
                {texto}
              </p>
            </div>
          )}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2 mt-2">
        <button
          type="button"
          className={`btn btn-xs ${
            feedbackState === "util" ? "btn-success" : "btn-outline btn-success"
          }`}
          disabled={feedbackBusy || voted}
          onClick={() => onFeedback(true)}
        >
          {feedbackBusy && !voted ? (
            <span className="loading loading-spinner loading-xs" />
          ) : null}
          Útil (HU11)
        </button>
        <button
          type="button"
          className={`btn btn-xs ${
            feedbackState === "no_util" ? "btn-error" : "btn-ghost"
          }`}
          disabled={feedbackBusy || voted}
          onClick={() => onFeedback(false)}
        >
          No útil
        </button>
        {feedbackState === "util" && (
          <span className="text-xs text-success font-medium">Marcada como útil</span>
        )}
        {feedbackState === "no_util" && (
          <span className="text-xs text-error font-medium">Marcada como no útil</span>
        )}
      </div>
    </div>
  );
}

export default function OperatorPage() {
  const {
    routeTicketId,
    texto,
    setTexto,
    loading,
    resuming,
    pendingTicketId,
    result,
    setResult,
    activeStep,
    error,
    setError,
    viaWs,
    statusMsg,
    history,
    readPending,
    startNewTicket,
  } = usePipelineSession();

  // Review-only UI: annotating/correcting a result once the pipeline session
  // has produced one. Independent of how that result was obtained.
  const [correccion, setCorreccion] = useState("");
  const [feedbackMsg, setFeedbackMsg] = useState("");
  const [nuevaSolucion, setNuevaSolucion] = useState("");
  const [expandedSolucionId, setExpandedSolucionId] = useState<string | null>(null);
  const [feedbackById, setFeedbackById] = useState<Record<string, "util" | "no_util">>({});
  const [feedbackBusyId, setFeedbackBusyId] = useState<string | null>(null);

  // Fires both when the route's ticket changes (result resets to null) and
  // when a new result arrives for it — the two moments this review state
  // needs to forget whatever the previous ticket left behind. Keyed on
  // ticket_id, not the result object, so handleCorreccion's optimistic
  // setResult (same ticket, new object) doesn't wipe feedback in progress.
  useEffect(() => {
    setCorreccion("");
    setFeedbackMsg("");
    setNuevaSolucion("");
    setExpandedSolucionId(null);
    setFeedbackById({});
    setFeedbackBusyId(null);
  }, [routeTicketId, result?.ticket_id]);

  const handleCorreccion = async () => {
    if (!result || !correccion) return;
    await api.correctCategoria(result.ticket_id, correccion);
    setResult({ ...result, categoria: correccion });
    setCorreccion("");
  };

  const handleFeedback = async (articuloId: string, util: boolean) => {
    if (!result || feedbackById[articuloId] || feedbackBusyId) return;
    setFeedbackBusyId(articuloId);
    setFeedbackMsg("");
    try {
      await api.feedback(result.ticket_id, { articulo_id: articuloId, util });
      setFeedbackById((prev) => ({
        ...prev,
        [articuloId]: util ? "util" : "no_util",
      }));
      setFeedbackMsg(
        util
          ? "Feedback registrado: solución marcada como útil."
          : "Feedback registrado: solución marcada como no útil."
      );
    } catch (err) {
      setError(`No se pudo registrar el feedback: ${String(err)}`);
    } finally {
      setFeedbackBusyId(null);
    }
  };

  const handleNuevaSolucion = async () => {
    if (!result || !nuevaSolucion) return;
    await api.feedback(result.ticket_id, { nueva_solucion: nuevaSolucion });
    setFeedbackMsg("Nueva solución registrada como candidata KEDB (HU12).");
    setNuevaSolucion("");
  };

  return (
    <div className="max-w-5xl mx-auto p-4">
      <div className="navbar page-header bg-primary text-primary-content rounded-lg mb-4 px-4 shadow">
        <span className="text-lg font-bold">Mesa de Ayuda OITSI-MTC</span>
        <span className="ml-4 badge badge-accent">Asistente IA activo</span>
        {routeTicketId && (
          <Link to="/" className="btn btn-ghost btn-xs ml-auto text-primary-content">
            + Nuevo ticket
          </Link>
        )}
      </div>

      {history.length > 0 && (
        <div className="card bg-base-100 shadow mb-4">
          <div className="card-body gap-2 p-4 !flex-none">
            <h2 className="card-title text-sm">Tickets recientes</h2>
            <ul className="flex flex-col gap-1">
              {history.map((h) => {
                const isCurrent = h.ticketId === routeTicketId;
                const stillPending = Boolean(readPending(h.ticketId));
                return (
                  <li key={h.ticketId}>
                    <Link
                      to={`/tickets/${h.ticketId}`}
                      className={`flex items-center justify-between gap-2 rounded-md px-2 py-1.5 text-xs hover:bg-base-200 ${
                        isCurrent ? "bg-base-200 font-semibold" : ""
                      }`}
                    >
                      <span className="truncate">{h.texto}</span>
                      <span className="flex items-center gap-1 shrink-0">
                        <span className="badge badge-ghost badge-xs font-mono">{h.ticketId}</span>
                        {stillPending && !isCurrent && (
                          <span className="badge badge-warning badge-xs">en curso</span>
                        )}
                      </span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      )}

      {statusMsg && (
        <div className={`alert mb-4 text-sm py-2 ${loading ? "alert-warning" : "alert-info"}`}>
          {loading && <span className="loading loading-spinner loading-sm" />}
          <span>{statusMsg}</span>
          {pendingTicketId && loading && (
            <span className="badge badge-ghost badge-sm font-mono">{pendingTicketId}</span>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
        <div className="card bg-base-100 shadow self-start w-full">
          <div className="card-body gap-3 p-4 !flex-none">
            <h2 className="card-title text-sm">Nuevo ticket</h2>
            <textarea
              className="textarea textarea-bordered w-full h-32"
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              placeholder="Describe el problema del usuario..."
              disabled={loading}
            />
            <button
              className="btn btn-primary"
              onClick={() => startNewTicket()}
              disabled={loading || texto.length < 5}
            >
              {loading ? (resuming ? "Reanudando pipeline…" : "Procesando...") : "Enviar ticket"}
            </button>
            {error && <p className="text-error text-sm">{error}</p>}
          </div>
        </div>

        <div className="card bg-base-100 shadow border-l-4 border-primary self-start w-full">
          <div className="card-body gap-3 p-4 !flex-none">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="card-title text-sm text-primary mb-0">Estado del pipeline (C7)</h2>
              {loading && (
                <span className="badge badge-warning badge-sm gap-1">
                  <span className="loading loading-spinner loading-xs" />
                  {resuming ? "En curso (reconectado)" : "En curso"}
                </span>
              )}
            </div>
            <ul className="steps steps-vertical text-xs">
              {STEPS.map((step, i) => {
                const current = loading && i === Math.min(activeStep, STEPS.length - 1);
                return (
                  <li
                    key={step}
                    className={`step ${i <= activeStep ? "step-primary" : ""} ${current ? "font-semibold" : ""}`}
                  >
                    <span className="inline-flex items-center gap-2">
                      {step}
                      {current && <span className="loading loading-spinner loading-xs" />}
                    </span>
                  </li>
                );
              })}
            </ul>
            {loading && (
              <p className="text-xs text-base-content/60 mt-2">
                {resuming
                  ? "El trabajo sigue en el servidor. Se muestran el último paso conocido y los eventos nuevos."
                  : "Procesando agentes en vivo vía WebSocket."}
              </p>
            )}
            {result && !loading && (
              <p className="text-xs text-base-content/50 mt-2">
                {viaWs ? "Eventos en vivo vía WebSocket" : "Resultado vía REST / reanudación"}
              </p>
            )}
          </div>
        </div>
      </div>

      {result && (
        <div className="mt-4 grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
          <div className="card bg-base-100 shadow border-l-4 border-info self-start w-full">
            <div className="card-body gap-3 p-4 !flex-none">
              <div>
                <h2 className="card-title text-sm text-info">Sugerencias del Agente IA</h2>
                <p className="text-xs text-base-content/60 mt-0.5">Ticket: {result.ticket_id}</p>
              </div>

              <div>
                <p className="text-xs font-semibold uppercase text-base-content/60">Clasificación (C3)</p>
                <div className="mt-1 flex flex-wrap items-start gap-2">
                  <span className="badge badge-info h-auto min-h-6 whitespace-normal text-left py-1.5 px-2 leading-snug">
                    {result.categoria}
                  </span>
                  <span className="text-xs shrink-0 pt-1">
                    confianza {(result.confianza * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="mt-2 flex gap-2">
                  <input
                    className="input input-bordered input-sm flex-1"
                    placeholder="Corregir categoría (HU03)"
                    value={correccion}
                    onChange={(e) => setCorreccion(e.target.value)}
                  />
                  <button className="btn btn-sm btn-outline shrink-0" onClick={handleCorreccion}>
                    Corregir
                  </button>
                </div>
              </div>

              <div>
                <p className="text-xs font-semibold uppercase text-base-content/60">Prioridad (C4)</p>
                <span className="badge badge-warning mt-1">{result.prioridad}</span>
                {result.justificacion_prioridad && (
                  <ul className="mt-2 space-y-0.5 text-xs text-base-content/70">
                    {Object.entries(result.justificacion_prioridad).map(([k, v]) => (
                      <li key={k} className="flex justify-between gap-4">
                        <span>{FACTOR_LABELS[k] ?? k}</span>
                        <span className="font-mono tabular-nums">{(v * 100).toFixed(0)}%</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </div>

          <div className="card bg-base-100 shadow border-l-4 border-success self-start w-full">
            <div className="card-body gap-3 p-4 !flex-none">
              <h2 className="card-title text-sm text-success">Top-5 Soluciones (C5 RAG)</h2>
              {result.soluciones.length === 0 ? (
                <p className="text-sm text-base-content/60">Sin soluciones similares encontradas.</p>
              ) : (
                <div className="space-y-3">
                  {result.soluciones.map((s) => (
                    <SolucionCard
                      key={s.articulo_o_ticket_id}
                      solucion={s}
                      expanded={expandedSolucionId === s.articulo_o_ticket_id}
                      onToggle={() =>
                        setExpandedSolucionId((prev) =>
                          prev === s.articulo_o_ticket_id ? null : s.articulo_o_ticket_id
                        )
                      }
                      onFeedback={(util) => handleFeedback(s.articulo_o_ticket_id, util)}
                      feedbackState={feedbackById[s.articulo_o_ticket_id] ?? null}
                      feedbackBusy={feedbackBusyId === s.articulo_o_ticket_id}
                    />
                  ))}
                </div>
              )}
              {feedbackMsg && (
                <div className="alert alert-success text-xs py-2 mt-2">
                  <span>{feedbackMsg}</span>
                </div>
              )}
              <div className="mt-2 border-t pt-3">
                <p className="text-xs font-semibold">Nueva solución (HU12)</p>
                <textarea
                  className="textarea textarea-bordered textarea-sm w-full mt-1"
                  placeholder="Documentar solución no sugerida..."
                  value={nuevaSolucion}
                  onChange={(e) => setNuevaSolucion(e.target.value)}
                />
                <button className="btn btn-xs btn-outline mt-1" onClick={handleNuevaSolucion}>
                  Registrar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
