import { createContext, useContext, type ReactNode } from "react";

/** Espejo de `pi_core.feature_flags.FeatureFlags` (ADR-0011); el servidor es la fuente de verdad. */
export type FeatureFlags = {
  e02_busqueda_kedb: boolean;
  e03_generacion_kedb: boolean;
  e03_ciclo_vida: boolean;
  e04_nueva_solucion: boolean;
  e05_tablero_coordinador: boolean;
};

export type FeatureName = keyof FeatureFlags;

/** Mismos defaults que el backend (todo encendido): si `/config/features` falla, la UI no se rompe. */
export const DEFAULT_FLAGS: FeatureFlags = {
  e02_busqueda_kedb: true,
  e03_generacion_kedb: true,
  e03_ciclo_vida: true,
  e04_nueva_solucion: true,
  e05_tablero_coordinador: true,
};

const FeatureFlagsContext = createContext<FeatureFlags>(DEFAULT_FLAGS);

export function FeatureFlagsProvider({ flags, children }: { flags: FeatureFlags; children: ReactNode }) {
  return <FeatureFlagsContext.Provider value={flags}>{children}</FeatureFlagsContext.Provider>;
}

export function useFeature(name: FeatureName): boolean {
  return useContext(FeatureFlagsContext)[name];
}

/** Para la navegación: el tablero agrupa HU15/HU16/HU17, así que `/dashboard` solo se oculta si los tres están apagados. */
export function useDashboardEnabled(): boolean {
  const flags = useContext(FeatureFlagsContext);
  return flags.e05_tablero_coordinador || flags.e02_busqueda_kedb || flags.e03_ciclo_vida;
}
