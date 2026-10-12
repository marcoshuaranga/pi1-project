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
