# Guía de demo — Plataforma RAG + KEDB

## Pre-requisitos

1. `docker compose up --build` corriendo
2. `Tickets_Consolidados.xlsx` en `data/raw/`
3. `.env` con `OPENAI_API_KEY` válida

## Prework (antes de la sesión con el patrocinador)

```bash
# Pipeline de datos (muestra top-9)
docker compose --profile pipeline run --rm pipeline full

# Artículo KEDB demo Kyocera
docker compose exec api python scripts/seed_demo.py

# Opcional: generar más artículos vía clustering
curl -X POST "http://localhost:8000/kedb/generate?keyword=Kyocera"
```

## Escena 1 — Asistencia en vivo

1. Abrir http://localhost:3000
2. Pegar: *"Impresora Kyocera 7003 no imprime, necesito que la configuren de nuevo"*
3. Clic en **Enviar ticket**
4. Mostrar categoría, prioridad Media, Top-5 soluciones

## Escena 2 — Conocimiento generado

1. Ir a http://localhost:3000/experto
2. Abrir artículo Kyocera pre-generado
3. Mostrar trazabilidad a tickets fuente

## Escena 3 — Cierre del ciclo

1. Clic en **Aprobar**
2. Volver a Escena 1 con ticket similar — el artículo KEDB aparece en RAG

## Cifras de respaldo (si preguntan)

```bash
curl http://localhost:8000/metrics/evaluacion
```
