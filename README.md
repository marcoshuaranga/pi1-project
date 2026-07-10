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

# 6. Sembrar artículo demo Kyocera (elige una opción)
curl -X POST http://localhost:8000/kedb/seed-demo
# o: docker compose exec -e PYTHONPATH=/app api python /app/scripts/seed_demo.py
```

## URLs

| Servicio | URL |
|----------|-----|
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Web UI | http://localhost:3000 |
| ChromaDB | http://localhost:8001 |

## Pantallas

- **Operador** (`/`) — HU01, HU04, HU06 + Fase 2 (HU02, HU03, HU05, HU07, HU11)
- **Experto KEDB** (`/experto`) — HU10, HU14, HU09
- **Coordinador** (`/dashboard`) — HU15, HU16, HU17

## Pipeline CLI

```bash
docker compose --profile pipeline run --rm pipeline extract
docker compose --profile pipeline run --rm pipeline anonymize
docker compose --profile pipeline run --rm pipeline ingest
docker compose --profile pipeline run --rm pipeline embed
docker compose --profile pipeline run --rm pipeline full
```

## Demo (DEMO.md)

1. **Escena 1:** Pegar ticket Kyocera en pantalla Operador
2. **Escena 2:** Mostrar artículo KEDB pre-generado en pantalla Experto
3. **Escena 3:** Aprobar artículo con un clic

## Arquitectura

```
Capa 1: C1 Anonimización → C2 Ingesta → ChromaDB
Capa 2: C7 Orquestador → C3 ‖ C4 → C5 → C6 KEDB
Capa 3: C8 React SPA · C9 Evaluación
```

Ver [PRD.md](PRD.md) y [DEMO.md](DEMO.md) para especificación completa.
