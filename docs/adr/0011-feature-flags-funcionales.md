# Feature flags funcionales por épica/HU (env vars, sin librería)

_Escrito el 2026-10-11, tras contrastar el backlog de Linear (E01–E05) con el código._

El backlog de Linear tiene HU que ya viven en el código pero siguen en Backlog o In Progress (HU15, HU16, HU17, HU12), y una capacidad costosa por LLM (generación de borradores, HU08). Hasta ahora todo se desplegaba "todo o nada". Se añadió un conjunto pequeño de **feature flags de tipo *release*** que separan el despliegue de la liberación y se reflejan en el frontend.

## Decisión

- Registro único y tipado: `pi_core.feature_flags.FeatureFlags` (pydantic-settings, `env_prefix="FEATURE_"`). Todos arrancan en **ON** (comportamiento actual); se apagan por entorno, p. ej. `FEATURE_E05_TABLERO_COORDINADOR=false`.
- El servidor es la fuente de verdad. El frontend lee `GET /config/features` al cargar `App` y, si falla, usa los mismos defaults (todo ON) para no romper la UI. No se usan `VITE_*` porque se hornean en el build.
- Defensa en profundidad: la UI oculta la capacidad y el endpoint responde `404 feature_deshabilitada` (`pi_api.deps.require_feature` / `ensure_feature`), evaluado en cada request.

| Flag | HU | Efecto |
|---|---|---|
| `e02_busqueda_kedb` | HU16 | Buscador del tablero y `GET /kedb/buscar` |
| `e03_generacion_kedb` | HU08 | Botón y `POST /kedb/generate` |
| `e03_ciclo_vida` | HU17 | Tabla de gestión y `PATCH .../ciclo-vida` (el `PATCH` de HU10 sigue activo) |
| `e04_nueva_solucion` | HU12 | Formulario y rama `nueva_solucion` de `/feedback` y `/resolucion` |
| `e05_tablero_coordinador` | HU15 | Indicadores y métricas del tablero, `GET /metrics/dashboard` |

La ruta `/dashboard` y su entrada de menú solo se ocultan si HU15, HU16 y HU17 están apagadas a la vez, porque comparten página.

## Qué NO se flaguea (y por qué)

- **El núcleo**: HU01, HU04, HU06, HU08a/b (agrupar y sintetizar), HU09, HU10. Apagarlos rompe el lazo cerrado o la regla "solo se publica lo validado".
- **Presentación de bajo riesgo ya aceptada** (HU02, HU05, HU07) y **retroalimentación acotada** (HU03, HU11): un toggle sería configuración, no un flag. HU14 (bandeja) es parte del flujo central del experto.
- **Banderas operativas** (seed-demo, evaluación, Live Docs): no son capacidades de usuario ligadas a una HU.

## Consecuencias

- Un flag se **retira** cuando el Product Owner acepta la HU y el issue pasa a Done en Linear. Toda HU opcional nueva nace con su flag; no se añaden flags por comodidad.
- Los flags se leen con `get_flags()` (caché `lru_cache`); en tests se cambian con `monkeypatch.setenv` y `get_flags.cache_clear()`.
- No hay segmentación por usuario ni rollout porcentual: si hiciera falta, se migraría a OpenFeature manteniendo `flag_enabled()` como única puerta de entrada.
- Los flags de arranque ON no ocultan nada hasta que alguien los apague; para que Sprint 4 salga apagado basta `false` en el `.env` del entorno, sin tocar código.
