"""
Helpers de parsing tolerantes a las variantes que produce Moodle
(gradebook, PGA, snapshots, etc.) segun el locale de la institucion.

Estos helpers centralizan la logica de normalizacion para evitar
re-implementar (y re-romper) la misma defensa en cada script.
"""

# Centinelas explicitos que NO representan un valor numerico.
# Cualquier string en este set -> 0.0.
_SENTINELAS = {
    "",
    "-",
    "\u2014",  # em-dash
    "n/a",
    "sin calificar",
}

# Aliases con capitalizacion variable (Moodle a veces pone
# "Sin calificar", otras "SIN CALIFICAR").
_SENTINELAS_CASED = {s.lower() for s in _SENTINELAS}


def _parse_porcentaje(valor) -> float:
    """Parsea un valor de porcentaje del gradebook Moodle.

    Tolerante a None, "", "-", "\u2014", "N/A", "Sin calificar",
    "100%", " - %", "12,5 %", "12.5 %", " 12,50 % ".

    Retorna float en rango [0, 100] o 0.0 si no parseable.
    NUNCA lanza excepcion: un valor raro del gradebook no debe tumbar
    la corrida completa (L1, B1 del plan 2026-07-21).
    """
    if valor is None:
        return 0.0
    s = str(valor).strip()
    if not s or s.lower() in _SENTINELAS_CASED:
        return 0.0
    try:
        # Quitar % y normalizar coma decimal (locale es-CO).
        cleaned = s.replace("%", "").replace(",", ".").strip()
        if not cleaned:
            return 0.0
        return float(cleaned)
    except (ValueError, TypeError):
        return 0.0
