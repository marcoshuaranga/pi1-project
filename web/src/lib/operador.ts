// Lógica pura de presentación de la pantalla Operador (sin React, verificable con node).

/** HU02 CA3: 1.0 → "100%" sin error de redondeo en coma flotante. */
export function formatPorcentaje(valor: number): string {
  return `${Math.round(valor * 100)}%`;
}

/**
 * Extrae el mensaje legible de un error de la API (`request` lanza Error con el cuerpo crudo).
 * FastAPI responde `{"detail": "texto"}` o, en 422 de validación, `{"detail": [{"msg", "loc"}]}`.
 */
export function mensajeDeError(err: unknown): string {
  const raw = err instanceof Error ? err.message : String(err);
  try {
    const detail = (JSON.parse(raw) as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((d: { msg?: string }) => d.msg)
        .filter(Boolean)
        .join("; ");
    }
  } catch {
    // no era JSON: se muestra tal cual
  }
  return raw;
}

/** HU05 CA2: `{}` es truthy en JS; "sin factores" = ausente o sin claves. */
export function tieneFactores(justificacion?: Record<string, number> | null): boolean {
  return justificacion != null && Object.keys(justificacion).length > 0;
}

export const MENSAJE_SIN_FACTORES = "No hay factores disponibles para esta prioridad";

export interface SimilarKedb {
  articulo_o_ticket_id: string;
  titulo?: string;
  score: number;
}

/** HU12 CA3: la API responde 409 con `detail.codigo === "posible_duplicado"` y los artículos similares. */
export function duplicadoDeError(err: unknown): { mensaje: string; similares: SimilarKedb[] } | null {
  try {
    const raw = err instanceof Error ? err.message : String(err);
    const detail = (JSON.parse(raw) as { detail?: { codigo?: string; mensaje?: string; similares?: SimilarKedb[] } })
      .detail;
    if (detail && typeof detail === "object" && detail.codigo === "posible_duplicado") {
      return { mensaje: detail.mensaje ?? "Posible duplicado.", similares: detail.similares ?? [] };
    }
  } catch {
    // no era JSON
  }
  return null;
}
