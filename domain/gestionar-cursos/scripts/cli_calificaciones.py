#!/usr/bin/env python3
"""
CLI calificaciones: extraer calificaciones del gradebook de Moodle.

Uso:
    uv run python cli_calificaciones.py <CARPETA_CURSO>
    uv run python cli_calificaciones.py <CARPETA_CURSO> --dry-run

Hace:
1. Verifica sesión Moodle (vía browser_api / navegador_cdp)
2. Navega al gradebook del usuario del curso
3. Extrae calificaciones con BeautifulSoup
4. Actualiza el `snapshot.json` con campo `calificacion` por actividad
5. Actualiza cada archivo .md de actividad con sección "## Calificación"
6. Persiste cache crudo en `_cache/gradebook_<courseid>.html` y JSON en
   `_cache/calificaciones_<courseid>.json`

Lección aprendida (2026-2-B1, Línea de Énfasis 1):
- El gradebook es la única fuente de verdad para notas de actividades
  evaluables (no `PGA`, no `snapshot`).
- El HTML del gradebook tiene acciones con texto "Análisis de
  calificaciones" mezcladas con la nota. El parser debe eliminar
  el `.action-menu` antes de leer la nota.
- `state-icons`: `fa-check text-success` = aprobado,
  `fa-remove text-danger` = reprobado. Sin icono = pendiente.
- El "Contribución al total del curso" es la nota sobre 100 puntos
  que ya se computó con la ponderación real del curso.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Asegurar que scripts/ esté en path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _parsing import _parse_porcentaje
from navegador_cdp import get_driver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

console = Console()

# Ruta al chromedriver cacheado por selenium-manager
_CHROMEDRIVER = (
    "/Users/andres.rendon/.cache/selenium/chromedriver/"
    "mac-arm64/150.0.7871.115/chromedriver"
)


def _abrir_driver_cdp() -> "webdriver.Chrome":
    """Conecta Selenium a Chrome vía CDP localhost:9222.

    Reutiliza la sesión activa del usuario. Si Chrome no tiene
    pages abiertas, abre una.
    """
    import urllib.request

    # Verificar que CDP esté disponible
    try:
        with urllib.request.urlopen("http://localhost:9222/json/version", timeout=2) as r:
            pass
    except Exception as e:
        raise RuntimeError(
            f"Chrome CDP no disponible en localhost:9222: {e}. "
            "Asegúrate de que Chrome esté abierto con --remote-debugging-port=9222"
        ) from e

    # Asegurar que haya al menos una página abierta
    try:
        with urllib.request.urlopen("http://localhost:9222/json/list", timeout=2) as r:
            import json as _json
            targets = _json.loads(r.read())
            has_page = any(t.get("type") == "page" for t in targets)
            if not has_page:
                # Crear nueva tab
                req = urllib.request.Request(
                    "http://localhost:9222/json/new?about:blank", method="PUT"
                )
                urllib.request.urlopen(req, timeout=2)
    except Exception:
        pass

    opts = Options()
    opts.add_experimental_option("debuggerAddress", "localhost:9222")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    service = Service(executable_path=_CHROMEDRIVER)
    from selenium import webdriver
    return webdriver.Chrome(service=service, options=opts)


def _verificar_sesion(driver) -> bool:
    """Verifica que la sesión Moodle esté activa."""
    from time import sleep
    driver.get("https://aulavirtual.uniremington.edu.co/my/")
    sleep(2)
    if "login/index.php" in driver.current_url:
        return False
    body = driver.find_element(By.TAG_NAME, "body").text
    if "Usted no se ha identificado" in body:
        return False
    if "Andres Felipe Rendon Hernandez" in body or "Área personal" in body:
        return True
    return False


def _courseid_desde_sitemap(ruta_curso: str) -> str:
    """Extrae course ID de SITEMAP.md o AGENTS.md."""
    for filename in ("AGENTS.md", "SITEMAP.md"):
        path = os.path.join(ruta_curso, filename)
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as f:
            text = f.read()
        m = re.search(r"course/view\.php\?id=(\d+)", text)
        if m:
            return m.group(1)
    raise RuntimeError(f"No se pudo extraer course ID de {ruta_curso}")


def _descargar_gradebook(driver, courseid: str) -> str:
    """Navega al gradebook del usuario y devuelve HTML."""
    from time import sleep
    url = (
        f"https://aulavirtual.uniremington.edu.co/grade/report/user/"
        f"index.php?id={courseid}"
    )
    driver.get(url)
    sleep(3)
    if "login/index.php" in driver.current_url:
        raise RuntimeError("Sesión expirada. Inicia sesión en Moodle primero.")
    return driver.page_source


def _parsear_gradebook(html: str) -> list[dict]:
    """Parsea el HTML del gradebook y devuelve lista de items."""
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.find_all("th", class_=re.compile(r"level[23] item.*column-itemname"))

    items = []
    for th in rows:
        tr = th.find_parent("tr")
        row_id = th.get("id", "")

        a = th.find("a", class_="gradeitemheader")
        if not a:
            continue
        nombre = a.get_text(strip=True)
        url = a.get("href", "")

        dim = th.find("span", class_="dimmed_text")
        tipo = dim.get("title", "") if dim else ""

        # Ponderación dentro de la categoría
        weight_td = tr.find("td", class_="column-weight")
        weight = weight_td.get_text(strip=True) if weight_td else ""

        # Calificación
        grade_td = tr.find("td", class_="column-grade")
        aprobado = False
        reprobado = False
        grade_num = ""
        if grade_td:
            aprobado = "fa-check text-success" in str(grade_td)
            reprobado = "fa-remove text-danger" in str(grade_td)
            for am in grade_td.find_all("div", class_="action-menu"):
                am.decompose()
            div = grade_td.find("div", class_="d-flex")
            if div:
                grade_num = (
                    div.get_text(strip=True)
                    .replace("Aprobado", "")
                    .replace("Reprobado", "")
                    .strip()
                )
        if not grade_num or grade_num == "-":
            grade_num = ""
            estado = "Pendiente"
        elif aprobado:
            estado = "Aprobado"
        elif reprobado:
            estado = "Reprobado"
        else:
            estado = "Calificado"

        range_td = tr.find("td", class_="column-range")
        rango = range_td.get_text(strip=True) if range_td else ""

        pct_td = tr.find("td", class_="column-percentage")
        porcentaje = pct_td.get_text(strip=True) if pct_td else ""

        contrib_td = tr.find("td", class_="column-contributiontocoursetotal")
        aporte_curso = contrib_td.get_text(strip=True) if contrib_td else ""

        fb_td = tr.find("td", class_="column-feedback")
        feedback = fb_td.get_text(strip=True) if fb_td else ""

        # id_mod desde URL
        mod_id = ""
        if url:
            m_id = re.search(r"id=(\d+)", url)
            if m_id:
                mod_id = m_id.group(1)

        items.append({
            "row_id": row_id,
            "nombre": nombre,
            "tipo": tipo,
            "url": url,
            "mod_id": mod_id,
            "ponderacion_pct": weight,
            "calificacion": grade_num,
            "rango": rango,
            "porcentaje": porcentaje,
            "aporte_curso": aporte_curso,
            "estado": estado,
            "feedback": feedback,
        })
    return items


def _seccion_md_calificacion(item: dict, courseid: str) -> str:
    """Genera la sección markdown '## Calificación' para el .md de la actividad."""
    if item["calificacion"]:
        nota_str = f'{item["calificacion"]} / {item["rango"]}'
    else:
        nota_str = "— (sin entregar)"

    lineas = [
        "",
        "## Calificación",
        "",
        "| Campo | Valor |",
        "|-------|-------|",
        f"| Nota | {nota_str} |",
        f"| Estado | {item['estado']} |",
        f"| Ponderación (categoría) | {item['ponderacion_pct'] or '—'} |",
        f"| Porcentaje sobre rango | {item['porcentaje'] or '—'} |",
        f"| Aporte al total del curso | {item['aporte_curso'] or '0,00 %'} |",
    ]
    if item["feedback"]:
        lineas += ["", f"> **Retroalimentación del docente:** {item['feedback']}"]
    lineas += [
        "",
        f"_Fuente: [Gradebook del curso](https://aulavirtual.uniremington.edu.co/grade/report/user/index.php?id={courseid}) — capturado {datetime.now().strftime('%Y-%m-%d %H:%M')}_",
        "",
    ]
    return "\n".join(lineas)


def _actualizar_md_actividad(path_md: str, item: dict, courseid: str):
    """Agrega o reemplaza la sección ## Calificación en el .md de la actividad."""
    with open(path_md, encoding="utf-8") as f:
        contenido = f.read()

    seccion = _seccion_md_calificacion(item, courseid)
    # Buscar sección existente
    m = re.search(
        r"\n## Calificación\s*\n.*?(?=\n## |\Z)",
        contenido,
        re.DOTALL,
    )
    if m:
        contenido = contenido[: m.start()] + seccion.rstrip() + "\n" + contenido[m.end():]
    else:
        contenido = contenido.rstrip() + "\n" + seccion

    with open(path_md, "w", encoding="utf-8") as f:
        f.write(contenido)


# Alias canónicos nombre-PGA → nombre de archivo. Se consultan primero
# antes de cualquier matching heurístico. Cada entrada es (regex_nombre, regex_stem).
_ALIAS_PGA_A_MD = [
    (r"^Prueba Inicial\b",         r"^PruebaInicial\b"),
    (r"^Primer Parcial\b",         r"^Parcial-?1\b"),
    (r"^Segundo Parcial\b",        r"^Parcial-?2\b"),
    (r"^Tercer Parcial\b",         r"^Parcial-?3\b"),
    (r"^Lecci[oó]n\s*1\b",         r"^Lecci[oó]n\s*1\b"),
    (r"^Lecci[oó]n\s*2\b",         r"^Lecci[oó]n\s*2\b"),
    (r"^Lecci[oó]n\s*3\b",         r"^Lecci[oó]n\s*3\b"),
    (r"^Final\b",                  r"^Final\b"),
    (r"^Taller\b.*env[ií]o",       r"^Taller\b"),
    (r"^Taller\b.*evaluaci[oó]n",  r"^Taller\b"),
    (r"^Taller\b",                 r"^Taller\b"),
    (r"^.*Unidad\s*1\b.*sistemas\s*inform",     r"^Gu[ií]a\s+de\s+Estudio.*Unidad\s*1"),
    (r"^.*Unidad\s*2\b.*Tecnolog", r"^Gu[ií]a\s+de\s+Estudio.*Unidad\s*2"),
    (r"^.*Unidad\s*1\b",            r"^.*Unidad-?1\b"),
    (r"^.*Unidad\s*2\b",            r"^.*Unidad-?2\b"),
]


def _normalizar(s: str) -> str:
    """Minúsculas + sin acentos + colapsa espacios."""
    s = s.lower()
    repl = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "ñ": "n", "ü": "u",
    }
    for k, v in repl.items():
        s = s.replace(k, v)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _encontrar_md_para_item(ruta_curso: str, item: dict) -> str | None:
    """Encuentra el archivo .md de la actividad que coincide con el item."""
    nombre = item["nombre"]
    nombre_base = re.sub(r"\s*\([\d%]+[^)]*\)", "", nombre).strip()
    nombre_base = re.sub(r"\s*\(envío\)", "", nombre_base, flags=re.IGNORECASE).strip()
    nombre_base = re.sub(r"\s*\(evaluación\)", "", nombre_base, flags=re.IGNORECASE).strip()

    # 1) Buscar alias explícitos
    for patron_nombre, patron_stem in _ALIAS_PGA_A_MD:
        if re.search(patron_nombre, nombre_base, re.IGNORECASE):
            for unidad in sorted(Path(ruta_curso).glob("Unidad-*/actividades/")):
                for md in sorted(unidad.glob("*.md")):
                    if re.search(patron_stem, md.stem, re.IGNORECASE):
                        return str(md)
            for sub in ("contenido", "materiales"):
                for unidad in sorted(Path(ruta_curso).glob(f"Unidad-*/{sub}/")):
                    for md in sorted(unidad.glob("*.md")):
                        if re.search(patron_stem, md.stem, re.IGNORECASE):
                            return str(md)

    # 2) Matching exacto por nombre normalizado
    nombre_norm = _normalizar(nombre_base)
    for unidad in sorted(Path(ruta_curso).glob("Unidad-*/actividades/")):
        for md in sorted(unidad.glob("*.md")):
            stem_base = re.sub(r"\s*\([\d%]+[^)]*\)", "", md.stem).strip()
            if _normalizar(stem_base) == nombre_norm:
                return str(md)

    # 3) Matching por subsecuencia de tokens
    tokens_item = set(_normalizar(nombre_base).split())
    tokens_item.discard("unidad")  # ignorar palabra "unidad" en matching
    mejor = None
    mejor_score = 0
    for unidad in sorted(Path(ruta_curso).glob("Unidad-*/actividades/")):
        for md in sorted(unidad.glob("*.md")):
            stem_base = re.sub(r"\s*\([\d%]+[^)]*\)", "", md.stem).strip()
            tokens_stem = set(_normalizar(stem_base).split())
            if not tokens_stem:
                continue
            comun = tokens_item & tokens_stem
            score = len(comun) / max(len(tokens_stem), 1)
            if score > mejor_score and score >= 0.5:
                mejor = str(md)
                mejor_score = score

    # 4) Para foros evaluables
    if mejor is None and "foro" in nombre.lower():
        for unidad in sorted(Path(ruta_curso).glob("Unidad-*/Foros/")):
            for md in sorted(unidad.glob("*.md")):
                if _normalizar(nombre_base) in _normalizar(md.stem):
                    return str(md)

    return mejor


def _actualizar_snapshot(snapshot_path: str, items: list[dict]):
    """Actualiza snapshot.json con campo calificacion por actividad."""
    with open(snapshot_path, encoding="utf-8") as f:
        snapshot = json.load(f)

    actividades = snapshot.get("actividades", {})
    ahora = datetime.now().isoformat()

    for item in items:
        mod_id = item["mod_id"]
        if not mod_id:
            continue
        # Buscar key que termine con id={mod_id}
        matched = None
        for key in actividades:
            if f"id={mod_id}" in key:
                matched = key
                break
        if matched is None:
            continue
        actividades[matched]["calificacion"] = {
            "nota": item["calificacion"] or None,
            "estado": item["estado"],
            "rango": item["rango"],
            "porcentaje": item["porcentaje"],
            "aporte_curso": item["aporte_curso"],
            "ponderacion_categoria": item["ponderacion_pct"],
            "actualizado": ahora,
        }

    snapshot["calificaciones_capturadas"] = ahora
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)


def _imprimir_resumen(items: list[dict]):
    """Imprime tabla resumen de calificaciones."""
    pga = [i for i in items if "Contenido interactivo" not in i["tipo"]]
    table = Table(title="Calificaciones PGA (excluye Contenido interactivo)", show_lines=False)
    table.add_column("Actividad", style="cyan", no_wrap=True)
    table.add_column("Tipo", style="dim")
    table.add_column("Nota", justify="right")
    table.add_column("Rango", justify="right", style="dim")
    table.add_column("Pond. cat.", justify="right", style="dim")
    table.add_column("Aporte curso", justify="right", style="green")
    table.add_column("Estado")

    for it in pga:
        nota_display = it["calificacion"] or "—"
        estilo = (
            "bold green" if it["estado"] == "Aprobado"
            else "bold red" if it["estado"] == "Reprobado"
            else "dim"
        )
        table.add_row(
            it["nombre"],
            it["tipo"],
            nota_display,
            it["rango"] or "—",
            it["ponderacion_pct"] or "—",
            it["aporte_curso"] or "0,00 %",
            f"[{estilo}]{it['estado']}[/{estilo}]",
        )
    console.print(table)

    # Aporte total al curso (tolera "-", "", "Sin calificar" sin crashear).
    aporte_total = sum(_parse_porcentaje(it["aporte_curso"]) for it in items)
    console.print(
        Panel(
            f"[bold]Aporte total al curso: {aporte_total:.2f}%[/bold]\n"
            f"Items calificados: {sum(1 for it in items if it['calificacion'])} / {len(items)}",
            title="Resumen",
        )
    )


def main():
    parser = argparse.ArgumentParser(
        description="Extraer calificaciones del gradebook de Moodle"
    )
    parser.add_argument("ruta_curso", help="Carpeta del curso (ej: 2607B04G1-línea-de-énfasis-1)")
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar, no escribir")
    args = parser.parse_args()

    ruta_curso = os.path.abspath(args.ruta_curso)
    if not os.path.isdir(ruta_curso):
        raise SystemExit(f"Carpeta no existe: {ruta_curso}")

    courseid = _courseid_desde_sitemap(ruta_curso)
    console.print(f"[bold blue]Curso:[/bold blue] {ruta_curso}")
    console.print(f"[bold blue]Course ID:[/bold blue] {courseid}")

    driver = _abrir_driver_cdp()
    try:
        if not _verificar_sesion(driver):
            raise SystemExit("Sesión Moodle inactiva. Inicia sesión y reintenta.")
        console.print("[green]✓[/green] Sesión Moodle verificada")

        html = _descargar_gradebook(driver, courseid)
        console.print(f"[green]✓[/green] Gradebook descargado ({len(html):,} chars)")

        # Guardar HTML crudo para auditoría
        cache_dir = os.path.join(ruta_curso, "_cache")
        os.makedirs(cache_dir, exist_ok=True)
        html_path = os.path.join(cache_dir, f"gradebook_{courseid}.html")
        if not args.dry_run:
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)

        items = _parsear_gradebook(html)
        console.print(f"[green]✓[/green] {len(items)} items extraídos")

        # Persistir JSON + .md + snapshot SOLO si no es dry-run.
        # El resumen se imprime SIEMPRE (incluso en dry-run), envuelto en
        # try/except para que un valor raro del gradebook (ej. "-" en un
        # campo que la tabla espera float) no tumbe la persistencia.
        if not args.dry_run:
            json_path = os.path.join(cache_dir, f"calificaciones_{courseid}.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(items, f, indent=2, ensure_ascii=False)

            # Actualizar .md de actividades
            actualizados = 0
            for item in items:
                md_path = _encontrar_md_para_item(ruta_curso, item)
                if not md_path:
                    console.print(
                        f"  [yellow]⚠ No se encontró .md para:[/yellow] {item['nombre']}"
                    )
                    continue
                _actualizar_md_actividad(md_path, item, courseid)
                actualizados += 1
            console.print(f"\n[green]✓[/green] {actualizados} archivos .md actualizados")

            # Actualizar snapshot
            snap_path = os.path.join(cache_dir, "snapshot.json")
            if os.path.isfile(snap_path):
                _actualizar_snapshot(snap_path, items)
                console.print(f"[green]✓[/green] snapshot.json actualizado")
            else:
                console.print(f"[yellow]⚠ No se encontró snapshot.json[/yellow]")

        try:
            _imprimir_resumen(items)
        except Exception as e:
            console.print(f"[yellow]⚠ Resumen no se pudo imprimir: {e}[/yellow]")

        if args.dry_run:
            console.print("\n[yellow]DRY RUN: no se actualizaron archivos .md ni snapshot.json[/yellow]")
            return

    finally:
        # No cerramos el driver para no cerrar Chrome del usuario
        pass


if __name__ == "__main__":
    main()
