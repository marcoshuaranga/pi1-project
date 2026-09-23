import { useEffect, useRef, useState } from "react";
import {
  api,
  newTicketId,
  processTicketViaWs,
  subscribePipelineWs,
  Solucion,
  TicketResponse,
} from "../api";
import { usePipelineNavGuard } from "../App";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

const STEPS = [
  "C1 Anonimización",
  "C3 Clasificación",
  "C4 Priorización",
  "C5 Recuperación RAG",
];

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

const PENDING_PREFIX = "operator-pipeline-pending:";
const HISTORY_KEY = "operator-ticket-history";
const HISTORY_LIMIT = 12;
const RESUME_POLL_MS = 2_000;
const RESUME_TIMEOUT_MS = 60_000;

type PendingPipeline = {
  ticketId: string;
  texto: string;
  startedAt: number;
  activeStep: number;
};

type HistoryEntry = { ticketId: string; texto: string; startedAt: number };

// Pending pipeline state is namespaced per ticket_id (not one global slot) so
// several tickets can each be tracked/resumed independently via their own
// /tickets/:ticketId route, instead of a new ticket overwriting the last one.
function readPending(ticketId: string): PendingPipeline | null {
  try {
    const raw = sessionStorage.getItem(PENDING_PREFIX + ticketId);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as PendingPipeline;
    if (!parsed?.ticketId || !parsed?.texto) return null;
    return {
      ...parsed,
      activeStep: typeof parsed.activeStep === "number" ? parsed.activeStep : 0,
    };
  } catch {
    return null;
  }
}

function writePending(pending: PendingPipeline) {
  sessionStorage.setItem(PENDING_PREFIX + pending.ticketId, JSON.stringify(pending));
}

function patchPending(ticketId: string, patch: Partial<PendingPipeline>) {
  const current = readPending(ticketId);
  if (!current) return;
  writePending({ ...current, ...patch });
}

function clearPending(ticketId: string) {
  sessionStorage.removeItem(PENDING_PREFIX + ticketId);
}

function readHistory(): HistoryEntry[] {
  try {
    const parsed = JSON.parse(sessionStorage.getItem(HISTORY_KEY) ?? "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function pushHistory(entry: HistoryEntry) {
  const next = [entry, ...readHistory().filter((h) => h.ticketId !== entry.ticketId)].slice(
    0,
    HISTORY_LIMIT
  );
  sessionStorage.setItem(HISTORY_KEY, JSON.stringify(next));
  return next;
}

/** Map orchestrator agent names to step index (inicio/fin). */
function stepIndexForAgent(agente?: string): number {
  switch (agente) {
    case "Orquestador":
      return 0;
    case "Clasificador":
      return 1;
    case "Priorizador":
      return 2;
    case "RAG":
      return 3;
    default:
      return -1;
  }
}

export default function OperatorPage() {
  const { setPipelineBusy } = usePipelineNavGuard();
  const location = useLocation();
  const navigate = useNavigate();
  const { ticketId: routeTicketId } = useParams<{ ticketId?: string }>();
  const [texto, setTexto] = useState(
    "Impresora Kyocera 7003 no imprime, necesito que la configuren de nuevo"
  );
  const [loading, setLoading] = useState(false);
  const [resuming, setResuming] = useState(false);
  const [pendingTicketId, setPendingTicketId] = useState<string | null>(null);
  const [result, setResult] = useState<TicketResponse | null>(null);
  const [activeStep, setActiveStep] = useState(-1);
  const [error, setError] = useState("");
  const [correccion, setCorreccion] = useState("");
  const [feedbackMsg, setFeedbackMsg] = useState("");
  const [nuevaSolucion, setNuevaSolucion] = useState("");
  const [expandedSolucionId, setExpandedSolucionId] = useState<string | null>(null);
  const [feedbackById, setFeedbackById] = useState<
    Record<string, "util" | "no_util">
  >({});
  const [feedbackBusyId, setFeedbackBusyId] = useState<string | null>(null);
  const [viaWs, setViaWs] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");
  const [history, setHistory] = useState<HistoryEntry[]>(() => readHistory());
  const abortRef = useRef<AbortController | null>(null);
  const resumeAbortRef = useRef<AbortController | null>(null);

  const advanceStep = (ticketId: string, agente?: string) => {
    if (!agente) return;
    const idx = stepIndexForAgent(agente);
    if (idx < 0) return;
    setActiveStep((prev) => {
      const next = Math.max(prev, idx);
      patchPending(ticketId, { activeStep: next });
      return next;
    });
  };

  const finishWithResult = (ticketId: string, ticket: TicketResponse, fromWs: boolean) => {
    clearPending(ticketId);
    setResult(ticket);
    setExpandedSolucionId(null);
    setFeedbackById({});
    setFeedbackBusyId(null);
    setFeedbackMsg("");
    setActiveStep(STEPS.length);
    setViaWs(fromWs);
    setStatusMsg(
      fromWs
        ? "Pipeline completado (eventos en vivo)."
        : "Resultado recuperado: el pipeline terminó en el servidor."
    );
    setLoading(false);
    setResuming(false);
    setPendingTicketId(null);
  };

  useEffect(() => {
    setPipelineBusy(loading);
    return () => setPipelineBusy(false);
  }, [loading, setPipelineBusy]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
      resumeAbortRef.current?.abort();
    };
  }, []);

  const handleSubmit = async (text: string, ticketId: string) => {
    abortRef.current?.abort();
    resumeAbortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;

    writePending({ ticketId, texto: text, startedAt: Date.now(), activeStep: 0 });
    setHistory(pushHistory({ ticketId, texto: text, startedAt: Date.now() }));

    setLoading(true);
    setResuming(false);
    setPendingTicketId(ticketId);
    setError("");
    setResult(null);
    setActiveStep(0);
    setViaWs(false);
    setFeedbackMsg("");
    setStatusMsg(`Pipeline en curso (${ticketId})…`);
    try {
      const res = await processTicketViaWs(text, {
        ticketId,
        signal: ac.signal,
        onEvent: (evento) => {
          if (evento.tipo === "inicio" || evento.tipo === "fin") {
            advanceStep(ticketId, evento.agente);
          }
        },
      });
      if (ac.signal.aborted) return;
      finishWithResult(ticketId, res, true);
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") {
        // Salida de página: pending queda para reanudar.
        return;
      }
      try {
        setActiveStep(0);
        const res = await api.submitTicket(text);
        if (ac.signal.aborted) return;
        finishWithResult(ticketId, res, false);
      } catch (err) {
        clearPending(ticketId);
        setError(String(err));
        setActiveStep(-1);
        setStatusMsg("");
        setPendingTicketId(null);
        setLoading(false);
        setResuming(false);
      }
    }
  };

  /** Reabrir WS (pasos restantes) + polling REST (status-aware) por si ya terminó. */
  const resumeTicket = async (
    ticketId: string,
    ac: AbortController,
    pending: PendingPipeline | null
  ) => {
    setLoading(true);
    setResuming(true);
    setPendingTicketId(ticketId);
    setError("");
    setResult(null);
    setActiveStep(pending ? Math.max(0, pending.activeStep) : 0);
    setStatusMsg(
      pending
        ? `Pipeline en ejecución en el servidor (${ticketId}). Reconectado a los pasos en vivo…`
        : `Comprobando estado del ticket ${ticketId}…`
    );

    let settled = false;
    const complete = (ticket: TicketResponse, fromWs: boolean) => {
      if (settled || ac.signal.aborted) return;
      settled = true;
      ac.abort();
      finishWithResult(ticketId, ticket, fromWs);
    };
    const fail = (message: string) => {
      if (settled || ac.signal.aborted) return;
      settled = true;
      clearPending(ticketId);
      setError(message);
      setStatusMsg("");
      setLoading(false);
      setResuming(false);
      setPendingTicketId(null);
      setActiveStep(-1);
    };

    subscribePipelineWs(ticketId, {
      signal: ac.signal,
      onEvent: (evento) => {
        if (evento.tipo === "inicio" || evento.tipo === "fin") {
          advanceStep(ticketId, evento.agente);
        }
      },
      onResult: (ticket) => complete(ticket, true),
      onError: (message) => fail(message),
    });

    // Known locally as pending (this tab started it, or a previous poll already
    // confirmed "procesando" server-side): a 404 here would be a real failure,
    // not "still running", so we only keep quietly retrying while that holds.
    let knownRunning = Boolean(pending);
    const deadline = Date.now() + RESUME_TIMEOUT_MS;
    while (Date.now() < deadline) {
      if (ac.signal.aborted || settled) return;
      try {
        const status = await api.getTicket(ticketId);
        if (status.status === "completado" && status.result) {
          complete(status.result, false);
          return;
        }
        if (status.status === "error") {
          fail(status.error ?? "El pipeline falló en el servidor.");
          return;
        }
        if (!knownRunning) {
          knownRunning = true;
          writePending({
            ticketId,
            texto: pending?.texto ?? "",
            startedAt: Date.now(),
            activeStep: 0,
          });
        }
      } catch {
        if (!knownRunning) {
          fail(`No se encontró el ticket ${ticketId}.`);
          return;
        }
        // else: genuine but transient race right at start-up — keep polling.
      }
      await new Promise<void>((resolve, reject) => {
        const t = setTimeout(resolve, RESUME_POLL_MS);
        ac.signal.addEventListener(
          "abort",
          () => {
            clearTimeout(t);
            reject(new DOMException("abort", "AbortError"));
          },
          { once: true }
        );
      }).catch(() => undefined);
    }
    if (ac.signal.aborted || settled) return;
    fail(`No se pudo recuperar ${ticketId}. El pipeline puede haber fallado; envía uno nuevo si hace falta.`);
  };

  /** Cada ticket vive en su propia ruta /tickets/:ticketId — cambiar de ticket
   * reinicia la vista y reengancha (WS + polling) al ticket de la URL, sin
   * cancelar el procesamiento en curso de los demás (sigue en el servidor). */
  useEffect(() => {
    abortRef.current?.abort();
    resumeAbortRef.current?.abort();
    setLoading(false);
    setResuming(false);
    setPendingTicketId(null);
    setResult(null);
    setActiveStep(-1);
    setError("");
    setStatusMsg("");
    setViaWs(false);
    setCorreccion("");
    setFeedbackMsg("");
    setNuevaSolucion("");
    setExpandedSolucionId(null);
    setFeedbackById({});
    setFeedbackBusyId(null);

    if (!routeTicketId) return;

    const submitText = (location.state as { submitText?: string } | null)?.submitText;
    if (submitText) {
      setTexto(submitText);
      // Absolute path — "." here has resolved unpredictably given OperatorPage
      // is mounted from two different route entries (index and /tickets/:id).
      navigate(`/tickets/${routeTicketId}`, { replace: true, state: null });
      void handleSubmit(submitText, routeTicketId);
      return;
    }

    // Switching directly between two /tickets/:id routes doesn't remount this
    // component, so without this the textarea would keep showing whichever
    // ticket's text was there before — clear it when this ticket has none
    // recorded locally (e.g. opened fresh from "Tickets recientes").
    const pending = readPending(routeTicketId);
    setTexto(pending?.texto ?? "");

    const ac = new AbortController();
    resumeAbortRef.current = ac;
    void resumeTicket(routeTicketId, ac, pending);
    return () => ac.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- runs once per ticket id
  }, [routeTicketId]);

  const startNewTicket = (submittedText = texto) => {
    const text = submittedText.trim();
    if (text.length < 5) {
      setError("Describe el problema con al menos 5 caracteres.");
      return;
    }
    setError("");
    const ticketId = newTicketId();
    navigate(`/tickets/${ticketId}`, { state: { submitText: text } });
  };

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
