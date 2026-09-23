"""Sample extraction and ingestion utilities."""

import re
from datetime import datetime

import pandas as pd

from app.constants import TOP9_CATEGORIES, TOP9_PATTERNS


def normalize_category(raw: str | None) -> str | None:
    if not raw or (isinstance(raw, float) and pd.isna(raw)):
        return None
    raw_str = str(raw).strip()
    for pattern, canonical in TOP9_PATTERNS:
        if pattern.lower() in raw_str.lower():
            return canonical
    for cat in TOP9_CATEGORIES:
        if cat.lower() in raw_str.lower():
            return cat
    return None


def is_top9(raw: str | None) -> bool:
    return normalize_category(raw) is not None


def clean_html(text: str | None) -> str:
    if not text or (isinstance(text, float) and pd.isna(text)):
        return ""
    text = str(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_date(value) -> datetime | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, datetime):
        return value
    try:
        return pd.to_datetime(value, dayfirst=True, errors="coerce").to_pydatetime()
    except Exception:
        return None


def assign_split(fecha: datetime | None) -> str | None:
    """PRD §4.2 temporal split: train mar-2024–may-2025, eval jun-sep 2025, holdout oct-2025+.

    Returns None for tickets without a date or outside the designed range,
    so callers can exclude them instead of silently defaulting to "train".
    """
    if not fecha:
        return None
    if fecha < datetime(2024, 3, 1):
        return None
    if fecha < datetime(2025, 6, 1):
        return "train"
    if fecha < datetime(2025, 10, 1):
        return "eval"
    return "holdout"


def load_glpi_excel(path: str, sheet: str = "Datos Consolidados") -> pd.DataFrame:
    return pd.read_excel(path, sheet_name=sheet, engine="openpyxl")


def extract_sample(df: pd.DataFrame) -> pd.DataFrame:
    """Filter top-9 categories with non-empty solutions."""
    cat_col = _find_column(df, ["categoría", "categoria", "category"])
    sol_col = _find_column(df, ["solución", "solucion", "solution"])
    title_col = _find_column(df, ["título", "titulo", "title", "asunto"])

    if cat_col is None:
        raise ValueError("No se encontró columna de categoría en el export GLPI")

    df = df.copy()
    df["_categoria_top9"] = df[cat_col].apply(normalize_category)
    df = df[df["_categoria_top9"].notna()]

    if sol_col:
        df["_solucion"] = df[sol_col].apply(clean_html)
        df = df[df["_solucion"].str.len() > 10]
    else:
        df["_solucion"] = ""

    if title_col:
        df["_titulo"] = df[title_col].apply(clean_html)
    else:
        df["_titulo"] = ""

    id_col = _find_column(df, ["id", "ticket", "número", "numero"])
    if id_col:
        df["_ticket_id"] = df[id_col].astype(str)
    else:
        df["_ticket_id"] = df.index.astype(str)

    df = df.drop_duplicates(subset=["_ticket_id"])
    return df


def _find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    cols_lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        for col_lower, col_orig in cols_lower.items():
            if cand in col_lower:
                return col_orig
    return None
