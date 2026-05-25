"""
Navegador via Chrome DevTools Protocol (CDP).

Estrategia:
1. Intentar conectar a Chrome existente en localhost:9222
2. Si no disponible, lanzar Chrome nuevo con --remote-debugging-port=9222
3. Usar Selenium con debuggerAddress para controlar la instancia

Ventaja: el usuario puede tener sesión activa en Chrome.
El script se conecta a esa instancia y navega automáticamente.
"""

import os
import sys
import time
import socket
import atexit
import subprocess
import tempfile
from typing import List, Dict, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException
)

CDP_PORT = 9222
CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"/usr/bin/google-chrome",
    r"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]

_driver = None
_cdp_launched_by_us = False


def _find_chrome() -> Optional[str]:
    for path in CHROME_PATHS:
        if os.path.exists(path):
            return path
    return None


def _is_port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def _launch_chrome_cdp() -> str:
    """Lanza Chrome con puerto de debugging remoto."""
    global _cdp_launched_by_us
    chrome_path = _find_chrome()
    if not chrome_path:
        raise RuntimeError(
            "No se encontró Google Chrome. "
            "Instálalo o define la ruta en CHROME_PATHS."
        )

    user_data_dir = os.path.join(tempfile.gettempdir(), "chrome_cdp_skill")
    os.makedirs(user_data_dir, exist_ok=True)

    cmd = [
        chrome_path,
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-blink-features=AutomationControlled",
    ]

    print(f"[CDP] Lanzando Chrome: {chrome_path}")
    print(f"[CDP] Perfil temporal: {user_data_dir}")
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _cdp_launched_by_us = True
    time.sleep(3)  # Esperar arranque
    return chrome_path


def _conectar_driver():
    """Conecta Selenium a Chrome via CDP."""
    global _driver
    if _driver is not None:
        return _driver

    if not _is_port_open("localhost", CDP_PORT):
        _launch_chrome_cdp()
        # Esperar a que el puerto esté disponible
        for _ in range(10):
            if _is_port_open("localhost", CDP_PORT):
                break
            time.sleep(1)
        else:
            raise RuntimeError("Chrome no abrió el puerto de debugging.")

    opts = Options()
    opts.add_experimental_option("debuggerAddress", "localhost:9222")
    opts.add_argument("--disable-blink-features=AutomationControlled")

    try:
        _driver = webdriver.Chrome(options=opts)
    except WebDriverException as e:
        raise RuntimeError(f"No se pudo conectar a Chrome CDP: {e}")

    atexit.register(_cerrar)
    return _driver


def _cerrar():
    global _driver, _cdp_launched_by_us
    if _driver:
        _driver.quit()
        _driver = None
    if _cdp_launched_by_us:
        # No matamos el proceso Chrome para no cerrar sesiones del usuario
        pass


def get_driver():
    return _conectar_driver()


def navegar(url: str):
    driver = get_driver()
    driver.get(url)
    esperar_carga()


def obtener_url_actual() -> str:
    return get_driver().current_url


def obtener_contenido() -> str:
    return get_driver().page_source


def click(selector):
    driver = get_driver()
    if hasattr(selector, "click"):
        selector.click()
    else:
        # selector es un string: intentar CSS luego XPATH
        try:
            el = driver.find_element(By.CSS_SELECTOR, selector)
        except NoSuchElementException:
            el = driver.find_element(By.XPATH, selector)
        el.click()
    time.sleep(0.5)


def esperar_carga(timeout: int = 15):
    WebDriverWait(get_driver(), timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )


def esperar_selector(selector: str, timeout: int = 10):
    WebDriverWait(get_driver(), timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
    )


def encontrar_elementos(selector: str) -> List:
    return get_driver().find_elements(By.CSS_SELECTOR, selector)


def encontrar_menus_cerrados() -> List:
    """Encuentra secciones colapsadas de Moodle."""
    try:
        # Moodle usa aria-expanded="false" en toggles de sección
        return encontrar_elementos('[aria-expanded="false"]')
    except Exception:
        return []


def extraer_sidebar() -> List[Dict]:
    """Extrae items del sidebar/secciones del curso."""
    driver = get_driver()
    items = []
    try:
        secciones = driver.find_elements(By.CSS_SELECTOR, 'li.section, .course-section')
        for sec in secciones:
            try:
                nombre_el = sec.find_element(By.CSS_SELECTOR, '.sectionname, .course-section-name')
                nombre = nombre_el.text.strip()
            except NoSuchElementException:
                nombre = sec.text.strip().split('\n')[0]

            try:
                link_el = sec.find_element(By.CSS_SELECTOR, 'a')
                link = link_el.get_attribute('href')
            except NoSuchElementException:
                link = ""

            if nombre:
                items.append({"nombre": nombre, "url": link, "tipo": "seccion"})
    except Exception:
        pass
    return items


def extraer_texto_descripcion() -> str:
    driver = get_driver()
    for selector in [
        '.activity-description',
        '#intro',
        '.content',
        '.description',
        '.summary',
    ]:
        try:
            return driver.find_element(By.CSS_SELECTOR, selector).text
        except NoSuchElementException:
            continue
    return ""


def extraer_instrucciones() -> str:
    driver = get_driver()
    for selector in [
        '.submissioninstructions',
        '.generalbox',
        '.instrucciones',
        '.box.generalbox',
    ]:
        try:
            return driver.find_element(By.CSS_SELECTOR, selector).text
        except NoSuchElementException:
            continue
    return ""


def extraer_links_materiales() -> List[str]:
    driver = get_driver()
    links = []
    try:
        for a in driver.find_elements(By.CSS_SELECTOR, 'a[href*="pluginfile.php"]'):
            href = a.get_attribute('href')
            if href:
                links.append(href)
    except Exception:
        pass
    return links


def extraer_criterios() -> str:
    driver = get_driver()
    for selector in [
        '.gradingform',
        '.criteria',
        '.criterios',
        '.grade-criteria',
    ]:
        try:
            return driver.find_element(By.CSS_SELECTOR, selector).text
        except NoSuchElementException:
            continue
    return ""


def extraer_nombre_unidad() -> str:
    driver = get_driver()
    for selector in ['h1', '.sectionname', '.course-section-name', '.page-header-headings h1']:
        try:
            return driver.find_element(By.CSS_SELECTOR, selector).text.strip()
        except NoSuchElementException:
            continue
    return "Unidad"


def obtener_cookies() -> str:
    driver = get_driver()
    cookies = driver.get_cookies()
    return "; ".join(f"{c['name']}={c['value']}" for c in cookies)


def hacer_get(url: str, headers: Optional[Dict] = None) -> bytes:
    import requests
    cookie_str = obtener_cookies()
    req_headers = {"User-Agent": "Mozilla/5.0"}
    if headers:
        req_headers.update(headers)
    req_headers["Cookie"] = cookie_str
    resp = requests.get(url, headers=req_headers)
    resp.raise_for_status()
    return resp.content


def extraer_filas_tabla(html_content: str, header_text: str) -> List[Dict]:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, 'lxml')
    tablas = soup.find_all('table')
    for tabla in tablas:
        texto_tabla = tabla.get_text(separator=' ', strip=True)
        if header_text.lower() in texto_tabla.lower():
            filas_raw = []
            for tr in tabla.find_all('tr'):
                celdas = tr.find_all(['td', 'th'])
                texto_celdas = [c.get_text(strip=True) for c in celdas]
                if texto_celdas:
                    filas_raw.append(texto_celdas)
            if len(filas_raw) >= 2:
                headers = [h.lower().replace(' ', '_') for h in filas_raw[0]]
                return [
                    dict(zip(headers, fila))
                    for fila in filas_raw[1:]
                ]
    return []
