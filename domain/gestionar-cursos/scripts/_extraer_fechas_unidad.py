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


# Etiquetas que Moodle usa en <strong> dentro de [data-region=activity-dates]
# o en celdas <th> de tablas .quizinfo / .assigninfo. La etiqueta cambia de
# tiempo presente ("Cierra:") a pasado ("Cerró:") cuando la actividad ya
# cerró — el extractor debe reconocer AMBAS formas. Lo mismo aplica a
# "Apertura" / "Abrió". Se incluyen también plurales y variantes para foros
# y workshops.
_LABELS_APERTURA = (
    "abrió", "abre", "apertura", "abierto", "abierta", "abiertas",
    "open", "opens", "inicio", "comienzo", "disponible desde",
    "envíos abiertos", "envío abierto", "evaluación abierta",
)
_LABELS_CIERRE = (
    "cerró", "cierra", "cierre", "cerrado", "cerrada", "cerradas",
    "close", "closes", "closed", "vence", "vencido", "vencida",
    "vencimiento", "límite", "expira", "expirado", "deadline",
    "cierre de envíos", "cierre de evaluaciones",
)


def _es_label_apertura(label: str) -> bool:
    """True si la etiqueta se refiere a una fecha de apertura."""
    label = label.lower()
    return any(kw in label for kw in _LABELS_APERTURA)


def _es_label_cierre(label: str) -> bool:
    """True si la etiqueta se refiere a una fecha de cierre."""
    label = label.lower()
    return any(kw in label for kw in _LABELS_CIERRE)


def extraer_fechas_pagina(html: str) -> dict[str, str]:
    """Extrae fecha_apertura y fecha_cierre del HTML de quiz/assign.

    Moodle moderno expone las fechas en un div[data-region='activity-dates']
    con etiquetas <strong>Abrió:</strong> / <strong>Cierra:</strong>. Cuando
    la actividad ya cerró, la etiqueta de cierre pasa a <strong>Cerró:</strong>
    (pretérito). Esta función reconoce AMBAS formas.

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
            # En workshops hay varias fases (Envíos abiertos, Cierre de envíos,
            # Apertura de evaluaciones, Cierre de evaluaciones). El último match
            # gana: para el cierre, el relevante es "Cierre de evaluaciones"
            # (fin de la fase de evaluación entre pares). Para la apertura, el
            # relevante es "Apertura de evaluaciones" (inicio de la fase
            # evaluable para el estudiante).
            if _es_label_apertura(label):
                fechas["fecha_apertura"] = _es_a_iso(value) or value
            elif _es_label_cierre(label):
                fechas["fecha_cierre"] = _es_a_iso(value) or value
        if fechas["fecha_apertura"] or fechas["fecha_cierre"]:
            return fechas

    # --- Legacy: tabla .quizinfo / .assigninfo ---
    for row in soup.select("table.quizinfo tr, .assigninfo tr, tr"):
        cells = row.find_all(["th", "td"])
        if len(cells) >= 2:
            label = cells[0].get_text(strip=True).lower()
            value = cells[1].get_text(strip=True)
            if _es_label_apertura(label):
                fechas["fecha_apertura"] = _es_a_iso(value) or value
            elif _es_label_cierre(label):
                fechas["fecha_cierre"] = _es_a_iso(value) or value

    return fechas


# Estados semánticos de la celda de estado del mod_assign (Moodle):
#   submissionstatussubmitted / submissionstatusnotsubmitted /
#   submissionstatusdraft / submissionstatusgraded / submissionstatusreopened
_SUBMISSION_CLASS_SUBMITTED = ("submitted", "graded", "reopened")
_SUBMISSION_TXT_SIN = ("sin entrega", "no entregado", "no ha entregado", "no enviado",
                       "todavía no se han realizado envíos", "todavía no se ha entregado",
                       "aún no se ha enviado", "aun no se ha enviado",
                       "no se han realizado envíos", "no se ha entregado", "aún no se ha entregado")
_SUBMISSION_TXT_ENTREGADO = ("enviado para calificar", "entregado", "calificado", "aceptado", "enviado")
_QUIZ_TXT_SIN = ("sin intentos", "no hay intentos", "aún no has realizado", "aun no has realizado")
_QUIZ_TXT_ENTREGADO = ("revisar intento", "continuar el último intento", "resultado del intento",
                       "intento finalizado", "intento terminado", "intentos utilizados")


def extraer_estado_entrega(html: str) -> str:
    """Determina el estado de ENTREGA leyendo la PÁGINA de la actividad (assign/quiz).

    NO se infiere desde la nota: lee la página. Devuelve:
        "Entregado" | "Sin entrega" | "Borrador" | "Sin intentos" | "Sin verificar"

    Prioridad:
      1. mod_assign: la celda del estado lleva una clase semántica
         (`submissionstatussubmitted`, `submissionstatusnotsubmitted`, `submissionstatusdraft`).
      2. mod_quiz: región de intentos.
      3. Contenedores de estado reconocidos (sin caer al texto plano, para no
         disparar falsos positivos con "borrador"/"entregar" de la navegación).
    """
    soup = BeautifulSoup(html, "lxml")

    def txt(node) -> str:
        return (node.get_text(" ", strip=True) or "").lower()

    # 1) mod_assign — celda semántica del estado
    cell = soup.select_one("td[class*='submissionstatus']")
    if cell is not None:
        cls = " ".join(cell.get("class", []))
        t = txt(cell)
        if "notsubmitted" in cls or any(k in t for k in _SUBMISSION_TXT_SIN):
            return "Sin entrega"
        if "draft" in cls or "borrador" in t:
            return "Borrador"
        if any(k in cls for k in _SUBMISSION_CLASS_SUBMITTED) or any(k in t for k in _SUBMISSION_TXT_ENTREGADO):
            return "Entregado"

    # 2) mod_quiz — estado del intento en el contenido principal
    #    (el quizinfo solo trae config: "Intentos permitidos", no el estado).
    quiz = (
        soup.select_one("#region-main, div[role='main'], .generalbox")
        or soup.select_one("div[data-region='quizinfo'], table.quizinfo, div[class*='quizinfo']")
    )
    if quiz is not None:
        t = txt(quiz)
        if any(k in t for k in _QUIZ_TXT_SIN) or "sin intentos" in t or "no ha realizado" in t:
            return "Sin intentos"
        # AND protege de "Intentos permitidos" (contiene "intento" como subcadena).
        if any(k in t for k in _QUIZ_TXT_ENTREGADO) or "sus intentos" in t or ("intento" in t and "finalizado" in t):
            return "Entregado"

    # 3) contenedores de estado de entrega reconocidos
    for sel in ("div.submissionstatustable", "table.submissionstatustable",
                "div[data-region='submissionstatus']", "#fitem_id_submissionstatussubmissionstatustbl"):
        node = soup.select_one(sel)
        if node is not None:
            t = txt(node)
            if any(k in t for k in _SUBMISSION_TXT_SIN):
                return "Sin entrega"
            if "borrador" in t:
                return "Borrador"
            if any(k in t for k in _SUBMISSION_TXT_ENTREGADO):
                return "Entregado"

    return "Sin verificar"


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
            fechas["estado_entrega"] = extraer_estado_entrega(html)
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
