# Plataforma Multi-Agente RAG + KEDB — OITSI-MTC

Plataforma de asistencia inteligente para la Mesa de Ayuda con ciclo cerrado asistencia ↔ KEDB.

## Documentación principal

- [CONTEXT.md](CONTEXT.md): glosario de dominio y lenguaje canónico del producto.
- [PRD.md](PRD.md): alcance, historias de usuario, métricas y especificación funcional.
- [AGENTS.md](AGENTS.md): reglas operativas para agentes y contribuyentes.
- [docs/README.md](docs/README.md): índice de toda la documentación técnica y de producto.
- [docs/architecture/overview.md](docs/architecture/overview.md): vista general de la arquitectura del sistema.
- [docs/operations/setup.md](docs/operations/setup.md): setup, arranque y validación del entorno.
- [specs/001-mvp-closed-assistance-kedb-loop/spec.md](specs/001-mvp-closed-assistance-kedb-loop/spec.md): baseline Spec Kit del comportamiento actual.
- [specs/001-mvp-closed-assistance-kedb-loop/quickstart.md](specs/001-mvp-closed-assistance-kedb-loop/quickstart.md): validación ejecutable del baseline.
- [demo/README.md](demo/README.md): narración y flujo de la demo.
- [demo/runbook.md](demo/runbook.md): checklist operativo y go/no-go.
- [demo/qa.md](demo/qa.md): preguntas de defensa y respuestas de negocio/arquitectura.

## Mapa de documentación

```text
root/
├── CONTEXT.md         # lenguaje y dominio
├── PRD.md             # requisitos y alcance
├── AGENTS.md          # reglas de contribución
├── README.md          # entrada del proyecto
├── docs/
│   ├── README.md      # índice general
│   ├── architecture/  # arquitectura y repo map
│   ├── operations/    # setup y troubleshooting
│   └── adr/           # decisiones técnicas
├── demo/
│   ├── README.md      # narrativa de la demo
│   ├── runbook.md     # checklist operativo
│   └── qa.md          # preguntas de defensa
└── web/, apps/, packages/, scripts/  # implementación
```

## Inicio rápido

```bash
cp .env.example .env
# editar OPENAI_API_KEY

# datos de entrada
# colocar Tickets_Consolidados.xlsx en data/raw/

docker compose up --build

docker compose --profile pipeline run --rm pipeline full
curl -X POST http://localhost:8000/kedb/seed-demo
```

## Requisitos

- Docker + Docker Compose
- clave de OpenAI
- export GLPI en `data/raw/`

## Flujo recomendado

1. Revisar [CONTEXT.md](CONTEXT.md) para entender términos del dominio.
2. Leer [PRD.md](PRD.md) para objetivos y alcance.
3. Consultar [docs/architecture/overview.md](docs/architecture/overview.md) para la vista de componentes.
4. Usar [demo/README.md](demo/README.md) y [demo/runbook.md](demo/runbook.md) para la sesión de demostración.
5. Consultar la especificación bajo `specs/` antes de implementar cambios de producto.

## Reset de demo

```bash
docker compose exec api python scripts/reset_demo.py
```

Si necesitas volver a un estado limpio del clúster Kyocera antes de una demo o ensayo.
