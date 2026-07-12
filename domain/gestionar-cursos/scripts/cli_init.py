#!/usr/bin/env python3
"""
CLI entry point: /gestionar-cursos init <URL>

Uso desde terminal (OpenCode CLI, VS Code terminal, etc.):
    python cli_init.py <URL_MOODLE> [--destino DIR]

Flujo:
1. Conecta a Chrome via CDP (lanza si no está abierto)
2. Verifica sesión Moodle (pide login si es necesario)
3. Extrae estructura del curso
4. Genera carpeta local con scaffold_curso
"""

import argparse
import contextlib
import os
import re
import subprocess
import sys
from datetime import datetime

from rich.console import Console
from rich.panel import Panel

# Asegurar que scripts/ esté en path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from browser_api import (
    esperar_carga,
    esta_usando_selenium,
    extraer_sidebar,
    get_current_url,
    get_driver,
    get_navegador,
    get_page_content,
    set_profile_dir,
)
from checkpoint import (
    clear_checkpoint,
    create_checkpoint,
    load_checkpoint,
    mark_done,
    save_checkpoint,
)
from parsear_pga import parsear_pga
from parsear_sesiones import parsear_sesiones
from scaffold_curso import crear_estructura_curso, nombre_carpeta_curso
from verificar_sesion import verificar_pagina_actual

console = Console()

BASE_URL = "https://aulavirtual.uniremington.edu.co"


def _cargar_env(path: str = ".env") -> None:
    """Carga variables de entorno desde archivo .env."""
    import os
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val


_cargar_env()


def _buscar_carpeta_curso(ruta_base: str, codigo: str) -> str:
    """Busca carpeta de curso existente que empiece con el código.

    Si no existe, devuelve la ruta default con solo el código.
    """
    if not os.path.isdir(ruta_base):
        return os.path.join(ruta_base, codigo)
    for entry in os.listdir(ruta_base):
        full = os.path.join(ruta_base, entry)
        if os.path.isdir(full) and entry.upper().startswith(codigo.upper()):
            return full
    return os.path.join(ruta_base, codigo)


class SessionExpiredError(RuntimeError):
    """Se lanza cuando Moodle redirige a login durante scraping."""
    pass


def _login_interactive():
    """
    Abre /my/ una sola vez y espera que el usuario haga login.
    Usa polling automático (no requiere input en terminal).
    No re-navega — solo verifica el estado actual de la página.
    """
    import time

    console.print()
    console.print(Panel(
        "[yellow]No hay sesión activa en Moodle.[/yellow]\n"
        "Se abrió Chrome en la página de login.\n"
        "Haz login manualmente en la ventana del navegador.",
        title="[bold blue]Autenticación[/bold blue]",
        border_style="blue"
    ))
    console.print("    [dim]Esperando login automáticamente (2 min máx)...[/dim]")

    for intento in range(60):  # 60 intentos × 2 seg = 2 minutos
        time.sleep(2)
        esperar_carga()
        if verificar_pagina_actual():
            console.print("[bold green]OK:[/bold green] Sesión detectada.\n")
            return True
        if intento % 10 == 0:
            console.print(f"    [dim]Esperando... ({intento * 2}s)[/dim]")

    console.print("[yellow]![/yellow] Tiempo de espera agotado. Sesión no detectada.")
    return False


def _limpiar_vision_general(texto: str) -> str:
    """Filtra líneas de UI/accessibilidad del texto de visión general."""
    lineas = []
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        ui_phrases = [
            "seleccionar sección", "hecho", "cerró:", "abrir", "mostrar",
            "ocultar", "toggle", "expandir", "contraer", "ir a", "saltar",
            "menú", "navegación", "cerrar", "volver", "seleccionar",
        ]
        if any(p in linea.lower() for p in ui_phrases):
            continue
        lineas.append(linea)
    return "\n".join(lineas)


def _extraer_info_basica(contenido_html: str, url: str) -> dict:
    """Extrae nombre, código, fechas y visión general del HTML."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(contenido_html, 'lxml')

    # Nombre del curso
    nombre = "Curso"
    for sel in ['h1', '.page-header-headings h1', '.course-title']:
        tag = soup.select_one(sel)
        if tag:
            nombre = tag.get_text(strip=True)
            break

    # Código del curso (heurística: busca patrón XXXX-XXXX o similar)
    codigo = "CODIGO"
    texto_completo = soup.get_text()
    m = re.search(r'\b\d{4}[A-Z]\d{2}[A-Z]\d\b', texto_completo)  # ej: 2601B04G1
    if m:
        codigo = m.group(0)
    else:
        # Fallback: buscar cualquier palabra mayúscula con números
        m2 = re.search(r'\b[A-Z0-9]{6,}\b', texto_completo)
        if m2:
            codigo = m2.group(0)

    # Fechas
    fecha_inicio = ""
    fecha_fin = ""
    for pat in [r'(?:Inicio|Desde)\s*[:\-]?\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'(\d{1,2}/\d{1,2}/\d{4}).{0,20}(?:Fin|Hasta|Final)']:
        m = re.search(pat, texto_completo, re.IGNORECASE)
        if m and not fecha_inicio:
            fecha_inicio = m.group(1)

    # Visión general
    vision = ""
    for sel in ['#course-summary', '.summary', '.box.generalbox', '.course-content']:
        tag = soup.select_one(sel)
        if tag:
            # Crear soup independiente para no mutar el original
            from bs4 import BeautifulSoup
            tag_soup = BeautifulSoup(str(tag), 'lxml')
            # Remover elementos de accesibilidad/UI
            for cls in ['.sr-only', '.accesshide', '.a11y', '.visually-hidden', '.hidden']:
                for el in tag_soup.select(cls):
                    el.decompose()
            vision = tag_soup.get_text(separator='\n', strip=True)
            if len(vision) > 50:
                break
    vision = _limpiar_vision_general(vision)

    # Contar unidades
    unidades_count = len(soup.select('li.section'))

    return {
        "nombre": nombre,
        "codigo": codigo,
        "url": url,
        "vision_general": vision,
        "unidades_count": unidades_count,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
    }


def _verificar_sesion_activa():
    """Verifica que no hayamos sido redirigidos a login. Si sí, lanza SessionExpiredError."""
    if "login" in get_current_url().lower():
        raise SessionExpiredError("Moodle redirigió a login. Sesión expirada.")


def _sync_curso(url: str, ruta_curso: str):
    """Sincroniza curso existente: merge selectivo de AGENTS.md + actualización de sitemap/PGA.

    Usa checkpointing para poder reanudar si la sesión expira durante el proceso.
    """
    console.print("\n[bold cyan][SYNC][/bold cyan] Iniciando sincronización...")

    # 1. Cargar checkpoint si existe
    checkpoint = load_checkpoint(ruta_curso)

    if checkpoint:
        console.print(f"[yellow]Checkpoint encontrado:[/yellow] {len(checkpoint['completed'])} actividades ya procesadas, {len(checkpoint['pending'])} pendientes.")
    else:
        console.print("[dim]No hay checkpoint previo. Extrayendo sitemap completo...[/dim]")

        # Extraer datos frescos de Moodle
        navegador = get_navegador()
        navegador(url)
        _verificar_sesion_activa()
        contenido = get_page_content()

        # Extraer sitemap (sidebar con actividades)
        actividades = []
        try:
            sidebar = extraer_sidebar()
            for item in sidebar:
                if item.get("url") and not item["url"].startswith("#"):
                    actividades.append({
                        "nombre": item["nombre"],
                        "url": item["url"],
                        "tipo": item.get("tipo", "unknown"),
                    })
        except Exception as e:
            console.print(f"[yellow]WARN:[/yellow] Error extrayendo sidebar: {e}")

        # Extraer info básica, PGA y sesiones
        info = _extraer_info_basica(contenido, url)
        pga = []
        with contextlib.suppress(Exception):
            pga = parsear_pga(contenido)
        sesiones = []
        with contextlib.suppress(Exception):
            sesiones = parsear_sesiones(contenido)

        # Crear checkpoint
        from scaffold_curso import extraer_codigo_desde_url
        course_code = extraer_codigo_desde_url(url)
        checkpoint = create_checkpoint(url, course_code, actividades)
        checkpoint["info"] = info
        checkpoint["pga"] = pga
        checkpoint["sesiones"] = sesiones
        # Nota: nombre_profesor se detecta bajo demanda durante el procesamiento
        save_checkpoint(ruta_curso, checkpoint)

    # 2. Procesar actividades pendientes con checkpointing
    info = checkpoint.get("info", {})
    pga = checkpoint.get("pga", [])
    sesiones = checkpoint.get("sesiones", [])

    while checkpoint["pending"]:
        act = checkpoint["pending"][0]
        console.print(f"[dim]Procesando:[/dim] {act['nombre'][:50]}...")

        try:
            # Determinar tipo de módulo y extraer
            tipo = act.get("tipo", "unknown")
            result_path = ""

            if tipo == "page":
                from extractor_modulos import extraer_modulo_page
                data = extraer_modulo_page(act["url"])
                result_path = _guardar_page(act, data, ruta_curso)
            elif tipo == "quiz":
                from extractor_modulos import extraer_modulo_quiz
                data = extraer_modulo_quiz(act["url"])
                result_path = _guardar_quiz(act, data, ruta_curso)
            elif tipo == "forum":
                # Foros evaluables (>0% en título) → flujo nuevo:
                # metadata + hilos principales de compañeros → Unidad-X/Foros/<slug>.md
                # Foros introductorios (Avisos, Consultas, Presentación) → flujo viejo (COMUNICACION/).
                from extractor_foro_evaluable import es_evaluable
                from _procesar_foro_evaluable import procesar_foro_en_unidad
                evaluable, _pct = es_evaluable(act.get("nombre", ""))
                if evaluable:
                    result_path = procesar_foro_en_unidad(act, ruta_curso, console)
                else:
                    from extractor_foro import extraer_discusiones_foro
                    nombre_profesor = checkpoint.get("nombre_profesor")
                    if not nombre_profesor:
                        nombre_profesor = _detectar_profesor(act["url"])
                    if nombre_profesor:
                        discusiones = extraer_discusiones_foro(act["url"], nombre_profesor)
                        result_path = _guardar_foro(act, discusiones, ruta_curso)
                    else:
                        console.print(f"      [yellow]Saltando foro (no se detectó profesor):[/yellow] {act['nombre']}")
                        result_path = ""
            elif tipo == "resource":
                from extractor_modulos import extraer_modulo_resource
                data = extraer_modulo_resource(act["url"])
                result_path = _guardar_resource(act, data, ruta_curso)
            elif tipo == "folder":
                from extractor_modulos import extraer_modulo_folder
                data = extraer_modulo_folder(act["url"])
                result_path = _guardar_folder(act, data, ruta_curso)
            elif tipo == "hvp":
                from extractor_modulos import extraer_modulo_hvp
                data = extraer_modulo_hvp(act["url"])
                result_path = _guardar_hvp(act, data, ruta_curso)
            elif tipo == "assign":
                from extractor_modulos import extraer_modulo_assign
                data = extraer_modulo_assign(act["url"])
                result_path = _guardar_assign(act, data, ruta_curso)
            elif tipo == "url":
                from extractor_modulos import extraer_modulo_url
                data = extraer_modulo_url(act["url"])
                result_path = _guardar_url(act, data, ruta_curso)
            elif tipo == "choice":
                from extractor_modulos import extraer_modulo_choice
                data = extraer_modulo_choice(act["url"])
                result_path = _guardar_choice(act, data, ruta_curso)
            elif tipo == "lesson":
                from extractor_modulos import extraer_modulo_lesson
                data = extraer_modulo_lesson(act["url"])
                result_path = _guardar_lesson(act, data, ruta_curso)
            elif tipo == "workshop":
                from extractor_modulos import extraer_modulo_workshop
                data = extraer_modulo_workshop(act["url"])
                result_path = _guardar_workshop(act, data, ruta_curso)
            else:
                console.print(f"      [dim]Tipo no soportado:[/dim] {tipo} — {act['nombre']}")
                result_path = ""

            checkpoint = mark_done(checkpoint, act, result_path)
            save_checkpoint(ruta_curso, checkpoint)

        except SessionExpiredError:
            console.print(Panel(
                "[yellow]Sesión expirada durante extracción.[/yellow]\n"
                f"Progreso guardado: {len(checkpoint['completed'])} actividades.\n"
                "Por favor haz re-login en Chrome y vuelve a ejecutar init.",
                title="[bold yellow]Pausa para re-login[/bold yellow]",
                border_style="yellow"
            ))
            raise  # Propagar para que main() maneje re-login

    # 3. Merge AGENTS.md (preservar manuales)
    agents_path = os.path.join(ruta_curso, "AGENTS.md")
    agents_original = ""
    if os.path.exists(agents_path):
        with open(agents_path, encoding='utf-8') as f:
            agents_original = f.read()

    manuales = {}
    for m in re.finditer(r'<!-- manual -->(.*?)<!-- /manual -->', agents_original, re.DOTALL):
        manuales['manual'] = m.group(1).strip()

    datos_curso = {
        "nombre": info.get("nombre", "Curso"),
        "codigo": info.get("codigo", ""),
        "url": url,
        "periodo": "",
        "bloque": "",
        "semanas": "",
        "fecha_inicio": info.get("fecha_inicio", ""),
        "fecha_fin": info.get("fecha_fin", ""),
        "vision_general": info.get("vision_general", ""),
        "unidades": [],
        "pga": pga,
        "sesiones": sesiones,
        "fecha_inicializacion": "",
    }

    from scaffold_curso import generar_agents_md
    generar_agents_md(ruta_curso, datos_curso)

    if manuales:
        with open(agents_path, encoding='utf-8') as f:
            nuevo = f.read()
        nuevo = re.sub(
            r'<!-- manual -->.*?<!-- /manual -->',
            f'<!-- manual -->\n{manuales.get("manual", "")}\n<!-- /manual -->',
            nuevo,
            flags=re.DOTALL
        )
        with open(agents_path, 'w', encoding='utf-8') as f:
            f.write(nuevo)

    # 4. Actualizar PGA.md y CONTEXT.md
    from scaffold_curso import generar_agents_md, generar_context_md, generar_pga_md
    generar_agents_md(ruta_curso, datos_curso)
    generar_pga_md(ruta_curso, pga)
    generar_context_md(ruta_curso, datos_curso)

    # 5. Limpiar checkpoint al completar
    clear_checkpoint(ruta_curso)

    console.print(Panel(
        f"[bold]{info.get('nombre', 'Curso')}[/bold]\n"
        f"Actividades procesadas: {len(checkpoint['completed'])}\n"
        f"PGA actualizado: {len(pga)} actividades",
        title="[bold green]Sincronización completada[/bold green]",
        border_style="green"
    ))
    console.print("[dim]Secciones manuales preservadas. Checkpoint eliminado.[/dim]")


def _init_curso(url: str, destino: str, profile_dir: str | None = None,
                reset_profile: bool = False, no_browser: bool = False,
                use_requests: bool = False,
                periodo: str = "", bloque: str = ""):
    """Inicializa UN curso desde Moodle. Llamable directamente o via subproceso.

    Args:
        url: URL del curso en Moodle.
        destino: Directorio destino.
        profile_dir: Directorio de perfil Chrome (None = default .browserdata).
        reset_profile: Borrar perfil antes de iniciar.
        no_browser: No lanzar Chrome, asumir CDP en localhost:9222.
        use_requests: Usar requests.Session en vez de Selenium/CDP.
        periodo: Período académico (ej: 2026-2). Se infiere de --destino si vacío.
        bloque: Bloque académico (ej: B1). Se infiere de --destino si vacío.
    """
    if use_requests:
        from moodle_session import cargar_session_requests
        session = cargar_session_requests()
        if not session:
            console.print(
                "[bold red]ERROR:[/bold red] No hay sesión guardada "
                "(.moodle_session.json). Corre primero con navegador para hacer login."
            )
            sys.exit(1)
        from browser_api import set_request_mode
        set_request_mode(session)
        console.print("[dim]Modo requests activado (sin navegador)[/dim]")
    elif not no_browser:
        profile = profile_dir or os.path.join(os.getcwd(), ".browserdata")
        if reset_profile and os.path.isdir(profile):
            import shutil
            shutil.rmtree(profile, ignore_errors=True)
        set_profile_dir(profile)

    if not use_requests and not esta_usando_selenium():
        console.print("[bold red]ERROR:[/bold red] No se detectó modo CDP/Selenium.")
        sys.exit(1)

    # Inferir periodo/bloque desde --destino si no se proporcionaron
    if not periodo or not bloque:
        p_inferido, b_inferido = _inferir_periodo_bloque(destino)
        if not periodo:
            periodo = p_inferido
        if not bloque:
            bloque = b_inferido
    if periodo:
        console.print(f"    [dim]Período: {periodo} | Bloque: {bloque or 'N/A'}[/dim]")

    # Detectar si el curso ya está inicializado
    from scaffold_curso import extraer_codigo_desde_url
    curso_code = extraer_codigo_desde_url(url)
    ruta_curso = _buscar_carpeta_curso(destino, curso_code)
    agents_path = os.path.join(ruta_curso, "AGENTS.md") if ruta_curso else ""

    if os.path.exists(agents_path):
        console.print(Panel(
            f"[yellow]Curso ya inicializado:[/yellow] {os.path.basename(ruta_curso)}\n"
            f"Redirigiendo a sincronización (merge selectivo)...",
            border_style="yellow"
        ))
        try:
            _sync_curso(url, ruta_curso)
            return
        except SessionExpiredError:
            console.print("\n[bold yellow]Sesión expirada.[/bold yellow]")
            if not _login_interactive():
                console.print("[bold red]ERROR:[/bold red] No se pudo re-autenticar.")
                return
            _sync_curso(url, ruta_curso)
            return

    # 1. Verificar sesión
    console.print("\n[bold cyan][1/6][/bold cyan] Abriendo Moodle para verificar sesión...")
    navegador = get_navegador()
    navegador(BASE_URL + "/my/")

    if not verificar_pagina_actual() and not _login_interactive():
        console.print("[bold red]ERROR:[/bold red] No se pudo autenticar.")
        return

    if esta_usando_selenium():
        from moodle_session import guardar_cookies_selenium
        guardar_cookies_selenium()

    # 2. Navegar al curso
    console.print("[bold cyan][2/6][/bold cyan] Navegando al curso...")
    navegador(url)
    url_actual = get_current_url()

    if "login" in url_actual:
        console.print("[yellow]![/yellow] El curso redirigió a login. Revisa la sesión...")
        if not _login_interactive():
            console.print("[bold red]ERROR:[/bold red] No se pudo autenticar.")
            return
        navegador(url)

    console.print(f"    [dim]URL actual: {get_current_url()}[/dim]")
    contenido = get_page_content()

    # 3. Extraer info básica
    console.print("\n[bold cyan][3/6][/bold cyan] Extrayendo información del curso...")
    info = _extraer_info_basica(contenido, url)
    console.print(f"    [green]Nombre:[/green] {info['nombre']}")
    console.print(f"    [green]Código:[/green] {info['codigo']}")

    # 4. Extraer PGA
    pga = []
    with contextlib.suppress(Exception):
        pga = parsear_pga(contenido)
    if pga:
        console.print(f"    [green]PGA:[/green] {len(pga)} actividades")

    # 5. Extraer sesiones sincrónicas
    sesiones = []
    with contextlib.suppress(Exception):
        sesiones = parsear_sesiones(contenido)
    if sesiones:
        console.print(f"    [green]Sesiones sincrónicas:[/green] {len(sesiones)}")

    # Fallback Grid
    if not pga:
        try:
            console.print("    [dim]Intentando sección 1 (Grid)...[/dim]")
            url_sec1 = f"{url}&section=1"
            navegador(url_sec1)
            html_sec1 = get_page_content()
            if html_sec1 and html_sec1 != contenido:
                pga = parsear_pga(html_sec1)
                sesiones = parsear_sesiones(html_sec1)
            navegador(url)
        except Exception:
            pass

    # 6. Extraer sidebar / unidades
    unidades = []
    sidebar = []
    try:
        sidebar = extraer_sidebar()
        for item in sidebar:
            if item.get("tipo") == "seccion":
                section_num = item.get("section_num", "")
                sec_url = f"{url}&section={section_num}" if section_num else ""
                unidades.append({"nombre": item["nombre"], "url": sec_url, "actividades": []})
        console.print(f"    [green]Unidades en sidebar:[/green] {len(unidades)}")
    except Exception as e:
        console.print(f"    [yellow]WARN:[/yellow] Sidebar: {e}")

    # Extraer actividades_intro
    actividades_intro = _extraer_actividades_intro(sidebar)

    # Extraer nombre del profesor
    nombre_profesor = _extraer_profesor(sidebar, actividades_intro)

    # Mejorar visión general desde página "Visión general del curso"
    if not info.get("vision_general") or len(info["vision_general"]) < 100:
        _mejorar_vision_general(info, actividades_intro)

    # 7. Preparar datos para scaffold
    datos_curso = {
        "nombre": info["nombre"], "codigo": info["codigo"], "url": url,
        "periodo": periodo, "bloque": bloque, "semanas": "",
        "fecha_inicio": info["fecha_inicio"], "fecha_fin": info["fecha_fin"],
        "vision_general": info["vision_general"],
        "unidades": unidades, "pga": pga, "sesiones": sesiones,
        "fecha_inicializacion": datetime.now().isoformat(),
        "secciones": [{"nombre": u["nombre"], "url": u["url"]} for u in unidades],
        "actividades_intro": actividades_intro, "nombre_profesor": nombre_profesor,
    }

    # 8. Crear estructura
    console.print("\n[bold cyan][4/6][/bold cyan] Creando estructura local...")
    exito = crear_estructura_curso(datos_curso, destino)
    if not exito:
        console.print("[bold red]ERROR:[/bold red] Falló scaffold_curso")
        return

    ruta_curso = os.path.join(
        destino, nombre_carpeta_curso(datos_curso["codigo"], datos_curso["nombre"], url),
    )
    console.print(f"    [green]Creado:[/green] {os.path.abspath(ruta_curso)}")

    # Activar caché LLM
    from llm_api import set_cache_dir
    set_cache_dir(os.path.join(ruta_curso, "_cache"))

    # 9. Extraer documentos introductorios
    console.print("\n[bold cyan][5/6][/bold cyan] Extrayendo contenido de documentos introductorios...")
    docs_intro = _procesar_documentos_intro(actividades_intro, ruta_curso)

    datos_curso["docs_introductorios"] = docs_intro
    from formatear_llm import obtener_metadatos
    metadatos_llm = obtener_metadatos()
    datos_curso["metadatos_llm"] = _fusionar_metadatos(metadatos_llm) if metadatos_llm else {}

    from scaffold_curso import generar_agents_md, generar_context_md
    generar_agents_md(ruta_curso, datos_curso)
    generar_context_md(ruta_curso, datos_curso)

    # 10. Extraer foros
    console.print("\n[bold cyan][5.5/6][/bold cyan] Extrayendo foros introductorios...")
    _extraer_y_guardar_foros(actividades_intro, ruta_curso, nombre_profesor)

    # Phase 2: actividades de unidades
    _procesar_actividades_unidades(sidebar, ruta_curso, nombre_profesor)

    # Crear snapshot inicial para futuros diffs
    _crear_snapshot_inicial(sidebar, ruta_curso)

    # Escribir/actualizar clickup.json en la raíz del período
    _escribir_clickup_json(destino, datos_curso["codigo"], datos_curso["nombre"],
                           periodo, bloque, url)

    # 11. Resumen
    console.print(f"\n[bold green]Inicialización completa:[/bold green] {datos_curso['nombre']}")
    console.print(f"  Ruta: {os.path.abspath(ruta_curso)}")


def _extraer_actividades_intro(sidebar: list[dict]) -> list[dict]:
    """Extrae actividades de la sección Introducción/Inicio del sidebar."""
    actividades = []
    en_introduccion = False
    for item in sidebar:
        if item.get("tipo") == "seccion":
            nombre_sec = item.get("nombre", "").lower()
            if "introduccion" in nombre_sec or "inicio" in nombre_sec:
                en_introduccion = True
                continue
            if en_introduccion:
                en_introduccion = False
                continue
        if en_introduccion and item.get("url") and "/mod/" in item["url"]:
            url = item["url"]
            tipo = _detectar_tipo_url(url)
            actividades.append({"nombre": item["nombre"], "url": url, "tipo": tipo})
    return actividades


def _detectar_tipo_url(url: str) -> str:
    """Detecta tipo de módulo desde URL (versión standalone sin BeautifulSoup)."""
    for mod in ["page", "resource", "forum", "quiz", "folder", "url", "assign",
                "hvp", "label", "choice", "lesson", "workshop"]:
        if f"/mod/{mod}/" in url:
            return mod
    # Detectar redirects de Teams
    if "/l/meetup-join/" in url or "/l/channel/" in url:
        return "url"
    return "unknown"


def _extraer_profesor(sidebar: list[dict], actividades_intro: list[dict]) -> str | None:
    """Extrae nombre del profesor desde sidebar y páginas de profesor."""
    try:
        from extractor_foro import extraer_nombre_profesor
        from extractor_modulos import extraer_modulo_page
        candidatos = []
        for act in sidebar:
            if act.get("tipo") != "seccion" and act.get("url"):
                nl = act["nombre"].lower()
                if any(kw in nl for kw in ("profesor", "docente", "tutor")):
                    candidatos.append(act)
        for act in actividades_intro:
            if act.get("tipo") == "page" and act.get("url"):
                    nl = act["nombre"].lower()
                    if any(kw in nl for kw in ("profesor", "docente", "tutor")) \
                       and act not in candidatos:
                        candidatos.append(act)
        for act in candidatos:
            data = extraer_modulo_page(act["url"])
            nombre = extraer_nombre_profesor(data.get("contenido_html", ""))
            if nombre:
                console.print(f"    [green]Profesor:[/green] {nombre}")
                return nombre
    except Exception as e:
        console.print(f"    [yellow]WARN:[/yellow] No se pudo detectar profesor: {e}")
    return None


def _mejorar_vision_general(info: dict, actividades_intro: list[dict]):
    """Intenta extraer visión general desde página 'Visión general del curso'."""
    try:
        from extractor_modulos import extraer_modulo_page
        for act in actividades_intro:
            if "visi" in act["nombre"].lower() and act.get("tipo") == "page":
                data = extraer_modulo_page(act["url"])
                texto = data.get("contenido_texto", "")
                if texto and len(texto) > 50:
                    info["vision_general"] = texto[:500] + ("..." if len(texto) > 500 else "")
                    console.print(f"    [green]Visión general:[/green] Extraída de {act['nombre']}")
                    break
    except Exception:
        pass


def _procesar_documentos_intro(actividades_intro: list[dict], ruta_curso: str) -> list[dict]:
    """Descarga y formatea documentos introductorios (PDF, DOCX, etc.)."""
    from extractor_documentos import extraer_texto_documento
    from extractor_modulos import extraer_modulo_resource
    from formatear_llm import formatear_texto_llm

    docs = []
    for act in actividades_intro:
        if act.get("tipo") != "resource" or not act.get("url"):
            continue
        try:
            data = extraer_modulo_resource(act["url"])
            download_url = data.get("download_url", "")
            if not download_url:
                continue
            ruta_materia = os.path.join(ruta_curso, "MATERIA")
            os.makedirs(ruta_materia, exist_ok=True)
            filename = data.get("filename") or act["nombre"].replace(" ", "_").replace("/", "_")
            ruta_archivo = os.path.join(ruta_materia, filename)
            _descargar_binario(download_url, ruta_archivo)
            console.print(f"    [green]Descargado:[/green] {ruta_archivo}")
            texto = extraer_texto_documento(download_url)
            if texto:
                texto_formateado = formatear_texto_llm(
                    texto,
                    instruccion="Limpia y estructura este documento introductorio académico.",
                )
                docs.append({"nombre": act["nombre"], "texto": texto_formateado})
                console.print(f"    [green]{act['nombre'][:40]}:[/green] "
                             f"Texto extraído ({len(texto_formateado)} chars)")
            else:
                console.print(f"    [yellow]{act['nombre'][:40]}:[/yellow] No se pudo extraer texto")
        except Exception as e:
            console.print(f"    [yellow]{act['nombre'][:40]}:[/yellow] Error: {e}")
    return docs


def _extraer_y_guardar_foros(actividades_intro: list[dict], ruta_curso: str,
                             nombre_profesor: str | None):
    """Extrae y guarda discusiones de foros introductorios."""
    from extractor_foro import extraer_discusiones_foro

    if not nombre_profesor:
        console.print("    [yellow]No se pudo identificar al profesor, omitiendo foros[/yellow]")
        return

    foros_extraidos = []
    for act in actividades_intro:
        if act.get("tipo") != "forum":
            continue
        console.print(f"    Procesando foro: {act['nombre']}...")
        discusiones = extraer_discusiones_foro(act["url"], nombre_profesor)
        if discusiones:
            foros_extraidos.append({
                "nombre": act["nombre"], "url": act["url"], "discusiones": discusiones,
            })
            console.print(f"      [green]Extraídas {len(discusiones)} discusiones[/green]")
        else:
            console.print("      [yellow]No se encontraron discusiones del profesor[/yellow]")

    if foros_extraidos:
        ruta_comunicacion = os.path.join(ruta_curso, "COMUNICACION")
        os.makedirs(ruta_comunicacion, exist_ok=True)
        for foro in foros_extraidos:
            ts = _timestamp_foro(foro["discusiones"])
            nombre_base = foro["nombre"].replace(" ", "_").replace("/", "_")
            ruta_foro = os.path.join(ruta_comunicacion, f"{ts}{nombre_base}.md")
            contenido_foro = f"# {foro['nombre']}\n\nURL: {foro['url']}\n\n"
            for disc in foro["discusiones"]:
                contenido_foro += f"## {disc['titulo']}\n\n"
                contenido_foro += f"**Autor:** {disc['autor']}\n"
                if disc.get("fecha"):
                    contenido_foro += f"**Fecha:** {disc['fecha']}\n"
                contenido_foro += f"\n{disc['contenido']}\n\n---\n\n"
            with open(ruta_foro, "w", encoding="utf-8") as f:
                f.write(contenido_foro)
            console.print(f"    [green]Foro guardado:[/green] {ruta_foro}")


def main():
    parser = argparse.ArgumentParser(
        description="Inicializar curso(s) desde Moodle Uniremington"
    )
    parser.add_argument("urls", nargs="+", help="URL(s) del curso en Moodle")
    parser.add_argument(
        "--destino", "-d", default=".",
        help="Directorio destino para el/los curso(s) (default: actual)"
    )
    parser.add_argument(
        "--parallel", action="store_true",
        help="Procesar múltiples URLs en paralelo via subprocesos"
    )
    parser.add_argument(
        "--no-browser", action="store_true",
        help="No abrir Chrome; asume que ya está corriendo con --remote-debugging-port=9222"
    )
    parser.add_argument(
        "--requests", action="store_true",
        help="Usar requests.Session (sin navegador). Requiere .moodle_session.json válido."
    )
    parser.add_argument(
        "--profile-dir", "-p", default=None,
        help="Directorio para perfil persistente de Chrome"
    )
    parser.add_argument(
        "--reset-profile", action="store_true",
        help="Borrar perfil persistente antes de iniciar"
    )
    parser.add_argument(
        "--periodo", default="",
        help="Período académico (ej: 2026-2). Si no, se infiere del --destino."
    )
    parser.add_argument(
        "--bloque", default="",
        help="Bloque académico (ej: B1). Si no, se infiere del --destino."
    )
    args = parser.parse_args()

    console.print(Panel.fit(
        "[bold]GESTIONAR-CURSOS[/bold] :: CLI INIT",
        style="bold cyan", border_style="cyan"
    ))

    if not args.requests and not esta_usando_selenium():
        console.print("[bold red]ERROR:[/bold red] No se detectó modo CDP/Selenium.")
        sys.exit(1)

    profile = args.profile_dir or os.path.join(os.getcwd(), ".browserdata")
    import shutil
    if args.reset_profile and os.path.isdir(profile):
        shutil.rmtree(profile, ignore_errors=True)

    # Múltiples URLs con --parallel
    if len(args.urls) > 1 and args.parallel:
        console.print(f"\n[bold cyan]PARALELO:[/bold cyan] {len(args.urls)} cursos en simultáneo")
        _init_parallel(args.urls, args.destino, profile, periodo=args.periodo,
                       bloque=args.bloque)
        return

    # Modo secuencial (1 URL o múltiples sin --parallel)
    for url in args.urls:
        console.print(f"\n[bold]Curso:[/bold] {url}")
        _init_curso(url, args.destino, profile_dir=profile,
                    reset_profile=args.reset_profile, no_browser=args.no_browser,
                    use_requests=args.requests,
                    periodo=args.periodo, bloque=args.bloque)


def _crear_snapshot_inicial(sidebar: list[dict], ruta_curso: str):
    """Crea _cache/snapshot.json con el estado inicial del sidebar."""
    import json

    actividades = {}
    seccion_actual = ""
    for item in sidebar:
        if item.get("tipo") == "seccion":
            seccion_actual = item.get("nombre", "")
            continue
        url = item.get("url", "")
        if not url:
            continue
        key = _url_key(url)
        actividades[key] = {
            "nombre": item.get("nombre", ""),
            "tipo": item.get("tipo", "unknown"),
            "seccion": seccion_actual,
            "fecha_apertura": "",
            "fecha_cierre": "",
        }

    cache_dir = os.path.join(ruta_curso, "_cache")
    os.makedirs(cache_dir, exist_ok=True)
    snapshot_path = os.path.join(cache_dir, "snapshot.json")
    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "actividades": actividades,
    }
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)
    console.print(f"    [dim]Snapshot inicial: {len(actividades)} actividades[/dim]")


def _url_key(url: str) -> str:
    """Extrae parte estable de una URL de módulo Moodle como clave de snapshot.

    'https://aulavirtual.../mod/quiz/view.php?id=123' → '/mod/quiz/view.php?id=123'
    """
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return parsed.path + ("?" + parsed.query if parsed.query else "")


def _inferir_periodo_bloque(destino: str) -> tuple[str, str]:
    """Infiera periodo y bloque desde la ruta destino.

    'C:/.../Universidad/2026-2-B1' → ('2026-2', 'B1')
    'C:/.../2026-2' → ('2026-2', '')
    """
    import re
    partes = os.path.normpath(destino).split(os.sep)
    for parte in reversed(partes):
        m = re.match(r'^(\d{4}-\d)(?:-(B\d+))?$', parte)
        if m:
            return m.group(1), m.group(2) or ""
    return "", ""


CLICKUP_SPACE_ID = "901311224662"
CLICKUP_SPACE_NAME = "Universidad"

CLICKUP_TEMPLATE = {
    "space": {"id": CLICKUP_SPACE_ID, "name": CLICKUP_SPACE_NAME},
    "activity_tags": {
        "parcial": ["evaluable", "parcial", "entregable"],
        "quiz": ["evaluable", "quiz"],
        "assignment": ["evaluable", "actividad", "entregable"],
        "forum": ["foro", "participacion"],
    },
    "priority_map": {
        "parcial": "urgente",
        "quiz": "normal",
        "assignment": "alta",
        "forum": "normal",
    },
    "support_tags": [
        "grupal", "lectura", "repaso", "documento",
        "investigar", "practica", "exposicion", "no-evaluable",
    ],
}


def _escribir_clickup_json(destino: str, codigo: str, nombre_curso: str,
                           periodo: str, bloque: str, url: str = ""):
    """Escribe o actualiza clickup.json en la raíz del período académico.

    Usa el ID de Moodle (?id=) como key para soportar cursos con mismo código.
    Si ya existe, solo agrega la entrada courses[key].
    """
    import json

    from scaffold_curso import extraer_codigo_desde_url

    course_key = extraer_codigo_desde_url(url) if url else codigo

    ruta_clickup = os.path.join(destino, "clickup.json")
    if os.path.isfile(ruta_clickup):
        with open(ruta_clickup, encoding="utf-8") as f:
            data = json.load(f)
    else:
        folder_name = f"{periodo}-{bloque}" if bloque else periodo
        data = dict(CLICKUP_TEMPLATE)
        data["folder"] = {"id": None, "name": folder_name}
        data["courses"] = {}
        console.print("    [dim]clickup.json creado en período[/dim]")

    if course_key not in data.get("courses", {}):
        data.setdefault("courses", {})[course_key] = {
            "list_id": None,
            "list_name": f"{nombre_curso} - {codigo}",
            "tasks": {},
        }
        console.print(f"    [dim]Curso {course_key} agregado a clickup.json[/dim]")
    else:
        console.print(f"    [dim]Curso {course_key} ya existe en clickup.json[/dim]")

    with open(ruta_clickup, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _init_parallel(urls: list[str], destino: str, profile_dir: str,
                   periodo: str = "", bloque: str = ""):
    """Lanza subprocesos independientes para cada URL usando requests.

    Flujo:
    1. Padre hace login via Chrome CDP.
    2. Exporta cookies a .moodle_session.json.
    3. Cierra Chrome/desconecta driver.
    4. Lanza N subprocesos, cada uno con --requests.
    5. Cada subproceso carga cookies y usa requests.Session sin navegador.
    """
    import shlex

    # 1. Login via Chrome CDP (padre)
    set_profile_dir(profile_dir)
    navegador = get_navegador()
    navegador(BASE_URL + "/my/")

    if not verificar_pagina_actual() and not _login_interactive():
        console.print("[bold red]ERROR:[/bold red] No se pudo autenticar.")
        return

    # 2. Exportar cookies para subprocesos
    console.print("[dim]Exportando cookies de sesión...[/dim]")
    from moodle_session import guardar_cookies_selenium
    if not guardar_cookies_selenium():
        console.print("[bold red]ERROR:[/bold red] No se pudieron exportar cookies.")
        return

    # 3. Desconectar driver del padre (libera Chrome)
    try:
        driver = get_driver()
        driver.quit()
    except Exception:
        pass

    # 4. Lanzar subprocesos (cada uno con --requests)
    console.print(f"\n[dim]Lanzando {len(urls)} subprocesos (modo requests)...[/dim]")
    proceso_script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "cli_init.py")

    procesos = []
    for i, url in enumerate(urls, 1):
        cmd = [
            sys.executable, proceso_script,
            url,
            "--destino", destino,
            "--requests",
        ]
        if periodo:
            cmd.extend(["--periodo", periodo])
        if bloque:
            cmd.extend(["--bloque", bloque])
        console.print(f"  [{i}/{len(urls)}] {' '.join(shlex.quote(a) for a in cmd[:3])}...")
        env = os.environ.copy()
        env.setdefault("PYTHONIOENCODING", "utf-8")
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, encoding="utf-8", errors="replace", env=env)
        procesos.append((url, p))

    # 5. Esperar y recolectar resultados
    for url, p in procesos:
        console.print(f"\n[bold]--- Resultado: {url} ---[/bold]")
        for line in p.stdout:
            console.print(f"  {line.rstrip()}", markup=False, highlight=False)
        p.wait()
        if p.returncode == 0:
            console.print("  [green]OK[/green]")
        else:
            console.print(f"  [yellow]Código salida: {p.returncode}[/yellow]")

    console.print(f"\n[bold green]Paralelo completado:[/bold green] {len(urls)} cursos")


def _detectar_profesor(url_foro: str) -> str | None:
    """Intenta detectar el nombre del profesor navegando a una página del curso."""
    try:
        from browser_api import get_page_content as _get_content
        from browser_api import navegar as _navegar
        from extractor_foro import extraer_nombre_profesor
        _navegar(url_foro)
        return extraer_nombre_profesor(_get_content())
    except Exception:
        return None


def _descargar_binario(url: str, ruta_destino: str) -> str:
    """Descarga archivo binario usando hacer_get y lo guarda en disco."""
    from browser_api import hacer_get
    contenido = hacer_get(url)
    with open(ruta_destino, "wb") as f:
        f.write(contenido)
    return ruta_destino


def _parsear_fecha_foro(fecha_str: str) -> datetime | None:
    """Convierte fechas tipo '10 mar 2026' a datetime."""
    meses_es = {
        "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
        "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12,
    }
    # Normalizar: quitar puntos, espacios extras
    fecha_str = fecha_str.strip().lower().replace(".", "")
    # Patrones: "10 mar 2026", "10 marzo 2026", "2026-03-10"
    partes = fecha_str.split()
    if len(partes) == 3:
        dia_str, mes_str, anio_str = partes
        try:
            dia = int(dia_str)
            anio = int(anio_str)
            mes = meses_es.get(mes_str[:3], 0)
            if mes:
                return datetime(anio, mes, dia)
        except ValueError:
            pass
    return None


def _timestamp_foro(discusiones: list[dict]) -> str:
    """Devuelve prefijo YYYYMMDD basado en la discusión más antigua."""
    fechas = []
    for d in discusiones:
        f = _parsear_fecha_foro(d.get("fecha", ""))
        if f:
            fechas.append(f)
    if fechas:
        return min(fechas).strftime("%Y%m%d") + "_"
    return ""


def _ruta_unidad_por_nombre(nombre_actividad: str, ruta_curso: str, seccion: str = "") -> str:
    """
    Determina a qué unidad pertenece una actividad basándose en su nombre,
    la sección de la sidebar, o el sitemap. Fallback a 'Unidad-1'.
    """
    import re
    # 1. Usar sección de la sidebar (más confiable)
    if seccion:
        m_sec = re.search(r'(?:Unidad|Semana|Unit)\s*(\d+)', seccion, re.IGNORECASE)
        if m_sec:
            return os.path.join(ruta_curso, f"Unidad-{m_sec.group(1)}")
    # 2. Heurística: buscar "Unidad X" o "Semana X" en el nombre de la actividad
    match = re.search(r'(?:Unidad|Semana|Unit)\s*(\d+)', nombre_actividad, re.IGNORECASE)
    if match:
        return os.path.join(ruta_curso, f"Unidad-{match.group(1)}")
    # 3. Si no hay match, buscar en carpetas existentes
    if os.path.isdir(ruta_curso):
        for unidad_dir in sorted(os.listdir(ruta_curso)):
            if unidad_dir.startswith("Unidad-"):
                return os.path.join(ruta_curso, unidad_dir)
    return os.path.join(ruta_curso, "Unidad-1")


def _acortar_nombre_archivo(nombre: str) -> str:
    """Acorta nombres de actividades con patrones parseables.

    'Actividad de seguimiento (Calificable 10%) Disponible del 2 al 8 de febrero'
    -> 'Seguimiento[10%]'

    'Tercer parcial (Calificable 25%) Disponible del 4 al 8 de marzo'
    -> 'Parcial-3[25%]'
    """
    import re

    original = nombre.strip()

    # Extraer peso: (Calificable XX%) o (No calificable)
    peso = ""
    m_peso = re.search(r'\(Calificable\s+(\d+%)\)', original, re.IGNORECASE)
    if m_peso:
        peso = f"[{m_peso.group(1)}]"
    elif re.search(r'\(No\s+calificable\)', original, re.IGNORECASE):
        peso = "[N/A]"

    # Limpiar: quitar todo desde "Disponible" y el peso entre paréntesis
    nombre_limpio = re.sub(r'\s*\(Calificable\s+\d+%\)', '', original, flags=re.IGNORECASE)
    nombre_limpio = re.sub(r'\s*\(No\s+calificable\)', '', nombre_limpio, flags=re.IGNORECASE)
    nombre_limpio = re.sub(r'\s*Disponible\s+.*$', '', nombre_limpio, flags=re.IGNORECASE)

    # Quitar prefijo "Unidad X. " o "Unidad X - "
    nombre_limpio = re.sub(r'^Unidad\s+\d+[\.\-\s]+', '', nombre_limpio, flags=re.IGNORECASE)

    # Mapa de patrones -> nombres cortos
    ordinales = {
        "primer": "1", "primero": "1", "segundo": "2", "tercer": "3",
        "cuarto": "4", "quinto": "5", "sexto": "6",
    }
    tipo_map = {
        "actividad de seguimiento": "Seguimiento",
        "actividad_de_seguimiento": "Seguimiento",
        "prueba inicial": "PruebaInicial",
        "prueba_inicial": "PruebaInicial",
        "cuestionario evaluativo": "Cuestionario",
        "cuestionario_evaluativo": "Cuestionario",
        "examen final": "ExamenFinal",
        "examen_final": "ExamenFinal",
    }

    nombre_lower = nombre_limpio.strip().lower()
    nombre_final = nombre_limpio.strip()

    # Detectar "X parcial"
    m_parcial = re.search(
        r'(primer|primero|segundo|tercer|cuarto|quinto|sexto)\s*parcial',
        nombre_lower
    )
    if m_parcial:
        num = ordinales.get(m_parcial.group(1), "?")
        nombre_final = f"Parcial-{num}"
    else:
        for patron, corto in tipo_map.items():
            if patron in nombre_lower:
                nombre_final = corto
                break

    # Agregar peso al final
    if peso:
        nombre_final = f"{nombre_final}{peso}"

    # Sanitizar para sistema de archivos
    nombre_final = re.sub(r'[<>"/\\|?*:]', '-', nombre_final)
    nombre_final = re.sub(r'\s+', ' ', nombre_final).strip()
    return nombre_final if nombre_final else nombre.replace(" ", "_")


def _guardar_page(act: dict, data: dict, ruta_curso: str) -> str:
    """Guarda contenido de página en Unidad-X/contenido/."""
    ruta_unidad = _ruta_unidad_por_nombre(act["nombre"], ruta_curso, act.get("seccion", ""))
    ruta_contenido = os.path.join(ruta_unidad, "contenido")
    os.makedirs(ruta_contenido, exist_ok=True)

    nombre_archivo = _acortar_nombre_archivo(act["nombre"]) + ".md"
    ruta_archivo = os.path.join(ruta_contenido, nombre_archivo)

    # Convertir HTML a markdown si está disponible
    contenido_md = data.get("contenido_texto", "")
    try:
        from markdownify import markdownify as md
        contenido_md = md(data.get("contenido_html", ""), heading_style="ATX")
    except ImportError:
        pass

    with open(ruta_archivo, 'w', encoding='utf-8') as f:
        f.write(f"# {data['titulo']}\n\n")
        f.write(f"URL: {data['url']}\n\n")
        f.write(contenido_md)

    console.print(f"      [green]Page guardado:[/green] {ruta_archivo}")

    # Detectar links YouTube en el contenido de la página
    from extractor_youtube import detectar_youtube_en_texto
    youtube_urls = detectar_youtube_en_texto(data.get("contenido_texto", ""))
    for yt_url in youtube_urls:
        ruta_yt_dir = os.path.join(ruta_unidad, "materiales")
        os.makedirs(ruta_yt_dir, exist_ok=True)
        _procesar_youtube_video(yt_url, ruta_yt_dir, act["nombre"])

    return ruta_archivo


def _guardar_quiz(act: dict, data: dict, ruta_curso: str) -> str:
    """Guarda datos de quiz en Unidad-X/actividades/."""
    ruta_unidad = _ruta_unidad_por_nombre(act["nombre"], ruta_curso, act.get("seccion", ""))
    ruta_actividades = os.path.join(ruta_unidad, "actividades")
    os.makedirs(ruta_actividades, exist_ok=True)

    nombre_archivo = _acortar_nombre_archivo(act["nombre"]) + ".md"
    ruta_archivo = os.path.join(ruta_actividades, nombre_archivo)

    with open(ruta_archivo, 'w', encoding='utf-8') as f:
        f.write(f"# {data['titulo']}\n\n")
        f.write(f"URL: {data['url']}\n\n")
        if data.get('fecha_apertura'):
            f.write(f"**Apertura:** {data['fecha_apertura']}\n")
        if data.get('fecha_cierre'):
            f.write(f"**Cierre:** {data['fecha_cierre']}\n")
        if data.get('intentos'):
            f.write(f"**Intentos:** {data['intentos']}\n")
        if data.get('tiempo_limite'):
            f.write(f"**Tiempo límite:** {data['tiempo_limite']}\n")
        if data.get('nota_aprobacion'):
            f.write(f"**Nota de aprobación:** {data['nota_aprobacion']}\n")
        f.write(f"\n## Instrucciones\n\n{data['instrucciones']}\n")

    console.print(f"      [green]Quiz guardado:[/green] {ruta_archivo}")
    return ruta_archivo


def _guardar_foro(act: dict, discusiones: list, ruta_curso: str) -> str:
    """Guarda foro en COMUNICACION/ con timestamp."""
    ruta_comunicacion = os.path.join(ruta_curso, "COMUNICACION")
    os.makedirs(ruta_comunicacion, exist_ok=True)

    ts = _timestamp_foro(discusiones)
    nombre_base = act["nombre"].replace(" ", "_").replace("/", "_")
    nombre_archivo = ts + nombre_base + ".md"
    ruta_archivo = os.path.join(ruta_comunicacion, nombre_archivo)

    with open(ruta_archivo, 'w', encoding='utf-8') as f:
        f.write(f"# {act['nombre']}\n\n")
        f.write(f"URL: {act['url']}\n\n")
        for disc in discusiones:
            f.write(f"## {disc['titulo']}\n\n")
            f.write(f"**Autor:** {disc['autor']}\n")
            if disc.get('fecha'):
                f.write(f"**Fecha:** {disc['fecha']}\n")
            f.write(f"\n{disc['contenido']}\n\n---\n\n")

    console.print(f"      [green]Foro guardado:[/green] {ruta_archivo}")
    return ruta_archivo


def _guardar_resource(act: dict, data: dict, ruta_curso: str) -> str:
    """Descarga y guarda recurso en Unidad-X/materiales/ o MATERIA/ según sección."""
    nombre_act = act.get("nombre", "")
    # Recursos de secciones introductorias van a MATERIA/
    seccion_lower = act.get("seccion", "").lower()
    es_intro = any(kw in seccion_lower for kw in ("inicio", "introduccion", "introducción"))
    if es_intro:
        ruta_materiales = os.path.join(ruta_curso, "MATERIA")
    else:
        ruta_unidad = _ruta_unidad_por_nombre(nombre_act, ruta_curso, act.get("seccion", ""))
        ruta_materiales = os.path.join(ruta_unidad, "materiales")
    os.makedirs(ruta_materiales, exist_ok=True)

    download_url = data.get("download_url", "")
    filename = data.get("filename") or nombre_act.replace(" ", "_").replace("/", "_")
    if not download_url:
        console.print(f"      [yellow]Resource sin URL de descarga:[/yellow] {act['nombre']}")
        return ""

    ext = os.path.splitext(filename)[1].lower()
    extensiones_validas = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt",
                           ".zip", ".rar", ".7z", ".png", ".jpg", ".jpeg", ".gif",
                           ".mp4", ".mp3", ".txt", ".csv", ".html", ".htm"}

    if ext in extensiones_validas:
        ruta_binario = os.path.join(ruta_materiales, filename)
        try:
            _descargar_binario(download_url, ruta_binario)
            console.print(f"      [green]Descargado:[/green] {ruta_binario}")
        except Exception as e:
            console.print(f"      [yellow]Error descargando {filename}:[/yellow] {e}")
    else:
        console.print(f"      [dim]Sin extensión válida, solo metadatos:[/dim] {filename}")

    nombre_md = _acortar_nombre_archivo(nombre_act) + ".md"
    ruta_md = os.path.join(ruta_materiales, nombre_md)
    with open(ruta_md, 'w', encoding='utf-8') as f:
        f.write(f"# {data['titulo']}\n\n")
        f.write(f"URL: {data['url']}\n\n")
        if ext in extensiones_validas:
            f.write(f"**Archivo:** [{filename}]({filename})\n")

    console.print(f"      [green]Resource guardado:[/green] {ruta_md}")
    return ruta_md


def _guardar_folder(act: dict, data: dict, ruta_curso: str) -> str:
    """Descarga archivos de carpeta en Unidad-X/materiales/ o MATERIA/ según sección."""
    nombre_act = act.get("nombre", "")
    seccion_lower = act.get("seccion", "").lower()
    es_intro = any(kw in seccion_lower for kw in ("inicio", "introduccion", "introducción"))
    if es_intro:
        ruta_materiales = os.path.join(ruta_curso, "MATERIA")
    else:
        ruta_unidad = _ruta_unidad_por_nombre(nombre_act, ruta_curso, act.get("seccion", ""))
        ruta_materiales = os.path.join(ruta_unidad, "materiales")
    os.makedirs(ruta_materiales, exist_ok=True)

    # Descargar cada archivo del folder
    for arch in data.get("archivos", []):
        url_arch = arch.get("url", "")
        nombre_arch = arch.get("nombre", "archivo")
        if not url_arch:
            continue
        ruta_binario = os.path.join(ruta_materiales, nombre_arch)
        try:
            _descargar_binario(url_arch, ruta_binario)
            console.print(f"      [green]Descargado:[/green] {ruta_binario}")
        except Exception as e:
            console.print(f"      [yellow]Error descargando {nombre_arch}:[/yellow] {e}")

    # Crear .md con metadatos
    nombre_md = _acortar_nombre_archivo(act["nombre"]) + ".md"
    ruta_md = os.path.join(ruta_materiales, nombre_md)
    with open(ruta_md, 'w', encoding='utf-8') as f:
        f.write(f"# {data['titulo']}\n\n")
        f.write(f"URL: {data['url']}\n\n")
        f.write("## Archivos\n\n")
        for arch in data.get("archivos", []):
            f.write(f"- [{arch['nombre']}]({arch['nombre']})\n")

    console.print(f"      [green]Folder guardado:[/green] {ruta_md}")
    return ruta_md


def _guardar_hvp(act: dict, data: dict, ruta_curso: str) -> str:
    """Guarda proxy H5P en Unidad-X/materiales/."""
    ruta_unidad = _ruta_unidad_por_nombre(act["nombre"], ruta_curso, act.get("seccion", ""))
    ruta_materiales = os.path.join(ruta_unidad, "materiales")
    os.makedirs(ruta_materiales, exist_ok=True)

    nombre_archivo = _acortar_nombre_archivo(act["nombre"]) + ".html"
    ruta_archivo = os.path.join(ruta_materiales, nombre_archivo)

    html = f"""<!DOCTYPE html>
<html>
<head><title>{data['titulo']}</title></head>
<body>
<h1>{data['titulo']}</h1>
<p>URL: {data['url']}</p>
<iframe src="{data['embed_url']}" width="100%" height="600" frameborder="0"></iframe>
</body>
</html>"""

    with open(ruta_archivo, 'w', encoding='utf-8') as f:
        f.write(html)

    console.print(f"      [green]H5P proxy guardado:[/green] {ruta_archivo}")
    return ruta_archivo


def _guardar_assign(act: dict, data: dict, ruta_curso: str) -> str:
    """Guarda datos de tarea (assign) en Unidad-X/actividades/."""
    ruta_unidad = _ruta_unidad_por_nombre(act["nombre"], ruta_curso, act.get("seccion", ""))
    ruta_actividades = os.path.join(ruta_unidad, "actividades")
    os.makedirs(ruta_actividades, exist_ok=True)

    nombre_archivo = _acortar_nombre_archivo(act["nombre"]) + ".md"
    ruta_archivo = os.path.join(ruta_actividades, nombre_archivo)

    with open(ruta_archivo, 'w', encoding='utf-8') as f:
        f.write(f"# {data['titulo']}\n\n")
        f.write(f"URL: {data['url']}\n\n")
        if data.get('fecha_apertura'):
            f.write(f"**Apertura:** {data['fecha_apertura']}\n")
        if data.get('fecha_cierre'):
            f.write(f"**Cierre:** {data['fecha_cierre']}\n")
        if data.get('nota_aprobacion'):
            f.write(f"**Nota de aprobación:** {data['nota_aprobacion']}\n")
        f.write(f"\n## Instrucciones\n\n{data['instrucciones']}\n")

    console.print(f"      [green]Assign guardado:[/green] {ruta_archivo}")
    return ruta_archivo


def _guardar_url(act: dict, data: dict, ruta_curso: str) -> str:
    """Guarda link externo (url) en Unidad-X/materiales/. Extrae YouTube si aplica."""
    ruta_unidad = _ruta_unidad_por_nombre(act["nombre"], ruta_curso, act.get("seccion", ""))
    ruta_materiales = os.path.join(ruta_unidad, "materiales")
    os.makedirs(ruta_materiales, exist_ok=True)

    nombre_archivo = _acortar_nombre_archivo(act["nombre"]) + ".md"
    ruta_archivo = os.path.join(ruta_materiales, nombre_archivo)

    external_url = data.get("external_url", "")

    with open(ruta_archivo, 'w', encoding='utf-8') as f:
        f.write(f"# {data['titulo']}\n\n")
        f.write(f"URL: {data['url']}\n\n")
        f.write(f"**Link externo:** [{external_url}]({external_url})\n")

    console.print(f"      [green]URL guardado:[/green] {ruta_archivo}")

    # YouTube: extraer subtítulos y resumir
    if external_url and ("youtube.com" in external_url or "youtu.be" in external_url):
        _procesar_youtube_video(external_url, ruta_materiales, act["nombre"])

    return ruta_archivo


def _guardar_choice(act: dict, data: dict, ruta_curso: str) -> str:
    """Guarda datos de encuesta (choice) en Unidad-X/actividades/."""
    ruta_unidad = _ruta_unidad_por_nombre(act["nombre"], ruta_curso, act.get("seccion", ""))
    ruta_actividades = os.path.join(ruta_unidad, "actividades")
    os.makedirs(ruta_actividades, exist_ok=True)

    nombre_archivo = _acortar_nombre_archivo(act["nombre"]) + ".md"
    ruta_archivo = os.path.join(ruta_actividades, nombre_archivo)

    with open(ruta_archivo, 'w', encoding='utf-8') as f:
        f.write(f"# {data['titulo']}\n\n")
        f.write(f"URL: {data['url']}\n\n")
        if data.get('fecha_apertura'):
            f.write(f"**Apertura:** {data['fecha_apertura']}\n")
        if data.get('fecha_cierre'):
            f.write(f"**Cierre:** {data['fecha_cierre']}\n")
        if data.get('opciones'):
            f.write("\n## Opciones\n\n")
            for opt in data['opciones']:
                f.write(f"- {opt}\n")
        f.write(f"\n## Detalle\n\n{data.get('pregunta', '')}\n")

    console.print(f"      [green]Choice guardado:[/green] {ruta_archivo}")
    return ruta_archivo


def _guardar_lesson(act: dict, data: dict, ruta_curso: str) -> str:
    """Guarda contenido de lección (lesson) en Unidad-X/actividades/."""
    ruta_unidad = _ruta_unidad_por_nombre(act["nombre"], ruta_curso, act.get("seccion", ""))
    ruta_actividades = os.path.join(ruta_unidad, "actividades")
    os.makedirs(ruta_actividades, exist_ok=True)

    nombre_archivo = _acortar_nombre_archivo(act["nombre"]) + ".md"
    ruta_archivo = os.path.join(ruta_actividades, nombre_archivo)

    contenido_md = data.get("contenido_texto", "")
    try:
        from markdownify import markdownify as md
        contenido_md = md(data.get("contenido_html", ""), heading_style="ATX")
    except ImportError:
        pass

    with open(ruta_archivo, 'w', encoding='utf-8') as f:
        f.write(f"# {data['titulo']}\n\n")
        f.write(f"URL: {data['url']}\n\n")
        if data.get('fecha_apertura'):
            f.write(f"**Apertura:** {data['fecha_apertura']}\n")
        if data.get('fecha_cierre'):
            f.write(f"**Cierre:** {data['fecha_cierre']}\n")
        if data.get('nota_maxima'):
            f.write(f"**Nota máxima:** {data['nota_maxima']}\n")
        f.write(f"\n{contenido_md}\n")

    console.print(f"      [green]Lesson guardado:[/green] {ruta_archivo}")
    return ruta_archivo


def _guardar_workshop(act: dict, data: dict, ruta_curso: str) -> str:
    """Guarda datos de taller (workshop) en Unidad-X/actividades/."""
    ruta_unidad = _ruta_unidad_por_nombre(act["nombre"], ruta_curso, act.get("seccion", ""))
    ruta_actividades = os.path.join(ruta_unidad, "actividades")
    os.makedirs(ruta_actividades, exist_ok=True)

    nombre_archivo = _acortar_nombre_archivo(act["nombre"]) + ".md"
    ruta_archivo = os.path.join(ruta_actividades, nombre_archivo)

    with open(ruta_archivo, 'w', encoding='utf-8') as f:
        f.write(f"# {data['titulo']}\n\n")
        f.write(f"URL: {data['url']}\n\n")
        if data.get('fecha_apertura'):
            f.write(f"**Apertura:** {data['fecha_apertura']}\n")
        if data.get('fecha_cierre'):
            f.write(f"**Cierre:** {data['fecha_cierre']}\n")
        if data.get('nota_maxima'):
            f.write(f"**Nota máxima:** {data['nota_maxima']}\n")
        f.write(f"\n## Instrucciones\n\n{data['instrucciones']}\n")

    console.print(f"      [green]Workshop guardado:[/green] {ruta_archivo}")
    return ruta_archivo


def _procesar_youtube_video(url: str, ruta_destino: str, nombre_actividad: str):
    """Extrae subtítulos y resume video YouTube si yt-dlp disponible."""
    try:
        from extractor_youtube import procesar_video_youtube
        procesar_video_youtube(url, ruta_destino, nombre_actividad)
    except ImportError:
        console.print(f"      [dim]yt-dlp no instalado, omitiendo YouTube:[/dim] {url}")
    except Exception as e:
        console.print(f"      [yellow]Error procesando YouTube {url}:[/yellow] {e}")


def _fusionar_metadatos(metadatos_list: list[dict]) -> dict:
    """Fusiona múltiples dicts de metadata del LLM en uno solo.

    Arrays se concatenan, strings se unen con saltos de línea.
    """
    campos_array = {"objetivos", "competencias", "criterios_evaluacion",
                    "unidades_tematicas", "bibliografia"}
    resultado: dict[str, list | str] = {}

    for meta in metadatos_list:
        for key, val in meta.items():
            if key in campos_array and isinstance(val, list):
                resultado.setdefault(key, []).extend(val)
            elif isinstance(val, str) and val.strip():
                existente = resultado.get(key, "")
                resultado[key] = f"{existente}\n\n{val}".strip() if existente else val

    return resultado


def _procesar_actividades_unidades(
    sidebar: list[dict],
    ruta_curso: str,
    nombre_profesor: str | None,
):
    """Phase 2: extrae y guarda cada actividad de cada unidad."""
    console.print("\n[bold cyan][5.75/6][/bold cyan] Extrayendo actividades de unidades...")
    unidad_actual = None
    for item in sidebar:
        if item.get("tipo") == "seccion":
            unidad_actual = item.get("nombre", "")
            continue
        if not item.get("url"):
            continue

        tipo = item.get("tipo", "unknown")
        nombre = item.get("nombre", "")
        url = item["url"]

        # Propagar sección actual para routing en _guardar_*()
        item["seccion"] = unidad_actual or ""

        # Determinar ruta destino basada en unidad actual
        ruta_destino = _ruta_unidad_por_nombre(nombre, ruta_curso)
        # Si la heurística fallback no funciona bien, intentar usar unidad_actual
        if unidad_actual and unidad_actual.lower() not in ruta_destino.lower():
            # Construir nombre de carpeta desde unidad_actual
            import re
            safe = re.sub(r'[<>"/\\|?*]', '-', unidad_actual).strip().replace(" ", "-")
            fallback = os.path.join(ruta_curso, safe)
            if os.path.isdir(fallback):
                ruta_destino = fallback

        console.print(f"    [dim]{tipo}:[/dim] {nombre[:50]}...")

        try:
            if tipo == "page":
                from extractor_modulos import extraer_modulo_page
                data = extraer_modulo_page(url)
                _guardar_page(item, data, ruta_curso)
            elif tipo == "quiz":
                from extractor_modulos import extraer_modulo_quiz
                data = extraer_modulo_quiz(url)
                _guardar_quiz(item, data, ruta_curso)
            elif tipo == "forum":
                from extractor_foro import extraer_discusiones_foro
                if nombre_profesor:
                    discusiones = extraer_discusiones_foro(url, nombre_profesor)
                    if discusiones:
                        _guardar_foro(item, discusiones, ruta_curso)
            elif tipo == "resource":
                from extractor_modulos import extraer_modulo_resource
                data = extraer_modulo_resource(url)
                _guardar_resource(item, data, ruta_curso)
            elif tipo == "folder":
                from extractor_modulos import extraer_modulo_folder
                data = extraer_modulo_folder(url)
                _guardar_folder(item, data, ruta_curso)
            elif tipo == "hvp":
                from extractor_modulos import extraer_modulo_hvp
                data = extraer_modulo_hvp(url)
                _guardar_hvp(item, data, ruta_curso)
            elif tipo == "assign":
                from extractor_modulos import extraer_modulo_assign
                data = extraer_modulo_assign(url)
                _guardar_assign(item, data, ruta_curso)
            elif tipo == "url":
                from extractor_modulos import extraer_modulo_url
                data = extraer_modulo_url(url)
                _guardar_url(item, data, ruta_curso)
            elif tipo == "choice":
                from extractor_modulos import extraer_modulo_choice
                data = extraer_modulo_choice(url)
                _guardar_choice(item, data, ruta_curso)
            elif tipo == "lesson":
                from extractor_modulos import extraer_modulo_lesson
                data = extraer_modulo_lesson(url)
                _guardar_lesson(item, data, ruta_curso)
            elif tipo == "workshop":
                from extractor_modulos import extraer_modulo_workshop
                data = extraer_modulo_workshop(url)
                _guardar_workshop(item, data, ruta_curso)
            else:
                console.print(f"      [dim]Tipo no soportado:[/dim] {tipo}")
        except SessionExpiredError:
            raise
        except Exception as e:
            console.print(f"      [yellow]Error:[/yellow] {e}")


if __name__ == "__main__":
    main()
