# Plataforma Multi-Agente RAG + KEDB — OITSI-MTC

Plataforma de asistencia inteligente para Mesa de Ayuda con ciclo cerrado asistencia ↔ KEDB.

## Requisitos

- Docker & Docker Compose
- OpenAI API key
- Export GLPI: `Tickets_Consolidados.xlsx` en `data/raw/`

## Inicio rápido

```bash
# 1. Configurar entorno
cp .env.example .env
# Editar .env con OPENAI_API_KEY

# 2. Copiar datos (nunca commitear el xlsx crudo)
# Colocar Tickets_Consolidados.xlsx en data/raw/

# 3. Configurar embeddings (si OpenAI da insufficient_quota, usar local)
# En .env: EMBEDDING_PROVIDER=local

# 4. Levantar stack
docker compose up --build

# 5. Ejecutar pipeline de datos (Fase 1)
docker compose --profile pipeline run --rm pipeline full

# 6. Sembrar artículo demo Kyocera + métricas de respaldo
curl -X POST http://localhost:8000/kedb/seed-demo
# o: docker compose exec api python scripts/seed_demo.py
```

Guía operativa completa (go/no-go, escenas, HU14): [`docs/DEMO_RUNBOOK.md`](docs/DEMO_RUNBOOK.md).

## Reset de demo (volver al seed inicial)

Tras practicar las escenas (editar, aprobar, rechazar), el estado KEDB puede quedar “sucio” (artículo validado en RAG, varios borradores, títulos de prueba). Para **resetear y dejar un único borrador Kyocera limpio** listo para Escena 2:

```bash
docker compose exec api python scripts/reset_demo.py
```

Qué hace:

1. Elimina artículos Kyocera/7003 en **cualquier** estado (`borrador`, `validado`, `obsoleto`)
2. Los quita de Chroma (colección KEDB) y de Live Docs (Markdown)
3. Crea de nuevo **1** artículo canónico en `borrador` (~142 `tickets_fuente`)

Opciones:

```bash
# Sin tocar Chroma
docker compose exec api python scripts/reset_demo.py --no-chroma

# Sin borrar archivos Markdown de Live Docs
docker compose exec api python scripts/reset_demo.py --no-markdown

# Además recalcular métricas C9 (más lento)
docker compose exec api python scripts/reset_demo.py --with-eval
```

Verificación rápida:

```bash
curl -s http://localhost:8000/kedb/pendientes
# Debe haber exactamente 1 ítem: título TaskAlfa 7003i, estado borrador
```

| Situación | Comando |
| :--- | :--- |
| Primera siembra / solo limpiar borradores | `seed_demo` o `POST /kedb/seed-demo` |
| Ya aprobaste en Escena 3 y quieres reensayar | `scripts/reset_demo.py` |

## URLs

| Servicio | URL |
|----------|-----|
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Web UI | http://localhost:3000 |
| ChromaDB | http://localhost:8001 |

## Pantallas

- **Operador** (`/`) — MVP: HU01, HU02 ✅, HU04, HU06, HU07 ✅ (+ extras UI: HU03, HU05, HU11, HU12)
- **Experto KEDB** (`/experto`) — MVP: HU09 ✅, HU10 (editar / aprobar / rechazar), HU14
- **Live Docs** (`/docs`) — proyección Markdown de artículos validados
- **Coordinador** (`/dashboard`) — Fase 2: HU15, HU16, HU17 (esqueleto)

### Historias adelantadas al MVP (hechas)

| ID | Qué ve el usuario |
| :--- | :--- |
| **HU02** | % de confianza junto a la categoría (Operador) |
| **HU07** | % de similitud en cada solución del Top-5 (Operador) |
| **HU09** | Tickets fuente N:1 + conteo en Experto (Escena 2) |

## Pipeline CLI

```bash
docker compose --profile pipeline run --rm pipeline extract
docker compose --profile pipeline run --rm pipeline anonymize
docker compose --profile pipeline run --rm pipeline ingest
docker compose --profile pipeline run --rm pipeline embed
# Solo clúster Kyocera (resoluciones operativas largas para Escena 1):
docker compose --profile pipeline run --rm pipeline enrich-kyocera
docker compose --profile pipeline run --rm pipeline full
```

## Demo

Checklist operativa: [`docs/DEMO_RUNBOOK.md`](docs/DEMO_RUNBOOK.md). Guion narrativo: [`DEMO.md`](DEMO.md). Q&A de defensa: [`docs/DEMO_QA.md`](docs/DEMO_QA.md).

1. **Escena 1:** Pegar ticket Kyocera en pantalla Operador
2. **Escena 2:** Mostrar artículo KEDB pre-generado en pantalla Experto (~142 tickets fuente)
3. **Escena 3:** Aprobar artículo → reenviar ticket similar y señalar hit KEDB

Antes de una sesión con el patrocinador (o tras un ensayo):

```bash
docker compose exec api python scripts/reset_demo.py
```

## Arquitectura

```
Capa 1: C1 Anonimización → C2 Ingesta → ChromaDB
Capa 2: C7 Orquestador → C3 ‖ C4 → C5 → C6 KEDB
Capa 3: C8 React SPA · C9 Evaluación
```

Ver [PRD.md](PRD.md) y [DEMO.md](DEMO.md) para especificación completa.
