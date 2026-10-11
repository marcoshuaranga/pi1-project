"""Sugerencia de categoría top-9 para etiquetas en texto libre de los expertos.

Los expertos etiquetaron con un vocabulario más grueso que el top-9 ("acceso a cuenta", "vpn", ...).
Esto propone la subcategoría más probable a partir del título y la solución del ticket, para que
los expertos solo confirmen o corrijan; nunca reemplaza su etiqueta original.
"""

from __future__ import annotations

from pi_core.constants import FUERA_TOP9, TOP9_CATEGORIES

ALTA, BLOQUEO, VIGENCIA = TOP9_CATEGORIES[5], TOP9_CATEGORIES[6], TOP9_CATEGORIES[7]
VPN_NO_ACCEDE, VPN_HABILITACION = TOP9_CATEGORIES[3], TOP9_CATEGORIES[4]
IMPRESORA, STD, CPU, BUZON = (TOP9_CATEGORIES[0], TOP9_CATEGORIES[1], TOP9_CATEGORIES[2], TOP9_CATEGORIES[8])

_DIRECT = {
    "correo": BUZON,
    "impresora": IMPRESORA,
    "cpu": CPU,
    "std": STD,
    "aplicaciones": STD,
}

_HARDWARE = ("monitor", "usb", "internet")


def _has(text: str, *keys: str) -> bool:
    return any(k in text for k in keys)


def suggest_category(etiqueta: str, titulo: str, solucion: str = "") -> tuple[str | None, str, str]:
    """Devuelve (categoria_sugerida | None, confianza, motivo). Confianza: alta | media | baja."""
    etiqueta = etiqueta.strip().lower()
    t = titulo.lower()
    full = f"{t} {solucion.lower()}"

    if etiqueta in _DIRECT:
        return _DIRECT[etiqueta], "alta", "Equivale 1:1 a la etiqueta del experto"

    if etiqueta == "acceso a cuenta":
        if _has(t, "vigencia", "ampli"):
            return VIGENCIA, "alta", "Título habla de vigencia/ampliación"
        if _has(t, "bloque", "desbloq"):
            return BLOQUEO, "alta", "Título habla de bloqueo/desbloqueo"
        if _has(t, "contraseña", "clave", "restablec"):
            return BLOQUEO, "media", "Restablecer contraseña suele cerrarse como bloqueo"
        if _has(t, "habilitar", "creacion", "creación", "alta", "accesos"):
            return ALTA, "alta" if _has(t, "habilitar", "creacion", "creación") else "media", (
                "Título habla de crear/habilitar accesos"
            )
        if _has(full, "vigencia", "ampli"):
            return VIGENCIA, "baja", "Solo la solución menciona vigencia"
        if _has(full, "bloque", "desbloq"):
            return BLOQUEO, "baja", "Solo la solución menciona bloqueo"
        return ALTA, "baja", "Sin pistas; Alta es la subcategoría por defecto"

    if etiqueta == "vpn":
        problema = _has(t, "problema", "sin ", "no puede", "no accede", "no tiene", "conectividad")
        gestion = _has(t, "acceso al", "gestion", "gestión", "configuración", "configuracion", "carta", "habilit")
        if _has(full, "no cuenta con permisos", "no tiene permisos", "sin conexión", "sin conexion", "sin acceso"):
            return VPN_NO_ACCEDE, "media", "Describe una falla de conexión o permisos"
        if problema and not gestion:
            return VPN_NO_ACCEDE, "media", "Título describe un problema de acceso"
        if gestion and not problema:
            return VPN_HABILITACION, "media", "Título habla de gestionar/configurar el acceso"
        return None, "baja", "Ambos significados posibles; requiere decisión del experto"

    if etiqueta == "signnet":
        return STD, "alta", "Firma de documentos en el STD (Signnet)"
    if etiqueta in _HARDWARE:
        return FUERA_TOP9, "media", "Monitor/USB/red: el top-9 no tiene categoría para esto"
    if etiqueta == "otros":
        return FUERA_TOP9, "media", "Traslado, cableado o trámite: ninguna categoría top-9 lo cubre"

    return None, "baja", f"Etiqueta '{etiqueta}' no reconocida"
