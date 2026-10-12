# Evidencia Sprint 3

Artefactos verificables citados en el documento. Todo se generó sobre el commit indicado en
`evaluation_results_golden.json` (`commit_evaluado`) con el stack de `compose.yml` levantado.

## 1. Evaluación del golden set (C9)

`evaluation_results_golden.json` — F1 macro, Kappa, Recall@5 (exacto y por categoría), muestra (185), semilla,
`tipo_evidencia` (`proxy`), hash del commit y fecha. Es el mismo cálculo que `POST /metrics/evaluacion-golden`
(`EvaluationFramework.run_golden_evaluation`), envuelto para añadir la trazabilidad.

Reproducir (con `docker compose up -d` y los datos de `data/processed/` presentes: `golden_set_sample.json`,
`golden_set_kappa.json`, `tickets_eval.json`, y el índice Chroma cargado):

```bash
docker compose exec -T -e GIT_COMMIT=$(git rev-parse HEAD) -e GIT_DIRTY=$([ -n "$(git status --porcelain)" ] && echo 1 || echo 0) api \
  uv run --no-sync python - < scripts/export_evaluation_evidence.py > docs/evidence/sprint3/evaluation_results_golden.json
```

La evaluación es determinista (no muestrea: recorre los 185 tickets del golden set, 15 más quedan fuera por
`Fuera de top-9`); la semilla `42` solo gobernó el muestreo estratificado del golden set.
Recall@5 **exacto** = el propio ticket aparece en el top-5; **por categoría** = alguna de las 5 soluciones
(sin contar el propio ticket) es de la categoría gold. No hay juicio experto de relevancia
(`relevance_results.json` ausente), por eso `juicio_experto` va vacío.

## 2. Capturas de la interfaz (1280 px de ancho)

| Archivo | Muestra |
|---|---|
| `01-confianza-baja-resaltada.png` | Clasificación con confianza 45 % resaltada como "baja" (umbral 60 %). |
| `02a-correccion-categoria-valida.png` | Corrección de categoría con una categoría del catálogo ("Categoría corregida."). |
| `02b-correccion-categoria-invalida-rechazada.png` | Rechazo de una categoría fuera del catálogo (422 del backend). |
| `03a-factores-de-prioridad.png` | Prioridad con sus 5 factores y porcentajes. |
| `03b-sin-factores-de-prioridad.png` | Mensaje "No hay factores disponibles para esta prioridad". |
| `04-calificacion-utilidad-articulo.png` | Solución marcada "Útil" y mensaje de feedback registrado. |
| `05a-nueva-solucion-validacion.png` | Nueva solución con texto demasiado corto: error de validación. |
| `05b-nueva-solucion-advertencia-duplicado.png` | Advertencia "Posible duplicado" (similitud 89 %) con "Guardar igual / Cancelar". |
| `06-detalle-articulo-kedb-tickets-fuente.png` | Artículo KEDB (borrador) con trazabilidad N:1 a sus tickets fuente. |

Cómo se obtuvieron:

- Tickets reales vía `POST /tickets`; la confianza baja (0.453) salió orgánicamente del texto "revisar cosas pendientes de la oficina".
- **Sembrado (único caso):** "sin factores" (03b). El Priorizador siempre devuelve factores, así que
  `scripts/seed_evidence_sprint3.py` guarda el ticket `T-EVID0001` con `justificacion_prioridad = {}` en la sesión de tickets:
  `docker compose exec -T api uv run --no-sync python - < scripts/seed_evidence_sprint3.py`
- **Categoría inválida (02b):** el `<select>` solo ofrece categorías válidas, así que el script de capturas reescribe el cuerpo del
  `PATCH /tickets/{id}/categoria` con una categoría inexistente; el rechazo mostrado es la respuesta real de la API.
- **Duplicado (05b):** la detección compara contra artículos *validados e indexados* (umbral 0.85). Se escribe la solución textual del
  artículo validado de correo institucional (`KEDB-B65F03339F00`); no se pulsa "Guardar igual", así que no se crea ningún artículo.
- Efectos colaterales en datos de demo: un par de tickets nuevos, una corrección de categoría y un voto de utilidad.
- El script `scripts/capture_evidence_sprint3.mjs` las regenera. Se usó el build de producción (`VITE_API_URL=http://localhost:8000 npm run build`
  + `vite preview --port 3000`, puerto permitido por CORS) porque el servidor de desarrollo de Vite dentro de Docker se atascaba con Chrome headless.
  Requiere `playwright-core` instalado fuera del repo y Chrome: `WEB_URL=http://localhost:3000 node scripts/capture_evidence_sprint3.mjs docs/evidence/sprint3`.
