// Lógica pura de presentación de la pantalla Operador (sin React, verificable con node).

/** HU02 CA3: 1.0 → "100%" sin error de redondeo en coma flotante. */
export function formatPorcentaje(valor: number): string {
  return `${Math.round(valor * 100)}%`;
}
