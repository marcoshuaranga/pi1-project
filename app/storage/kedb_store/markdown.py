"""Export KEDB articles as Markdown files (live docs)."""

from pathlib import Path

from app.config import Settings, get_settings
from app.schemas import KedbArticulo


def docs_dir(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    path = Path(settings.kedb_docs_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def articulo_to_markdown(articulo: KedbArticulo) -> str:
    tickets = ", ".join(articulo.tickets_fuente) if articulo.tickets_fuente else "—"
    aplicable = articulo.aplicable_a or "—"
    return f"""---
articulo_id: {articulo.articulo_id}
estado: {articulo.estado.value}
categoria: {articulo.categoria}
version: {articulo.version}
fecha_generacion: {articulo.fecha_generacion.isoformat()}
---

# {articulo.titulo}

## Síntoma
{articulo.sintoma}

## Categoría
{articulo.categoria}

## Causa probable
{articulo.causa}

## Solución
{articulo.solucion}

## Aplicable a
{aplicable}

## Trazabilidad
- Tickets fuente: {tickets}
- Última actualización: {articulo.fecha_generacion.date().isoformat()}
- Estado: {articulo.estado.value}
"""


def write_markdown(articulo: KedbArticulo, settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    path = docs_dir(settings) / f"{articulo.articulo_id}.md"
    path.write_text(articulo_to_markdown(articulo), encoding="utf-8")
    return path


def list_markdown_docs(settings: Settings | None = None) -> list[dict]:
    settings = settings or get_settings()
    directory = docs_dir(settings)
    docs = []
    for path in sorted(directory.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        text = path.read_text(encoding="utf-8")
        meta: dict[str, str] = {}
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].strip().splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        meta[k.strip()] = v.strip()
        docs.append(
            {
                "articulo_id": path.stem,
                "filename": path.name,
                "titulo": _title_from_md(text) or path.stem,
                "estado": meta.get("estado", "desconocido"),
                "categoria": meta.get("categoria", ""),
                "path": str(path),
            }
        )
    return docs


def read_markdown(articulo_id: str, settings: Settings | None = None) -> str | None:
    settings = settings or get_settings()
    path = docs_dir(settings) / f"{articulo_id}.md"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _title_from_md(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None
