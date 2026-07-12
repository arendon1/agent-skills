"""
Extractor de foros evaluables de Moodle.

Diferencias vs `extractor_foro.py` (flujo intro/Avisos/Consultas):
- Filtra por calificación > 0% (regex `(\\d+)%` en título).
- Devuelve TODOS los hilos principales, no solo del profesor.
- Cap de MAX_HILOS por foro (default 20) para no abusar del servidor.
- Cache por `discuss_id` (query string de `discuss.php`).
- Extrae metadata de la página del foro: título, vencimiento,
  indicaciones, actividad a realizar.

Output principal: `Unidad-X/Foros/<forum-slug>.md` con metadata +
hilos inline (uno por `##` section).
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime

from bs4 import BeautifulSoup, Tag

from browser_api import get_navegador, get_page_content

MAX_HILOS = 20  # cap de debates por foro


# ─────────────────────────────────────────────────────────────────────
# Detección de "es evaluable"
# ─────────────────────────────────────────────────────────────────────

_RE_PORCENTAJE = re.compile(r"\((\d+)%\)")


def es_evaluable(titulo: str) -> tuple[bool, int]:
    """
    Determina si un foro es evaluable por su título.

    Regla: el título debe contener `(X%)` con X>0. "(0%)" o sin match
    se considera no evaluable.

    Returns:
        (es_evaluable, porcentaje)
    """
    m = _RE_PORCENTAJE.search(titulo or "")
    if not m:
        return False, 0
    pct = int(m.group(1))
    return (pct > 0), pct


# ─────────────────────────────────────────────────────────────────────
# Extracción de metadata de la página del foro
# ─────────────────────────────────────────────────────────────────────

def _limpiar_texto(el: Tag) -> str:
    """Devuelve el texto de un nodo con saltos de línea entre bloques."""
    if el is None:
        return ""
    # Insert newlines between block elements for readability
    for br in el.find_all("br"):
        br.replace_with("\n")
    for li in el.find_all("li"):
        li.insert_before("\n• ")
        li.append("\n")
    return el.get_text(separator="\n", strip=True)


def _extraer_titulo(soup: BeautifulSoup) -> str:
    h1 = soup.select_one("h1, .page-header-headings h1")
    return h1.get_text(strip=True) if h1 else ""


def _extraer_vencimiento(soup: BeautifulSoup) -> str:
    """
    Busca el bloque `div[data-region='activity-dates']` con un
    <strong>Vencimiento:</strong> y parsea la fecha a ISO 8601.
    """
    container = soup.select_one("div[data-region='activity-dates']")
    if not container:
        return ""
    texto = container.get_text(separator=" ", strip=True)
    m = re.search(r"Vencimiento:\s*([^<\n]+)", texto)
    if not m:
        return ""
    fecha_str = m.group(1).strip()
    return _parsear_fecha_es(fecha_str)


_MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}


def _parsear_fecha_es(fecha_str: str) -> str:
    """
    Convierte "domingo, 19 de julio de 2026, 23:59" → "2026-07-19 23:59".
    Si no parsea, devuelve el string original.
    """
    m = re.search(
        r"(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de\s+(\d{4})(?:\s*,?\s*(\d{1,2}):(\d{2}))?",
        fecha_str,
        re.IGNORECASE,
    )
    if not m:
        return fecha_str
    dia = int(m.group(1))
    mes_nombre = m.group(2).lower()
    mes = _MESES_ES.get(mes_nombre, 0)
    anio = int(m.group(3))
    hora = m.group(4) or "00"
    minuto = m.group(5) or "00"
    if not mes:
        return fecha_str
    try:
        dt = datetime(anio, mes, dia, int(hora), int(minuto))
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return fecha_str


def _extraer_bloque_desde_intro(
    soup: BeautifulSoup, marcador_substr: str
) -> str:
    """
    Busca dentro de `#region-main` (intro del foro) un párrafo o div
    cuyo texto contenga `marcador_substr` (ej: "Para participar siga
    las instrucciones" o "Pregunta orientadora"). Devuelve el texto del
    contenedor padre (la caja completa).
    """
    region = soup.select_one("#region-main, .activity-information")
    if not region:
        return ""

    # Buscar un nodo cuyo texto EMPIE con el marcador (case-insensitive)
    target_lower = marcador_substr.lower()
    for el in region.find_all(["p", "div", "li", "section"]):
        text = el.get_text(" ", strip=True).lower()
        if not text:
            continue
        if target_lower in text:
            # Subir al contenedor padre que sea un bloque "tipo caja"
            candidato = el
            for _ in range(5):
                if candidato.parent and candidato.parent.name in (
                    "div", "section", "article"
                ):
                    candidato = candidato.parent
                else:
                    break
            return _limpiar_texto(candidato)
    return ""


def _extraer_introduccion_foro(soup: BeautifulSoup) -> tuple[str, str]:
    """
    Devuelve (indicaciones, actividad) parseando la intro del foro.

    Heurística: la primera caja que contiene "Para participar" o
    "instrucciones" → indicaciones. La primera caja que contiene
    "Pregunta orientadora" → actividad.
    """
    indicaciones = _extraer_bloque_desde_intro(
        soup, "para participar siga las instrucciones"
    )
    actividad = _extraer_bloque_desde_intro(soup, "pregunta orientadora")
    return indicaciones, actividad


# ─────────────────────────────────────────────────────────────────────
# Extracción de la lista de hilos
# ─────────────────────────────────────────────────────────────────────

_RE_DISCUSS_ID = re.compile(r"discuss\.php\?d=(\d+)")


def _discutir_id_de_url(url: str) -> str:
    m = _RE_DISCUSS_ID.search(url or "")
    return m.group(1) if m else ""


def _parsear_contador_replicas(texto: str) -> int:
    """Lee "3" o "3 réplicas" → 3."""
    m = re.search(r"(\d+)", texto or "")
    return int(m.group(1)) if m else 0


def _autor_y_fecha_de_celda(celda: Tag) -> tuple[str, str]:
    """
    Moodle muestra el autor y la fecha juntos, ej:
    "Juan Fernando Q... 7 jul 2026"
    o separados con <time>. Devuelve (autor, fecha_iso_o_cruda).
    """
    if celda is None:
        return "", ""
    time_el = celda.select_one("time")
    if time_el:
        fecha_dt = time_el.get("datetime") or time_el.get_text(strip=True)
        # Quitar el bloque time del HTML y re-leer para el autor
        from copy import copy
        clon = copy(celda)
        for t in clon.select("time"):
            t.decompose()
        autor = clon.get_text(" ", strip=True)
        return autor, fecha_dt

    texto = celda.get_text(" ", strip=True)
    m = re.search(
        r"(.+?)\s+(\d{1,2}\s+[a-záéíóú]{3,}\s+\d{4})\s*$",
        texto,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return texto, ""


def extraer_hilos_listado(soup: BeautifulSoup) -> list[dict]:
    """
    Lee la tabla/listado de hilos principales del foro.

    Devuelve hasta MAX_HILOS con: discuss_id, titulo, autor, fecha,
    ultimo_mensaje_autor, ultimo_mensaje_fecha, replicas, url.
    """
    filas = soup.select(
        'table.forumheaderlist tr, .discussion-list tr, '
        '[data-region="discussion-list"] tr'
    )
    hilos: list[dict] = []
    for fila in filas:
        titulo_el = fila.select_one('a[href*="discuss.php"]')
        if not titulo_el:
            continue
        url = titulo_el.get("href", "")
        discuss_id = _discutir_id_de_url(url)
        if not discuss_id:
            continue

        titulo = titulo_el.get_text(strip=True)
        celdas = fila.find_all(["td", "th"])
        # Heurística: col 0=debate, col 1=comenzado por, col 2=último
        # mensaje, col 3=réplicas, col 4=suscribir
        autor, fecha = "", ""
        ult_autor, ult_fecha = "", ""
        replicas = 0

        if len(celdas) >= 4:
            autor, fecha = _autor_y_fecha_de_celda(celdas[1])
            ult_autor, ult_fecha = _autor_y_fecha_de_celda(celdas[2])
            # Réplicas puede ser número o "0"/"3" sin texto
            contador = celdas[3].get_text(" ", strip=True)
            # A veces tiene un badge y un número separado
            num = celdas[3].select_one(".badge, .count, strong")
            if num:
                replicas = _parsear_contador_replicas(num.get_text(strip=True))
            else:
                # Tomar el primer número entero
                nums = re.findall(r"\b\d+\b", contador)
                if nums:
                    replicas = int(nums[0])
        else:
            # Fallback: si no hay celdas claras, intentar selectores
            autor_el = fila.select_one(".author, .starter")
            if autor_el:
                autor, fecha = _autor_y_fecha_de_celda(autor_el)
            ult_el = fila.select_one(".lastpost")
            if ult_el:
                ult_autor, ult_fecha = _autor_y_fecha_de_celda(ult_el)
            repl_el = fila.select_one(".replies, .discussion-replies")
            if repl_el:
                replicas = _parsear_contador_replicas(repl_el.get_text(" "))

        hilos.append({
            "discuss_id": discuss_id,
            "titulo": titulo,
            "autor": autor,
            "fecha": fecha,
            "ultimo_mensaje_autor": ult_autor,
            "ultimo_mensaje_fecha": ult_fecha,
            "replicas": replicas,
            "url": url,
        })
        if len(hilos) >= MAX_HILOS:
            break

    return hilos


# ─────────────────────────────────────────────────────────────────────
# API principal
# ─────────────────────────────────────────────────────────────────────

def extraer_datos_foro(url_foro: str) -> dict:
    """
    Visita la página del foro y extrae: título, vencimiento,
    indicaciones, actividad, y la lista de hilos.

    Returns:
        dict con keys: titulo, vencimiento, indicaciones, actividad,
        es_evaluable, porcentaje, url, hilos.
    """
    get_navegador()(url_foro)
    soup = BeautifulSoup(get_page_content(), "lxml")

    titulo = _extraer_titulo(soup)
    vencimiento = _extraer_vencimiento(soup)
    indicaciones, actividad = _extraer_introduccion_foro(soup)
    hilos = extraer_hilos_listado(soup)
    evaluable, porcentaje = es_evaluable(titulo)

    return {
        "titulo": titulo,
        "vencimiento": vencimiento,
        "indicaciones": indicaciones,
        "actividad": actividad,
        "es_evaluable": evaluable,
        "porcentaje": porcentaje,
        "url": url_foro,
        "hilos": hilos,
    }


# ─────────────────────────────────────────────────────────────────────
# Extracción del primer post (con cache por discuss_id)
# ─────────────────────────────────────────────────────────────────────

def _extraer_primer_post_raw(url_discusion: str) -> str:
    """
    Navega a la discusión y devuelve SOLO el primer post, sin replies.
    Sin cache.
    """
    try:
        get_navegador()(url_discusion)
        soup = BeautifulSoup(get_page_content(), "lxml")
        primer_post = soup.select_one(
            ".firstpost, article.forum-post-container, #p1, "
            ".forumpost, [data-region='post-content']"
        )
        if not primer_post:
            return ""
        contenido_el = primer_post.select_one(
            ".post-message, .content, .post-content, "
            "[data-region='post-content']"
        )
        if contenido_el:
            return _limpiar_texto(contenido_el)
        return _limpiar_texto(primer_post)
    except Exception as e:  # noqa: BLE001
        print(f"[WARN] Error extrayendo post de {url_discusion}: {e}")
        return ""


def cargar_cache_foros(ruta_curso: str) -> dict:
    """Lee `_cache/foros_cache.json` o {} si no existe."""
    path = os.path.join(ruta_curso, "_cache", "foros_cache.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def guardar_cache_foros(ruta_curso: str, cache: dict) -> None:
    """Escribe `_cache/foros_cache.json` con indent=2."""
    cache_dir = os.path.join(ruta_curso, "_cache")
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, "foros_cache.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def extraer_primer_post_cached(
    discuss_id: str, url: str, cache: dict
) -> str:
    """
    Devuelve el contenido del primer post. Si `discuss_id` ya está
    en `cache`, no re-abre la página.
    """
    entry = cache.get(discuss_id)
    if entry and "contenido" in entry:
        return entry["contenido"]

    contenido = _extraer_primer_post_raw(url)
    cache[discuss_id] = {
        "titulo": entry.get("titulo", "") if entry else "",
        "autor": entry.get("autor", "") if entry else "",
        "fecha": entry.get("fecha", "") if entry else "",
        "url": url,
        "contenido": contenido,
        "extraido_en": datetime.now().isoformat(),
    }
    return contenido
