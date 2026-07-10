"""Top 9 Pareto categories (PRD §2.3, §10.2)."""

TOP9_CATEGORIES: list[str] = [
    "Equipos Informáticos > Equipo de impresión y escaneo > Impresora Multifuncional",
    "Aplicaciones MTC > STD",
    "Equipos Informáticos > Equipos de Escritorio > CPU",
    "VPN > No accede al servicio",
    "VPN > Habilitación del servicio",
    "Cuenta de usuario > Alta",
    "Cuenta de usuario > Bloqueo",
    "Cuenta de usuario > Vigencia",
    "Correo > Buzón lleno",
]

# Short labels for matching GLPI export column values
TOP9_PATTERNS: list[tuple[str, str]] = [
    ("Impresora Multifuncional", TOP9_CATEGORIES[0]),
    ("Aplicaciones MTC", TOP9_CATEGORIES[1]),
    ("STD", TOP9_CATEGORIES[1]),
    ("Equipos de Escritorio", TOP9_CATEGORIES[2]),
    ("CPU", TOP9_CATEGORIES[2]),
    ("VPN > No accede", TOP9_CATEGORIES[3]),
    ("No accede al servicio", TOP9_CATEGORIES[3]),
    ("VPN > Habilitación", TOP9_CATEGORIES[4]),
    ("Habilitación del servicio", TOP9_CATEGORIES[4]),
    ("Cuenta de usuario", TOP9_CATEGORIES[5]),
    ("Alta", TOP9_CATEGORIES[5]),
    ("Bloqueo", TOP9_CATEGORIES[6]),
    ("Vigencia", TOP9_CATEGORIES[7]),
    ("Buzón lleno", TOP9_CATEGORIES[8]),
    ("Correo", TOP9_CATEGORIES[8]),
]

PRIORIDADES = ["Baja", "Media", "Alta", "Crítica"]
