"""Siembra los datos de prueba para las capturas de docs/evidence/sprint3/.

Un solo caso no se puede provocar con el pipeline real: el Priorizador siempre devuelve factores,
así que "sin factores de prioridad" (HU05 CA2) exige un ticket cuya `justificacion_prioridad` esté
vacía. Se persiste directamente en la sesión de tickets (SQLite de KedbStore), igual que lo haría
`POST /tickets`, sin tocar el código del producto. Es idempotente: el id es fijo.

Uso (dentro del contenedor api; ver docs/evidence/sprint3/README.md):
    docker compose exec -T api uv run --no-sync python - < scripts/seed_evidence_sprint3.py
"""

from pi_core.schemas import TicketResponse
from pi_core.storage.kedb_store.store import KedbStore

TICKET_SIN_FACTORES = "T-EVID0001"

KedbStore().save_ticket_session(
    TicketResponse(
        ticket_id=TICKET_SIN_FACTORES,
        categoria="Equipos Informáticos > Equipo de impresión y escaneo > Impresora Multifuncional",
        confianza=0.92,
        prioridad="Media",
        justificacion_prioridad={},
        soluciones=[],
    )
)
print(f"Ticket sembrado sin factores de prioridad: {TICKET_SIN_FACTORES}")
