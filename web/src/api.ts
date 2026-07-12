// In Docker/production the browser talks to same origin (/api → nginx → api).
// Override with VITE_API_URL only for local Vite dev (e.g. http://localhost:8000).
const API_URL = import.meta.env.VITE_API_URL ?? "/api";

export interface Solucion {
  articulo_o_ticket_id: string;
  score: number;
  tipo: string;
  titulo?: string;
  solucion?: string;
}

export interface TicketResponse {
  ticket_id: string;
  categoria: string;
  confianza: number;
  prioridad: string;
  justificacion_prioridad?: Record<string, number>;
  soluciones: Solucion[];
}

export interface KedbArticulo {
  articulo_id: string;
  titulo: string;
  categoria: string;
  sintoma: string;
  causa: string;
  solucion: string;
  tickets_fuente: string[];
  estado: string;
  fecha_generacion: string;
  aplicable_a?: string;
}

export interface KedbDoc {
  articulo_id: string;
  filename: string;
  titulo: string;
  estado: string;
  categoria: string;
  path?: string;
}

export interface JobStatus {
  job_id: string;
  status: string;
  task?: string;
  success?: boolean;
  result?: unknown;
  error?: string;
}

export interface JobEnqueue {
  job_id: string;
  status: string;
  task: string;
}

const REQUEST_TIMEOUT_MS = 15_000;
const JOB_POLL_INTERVAL_MS = 5_000;
const WS_PROCESS_TIMEOUT_MS = 45_000;

function wsBaseUrl(): string {
  const configured = import.meta.env.VITE_API_URL as string | undefined;
  if (configured && /^https?:\/\//i.test(configured)) {
    return configured.replace(/^http/i, "ws");
  }
  // Same-origin /api (Docker nginx or Vite proxy)
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const prefix = configured?.startsWith("/") ? configured.replace(/\/$/, "") : "/api";
  return `${proto}//${window.location.host}${prefix}`;
}

export interface PipelineWsEvent {
  evento_id?: string;
  timestamp?: string;
  agente?: string;
  ticket_id?: string;
  tipo?: string;
  entrada?: Record<string, unknown>;
  salida?: Record<string, unknown>;
}

export function newTicketId(): string {
  return `T-${crypto.randomUUID().replace(/-/g, "").slice(0, 8).toUpperCase()}`;
}

/** Process ticket via WebSocket pipeline events; rejects on WS failure. */
export function processTicketViaWs(
  texto: string,
  options?: {
    ticketId?: string;
    onEvent?: (evento: PipelineWsEvent) => void;
    signal?: AbortSignal;
    timeoutMs?: number;
  }
): Promise<TicketResponse> {
  const ticketId = options?.ticketId ?? newTicketId();
  const url = `${wsBaseUrl()}/ws/pipeline/${ticketId}`;
  const timeoutMs = options?.timeoutMs ?? WS_PROCESS_TIMEOUT_MS;

  return new Promise((resolve, reject) => {
    let settled = false;
    let ws: WebSocket;
    try {
      ws = new WebSocket(url);
    } catch (e) {
      reject(e instanceof Error ? e : new Error(String(e)));
      return;
    }

    const finish = (fn: () => void) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      options?.signal?.removeEventListener("abort", onAbort);
      try {
        ws.close();
      } catch {
        /* ignore */
      }
      fn();
    };

    const timer = setTimeout(() => {
      finish(() => reject(new Error("WebSocket del pipeline agotó el tiempo de espera.")));
    }, timeoutMs);

    const onAbort = () => {
      finish(() => reject(new DOMException("Procesamiento cancelado", "AbortError")));
    };
    options?.signal?.addEventListener("abort", onAbort, { once: true });

    ws.onopen = () => {
      ws.send(JSON.stringify({ action: "process", texto }));
    };

    ws.onerror = () => {
      finish(() => reject(new Error("No se pudo conectar al WebSocket del pipeline.")));
    };

    ws.onclose = () => {
      if (!settled) {
        finish(() => reject(new Error("WebSocket cerrado antes de recibir el resultado.")));
      }
    };

    ws.onmessage = (msg) => {
      try {
        const data = JSON.parse(msg.data as string);
        if (data?.type === "result" && data.data) {
          finish(() => resolve(data.data as TicketResponse));
          return;
        }
        if (data?.agente && data?.tipo) {
          options?.onEvent?.(data as PipelineWsEvent);
        }
      } catch (e) {
        finish(() => reject(e instanceof Error ? e : new Error(String(e))));
      }
    };
  });
}

/** Listen to an in-flight pipeline without starting a new process. */
export function subscribePipelineWs(
  ticketId: string,
  options?: {
    onEvent?: (evento: PipelineWsEvent) => void;
    onResult?: (result: TicketResponse) => void;
    signal?: AbortSignal;
  }
): void {
  const url = `${wsBaseUrl()}/ws/pipeline/${ticketId}`;
  let ws: WebSocket;
  try {
    ws = new WebSocket(url);
  } catch {
    return;
  }

  const cleanup = () => {
    options?.signal?.removeEventListener("abort", onAbort);
    try {
      ws.close();
    } catch {
      /* ignore */
    }
  };

  const onAbort = () => cleanup();
  options?.signal?.addEventListener("abort", onAbort, { once: true });

  // Stay subscribed only — do not send { action: "process" }.
  ws.onmessage = (msg) => {
    try {
      const data = JSON.parse(msg.data as string);
      if (data?.type === "result" && data.data) {
        options?.onResult?.(data.data as TicketResponse);
        cleanup();
        return;
      }
      if (data?.agente && data?.tipo) {
        options?.onEvent?.(data as PipelineWsEvent);
      }
    } catch {
      /* ignore malformed frames */
    }
  };

  ws.onerror = () => cleanup();
  ws.onclose = () => {
    options?.signal?.removeEventListener("abort", onAbort);
  };
}

async function request<T>(
  path: string,
  options?: RequestInit & { timeoutMs?: number }
): Promise<T> {
  const controller = new AbortController();
  const timeoutMs = options?.timeoutMs ?? REQUEST_TIMEOUT_MS;
  const { timeoutMs: _ignored, ...fetchOptions } = options ?? {};
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_URL}${path}`, {
      headers: { "Content-Type": "application/json", ...(fetchOptions.headers || {}) },
      ...fetchOptions,
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") {
      throw new Error(
        `La API no respondió a tiempo (${Math.round(timeoutMs / 1000)}s). Revisa que el contenedor api esté healthy.`
      );
    }
    throw e;
  } finally {
    clearTimeout(timeout);
  }
}

/** Poll GET /jobs/{id} every 5s until complete / not_found / abort. */
export async function pollJob(
  jobId: string,
  options?: {
    intervalMs?: number;
    signal?: AbortSignal;
    onStatus?: (job: JobStatus) => void;
  }
): Promise<JobStatus> {
  const intervalMs = options?.intervalMs ?? JOB_POLL_INTERVAL_MS;
  while (true) {
    if (options?.signal?.aborted) {
      throw new DOMException("Polling cancelado", "AbortError");
    }
    const job = await api.getJob(jobId);
    options?.onStatus?.(job);
    if (job.status === "complete") return job;
    if (job.status === "not_found") {
      throw new Error(`Job ${jobId} no encontrado`);
    }
    await new Promise<void>((resolve, reject) => {
      const timer = setTimeout(resolve, intervalMs);
      options?.signal?.addEventListener(
        "abort",
        () => {
          clearTimeout(timer);
          reject(new DOMException("Polling cancelado", "AbortError"));
        },
        { once: true }
      );
    });
  }
}

export const api = {
  submitTicket: (texto: string) =>
    request<TicketResponse>("/tickets", {
      method: "POST",
      body: JSON.stringify({ texto }),
    }),

  getTicket: (ticketId: string) =>
    request<TicketResponse>(`/tickets/${encodeURIComponent(ticketId)}`),

  getPendientes: () => request<KedbArticulo[]>("/kedb/pendientes"),

  getArticulo: (id: string) => request<KedbArticulo>(`/kedb/articulos/${id}`),

  listArticulos: (estado?: string) =>
    request<KedbArticulo[]>(`/kedb/articulos${estado ? `?estado=${estado}` : ""}`),

  approveArticulo: (id: string) =>
    request<KedbArticulo>(`/kedb/articulos/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ estado: "validado" }),
      timeoutMs: 60_000,
    }),

  rejectArticulo: (id: string) =>
    request<KedbArticulo>(`/kedb/articulos/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ estado: "obsoleto" }),
      timeoutMs: 30_000,
    }),

  updateArticulo: (
    id: string,
    data: {
      titulo?: string;
      sintoma?: string;
      causa?: string;
      solucion?: string;
      aplicable_a?: string;
    }
  ) =>
    request<KedbArticulo>(`/kedb/articulos/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
      timeoutMs: 30_000,
    }),

  searchKedb: (q: string) =>
    request<{ query: string; results: Solucion[] }>(`/kedb/buscar?q=${encodeURIComponent(q)}`),

  correctCategoria: (ticketId: string, categoria: string) =>
    request(`/tickets/${ticketId}/categoria`, {
      method: "PATCH",
      body: JSON.stringify({ categoria }),
    }),

  feedback: (ticketId: string, data: { articulo_id?: string; util?: boolean; nueva_solucion?: string }) =>
    request(`/tickets/${ticketId}/feedback`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getDashboard: () => request<Record<string, unknown>>("/metrics/dashboard"),

  getEvaluacion: () => request<Record<string, unknown>>("/metrics/evaluacion"),

  enqueueEvaluacion: () =>
    request<JobEnqueue>("/metrics/evaluacion", {
      method: "POST",
    }),

  enqueueKedbGenerate: (maxArticles = 50, keyword?: string) => {
    const params = new URLSearchParams({ max_articles: String(maxArticles) });
    if (keyword) params.set("keyword", keyword);
    return request<JobEnqueue>(`/kedb/generate?${params}`, { method: "POST" });
  },

  getJob: (jobId: string) => request<JobStatus>(`/jobs/${jobId}`),

  listDocs: (estado: string = "validado") =>
    request<KedbDoc[]>(`/kedb/docs?estado=${encodeURIComponent(estado)}`),

  getDoc: (id: string) =>
    request<{ articulo_id: string; markdown: string }>(`/kedb/docs/${id}`),

  exportDocs: (soloValidados = true) =>
    request<{ exported: number; path: string; solo_validados: boolean }>(
      `/kedb/export-docs?solo_validados=${soloValidados}`,
      { method: "POST" }
    ),
};
