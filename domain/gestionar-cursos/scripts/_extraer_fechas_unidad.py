"""
Subproceso auxiliar: extrae fechas de quiz/assign de una unidad.

Uso interno de cli_estado.py. Lee actividades JSON de stdin,
visita cada quiz/assign via CDP, devuelve fechas en stdout.
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from browser_api import get_navegador, get_page_content, set_profile_dir
from bs4 import BeautifulSoup

# Mapping Spanish month names → number.
_MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5,
    "junio": 6, "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9,
    "octubre": 10, "noviembre": 11, "diciembre": 12,
}

_RE_FECHA = re.compile(
    r"(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de\s+(\d{4})(?:[,]?\s+(\d{1,2}):(\d{2}))?",
    re.IGNORECASE,
)


def _es_a_iso(texto: str) -> str:
    """Convierte 'lunes, 6 de julio de 2026, 00:00' → '2026-07-06' (o '2026-07-06T00:00')."""
    if not texto:
        return ""
    m = _RE_FECHA.search(texto)
    if not m:
        return ""
    dia = int(m.group(1))
    mes = _MESES.get(m.group(2).lower())
    anio = int(m.group(3))
    hh, mm = m.group(4), m.group(5)
    if not mes:
        return ""
    base = f"{anio:04d}-{mes:02d}-{dia:02d}"
    if hh is not None and mm is not None:
        return f"{base}T{int(hh):02d}:{int(mm):02d}"
    return base


def extraer_fechas_pagina(html: str) -> dict[str, str]:
    """Extrae fecha_apertura y fecha_cierre del HTML de quiz/assign.

    Moodle moderno expone las fechas en un div[data-region='activity-dates']
    con etiquetas <strong>Abrió:</strong> / <strong>Cierra:</strong>.
    Formato legacy: tabla .quizinfo / .assigninfo.
    """
    soup = BeautifulSoup(html, "lxml")
    fechas = {"fecha_apertura": "", "fecha_cierre": ""}

    # --- Nuevo: div[data-region=activity-dates] ---
    cont = soup.select_one("[data-region='activity-dates'], .activity-dates")
    if cont:
        for div in cont.find_all("div"):
            strong = div.find("strong")
            if not strong:
                continue
            label = strong.get_text(strip=True).lower()
            strong.extract()  # quita la etiqueta para que get_text dé el valor
            value = div.get_text(" ", strip=True)
            if any(kw in label for kw in ("abrió", "abre", "apertura", "abiert", "open")):
                fechas["fecha_apertura"] = _es_a_iso(value) or value
            elif any(kw in label for kw in ("cierra", "cierre", "cerrad", "close", "límite", "vencimiento", "vence")):
                fechas["fecha_cierre"] = _es_a_iso(value) or value
        if fechas["fecha_apertura"] or fechas["fecha_cierre"]:
            return fechas

    # --- Legacy: tabla .quizinfo / .assigninfo ---
    for row in soup.select("table.quizinfo tr, .assigninfo tr, tr"):
        cells = row.find_all(["th", "td"])
        if len(cells) >= 2:
            label = cells[0].get_text(strip=True).lower()
            value = cells[1].get_text(strip=True)
            if any(kw in label for kw in ("apertura", "abre", "open")):
                fechas["fecha_apertura"] = _es_a_iso(value) or value
            elif any(kw in label for kw in ("cierre", "cierra", "close", "límite")):
                fechas["fecha_cierre"] = _es_a_iso(value) or value

    return fechas


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile-dir", "-p", default=None,
                       help="Directorio de perfil Chrome")
    args = parser.parse_args()

    if args.profile_dir:
        set_profile_dir(args.profile_dir)

    payload = sys.stdin.read()
    if not payload.strip():
        json.dump({}, sys.stdout)
        return

    try:
        actividades = json.loads(payload)
    except json.JSONDecodeError:
        json.dump({}, sys.stdout)
        return

    resultados = {}
    navegador = get_navegador()

    for act in actividades:
        url = act.get("url", "")
        if not url:
            continue
        try:
            navegador(url)
            html = get_page_content()
            fechas = extraer_fechas_pagina(html)
            # Extraer key de URL
            from urllib.parse import urlparse
            parsed = urlparse(url)
            key = parsed.path + ("?" + parsed.query if parsed.query else "")
            fechas["nombre"] = act.get("nombre", "")
            resultados[key] = fechas
        except Exception:
            continue

    json.dump(resultados, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
