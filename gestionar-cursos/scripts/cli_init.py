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

import sys
import os
import time
import argparse
import re
from datetime import datetime

# Asegurar que scripts/ esté en path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from browser_api import (
    get_navegador, get_current_url, get_page_content,
    esta_usando_selenium, get_driver, click, esperar_carga,
    extraer_sidebar, extraer_texto_descripcion, extraer_links_materiales,
)
from verificar_sesion import verificar_sesion_moodle
from parsear_pga import parsear_pga
from parsear_sesiones import parsear_sesiones
from scaffold_curso import crear_estructura_curso

BASE_URL = "https://aulavirtual.uniremington.edu.co"
AUTH_POLL_INTERVAL = 3
AUTH_MAX_WAIT = 300  # 5 minutos


def _esperar_autenticacion():
    """Pausa interactiva: espera a que el usuario haga login."""
    print("\n[!] Sesión NO detectada en Moodle.")
    print("    Chrome está abierto. Por favor haz login manualmente.")
    print(f"    Re-verificando cada {AUTH_POLL_INTERVAL}s (máx {AUTH_MAX_WAIT//60} min)...")

    navegador = get_navegador()
    esperado = 0
    while esperado < AUTH_MAX_WAIT:
        time.sleep(AUTH_POLL_INTERVAL)
        navegador(BASE_URL + "/my/")
        if verificar_sesion_moodle():
            print("[OK] Sesión detectada.")
            return True
        esperado += AUTH_POLL_INTERVAL
        print(f"    ... esperando ({esperado}s)")

    return False


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
    for sel in ['.course-content', '#course-summary', '.summary', '.box.generalbox']:
        tag = soup.select_one(sel)
        if tag:
            vision = tag.get_text(separator='\n', strip=True)
            if len(vision) > 50:
                break

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


def main():
    parser = argparse.ArgumentParser(
        description="Inicializar curso desde Moodle Uniremington"
    )
    parser.add_argument("url", help="URL del curso en Moodle")
    parser.add_argument(
        "--destino", "-d", default=".",
        help="Directorio destino para el curso (default: actual)"
    )
    parser.add_argument(
        "--no-browser", action="store_true",
        help="No abrir Chrome; asume que ya está corriendo con --remote-debugging-port=9222"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  GESTIONAR-CURSOS :: CLI INIT")
    print("=" * 60)

    if not esta_usando_selenium():
        print("[ERROR] No se detectó modo CDP/Selenium.")
        print("        Asegúrate de tener selenium instalado:")
        print("        pip install selenium beautifulsoup4 lxml requests")
        sys.exit(1)

    # 1. Verificar sesión
    print("\n[1/6] Verificando sesión en Moodle...")
    navegador = get_navegador()
    navegador(BASE_URL + "/my/")

    if not verificar_sesion_moodle():
        if not _esperar_autenticacion():
            print("[ERROR] Tiempo de espera agotado. No autenticado.")
            sys.exit(1)

    print("\n[2/6] Navegando al curso...")
    navegador(args.url)
    url_actual = get_current_url()
    if "login" in url_actual:
        print("[ERROR] El curso requiere login. Reintentando...")
        if not _esperar_autenticacion():
            sys.exit(1)
        navegador(args.url)

    print(f"    URL actual: {get_current_url()}")
    contenido = get_page_content()

    # 3. Extraer info básica
    print("\n[3/6] Extrayendo información del curso...")
    info = _extraer_info_basica(contenido, args.url)
    print(f"    Nombre: {info['nombre']}")
    print(f"    Código: {info['codigo']}")
    print(f"    Unidades visibles: {info['unidades_count']}")

    # 4. Extraer PGA
    pga = []
    try:
        pga = parsear_pga(contenido)
        if pga:
            print(f"    PGA: {len(pga)} actividades")
        else:
            print("    PGA: no encontrado en página actual")
    except Exception as e:
        print(f"    [WARN] PGA extraction error: {e}")

    # 5. Extraer sesiones sincrónicas
    sesiones = []
    try:
        sesiones = parsear_sesiones(contenido)
        if sesiones:
            print(f"    Sesiones sincrónicas: {len(sesiones)}")
    except Exception as e:
        print(f"    [WARN] Sesiones extraction error: {e}")

    # 6. Extraer sidebar / unidades
    unidades = []
    try:
        sidebar = extraer_sidebar()
        for item in sidebar:
            unidades.append({
                "nombre": item["nombre"],
                "url": item["url"],
                "actividades": [],
            })
        print(f"    Unidades en sidebar: {len(unidades)}")
    except Exception as e:
        print(f"    [WARN] Sidebar extraction error: {e}")

    # 7. Preparar datos para scaffold
    datos_curso = {
        "nombre": info["nombre"],
        "codigo": info["codigo"],
        "url": args.url,
        "periodo": "",
        "bloque": "",
        "semanas": "",
        "fecha_inicio": info["fecha_inicio"],
        "fecha_fin": info["fecha_fin"],
        "vision_general": info["vision_general"],
        "unidades": unidades,
        "pga": pga,
        "sesiones": sesiones,
        "fecha_inicializacion": datetime.now().isoformat(),
        "secciones": [{"nombre": u["nombre"], "url": u["url"]} for u in unidades],
    }

    # 8. Crear estructura
    print("\n[4/6] Creando estructura local...")
    exito = crear_estructura_curso(datos_curso, args.destino)
    if not exito:
        print("[ERROR] Falló scaffold_curso")
        sys.exit(1)

    ruta_curso = os.path.join(args.destino, datos_curso["codigo"])
    print(f"    Creado: {os.path.abspath(ruta_curso)}")

    # 9. Descargar materiales básicos (módulo, microcurrículo)
    print("\n[5/6] Buscando materiales para descarga...")
    from descargar_materiales import descargar_material
    links = extraer_links_materiales()
    descargados = 0
    for link in links:
        if "Modulo" in link or "Microcurriculo" in link or "modulo" in link.lower():
            dest = os.path.join(ruta_curso, "MATERIA", os.path.basename(link.split("?")[0]))
            if descargar_material(link, dest):
                descargados += 1
    print(f"    Materiales descargados: {descargados}")

    # 10. Resumen
    print("\n[6/6] Inicialización completa.")
    print("=" * 60)
    print(f"Curso:    {datos_curso['nombre']}")
    print(f"Código:   {datos_curso['codigo']}")
    print(f"Ruta:     {os.path.abspath(ruta_curso)}")
    print(f"Unidades: {len(unidades)}")
    print(f"PGA:      {len(pga)} actividades")
    print("=" * 60)
    print("\nPróximos pasos:")
    print("  1. Revisar AGENTS.md y completar PERIOD / BLOCK")
    print("  2. Ejecutar: python cli_estado.py <ruta_curso> (cuando exista)")
    print("  3. Sincronizar con ClickUp via skill /use-clickup")


if __name__ == "__main__":
    main()
