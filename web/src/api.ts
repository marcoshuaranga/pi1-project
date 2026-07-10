const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

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

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
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

  listDocs: (estado?: string) =>
    request<KedbDoc[]>(`/kedb/docs${estado ? `?estado=${estado}` : ""}`),

  getDoc: (id: string) =>
    request<{ articulo_id: string; markdown: string }>(`/kedb/docs/${id}`),

  exportDocs: () =>
    request<{ exported: number; path: string }>("/kedb/export-docs", { method: "POST" }),
};
