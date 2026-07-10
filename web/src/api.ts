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

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const res = await fetch(`${API_URL}${path}`, {
      headers: { "Content-Type": "application/json", ...(options?.headers || {}) },
      ...options,
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") {
      throw new Error("La API no respondió a tiempo (15s). Revisa que el contenedor api esté healthy.");
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

  getPendientes: () => request<KedbArticulo[]>("/kedb/pendientes"),

  getArticulo: (id: string) => request<KedbArticulo>(`/kedb/articulos/${id}`),

  listArticulos: (estado?: string) =>
    request<KedbArticulo[]>(`/kedb/articulos${estado ? `?estado=${estado}` : ""}`),

  approveArticulo: (id: string) =>
    request<KedbArticulo>(`/kedb/articulos/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ estado: "validado" }),
    }),

  rejectArticulo: (id: string) =>
    request<KedbArticulo>(`/kedb/articulos/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ estado: "obsoleto" }),
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
