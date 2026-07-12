import { useEffect, useRef, useState } from "react";
import {
  api,
  newTicketId,
  processTicketViaWs,
  subscribePipelineWs,
  TicketResponse,
} from "../api";
import { usePipelineNavGuard } from "../App";

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

const PENDING_KEY = "operator-pipeline-pending";
const RESUME_POLL_MS = 2_000;
const RESUME_TIMEOUT_MS = 60_000;

type PendingPipeline = {
  ticketId: string;
  texto: string;
  startedAt: number;
  activeStep: number;
};

function readPending(): PendingPipeline | null {
  try {
    const raw = sessionStorage.getItem(PENDING_KEY);
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
  sessionStorage.setItem(PENDING_KEY, JSON.stringify(pending));
}

function patchPending(patch: Partial<PendingPipeline>) {
  const current = readPending();
  if (!current) return;
  writePending({ ...current, ...patch });
}

function clearPending() {
  sessionStorage.removeItem(PENDING_KEY);
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
  const [viaWs, setViaWs] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");
  const abortRef = useRef<AbortController | null>(null);
  const resumeAbortRef = useRef<AbortController | null>(null);

  const advanceStep = (agente?: string) => {
    if (!agente) return;
    const idx = stepIndexForAgent(agente);
    if (idx < 0) return;
    setActiveStep((prev) => {
      const next = Math.max(prev, idx);
      patchPending({ activeStep: next });
      return next;
    });
  };

  const finishWithResult = (ticket: TicketResponse, fromWs: boolean) => {
    clearPending();
    setResult(ticket);
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

  /** Al volver: reabrir WS (pasos restantes) + polling REST por si ya terminó. */
  useEffect(() => {
    const pending = readPending();
    if (!pending) return;

    setTexto(pending.texto);
    setLoading(true);
    setResuming(true);
    setPendingTicketId(pending.ticketId);
    setActiveStep(Math.max(0, pending.activeStep));
    setError("");
    setResult(null);
    setStatusMsg(
      `Pipeline en ejecución en el servidor (${pending.ticketId}). Reconectado a los pasos en vivo…`
    );

    resumeAbortRef.current?.abort();
    const ac = new AbortController();
    resumeAbortRef.current = ac;
    let settled = false;

    const complete = (ticket: TicketResponse, fromWs: boolean) => {
      if (settled || ac.signal.aborted) return;
      settled = true;
      ac.abort();
      finishWithResult(ticket, fromWs);
    };

    subscribePipelineWs(pending.ticketId, {
      signal: ac.signal,
      onEvent: (evento) => {
        if (evento.tipo === "inicio" || evento.tipo === "fin") {
          advanceStep(evento.agente);
        }
      },
      onResult: (ticket) => complete(ticket, true),
    });

    const poll = async () => {
      const deadline = Date.now() + RESUME_TIMEOUT_MS;
      while (Date.now() < deadline) {
        if (ac.signal.aborted || settled) return;
        try {
          const ticket = await api.getTicket(pending.ticketId);
          complete(ticket, false);
          return;
        } catch {
          /* 404: aún corriendo */
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
      setError(
        `No se pudo recuperar ${pending.ticketId}. El pipeline puede haber fallado; envía de nuevo si hace falta.`
      );
      setStatusMsg("");
      setLoading(false);
      setResuming(false);
      setPendingTicketId(null);
      setActiveStep(-1);
      clearPending();
    };

    void poll();
    return () => ac.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- mount-only resume
  }, []);

  const handleSubmit = async () => {
    abortRef.current?.abort();
    resumeAbortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;

    const ticketId = newTicketId();
    writePending({ ticketId, texto, startedAt: Date.now(), activeStep: 0 });

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
      const res = await processTicketViaWs(texto, {
        ticketId,
        signal: ac.signal,
        onEvent: (evento) => {
          if (evento.tipo === "inicio" || evento.tipo === "fin") {
            advanceStep(evento.agente);
          }
        },
      });
      if (ac.signal.aborted) return;
      finishWithResult(res, true);
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") {
        // Salida de página: pending queda para reanudar.
        return;
      }
      try {
        setActiveStep(0);
        const res = await api.submitTicket(texto);
        if (ac.signal.aborted) return;
        finishWithResult(res, false);
      } catch (err) {
        clearPending();
        setError(String(err));
        setActiveStep(-1);
        setStatusMsg("");
        setPendingTicketId(null);
        setLoading(false);
        setResuming(false);
      }
    }
  };

  const handleCorreccion = async () => {
    if (!result || !correccion) return;
    await api.correctCategoria(result.ticket_id, correccion);
    setResult({ ...result, categoria: correccion });
    setCorreccion("");
  };

  const handleFeedback = async (articuloId: string, util: boolean) => {
    if (!result) return;
    await api.feedback(result.ticket_id, { articulo_id: articuloId, util });
    setFeedbackMsg(util ? "¡Gracias por tu retroalimentación!" : "Registrado.");
  };

  const handleNuevaSolucion = async () => {
    if (!result || !nuevaSolucion) return;
    await api.feedback(result.ticket_id, { nueva_solucion: nuevaSolucion });
    setFeedbackMsg("Nueva solución registrada como candidata KEDB (HU12).");
    setNuevaSolucion("");
  };

  return (
    <div className="max-w-5xl mx-auto p-4">
      <div className="navbar bg-primary text-primary-content rounded-lg mb-4 px-4 shadow">
        <span className="text-lg font-bold">Mesa de Ayuda OITSI-MTC</span>
        <span className="ml-4 badge badge-accent">Asistente IA activo</span>
      </div>

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
              onClick={handleSubmit}
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
                    <div key={s.articulo_o_ticket_id} className="border rounded-lg p-3 text-sm">
                      <div className="flex justify-between items-center">
                        <span className="badge badge-ghost badge-sm">{s.tipo}</span>
                        <span className="text-xs font-mono">similitud {(s.score * 100).toFixed(0)}%</span>
                      </div>
                      <p className="font-medium mt-1">{s.titulo || s.articulo_o_ticket_id}</p>
                      <p className="text-base-content/70 mt-1 text-xs">{s.solucion}</p>
                      <div className="flex gap-2 mt-2">
                        <button
                          className="btn btn-xs btn-success"
                          onClick={() => handleFeedback(s.articulo_o_ticket_id, true)}
                        >
                          Útil (HU11)
                        </button>
                        <button
                          className="btn btn-xs btn-ghost"
                          onClick={() => handleFeedback(s.articulo_o_ticket_id, false)}
                        >
                          No útil
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              {feedbackMsg && <p className="text-success text-xs mt-2">{feedbackMsg}</p>}
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
