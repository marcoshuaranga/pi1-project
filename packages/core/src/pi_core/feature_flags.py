"""Feature flags funcionales (ADR-0011).

Un flag = una capacidad de usuario ligada a una HU, de tipo *release*: separa el
despliegue de la liberación. Solo se flaguea trabajo incompleto, riesgoso o costoso
(HU12, HU15, HU16, HU17, generación KEDB); el núcleo (HU01/04/06/08/09/10) nunca.
Se retira el flag cuando el Product Owner acepta la HU y pasa a Done en Linear.

Todos arrancan en ON (comportamiento actual); se apagan por entorno, p. ej.
``FEATURE_E05_TABLERO_COORDINADOR=false``.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class FeatureFlags(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_prefix="FEATURE_", extra="ignore"
    )

    # E02 / HU16 — búsqueda directa en la KEDB.
    e02_busqueda_kedb: bool = True
    # E03 / HU08 — botón y endpoint de generación de borradores (dispara LLM en el worker).
    e03_generacion_kedb: bool = True
    # E03 / HU17 — gestión del ciclo de vida (no afecta a la validación de HU10).
    e03_ciclo_vida: bool = True
    # E04 / HU12 — registro de nueva solución como candidata KEDB.
    e04_nueva_solucion: bool = True
    # E05 / HU15 — tablero del coordinador.
    e05_tablero_coordinador: bool = True


@lru_cache
def get_flags() -> FeatureFlags:
    return FeatureFlags()


def flag_enabled(name: str) -> bool:
    """Evalúa un flag por nombre; un nombre desconocido es un error de programación."""
    if name not in FeatureFlags.model_fields:
        raise KeyError(f"Feature flag desconocido: {name}")
    return bool(getattr(get_flags(), name))
