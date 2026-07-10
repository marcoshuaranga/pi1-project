"""Seed demo KEDB fixture and golden set samples."""

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Allow `python scripts/seed_demo.py` inside Docker (script dir is on sys.path, not /app)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.schemas import KedbArticulo, KedbEstado
from app.storage.kedb_store.store import KedbStore, new_articulo_id
from app.config import get_settings


def seed_demo_kedb():
    """Create Kyocera demo article without LLM/Chroma (DEMO.md Escena 2)."""
    store = KedbStore()
    articulo = KedbArticulo(
        articulo_id=new_articulo_id(),
        titulo="Configuración de impresora Kyocera TaskAlfa 7003i",
        categoria=(
            "Equipos Informáticos > Equipo de impresión y escaneo > Impresora Multifuncional"
        ),
        sintoma=(
            "El usuario no puede imprimir o requiere configurar la impresora "
            "multifuncional Kyocera 7003 en su equipo."
        ),
        causa=(
            "Impresora predeterminada no configurada correctamente, "
            "o driver de la Kyocera 7003 no instalado."
        ),
        solucion=(
            "1. Instalar/verificar el driver de la impresora Kyocera 7003.\n"
            "2. Configurar la impresora como predeterminada.\n"
            "3. Validar con hoja de prueba."
        ),
        tickets_fuente=["96044", "95984", "95645", "95439", "94922"],
        fecha_generacion=datetime.now(timezone.utc),
        estado=KedbEstado.BORRADOR,
        aplicable_a="Impresoras Kyocera TaskAlfa 7003i en sedes MTC",
    )
    store.create(articulo)
    print(f"Demo KEDB article created: {articulo.articulo_id}")
    print(f"  estado={articulo.estado.value}  titulo={articulo.titulo}")
    return articulo


def seed_golden_set_sample(n: int = 50):
    settings = get_settings()
    processed = Path(settings.data_processed_path)
    eval_path = processed / "tickets_eval.json"
    if not eval_path.exists():
        print("No eval split found — run pipeline first")
        return

    tickets = json.loads(eval_path.read_text(encoding="utf-8"))
    golden = []
    for t in tickets[:n]:
        golden.append(
            {
                "golden_id": str(uuid.uuid4()),
                "ticket_id": t["ticket_id"],
                "categoria_experto1": t.get("categoria_top9"),
                "categoria_sistema": None,
                "split": "eval",
            }
        )

    out = processed / "golden_set_sample.json"
    out.write_text(json.dumps(golden, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Golden set sample: {len(golden)} entries → {out}")


if __name__ == "__main__":
    seed_demo_kedb()
    seed_golden_set_sample()
