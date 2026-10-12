// Lógica pura del tablero del Coordinador (HU15) y la gestión del ciclo de vida (HU17), sin React.

export const MENSAJE_RANGO_INVALIDO =
  "Rango de fechas inválido: la fecha de inicio es posterior a la de fin.";

/** HU15 CA3: devuelve el mensaje de error, o null si el rango es válido (extremos vacíos son válidos). */
export function validarRango(desde: string, hasta: string): string | null {
  if (desde && hasta && desde > hasta) return MENSAJE_RANGO_INVALIDO; // ISO yyyy-mm-dd ordena como texto
  return null;
}

export interface FiltrosTablero {
  categoria: string;
  desde: string;
  hasta: string;
}

export const FILTROS_VACIOS: FiltrosTablero = { categoria: "", desde: "", hasta: "" };

export function hayFiltros(f: FiltrosTablero): boolean {
  return Boolean(f.categoria || f.desde || f.hasta);
}

/** Query string del tablero; omite los filtros vacíos. */
export function queryDeFiltros(f: FiltrosTablero): string {
  const params = new URLSearchParams();
  if (f.categoria) params.set("categoria", f.categoria);
  if (f.desde) params.set("desde", f.desde);
  if (f.hasta) params.set("hasta", f.hasta);
  const q = params.toString();
  return q ? `?${q}` : "";
}

export type EstadoKedb = "borrador" | "validado" | "obsoleto" | "archivado";

/**
 * Espejo de `_ALLOWED_ESTADO_TRANSITIONS` (pi_core/storage/kedb_store/store.py) para las acciones que
 * HU17 expone en el listado. `borrador` no ofrece acciones aquí: se valida o rechaza en Experto KEDB (HU10),
 * y no puede pasar directo a archivado (CA2). `archivado` es terminal. El servidor sigue siendo la fuente de verdad.
 */
export const ACCIONES_CICLO_VIDA: Record<EstadoKedb, { destino: EstadoKedb; etiqueta: string }[]> = {
  borrador: [],
  validado: [
    { destino: "obsoleto", etiqueta: "Marcar obsoleto" },
    { destino: "archivado", etiqueta: "Archivar" },
  ],
  obsoleto: [{ destino: "archivado", etiqueta: "Archivar" }],
  archivado: [],
};

export function accionesDe(estado: string): { destino: EstadoKedb; etiqueta: string }[] {
  return ACCIONES_CICLO_VIDA[estado as EstadoKedb] ?? [];
}

/** Archivar es irreversible (estado terminal), por eso pide confirmación. */
export function confirmacionDe(destino: string, titulo: string): string | null {
  return destino === "archivado"
    ? `«${titulo}» pasará a archivado y no podrá volver a otro estado. ¿Continuar?`
    : null;
}

const CLASE_ESTADO: Record<EstadoKedb, string> = {
  borrador: "badge-warning",
  validado: "badge-success",
  obsoleto: "badge-ghost",
  archivado: "badge-neutral",
};

export function claseBadgeEstado(estado: string): string {
  return CLASE_ESTADO[estado as EstadoKedb] ?? "badge-outline";
}

/** C9: qué significa cada tipo de evidencia, para que el coordinador lea las métricas con contexto. */
export const EXPLICACION_EVIDENCIA: Record<string, string> = {
  medido: "Medido contra el golden set etiquetado por expertos.",
  objetivo: "Meta definida en el proyecto; todavía no es una medición.",
  proxy: "Estimación aproximada, sin etiquetado experto: úsala como orientación, no como resultado final.",
};

export function explicarEvidencia(tipo: string): string {
  return EXPLICACION_EVIDENCIA[tipo] ?? EXPLICACION_EVIDENCIA.proxy;
}
