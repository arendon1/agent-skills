"""
Subproceso auxiliar: extrae fechas de quiz/assign de una unidad.

Uso interno de cli_estado.py. Lee actividades JSON de stdin,
visita cada quiz/assign via CDP, devuelve fechas en stdout.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from browser_api import get_navegador, get_page_content, set_profile_dir
from bs4 import BeautifulSoup


def extraer_fechas_pagina(html: str) -> dict[str, str]:
    """Extrae fecha_apertura y fecha_cierre del HTML de quiz/assign."""
    soup = BeautifulSoup(html, "lxml")
    fechas = {"fecha_apertura": "", "fecha_cierre": ""}

    for row in soup.select("table.quizinfo tr, .assigninfo tr, tr"):
        cells = row.find_all(["th", "td"])
        if len(cells) >= 2:
            label = cells[0].get_text(strip=True).lower()
            value = cells[1].get_text(strip=True)
            if any(kw in label for kw in ("apertura", "abre", "open")):
                fechas["fecha_apertura"] = value
            elif any(kw in label for kw in ("cierre", "cierra", "close", "límite")):
                fechas["fecha_cierre"] = value

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
