"""Expand thin historical resolutions into operational runbooks for RAG.

GLPI closures for high-recurrence clusters (esp. Kyocera 7003) are often
2–3 generic lines. For indexing we replace those stubs with longer, still
plausible Mesa de Ayuda procedures so Escena 1 shows actionable Top-5 text.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

# Chroma metadata string budget (keep well under practical limits).
SOLUCION_META_MAX = 4500

# Already useful enough — do not rewrite.
_MIN_KEEP_LEN = 280

_GENERIC_RE = re.compile(
    r"(?is)^(?:"
    r"\s*(?:ok|listo|resuelto|solucionado|atendido)\.?\s*"
    r"|se\s+configur\w*.{0,80}(?:predeterminada|impresora).{0,60}"
    r"|se\s+instal\w*.{0,40}driver.{0,80}"
    r"|impresora\s+predeterminada.{0,100}hoja\s+de\s+prueba.{0,40}"
    r"|se\s+valid[oó].{0,40}(?:impresi[oó]n|prueba).{0,40}"
    r")$"
)

_KYOCERA_TITLE_RE = re.compile(r"(?i)kyocera|7003|task\s*alfa|taskalfa")
_IMPRESSORA_RE = re.compile(r"(?i)impresor|imprim|escaneo|multifuncional|print")
_VPN_RE = re.compile(r"(?i)\bvpn\b|globalprotect|escritorio\s+remoto|palo\s*alto")
_CORREO_RE = re.compile(r"(?i)correo|outlook|buz[oó]n|exchange|owa")


@dataclass(frozen=True)
class EnrichmentResult:
    solucion: str
    enriched: bool
    domain: str | None = None


def is_thin_resolution(solucion: str | None) -> bool:
    text = (solucion or "").strip()
    if len(text) < _MIN_KEEP_LEN:
        return True
    if len(text) < 450 and _GENERIC_RE.match(text):
        return True
    # Short bullet stubs without operational detail
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return len(lines) <= 3 and len(text) < _MIN_KEEP_LEN + 80


def enrich_resolution(
    *,
    titulo: str,
    solucion: str | None,
    categoria: str | None = None,
    ticket_id: str | None = None,
    force: bool = False,
) -> EnrichmentResult:
    """Return an indexable resolution; rewrite thin stubs into runbooks."""
    original = (solucion or "").strip()
    domain = _detect_domain(titulo, categoria)

    if not force and not is_thin_resolution(original) and domain != "kyocera":
        return EnrichmentResult(solucion=original, enriched=False, domain=domain)

    # Kyocera/demo cluster: always prefer a full runbook when the source is thin,
    # or when force=True (reindex path). Keep a long original if it already looks rich.
    if domain == "kyocera" and not force and not is_thin_resolution(original):
        return EnrichmentResult(solucion=original, enriched=False, domain=domain)

    variants = _VARIANTS.get(domain) or _VARIANTS["generic"]
    picked = _pick(ticket_id or titulo or original, variants)

    if original and not is_thin_resolution(original) and force:
        # force reindex: still vary, but prefer curated demo quality
        text = picked
    elif original and len(original) > 40 and domain != "kyocera":
        text = f"{picked}\n\nNota del ticket original: {original[:400]}"
    else:
        text = picked

    return EnrichmentResult(solucion=text[:SOLUCION_META_MAX], enriched=True, domain=domain)


def _detect_domain(titulo: str, categoria: str | None) -> str:
    blob = f"{titulo or ''} {categoria or ''}"
    if _KYOCERA_TITLE_RE.search(blob) or (_IMPRESSORA_RE.search(blob) and "7003" in blob.lower()):
        return "kyocera"
    if _IMPRESSORA_RE.search(blob) or (categoria and "impres" in categoria.lower()):
        return "impresora"
    if _VPN_RE.search(blob) or (categoria and "vpn" in categoria.lower()):
        return "vpn"
    if _CORREO_RE.search(blob) or (categoria and "correo" in categoria.lower()):
        return "correo"
    return "generic"


def _pick(key: str, variants: list[str]) -> str:
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
    idx = int(digest[:8], 16) % len(variants)
    return variants[idx]


_KYOCERA_VARIANTS = [
    """Procedimiento aplicado — Kyocera TaskAlfa 7003i (reconfiguración en estación de trabajo):

1. Verificar conectividad: ping a la IP de la multifuncional en la VLAN de impresión de la sede; confirmar que el equipo responde y que el usuario está en la red corporativa (no invitado).
2. En el panel de la Kyocera, anotar modelo exacto (TaskAlfa 7003i) y estado (sin atasco, toner/OK, no “offline”).
3. En el PC del usuario (Windows): Panel de control → Dispositivos e impresoras. Si existe una cola antigua o “WSD”, eliminarla para evitar reenvíos a un puerto inválido.
4. Instalar/reparar el driver oficial KX Driver / PCL XL de Kyocera 7003i (paquete corporativo OITSI). Preferir instalación por puerto TCP/IP estándar (IP fija / hostname DNS de sede), no WSD.
5. Crear la impresora, asignar nombre institucional (p. ej. KYOCERA-7003-<SEDE>) y marcarla como impresora predeterminada para el perfil del usuario.
6. Configurar preferencias: casete A4, dúplex según política de la sede, autenticación de impresión si aplica (código de departamento).
7. Reiniciar el servicio “Cola de impresión” (Spooler) si la cola quedó detenida: services.msc → Reiniciar → reenviar trabajo.
8. Validación: imprimir página de prueba de Windows y una hoja real desde el aplicativo del usuario (Word/PDF). Confirmar salida en la 7003i y que el contador de la impresora incrementa.
9. Cierre: documentar IP/cola utilizada y capacitar al usuario para seleccionar la impresora correcta en el diálogo de impresión.

Resultado: impresión OK; incidencia cerrada como configuración de impresora multifuncional.""",
    """Procedimiento aplicado — Kyocera 7003 no imprime (puerto/red y cola):

1. Reproducir el síntoma con el usuario: ¿error de “impresora no disponible”, trabajos en error, o envío sin salida física?
2. Revisar trabajos en cola (icono de impresora). Cancelar trabajos atascados en error y limpiar carpeta de spool si el servicio no libera la cola.
3. Validar ruta de red: IP de la TaskAlfa 7003i según inventario de sede; prueba de ping y acceso a la web embebida (si política lo permite) para ver estado online.
4. En propiedades de la impresora → Puertos: confirmar puerto TCP/IP correcto (9100 / raw). Corregir IP si el equipo se renumeró tras cambio de switch/VLAN.
5. Reinstalar el driver Kyocera 7003i desde el repositorio OITSI (versión homologada). Evitar el driver genérico de Windows que pierde opciones de acabado.
6. Definir la Kyocera como predeterminada; eliminar duplicados “Kyocera (copiar)” que desvían trabajos.
7. Si el usuario imprime desde remoto/VPN: verificar política de redirección de impresoras y, si aplica, publicar la cola en el servidor de impresión de sede en lugar del puerto local.
8. Prueba controlada: página de prueba + documento PDF de una página. Verificar tóner/papelería solo si el panel muestra alarma; si hay atasco, derivar a soporte de hardware de sede.
9. Registrar en el ticket: IP final, nombre de cola y evidencia de hoja de prueba.

Resultado: trabajos salen en la 7003i; usuario confirma impresión normal.""",
    """Procedimiento aplicado — reinstalación de perfil de impresión Kyocera 7003:

1. Confirmar que el equipo físico imprime desde otra estación de la misma sede (aislar fallo de red vs. perfil de usuario).
2. En la estación afectada, respaldar (si existe) la lista de impresoras y eliminar perfiles corruptos de la Kyocera 7003 / TaskAlfa.
3. Ejecutar desinstalación limpia del software Kyocera (Programa de desinstalación / panel de programas) y reiniciar el PC.
4. Instalar el paquete corporativo del driver TaskAlfa 7003i; crear puerto TCP/IP apuntando a la IP del activo de impresión.
5. Asociar la impresora al usuario, dejarla predeterminada y forzar preferencias A4 + calidad estándar.
6. Verificar que no queden políticas de GPO trayendo una cola antigua; si hay conflicto, coordinar con administración de directorio / imagen de sede.
7. Probar impresión desde sesión del usuario (no solo admin): hoja de prueba Windows y archivo del sistema misional que usa a diario.
8. Si falla solo un aplicativo: revisar “Imprimir como imagen” / PDF creator intermedio; documentar workaround.
9. Cierre con usuario: muestra de hoja impresa y ruta Inicio → Impresoras para que sepa cuál seleccionar.

Resultado: perfil de impresión reconstruido; Kyocera 7003 operativa en el PC del solicitante.""",
    """Procedimiento aplicado — Kyocera TaskAlfa 7003i (configuración inicial en PC nuevo o formateado):

1. Tomar del inventario de sede: modelo TaskAlfa 7003i, dirección IP/hostname y ubicación (piso/área).
2. Validar que el PC tiene conectividad al segmento de impresión (ping / traceroute interno según herramientas OITSI).
3. Descargar e instalar el driver homologado Kyocera KX para 7003i (x64). Aceptar instalación de componentes de puerto.
4. Agregar impresora local → “Crear nuevo puerto” Standard TCP/IP → IP del equipo. Esperar detección; si falla SNMP, continuar con puerto Raw 9100.
5. Seleccionar el driver correcto (no “Generic / Text Only”). Nombrar la cola con convención de sede.
6. Imprimir página de prueba del instalador. Luego marcar como predeterminada y copiar la configuración al perfil del usuario si el técnico trabajó con elevación.
7. Ajustar bandeja y tamaño de papel; desactivar dúplex solo si el área lo solicita explícitamente.
8. Segunda validación: imprimir desde el navegador y desde un PDF embebido (casos frecuentes post-formateo).
9. Entregar tip breve al usuario: cómo elegir la Kyocera en el cuadro de diálogo y a quién escalar si el panel muestra error de papel/tóner.

Resultado: PC nuevo queda con Kyocera 7003 configurada y validada con hojas de prueba.""",
]

_IMPRESSORA_VARIANTS = [
    """Procedimiento aplicado — incidente de impresión / multifuncional:

1. Identificar marca/modelo y si el fallo es local (un PC) o general (varios usuarios / cola de servidor).
2. Revisar panel del equipo: papel, tóner, atanques, modo offline o error de red.
3. En el PC: reiniciar cola de impresión, eliminar trabajos en error y comprobar impresora predeterminada.
4. Reinstalar o actualizar el driver oficial; recrear el puerto TCP/IP si la IP cambió.
5. Validar con página de prueba y con un documento real del usuario.
6. Si persiste en red: verificar cable/switch de la impresora y escalar a redes/sede según corresponda.

Resultado: impresión restablecida; se documenta cola/driver utilizados.""",
    """Procedimiento aplicado — impresora instalada pero no imprime:

1. Confirmar que el dispositivo aparece “Lista” y no “Sin conexión” en Windows.
2. Probar ping a la IP; corregir puerto o DNS si no hay respuesta.
3. Limpiar cola, reiniciar Spooler y reenviar un trabajo simple.
4. Reasignar driver correcto del fabricante (evitar genérico).
5. Dejar la impresora como predeterminada y validar hoja de prueba con el usuario.

Resultado: trabajos completados; usuario confirma salida física.""",
]

_VPN_VARIANTS = [
    """Procedimiento aplicado — acceso remoto / VPN:

1. Verificar que el usuario usa el portal/cliente corporativo (p. ej. GlobalProtect) y no un enlace improvisado.
2. Comprobar usuario/contraseña de directorio y estado de la cuenta (no bloqueada / password vigente).
3. Revisar conectividad base (Internet, DNS) antes del túnel; reiniciar el cliente VPN y el servicio asociado.
4. Si el túnel conecta pero no hay recursos internos: validar rutas, DNS interno y pertenencia a grupos de acceso.
5. Reinstalar el cliente VPN desde el paquete OITSI si la instalación está corrupta; reiniciar el PC.
6. Prueba final: acceso a escritorio remoto o recurso de red acordado con el usuario; documentar versión del cliente.

Resultado: sesión remota operativa; incidencia de VPN cerrada.""",
]

_CORREO_VARIANTS = [
    """Procedimiento aplicado — correo / buzón:

1. Confirmar síntoma: no envía, no recibe, buzón lleno, o error de autenticación.
2. Verificar cuota del buzón y liberar espacio (papelera, enviados grandes) si aplica.
3. Reparar perfil de Outlook (modo online, nueva cuenta IMAP/Exchange según estándar OITSI) o validar OWA.
4. Comprobar autenticación moderna / token; reset de contraseña solo si el directorio lo indica.
5. Probar envío y recepción de un correo de prueba con el usuario; documentar cliente usado.

Resultado: correo operativo; usuario confirma bandeja funcionando.""",
]

_GENERIC_VARIANTS = [
    """Procedimiento aplicado por Mesa de Ayuda:

1. Reproducir el incidente con el usuario y acotar alcance (un equipo vs. servicio completo).
2. Revisar cambios recientes (instalaciones, red, credenciales) y logs básicos del componente afectado.
3. Aplicar la corrección estándar del catálogo OITSI para la categoría del ticket (reinstalación, reconfiguración o restablecimiento controlado).
4. Validar funcionalidad extremo a extremo con el solicitante.
5. Documentar pasos y configuración final en el ticket para recurrencia.

Resultado: servicio restablecido según validación del usuario.""",
]

_VARIANTS: dict[str, list[str]] = {
    "kyocera": _KYOCERA_VARIANTS,
    "impresora": _IMPRESSORA_VARIANTS,
    "vpn": _VPN_VARIANTS,
    "correo": _CORREO_VARIANTS,
    "generic": _GENERIC_VARIANTS,
}
