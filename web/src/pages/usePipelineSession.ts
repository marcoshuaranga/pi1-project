import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { api, newTicketId, processTicketViaWs, subscribePipelineWs, TicketResponse } from "../api";
import { usePipelineNavGuard } from "../App";

export const STEPS = [
  "C1 Anonimización",
  "C3 Clasificación",
  "C4 Priorización",
  "C5 Recuperación RAG",
];

// Positional pairing with STEPS: STEP_AGENTS[i] is the AgenteTipo (app/schemas)
// whose inicio/fin event advances to STEPS[i]. GeneradorKEDB has no entry here
// on purpose — KEDB generation isn't part of this per-ticket pipeline view.
const STEP_AGENTS = ["Orquestador", "Clasificador", "Priorizador", "RAG"] as const;

function stepIndexForAgent(agente?: string): number {
  if (!agente) return -1;
  return STEP_AGENTS.indexOf(agente as (typeof STEP_AGENTS)[number]);
}

const PENDING_PREFIX = "operator-pipeline-pending:";
const HISTORY_KEY = "operator-ticket-history";
const HISTORY_LIMIT = 12;
const RESUME_POLL_MS = 2_000;
const RESUME_TIMEOUT_MS = 60_000;
const DEFAULT_TEXTO =
  "Impresora Kyocera 7003 no imprime, necesito que la configuren de nuevo";

type PendingPipeline = {
  ticketId: string;
  texto: string;
  startedAt: number;
  activeStep: number;
};

export type HistoryEntry = { ticketId: string; texto: string; startedAt: number };

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

/**
 * Owns a ticket's pipeline run: submit/resume over WS + REST fallback,
 * sessionStorage-backed pending state so a refresh can reconnect, and step
 * progress. Independent of any UI built on top of the result it produces.
 */
export function usePipelineSession() {
  const { setPipelineBusy } = usePipelineNavGuard();
  const location = useLocation();
  const navigate = useNavigate();
  const { ticketId: routeTicketId } = useParams<{ ticketId?: string }>();
  const [texto, setTexto] = useState(DEFAULT_TEXTO);
  const [loading, setLoading] = useState(false);
  const [resuming, setResuming] = useState(false);
  const [pendingTicketId, setPendingTicketId] = useState<string | null>(null);
  const [result, setResult] = useState<TicketResponse | null>(null);
  const [activeStep, setActiveStep] = useState(-1);
  const [error, setError] = useState("");
  const [viaWs, setViaWs] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");
  const [history, setHistory] = useState<HistoryEntry[]>(() => readHistory());
  const abortRef = useRef<AbortController | null>(null);
  const resumeAbortRef = useRef<AbortController | null>(null);

  const advanceStep = (ticketId: string, agente?: string) => {
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

  return {
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
  };
}
