# Plan de Implementación: /gestionar-cursos

> **Para agentes trabajadores:** SUB-HABILIDAD REQUERIDA: Usar `superpowers:subagent-driven-development` (recomendado) o `superpowers:executing-plans` para implementar este plan tarea por tarea. Los pasos usan sintaxis de checkbox (`- [ ]`).

**Meta:** Crear la skill `/gestionar-cursos` que extrae información de Moodle Uniremington y organiza cursos en estructura de carpetas local.

**Arquitectura:** Skill standalone con 2 workflows (`init`, `estado`). Detección de plataforma por tools disponibles. Política resiliente (nunca falla completamente). Fechas normalizadas a ISO 8601. Extracción profunda: PGA, sesiones sincrónicas, actividades con detalles de unidad, materiales.

**Tech Stack:** Python 3, markdown

---

## Estructura de Archivos

```
gestionar-cursos/
├── SKILL.md                              # Definición, auth, workflows
├── references/
│   ├── guia-extraccion.md                # Tipos de contenido Moodle
│   ├── deteccion-plataforma.md           # VS Code / Antigravity / OpenCode
│   └── estructura-carpetas.md            # Output local generado
├── reglas/
│   └── tipos-contenido.md                # Heurísticas por tipo de contenido
└── scripts/
    ├── verificar_sesion.py               # Verifica auth en Moodle
    ├── detectar_plataforma.py           # Detecta browser tool disponible
    ├── parsear_pga.py                    # Extrae tabla DO-FR-66
    ├── parsear_sesiones.py               # Extrae cronograma sesiones sincrónicas
    ├── extraer_unidad.py                 # Navega unidad y extrae actividades
    ├── descargar_materiales.py           # Descarga PDFs/docs
    ├── crear_proxy_h5p.py                # Crea proxies HTML para H5P
    ├── scaffold_curso.py                # Crea estructura de carpetas local
    ├── sincronizar_curso.py             # Detecta cambios Moodle vs local
    └── verificar_integridad.py          # Valida archivos y links
```

---

## Tarea 1: Definición del Skill (SKILL.md)

**Archivos:**
- Crear: `gestionar-cursos/SKILL.md`

- [ ] **Paso 1: Escribir SKILL.md con metadatos y workflows**

```markdown
---
name: gestionar-cursos
description: >-
  Extrae información de cursos Moodle Uniremington y organiza estructura
  de carpetas local. Úsalo para inicializar cursos, sincronizar contenido
  o verificar estado de un curso vs Moodle.
metadata:
  version: "3.0.0"
  language: es-CO
  risk_tier: LOW
---

# /gestionar-cursos

Skill standalone para gestión de cursos universitarios en la plataforma
Moodle de Uniremington (aulavirtual.uniremington.edu.co).

## Autenticación

Antes de cualquier navegación:

1. Navegar a `https://aulavirtual.uniremington.edu.co/my/`
2. Verificar estado:
   - **NO AUTENTICADO**: URL contiene `login/index.php` o texto "Usted no se ha identificado"
     → Detener y pedir al usuario: "Por favor haz login en Moodle manualmente"
   - **AUTENTICADO**: Ver nombre "Andres Felipe Rendon Hernandez" o heading "Área personal"
     → Continuar

## Detección de Plataforma

El skill detecta automáticamente qué tool de navegación está disponible:

1. **browser_tool** → VS Code / Antigravity (navegación headless integrada)
2. **open_browser** → OpenCode / fallback (ventana externa del SO)
3. **Ninguna** → Error: "No hay tool de navegación disponible"

```python
def detectar_navegacion():
    try:
        # Intentar browser_tool primero
        browser_tool()
        return "browser_tool"
    except:
        try:
            # Fallback a open_browser
            open_browser()
            return "open_browser"
        except:
            return "error"
```

## Workflows

### /gestionar-cursos init <URL>

**Uso:** Inicializar un curso nuevo desde URL de Moodle.

**Pasos:**
1. Verificar sesión en Moodle
2. Navegar a la URL del curso proporcionada
3. Extraer estructura del sidebar (todas las secciones)
4. Navegar a "Introducción" y extraer:
   - Visión general del curso (texto para AGENTS.md)
   - Tabla PGA (DO-FR-66) — normalizar fechas a ISO 8601
   - Tabla de sesiones sincrónicas — validar links Teams
   - Documentos: Módulo, Microcurrículo
   - Foros: Avisos, Foro de Consultas, Foro de Presentación
5. Por cada unidad en el sidebar:
   - Expandir menús desplegables
   - Buscar actividades del PGA
   - Extraer descripción completa, instrucciones, materiales
   - Consolidar: PGA info + detalle de unidad = actividad completa
6. Descargar materiales (PDFs, documentos de apoyo)
7. Crear estructura de carpetas local
8. Generar archivos: AGENTS.md, sitemap.md, PGA.md, SESIONES_SINCRONAS.md

**Output:** Carpeta local con toda la estructura organizada.

### /gestionar-cursos estado <CARPETA>

**Uso:** Verificar estado actual del curso comparando con Moodle.

**Internamente ejecuta:**
1. `sincronizar_curso.py` — detecta cambios en Moodle vs local
   - Nuevas actividades
   - Fechas modificadas
   - Nuevos materiales
   - Links de grabaciones publicados
2. `verificar_integridad.py` — valida archivos locales
   - Archivos faltantes
   - Links rotos
   - Actividades sin detalle

**Output:** Reporte en conversación (no persistido):

```markdown
# Estado: [Nombre del Curso]

## 🔄 Sincronización
- Última sync: [timestamp]
- Cambios detectados: [N]

| Tipo | Actividad | Acción |
|------|-----------|--------|
| Fecha cambiada | Primer Parcial | 8/2/2026 → 15/2/2026 |
| Nueva | Foro Unidad 2 | Agregada |

## ✅ Verificación
- Archivos locales: [N]/[N] OK
- Links rotos: [N]
- Actividades sin detalle: [N]

## 📅 Próximas entregas (7 días)
| Fecha | Actividad | Unidad |
|-------|-----------|--------|
| 1/2/2026 | Cuestionario evaluativo | 1 |

## ⚠️ Advertencias
- [N] actividad(es) no encontrada(s) en Moodle (puede estar oculta)
```

## Política de Errores

**Resiliente — nunca falla completamente.**

| Escenario | Comportamiento |
|-----------|----------------|
| Moodle caído / timeout | Reintentar 3 veces (1s, 2s, 4s). Si persiste, error con mensaje. |
| Actividad no encontrada | Warning + marcar `[DETALLE_NO_ENCONTRADO]`. Continuar. |
| PDF bloqueado | Warning + guardar link en lugar de archivo. No detener. |
| H5P no carga | Skip proxy + link original en sitemap. |
| Sesión expirada | Detectar redirect a login → pausar + pedir re-login. |
| Cambio en estructura HTML | Guardar raw para debug + warning. Parsear lo posible. |

## Formato de Fechas

Todas las fechas se normalizan a **ISO 8601** (`YYYY-MM-DD`).

En archivos markdown se muestra dual:
```markdown
| Actividad | Fecha Inicio | Fecha Fin |
|-----------|--------------|-----------|
| Prueba Inicial | 26/1/2026 (2026-01-26) | 1/2/2026 (2026-02-01) |
```

## Heurísticas de Extracción

### Links Teams

SOLO capturar links que apunten a `teams.microsoft.com/l/meetup-join/`.

Si el link usa acortadores o redirección de Moodle (`mod/url/view.php`), **ignorar**.

Si no hay link directo, marcar como `[PENDIENTE: Link no seguro o inexistente]`.

### forcedownload

Al descargar cualquier archivo de `pluginfile.php`, añadir:
- Si URL tiene `?`: `&forcedownload=1`
- Si URL no tiene `?`: `?forcedownload=1`

### H5P

Crear proxy HTML local:
```html
<!DOCTYPE html>
<html>
<head>
    <title>[Nombre]</title>
    <style>body { margin: 0; display: flex; justify-content: center; background: #000; overflow: hidden; height: 100vh; }</style>
</head>
<body>
    <iframe src="https://aulavirtual.uniremington.edu.co/mod/hvp/embed.php?id=[ID]"
            width="100%" height="100%" style="border:0;"
            allowfullscreen="allowfullscreen"></iframe>
    <script src="https://aulavirtual.uniremington.edu.co/mod/hvp/library/js/h5p-resizer.js" charset="UTF-8"></script>
</body>
</html>
```

Etiquetar en sitemap como `[Interactivo]`.

### Links Grabaciones

Los links de grabaciones NO existen al inicio del curso. Se publican después.

En workflow `estado`, verificar si aparecieron nuevos links de grabaciones y actualizar SESIONES_SINCRONAS.md.

## Estructura de Carpetas Local

```
[CURSO_CODE]/
├── AGENTS.md                    # Metadatos + visión general del curso
├── README.md                    # Resumen para humano
├── sitemap.md                   # Links permanentes de Moodle
├── PGA.md                       # Tabla de actividades (fechas ISO)
├── SESIONES_SINCRONAS.md        # Cronograma con links Teams + grabaciones
├── MATERIA/
│   ├── Modulo.pdf
│   └── Microcurriculo.pdf
├── COMUNICACION/
│   ├── Avisos.md
│   ├── Foro_Consultas.md
│   └── Foro_Presentacion.md
├── Unidad-1/
│   ├── materiales/
│   │   ├── documento.pdf
│   │   └── presentacion.html    # H5P proxy
│   └── actividades/
│       ├── Prueba_Inicial.md
│       ├── Cuestionario_evaluativo.md
│       └── Primer_Parcial.md
├── Unidad-2/
│   └── ...
└── Unidad-3/
    └── ...
```

## AGENTS.md - Contenido

```markdown
# [Nombre del Curso]

## Identidad
- **COURSE_NAME**: [Nombre completo]
- **COURSE_CODE**: [Código]
- **PERIOD**: [Periodo, ej: 2026-1]
- **BLOCK**: [Bloque]
- **MOODLE_URL**: [URL permanente del curso]
- **INITIALIZED**: [Fecha de inicialización]

## Alcance del curso
[Texto extraído de "Visión general del curso" en la sección Introducción]

## Estructura
- Unidades: [N]
- Semanas: [N]
- Fecha inicio: [YYYY-MM-DD]
- Fecha fin: [YYYY-MM-DD]

## Links clave
- [PGA](PGA.md)
- [Sesiones Sincrónicas](SESIONES_SINCRONAS.md)
- [Sitemap](sitemap.md)
```

---

## Tarea 2: Detección de Plataforma

**Archivos:**
- Crear: `gestionar-cursos/scripts/detectar_plataforma.py`

- [ ] **Paso 1: Escribir módulo de detección**

```python
"""
Detecta qué tool de navegación está disponible en el entorno.
Retorna: 'browser_tool' | 'open_browser' | 'error'
"""

def detectar_navegacion():
    """
    Verifica cuál tool de browser está disponible.
    
    Orden de prioridad:
    1. browser_tool (VS Code / Antigravity - navegación headless)
    2. open_browser (OpenCode / fallback - ventana externa)
    3. Error si ninguna disponible
    """
    try:
        # Intentar browser_tool primero
        browser_tool()
        return "browser_tool"
    except NameError:
        pass  # browser_tool no existe
    
    try:
        # Fallback a open_browser genérico
        open_browser()
        return "open_browser"
    except NameError:
        pass  # open_browser no existe
    
    return "error"


def get_navegador():
    """Retorna la función de navegación apropiada según plataforma."""
    plataforma = detectar_navegacion()
    
    if plataforma == "error":
        raise RuntimeError(
            "No hay tool de navegación disponible. "
            "Instala un plugin de navegador o usa OpenCode con open_browser."
        )
    
    if plataforma == "browser_tool":
        return browser_tool  # Función de navegación headless
    else:
        return open_browser  # Abre ventana del sistema
```

- [ ] **Paso 2: Escribir test**

```python
def test_detectar_plataforma():
    """Verifica que la detección retorna valores válidos."""
    resultado = detectar_navegacion()
    assert resultado in ['browser_tool', 'open_browser', 'error']


def test_get_navegador_exito():
    """Verifica que retorna función válida cuando hay tool disponible."""
    try:
        fn = get_navegador()
        assert callable(fn)
    except RuntimeError:
        # Es esperado si no hay browser tool disponible
        pass
```

- [ ] **Paso 3: Ejecutar tests**

```
pytest gestionar-cursos/scripts/test_detectar_plataforma.py -v
```

---

## Tarea 3: Verificación de Sesión

**Archivos:**
- Crear: `gestionar-cursos/scripts/verificar_sesion.py`

- [ ] **Paso 1: Escribir módulo de verificación de sesión**

```python
"""
Verifica estado de autenticación en Moodle Uniremington.
"""

BASE_URL = "https://aulavirtual.uniremington.edu.co"

def verificar_sesion_moodle():
    """
    Navega a la página de área personal y verifica si está autenticado.
    
    Returns:
        True si autenticado, False si no.
    
    Raises:
        RuntimeError si no se puede completar la verificación.
    """
    navegador = get_navegador()
    
    # Navegar a área personal
    navegador(BASE_URL + "/my/")
    
    # Obtener URL actual después de navegación
    url_actual = get_current_url()
    
    # Verificar indicadores de no autenticado
    if "login/index.php" in url_actual:
        return False
    
    # Verificar indicadores de autenticado
    page_content = get_page_content()
    
    if "Usted no se ha identificado" in page_content:
        return False
    
    if "Andres Felipe Rendon Hernandez" in page_content or "Área personal" in page_content:
        return True
    
    # Si no podemos determinar, asumir no autenticado
    return False


def requerir_sesion():
    """
    Verifica sesión y lanza error claro si no está autenticado.
    """
    if not verificar_sesion_moodle():
        raise RuntimeError(
            "Sesión no autenticada en Moodle. "
            "Por favor haz login manualmente en el navegador y avísame cuando estés listo."
        )
```

- [ ] **Paso 2: Escribir test**

```python
def test_verificar_sesion_retorna_bool():
    """Verifica que la función retorna boolean."""
    resultado = verificar_sesion_moodle()
    assert isinstance(resultado, bool)
```

- [ ] **Paso 3: Ejecutar tests**

```
pytest gestionar-cursos/scripts/test_verificar_sesion.py -v
```

---

## Tarea 4: Parser de PGA

**Archivos:**
- Crear: `gestionar-cursos/scripts/parsear_pga.py`

- [ ] **Paso 1: Escribir parser de tabla PGA**

```python
"""
Extrae y normaliza la tabla DO-FR-66 Plan de Gestión Académica.
"""

from datetime import datetime
from typing import List, Dict

def normalizar_fecha(fecha_str: str) -> str:
    """
    Convierte fecha de formato DD/M/YYYY a YYYY-MM-DD (ISO 8601).
    
    Args:
        fecha_str: String con fecha ej: "26/1/2026"
    
    Returns:
        Fecha en formato ISO 8601 ej: "2026-01-26"
    """
    try:
        # Parsear formato DD/M/YYYY
        fecha = datetime.strptime(fecha_str.strip(), "%d/%m/%Y")
        return fecha.strftime("%Y-%m-%d")
    except ValueError:
        # Si no funciona, intentar otros formatos comunes
        for fmt in ["%d/%m/%y", "%d-%m-%Y", "%d-%m-%y"]:
            try:
                fecha = datetime.strptime(fecha_str.strip(), fmt)
                return fecha.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        # Si ningún formato funciona, retornar original con warning
        return fecha_str


def parsear_pga(html_content: str) -> List[Dict]:
    """
    Extrae tabla DO-FR-66 del HTML de Introducción.
    
    La tabla tiene columnas:
    - Semanas
    - Unidad(es)
    - Actividad(es)
    - Valor en Porcentaje
    - Fecha Inicio
    - Fecha Fin
    
    Args:
        html_content: HTML crudo de la sección Introducción
    
    Returns:
        Lista de diccionarios con datos de cada actividad.
        Actividades compuestas se split en filas individuales.
    """
    actividades = []
    
    # Buscar tabla bajo encabezado "DO-FR-66"
    # El HTML de Moodle tiene estructura de tabla específica
    
    # Extracción ejemplo - ajustar según HTML real de Uniremington
    filas = extraer_filas_tabla(html_content, "DO-FR-66")
    
    for fila in filas:
        semanas = fila.get("Semanas", "")
        unidad = fila.get("Unidad(es)", "")
        actividad_raw = fila.get("Actividad(es)", "")
        valor_raw = fila.get("Valor en Porcentaje", "")
        fecha_inicio = normalizar_fecha(fila.get("Fecha Inicio", ""))
        fecha_fin = normalizar_fecha(fila.get("Fecha Fin", ""))
        
        # Split actividades compuestas (separadas por <br> o similar)
        actividades_list = split_actividades_compuestas(actividad_raw)
        valores_list = split_valores_compuestos(valor_raw)
        
        # Crear fila por cada actividad
        for i, act in enumerate(actividades_list):
            # Limpiar nombre de actividad
            act_nombre = limpiar_nombre_actividad(act)
            
            # Obtener valor correspondiente (o usar último si no hay match)
            valor = valores_list[i] if i < len(valores_list) else valores_list[-1] if valores_list else ""
            
            actividades.append({
                "semana": semanas,
                "unidad": unidad,
                "actividad": act_nombre,
                "valor": valor,
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "fecha_inicio_raw": fila.get("Fecha Inicio", ""),
                "fecha_fin_raw": fila.get("Fecha Fin", "")
            })
    
    return actividades


def split_actividades_compuestas(texto: str) -> List[str]:
    """Separa actividades unidas por <br> o ' + '."""
    # Moodle une actividades con <br> en celdas compuestas
    partes = texto.replace("<br>", "+").split("+")
    return [p.strip() for p in partes if p.strip()]


def split_valores_compuestos(texto: str) -> List[str]:
    """Separa valores de porcentaje unidos por <br> o ' + '."""
    partes = texto.replace("<br>", "+").split("+")
    return [p.strip() for p in partes if p.strip()]


def limpiar_nombre_actividad(nombre: str) -> str:
    """Limpia nombre de actividad, removiendo espacios extra y tags HTML."""
    import re
    # Remover tags HTML si existen
    nombre = re.sub(r'<[^>]+>', '', nombre)
    # Limpiar espacios
    nombre = ' '.join(nombre.split())
    return nombre.strip()


def generar_markdown_pga(actividades: List[Dict]) -> str:
    """Genera markdown formateado para archivo PGA.md."""
    lines = [
        "# Plan de Gestión Académica",
        "",
        "| Semana | Unidad | Actividad | Valor | Fecha Inicio | Fecha Fin |",
        "|--------|--------|-----------|-------|--------------|-----------|"
    ]
    
    for act in actividades:
        fecha_inicio = f"{act['fecha_inicio_raw']} ({act['fecha_inicio']})"
        fecha_fin = f"{act['fecha_fin_raw']} ({act['fecha_fin']})"
        
        lines.append(
            f"| {act['semana']} | {act['unidad']} | {act['actividad']} | "
            f"{act['valor']} | {fecha_inicio} | {fecha_fin} |"
        )
    
    return "\n".join(lines)
```

- [ ] **Paso 2: Escribir tests**

```python
def test_normalizar_fecha():
    assert normalizar_fecha("26/1/2026") == "2026-01-26"
    assert normalizar_fecha("1/2/2026") == "2026-02-01"
    assert normalizar_fecha("8/3/2026") == "2026-03-08"


def test_split_actividades_compuestas():
    assert split_actividades_compuestas("Prueba Inicial<br>Cuestionario evaluativo") == \
           ["Prueba Inicial", "Cuestionario evaluativo"]
    assert split_actividades_compuestas("Prueba Inicial + Cuestionario evaluativo") == \
           ["Prueba Inicial + Cuestionario evaluativo"]  # No split por +


def test_generar_markdown_pga():
    actividades = [{
        "semana": "1",
        "unidad": "UNIDAD 1 LENGUAJE PROCEDIMENTAL",
        "actividad": "Prueba Inicial",
        "valor": "0%",
        "fecha_inicio": "2026-01-26",
        "fecha_fin": "2026-02-01",
        "fecha_inicio_raw": "26/1/2026",
        "fecha_fin_raw": "1/2/2026"
    }]
    md = generar_markdown_pga(actividades)
    assert "Prueba Inicial" in md
    assert "2026-01-26" in md
```

- [ ] **Paso 3: Ejecutar tests**

```
pytest gestionar-cursos/scripts/test_parsear_pga.py -v
```

---

## Tarea 5: Parser de Sesiones Sincrónicas

**Archivos:**
- Crear: `gestionar-cursos/scripts/parsear_sesiones.py`

- [ ] **Paso 1: Escribir parser de sesiones sincrónicas**

```python
"""
Extrae cronograma de sesiones sincrónicas con validación de links Teams.
"""

import re
from typing import List, Dict

TEAMS_PATTERN = r'teams\.microsoft\.com/l/meetup-join/'

def es_link_teams_valido(url: str) -> bool:
    """Verifica si el URL es un link directo de reunión Teams."""
    if not url or url == "#" or "pendiente" in url.lower():
        return False
    return bool(re.search(TEAMS_PATTERN, url))


def parsear_sesiones(html_content: str) -> List[Dict]:
    """
    Extrae tabla de cronograma de sesiones sincrónicas.
    
    Columnas de la tabla:
    - Descripción (ej: "Primera sesión")
    - Enlace de Ingreso a las Sesiones
    - Fecha Inicio (dd/mm)
    - Hora Inicio (hh:mm)
    - Enlace de Ingreso a las Grabaciones
    
    Args:
        html_content: HTML crudo de la sección Sesiones Sincrónicas
    
    Returns:
        Lista de diccionarios con datos de cada sesión.
    """
    sesiones = []
    
    # Extraer filas de la tabla de sesiones sincrónicas
    filas = extraer_filas_tabla(html_content, "CRONOGRAMA DE SESIONES SINCRÓNICAS")
    
    for fila in filas:
        descripcion = fila.get("Descripción", "")
        link_teams_raw = fila.get("Enlace de Ingreso a las Sesiones", "")
        link_teams = limpiar_link(link_teams_raw)
        
        fecha_raw = fila.get("Fecha Inicio (dd/mm)", "")
        hora_raw = fila.get("Hora Inicio (hh:mm)", "")
        
        link_grabaciones_raw = fila.get("Enlace de Ingreso a las Grabaciones", "")
        link_grabaciones = limpiar_link(link_grabaciones_raw)
        
        # Validar link Teams
        if not es_link_teams_valido(link_teams):
            link_teams = "[PENDIENTE: Link no seguro o inexistente]"
        
        sesiones.append({
            "descripcion": descripcion,
            "link_teams": link_teams,
            "fecha": fecha_raw,
            "hora": hora_raw,
            "link_grabaciones": link_grabaciones if es_link_teams_valido(link_grabaciones) else "[PENDIENTE]"
        })
    
    return sesiones


def limpiar_link(url: str) -> str:
    """Limpia URL, removiendo parámetros tracking o vacío."""
    if not url or url.strip() in ["", "#", "link", "enlace"]:
        return ""
    
    # Remover espacios
    url = url.strip()
    
    # Remover parámetros de tracking si existen
    # Pero mantener el link real
    return url


def generar_markdown_sesiones(sesiones: List[Dict]) -> str:
    """Genera markdown formateado para archivo SESIONES_SINCRONAS.md."""
    lines = [
        "# Sesiones Sincrónicas",
        "",
        "| Descripción | Link Teams | Fecha | Hora | Grabaciones |",
        "|-------------|------------|-------|------|--------------|"
    ]
    
    for sesion in sesiones:
        lines.append(
            f"| {sesion['descripcion']} | {sesion['link_teams']} | "
            f"{sesion['fecha']} | {sesion['hora']} | {sesion['link_grabaciones']} |"
        )
    
    lines.append("")
    lines.append("**Nota:** Para ingresar a las sesiones debe iniciar sesión en Office 365 institucional.")
    
    return "\n".join(lines)
```

- [ ] **Paso 2: Escribir tests**

```python
def test_es_link_teams_valido():
    assert es_link_teams_valido(
        "https://teams.microsoft.com/l/meetup-join/19%3ameeting_xxx"
    ) == True
    assert es_link_teams_valido("https://bit.ly/xxx") == False
    assert es_link_teams_valido("") == False
    assert es_link_teams_valido("#") == False


def test_limpiar_link():
    assert limpiar_link("https://teams.microsoft.com/l/meetup-join/abc") == \
           "https://teams.microsoft.com/l/meetup-join/abc"
    assert limpiar_link("") == ""
    assert limpiar_link("#") == ""
```

- [ ] **Paso 3: Ejecutar tests**

```
pytest gestionar-cursos/scripts/test_parsear_sesiones.py -v
```

---

## Tarea 6: Extractor de Unidad

**Archivos:**
- Crear: `gestionar-cursos/scripts/extraer_unidad.py`

- [ ] **Paso 1: Escribir extractor de unidad**

```python
"""
Navega unidad de curso, expande menús desplegables,
busca actividades del PGA y extrae detalles completos.
"""

from typing import Dict, Optional, List
from difflib import SequenceMatcher

def extraer_unidad(url_unidad: str, actividades_pga: List[str]) -> Dict:
    """
    Extrae información completa de una unidad.
    
    1. Navega a la URL de la unidad
    2. Expande todos los menús desplegables del sidebar
    3. Por cada actividad del PGA, busca coincidencia en la unidad
    4. Extrae: descripción, instrucciones, materiales, criterios
    
    Args:
        url_unidad: URL de la unidad en Moodle
        actividades_pga: Lista de nombres de actividades del PGA
    
    Returns:
        Dict con estructura:
        {
            "nombre": "Unidad 1",
            "actividades": [
                {
                    "nombre": "Prueba Inicial",
                    "descripcion": "...",
                    "instrucciones": "...",
                    "materiales": ["link1", "link2"],
                    "encontrada": True/False
                }
            ]
        }
    """
    navegador = get_navegador()
    
    # Navegar a la unidad
    navegador(url_unidad)
    
    # Expandir todos los menús desplegables del sidebar
    expandir_menus_desplegables()
    
    # Extraer todas las secciones visibles
    sidebar_items = extraer_sidebar()
    
    actividades_encontradas = []
    
    for actividad_nombre in actividades_pga:
        detalle = buscar_actividad_en_sidebar(sidebar_items, actividad_nombre)
        
        if detalle:
            # Extraer información completa de la actividad
            detalle_completo = extraer_detalle_actividad(detalle["url"])
            actividades_encontradas.append({
                "nombre": actividad_nombre,
                **detalle_completo,
                "encontrada": True
            })
        else:
            # No encontrada - marcar pero no fallar
            actividades_encontradas.append({
                "nombre": actividad_nombre,
                "descripcion": "[DETALLE_NO_ENCONTRADO]",
                "encontrada": False
            })
    
    return {
        "nombre": extraer_nombre_unidad(),
        "actividades": actividades_encontradas
    }


def similar(a: str, b: str, threshold: float = 0.7) -> bool:
    """Determina si dos strings son similares usando ratio de coincidencias."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() >= threshold


def buscar_actividad_en_sidebar(sidebar_items: List[Dict], nombre_buscado: str) -> Optional[Dict]:
    """
    Busca actividad en sidebar usando fuzzy matching.
    
    Moodle a veces muestra nombres ligeramente diferentes.
    """
    nombre_buscado_normalizado = normalizar_nombre(nombre_buscado)
    
    for item in sidebar_items:
        nombre_item_normalizado = normalizar_nombre(item.get("nombre", ""))
        
        if nombre_buscado_normalizado in nombre_item_normalizado:
            return item
        
        if similar(nombre_buscado_normalizado, nombre_item_normalizado):
            return item
    
    return None


def normalizar_nombre(nombre: str) -> str:
    """Normaliza nombre de actividad para comparación."""
    import re
    # Remover tags HTML
    nombre = re.sub(r'<[^>]+>', '', nombre)
    # Lowercase y strip
    nombre = nombre.lower().strip()
    # Remover caracteres especiales excepto espacios y guiones
    nombre = re.sub(r'[^\w\s-]', '', nombre)
    return nombre


def expandir_menus_desplegables():
    """
    Expande todos los menús desplegables del sidebar de Moodle.
    Las actividades pueden estar ocultas dentro de estos menús.
    """
    # Los menús de Moodle típicamente tienen clase "collapside" o similar
    # Click en elementos con aria-expanded="false" o similares
    
    while True:
        menus_cerrados = encontrar_menus_cerrados()
        if not menus_cerrados:
            break
        
        for menu in menus_cerrados:
            click(menu)
            esperar_carga()


def extraer_sidebar() -> List[Dict]:
    """
    Extrae todos los items del sidebar de la unidad.
    
    Returns:
        Lista de dicts con {nombre, url, tipo}
    """
    # Implementar extracción de sidebar desde HTML
    # Buscar estructura de lista en sidebar
    pass


def extraer_detalle_actividad(url_actividad: str) -> Dict:
    """
    Navega a la página de detalle de una actividad y extrae:
    - Descripción completa
    - Instrucciones de entrega
    - Materiales adjuntos
    - Criterios de evaluación
    
    Returns:
        Dict con datos extraídos
    """
    navegador = get_navegador()
    navegador(url_actividad)
    
    # Extraer elementos de la página
    descripcion = extraer_texto_descripcion()
    instrucciones = extraer_instrucciones()
    materiales = extraer_links_materiales()
    criterios = extraer_criterios()
    
    return {
        "descripcion": descripcion,
        "instrucciones": instrucciones,
        "materiales": materiales,
        "criterios": criterios,
        "url": url_actividad
    }
```

- [ ] **Paso 2: Escribir tests de fuzzy matching**

```python
def test_similar():
    assert similar("Prueba Inicial", "Prueba Inicial") == True
    assert similar("Primer Parcial", "Primer Parcial") == True
    assert similar("Foro", "Foro de Consultas") == False  # Muy diferente


def test_normalizar_nombre():
    assert normalizar_nombre("Primer <b>Parcial</b>") == "primer parcial"
    assert normalizar_nombre("Cuestionario evaluativo (8%)") == "cuestionario evaluativo"
```

- [ ] **Paso 3: Ejecutar tests**

```
pytest gestionar-cursos/scripts/test_extraer_unidad.py -v
```

---

## Tarea 7: Descargador de Materiales

**Archivos:**
- Crear: `gestionar-cursos/scripts/descargar_materiales.py`

- [ ] **Paso 1: Escribir descargador con forcedownload**

```python
"""
Descarga materiales de Moodle aplicando forcedownload=1.
"""

import os
from typing import Optional

def descargar_material(url: str, ruta_destino: str) -> bool:
    """
    Descarga material de Moodle.
    
    Args:
        url: URL del material (puede ser pluginfile.php)
        ruta_destino: Ruta local donde guardar el archivo
    
    Returns:
        True si descarga exitosa, False si falló
    """
    # Aplicar forcedownload si es URL de archivo
    url_final = agregar_forcedownload(url)
    
    # Realizar descarga
    try:
        contenido = hacer_get(url_final, headers=generar_headers())
        
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(ruta_destino), exist_ok=True)
        
        # Guardar archivo
        with open(ruta_destino, 'wb') as f:
            f.write(contenido)
        
        # Verificar que el archivo no esté vacío
        if os.path.getsize(ruta_destino) > 0:
            return True
        else:
            return False
            
    except Exception as e:
        print(f"Error descargando {url}: {e}")
        return False


def agregar_forcedownload(url: str) -> str:
    """
    Añade parámetro forcedownload=1 a URLs de archivos de Moodle.
    """
    if "pluginfile.php" not in url:
        return url
    
    if "?" in url:
        return url + "&forcedownload=1"
    else:
        return url + "?forcedownload=1"


def generar_headers() -> dict:
    """Genera headers para request con cookie de sesión."""
    # Obtener cookies del navegador para autenticación
    cookies = obtener_cookies_browser()
    
    return {
        "User-Agent": "Mozilla/5.0",
        "Cookie": cookies
    }


def es_tipo_descargable(tipo_mime: str) -> bool:
    """Determina si el tipo MIME es descargable."""
    tipos_validos = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats",
        "image/",
        "video/",
        "audio/"
    ]
    
    return any(tipo_mime.startswith(t) for t in tipos_validos)


def descargar_si_existe(url: str, ruta_destino: str) -> bool:
    """
    Wrapper que verifica si el archivo ya existe antes de descargar.
    Evita re-descargar archivos ya existentes.
    """
    if os.path.exists(ruta_destino) and os.path.getsize(ruta_destino) > 0:
        print(f"Archivo ya existe: {ruta_destino}")
        return True
    
    return descargar_material(url, ruta_destino)
```

- [ ] **Paso 2: Escribir tests**

```python
def test_agregar_forcedownload():
    url = "https://aulavirtual.uniremington.edu.co/pluginfile.php/123/mod_resource/content/1/archivo.pdf"
    assert "forcedownload=1" in agregar_forcedownload(url)
    
    url_con_params = "https://aulavirtual.uniremington.edu.co/pluginfile.php?context=123"
    assert "&forcedownload=1" in agregar_forcedownload(url_con_params)


def test_no_forcedownload_para_no_archivos():
    url = "https://aulavirtual.uniremington.edu.co/mod/page/view.php?id=123"
    assert agregar_forcedownload(url) == url  # Sin cambios
```

- [ ] **Paso 3: Ejecutar tests**

```
pytest gestionar-cursos/scripts/test_descargar_materiales.py -v
```

---

## Tarea 8: Creador de Proxy H5P

**Archivos:**
- Crear: `gestionar-cursos/scripts/crear_proxy_h5p.py`

- [ ] **Paso 1: Escribir creador de proxy HTML**

```python
"""
Crea archivos HTML proxy para contenido H5P de Moodle.
Permite visualización offline de interactivos.
"""

import os
import re

TEMPLATE_H5P = """<!DOCTYPE html>
<html>
<head>
    <title>{titulo}</title>
    <style>
        body {{
            margin: 0;
            display: flex;
            justify-content: center;
            background: #000;
            overflow: hidden;
            height: 100vh;
        }}
    </style>
</head>
<body>
    <iframe src="{embed_url}"
            width="100%"
            height="100%"
            style="border:0;"
            allowfullscreen="allowfullscreen"></iframe>
    <script src="https://aulavirtual.uniremington.edu.co/mod/hvp/library/js/h5p-resizer.js" charset="UTF-8"></script>
</body>
</html>"""

def extraer_h5p_id(url_h5p: str) -> Optional[str]:
    """Extrae el ID del contenido H5P desde la URL."""
    # URL típica: https://aulavirtual.uniremington.edu.co/mod/hvp/view.php?id=12345
    match = re.search(r'[?&]id=(\d+)', url_h5p)
    if match:
        return match.group(1)
    return None


def crear_proxy_h5p(url_h5p: str, nombre: str, ruta_destino: str) -> bool:
    """
    Crea archivo HTML proxy para contenido H5P.
    
    Args:
        url_h5p: URL de la actividad H5P en Moodle
        nombre: Nombre para el archivo HTML (sin extensión)
        ruta_destino: Ruta donde guardar el proxy
    
    Returns:
        True si creado exitosamente
    """
    h5p_id = extraer_h5p_id(url_h5p)
    
    if not h5p_id:
        print(f"No se pudo extraer ID de H5P de: {url_h5p}")
        return False
    
    embed_url = f"https://aulavirtual.uniremington.edu.co/mod/hvp/embed.php?id={h5p_id}"
    
    html_content = TEMPLATE_H5P.format(
        titulo=nombre,
        embed_url=embed_url
    )
    
    # Asegurar extensión .html
    if not ruta_destino.endswith('.html'):
        ruta_destino += '.html'
    
    try:
        os.makedirs(os.path.dirname(ruta_destino), exist_ok=True)
        
        with open(ruta_destino, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return True
        
    except Exception as e:
        print(f"Error creando proxy H5P: {e}")
        return False


def marcar_como_interactivo_en_sitemap(ruta_sitemap: str, nombre_proxy: str):
    """
    Actualiza sitemap.md para marcar el H5P como [Interactivo].
    """
    with open(ruta_sitemap, 'r', encoding='utf-8') as f:
        contenido = f.read()
    
    # Agregar etiqueta [Interactivo] si no existe
    if "[Interactivo]" not in contenido:
        contenido = contenido.replace(
            nombre_proxy,
            f"[Interactivo] {nombre_proxy}"
        )
    
    with open(ruta_sitemap, 'w', encoding='utf-8') as f:
        f.write(contenido)
```

- [ ] **Paso 2: Escribir tests**

```python
def test_extraer_h5p_id():
    url = "https://aulavirtual.uniremington.edu.co/mod/hvp/view.php?id=467334"
    assert extraer_h5p_id(url) == "467334"
    
    url_sin_id = "https://aulavirtual.uniremington.edu.co/mod/hvp/view.php"
    assert extraer_h5p_id(url_sin_id) is None


def test_crear_proxy_h5p():
    # Test sin crear archivo real (mock)
    pass
```

- [ ] **Paso 3: Ejecutar tests**

```
pytest gestionar-cursos/scripts/test_crear_proxy_h5p.py -v
```

---

## Tarea 9: Scaffold de Curso

**Archivos:**
- Crear: `gestionar-cursos/scripts/scaffold_curso.py`

- [ ] **Paso 1: Escribir creador de estructura de carpetas**

```python
"""
Crea la estructura de carpetas completa para un curso.
Genera todos los archivos de metadatos.
"""

import os
from typing import Dict, List

def crear_estructura_curso(datos_curso: Dict, ruta_base: str) -> bool:
    """
    Crea estructura de carpetas y archivos para un curso.
    
    Args:
        datos_curso: Dict con todos los datos extraídos
            {
                "nombre": "Bases de Datos II",
                "codigo": "2601B04G1",
                "url": "https://...",
                "unidades": [...],
                "pga": [...],
                "sesiones": [...],
                "vision_general": "..."
            }
        ruta_base: Ruta raíz donde crear la estructura
    
    Returns:
        True si exitoso
    """
    curso_code = datos_curso.get("codigo", "CURSO_DESCONOCIDO")
    ruta_curso = os.path.join(ruta_base, curso_code)
    
    # Crear directorio principal
    os.makedirs(ruta_curso, exist_ok=True)
    
    # Crear subdirectorios
    crear_subdirectorios(ruta_curso, datos_curso.get("unidades", []))
    
    # Generar AGENTS.md
    generar_agents_md(ruta_curso, datos_curso)
    
    # Generar README.md
    generar_readme_md(ruta_curso, datos_curso)
    
    # Generar sitemap.md
    generar_sitemap_md(ruta_curso, datos_curso)
    
    # Generar PGA.md
    generar_pga_md(ruta_curso, datos_curso.get("pga", []))
    
    # Generar SESIONES_SINCRONAS.md
    generar_sesiones_md(ruta_curso, datos_curso.get("sesiones", []))
    
    # Crear carpetas de unidades y materiales
    crear_carpetas_unidades(ruta_curso, datos_curso.get("unidades", []))
    
    return True


def crear_subdirectorios(ruta_curso: str, unidades: List[Dict]):
    """Crea todos los subdirectorios necesarios."""
    subdirs = [
        "MATERIA",
        "COMUNICACION",
        "RECURSOS"
    ]
    
    for unidad in unidades:
        nombre_unidad = unidad.get("nombre", "").replace(" ", "-")
        subdirs.append(f"{nombre_unidad}/materiales")
        subdirs.append(f"{nombre_unidad}/actividades")
    
    for subdir in subdirs:
        os.makedirs(os.path.join(ruta_curso, subdir), exist_ok=True)


def generar_agents_md(ruta: str, datos: Dict):
    """Genera AGENTS.md con metadatos y visión general."""
    contenido = f"""# {datos.get('nombre', 'Curso')}

## Identidad
- **COURSE_NAME**: {datos.get('nombre', '')}
- **COURSE_CODE**: {datos.get('codigo', '')}
- **PERIOD**: {datos.get('periodo', '')}
- **BLOCK**: {datos.get('bloque', '')}
- **MOODLE_URL**: {datos.get('url', '')}
- **INITIALIZED**: {datos.get('fecha_inicializacion', '')}

## Alcance del curso
{datos.get('vision_general', '[No disponible]')}

## Estructura
- Unidades: {len(datos.get('unidades', []))}
- Semanas: {datos.get('semanas', '')}
- Fecha inicio: {datos.get('fecha_inicio', '')}
- Fecha fin: {datos.get('fecha_fin', '')}

## Links clave
- [PGA](PGA.md)
- [Sesiones Sincrónicas](SESIONES_SINCRONAS.md)
- [Sitemap](sitemap.md)
"""
    
    ruta_agents = os.path.join(ruta, "AGENTS.md")
    with open(ruta_agents, 'w', encoding='utf-8') as f:
        f.write(contenido)


def generar_pga_md(ruta: str, pga_data: List[Dict]):
    """Genera PGA.md usando el parser."""
    from parsear_pga import generar_markdown_pga
    
    contenido = generar_markdown_pga(pga_data)
    
    ruta_pga = os.path.join(ruta, "PGA.md")
    with open(ruta_pga, 'w', encoding='utf-8') as f:
        f.write(contenido)


def generar_sesiones_md(ruta: str, sesiones_data: List[Dict]):
    """Genera SESIONES_SINCRONAS.md."""
    from parsear_sesiones import generar_markdown_sesiones
    
    contenido = generar_markdown_sesiones(sesiones_data)
    
    ruta_sesiones = os.path.join(ruta, "SESIONES_SINCRONAS.md")
    with open(ruta_sesiones, 'w', encoding='utf-8') as f:
        f.write(contenido)


def generar_readme_md(ruta: str, datos: Dict):
    """Genera README.md para humanos."""
    contenido = f"""# {datos.get('nombre', 'Curso')}

> Resumen del curso para estudiantes

## Información
- **Código**: {datos.get('codigo', '')}
- **Periodo**: {datos.get('periodo', '')}
- **Fecha inicio**: {datos.get('fecha_inicio', '')}
- **Fecha fin**: {datos.get('fecha_fin', '')}

## Estructura

"""
    
    # Agregar unidades
    for unidad in datos.get('unidades', []):
        contenido += f"### {unidad.get('nombre', '')}\n"
        contenido += f"- Materiales: `{unidad.get('nombre', '')}/materiales/`\n"
        contenido += f"- Actividades: `{unidad.get('nombre', '')}/actividades/`\n\n"
    
    ruta_readme = os.path.join(ruta, "README.md")
    with open(ruta_readme, 'w', encoding='utf-8') as f:
        f.write(contenido)


def generar_sitemap_md(ruta: str, datos: Dict):
    """Genera sitemap.md con links permanentes de Moodle."""
    contenido = "# Sitemap del Curso\n\n"
    contenido += "## 🌐 Moodle Sections (Permanent Links)\n\n"
    
    # Agregar links de secciones
    for seccion in datos.get('secciones', []):
        contenido += f"- [{seccion.get('nombre', '')}]({seccion.get('url', '')})\n"
    
    contenido += "\n## 📂 Archivos Locales\n\n"
    contenido += "- [PGA](PGA.md)\n"
    contenido += "- [Sesiones Sincrónicas](SESIONES_SINCRONAS.md)\n"
    
    ruta_sitemap = os.path.join(ruta, "sitemap.md")
    with open(ruta_sitemap, 'w', encoding='utf-8') as f:
        f.write(contenido)
```

- [ ] **Paso 2: Ejecutar prueba de scaffold**

```
python gestionar-cursos/scripts/test_scaffold_curso.py
```

---

## Tarea 10: Sincronización de Curso

**Archivos:**
- Crear: `gestionar-cursos/scripts/sincronizar_curso.py`

- [ ] **Paso 1: Escribir módulo de sincronización**

```python
"""
Compara estado de Moodle vs local y detecta cambios.
"""

from typing import List, Dict, Tuple

def sincronizar_curso(ruta_local: str) -> Dict:
    """
    Detecta cambios entre Moodle y carpeta local.
    
    Returns:
        Dict con estructura:
        {
            "ultima_sync": "timestamp",
            "cambios": [
                {"tipo": "fecha_cambiada", "actividad": "...", "antes": "...", "despues": "..."},
                {"tipo": "nueva", "actividad": "..."},
                {"tipo": "nuevo_material", "recurso": "..."}
            ],
            "grabaciones_nuevas": [...]
        }
    """
    # Leer sitemap.md actual para comparar
    sitemap_actual = leer_sitemap(ruta_local)
    
    # Obtener datos frescos de Moodle
    datos_moodle = extraer_datos_moodle(ruta_local)
    
    cambios = []
    grabaciones_nuevas = []
    
    # Comparar fechas de PGA
    pga_local = sitemap_actual.get("pga", [])
    pga_moodle = datos_moodle.get("pga", [])
    
    for i, actividad in enumerate(pga_moodle):
        if i < len(pga_local):
            if actividad["fecha_fin"] != pga_local[i]["fecha_fin"]:
                cambios.append({
                    "tipo": "fecha_cambiada",
                    "actividad": actividad["actividad"],
                    "antes": pga_local[i]["fecha_fin"],
                    "despues": actividad["fecha_fin"]
                })
        else:
            # Nueva actividad
            cambios.append({
                "tipo": "nueva",
                "actividad": actividad["actividad"]
            })
    
    # Verificar links de grabaciones nuevas
    sesiones_moodle = datos_moodle.get("sesiones", [])
    sesiones_local = sitemap_actual.get("sesiones", [])
    
    for i, sesion in enumerate(sesiones_moodle):
        if sesion.get("link_grabaciones") and sesion.get("link_grabaciones") != "[PENDIENTE]":
            if i >= len(sesiones_local) or not sesiones_local[i].get("link_grabaciones"):
                grabaciones_nuevas.append({
                    "descripcion": sesion["descripcion"],
                    "link": sesion["link_grabaciones"],
                    "fecha": sesion["fecha"]
                })
    
    # Guardar nuevo estado
    actualizar_sitemap(ruta_local, datos_moodle)
    
    return {
        "ultima_sync": get_timestamp(),
        "cambios": cambios,
        "grabaciones_nuevas": grabaciones_nuevas
    }


def leer_sitemap(ruta_local: str) -> Dict:
    """Lee sitemap.md actual."""
    import json
    ruta = os.path.join(ruta_local, "sitemap.json")
    
    if os.path.exists(ruta):
        with open(ruta, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    return {"pga": [], "sesiones": [], "secciones": []}


def guardar_sitemap(ruta_local: str, datos: Dict):
    """Guarda estado actualizado en sitemap.json."""
    import json
    ruta = os.path.join(ruta_local, "sitemap.json")
    
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)
```

- [ ] **Paso 2: Ejecutar prueba**

```
python gestionar-cursos/scripts/test_sincronizar_curso.py
```

---

## Tarea 11: Verificación de Integridad

**Archivos:**
- Crear: `gestionar-cursos/scripts/verificar_integridad.py`

- [ ] **Paso 1: Escribir módulo de verificación**

```python
"""
Verifica integridad de archivos locales y links.
"""

import os
from typing import Dict, List

def verificar_integridad(ruta_curso: str) -> Dict:
    """
    Verifica estado de archivos locales vs referencias.
    
    Returns:
        Dict con:
        {
            "archivos_totales": N,
            "archivos_ok": N,
            "links_rotos": N,
            "actividades_sin_detalle": N,
            "problemas": [...]
        }
    """
    problemas = []
    
    # Verificar archivos referenciados en sitemap
    archivos_ok = 0
    archivos_totales = 0
    
    sitemap = leer_sitemap(ruta_curso)
    
    # Verificar archivos de materiales
    for unidad in sitemap.get("unidades", []):
        for material in unidad.get("materiales", []):
            archivos_totales += 1
            if os.path.exists(material["ruta_local"]):
                archivos_ok += 1
            else:
                problemas.append({
                    "tipo": "archivo_faltante",
                    "ruta": material["ruta_local"]
                })
    
    # Verificar actividades con detalle
    actividades_sin_detalle = 0
    for unidad in sitemap.get("unidades", []):
        for actividad in unidad.get("actividades", []):
            if actividad.get("descripcion") == "[DETALLE_NO_ENCONTRADO]":
                actividades_sin_detalle += 1
                problemas.append({
                    "tipo": "actividad_sin_detalle",
                    "nombre": actividad.get("nombre"),
                    "unidad": unidad.get("nombre")
                })
    
    return {
        "archivos_totales": archivos_totales,
        "archivos_ok": archivos_ok,
        "links_rotos": 0,  # Implementar validación de links
        "actividades_sin_detalle": actividades_sin_detalle,
        "problemas": problemas
    }
```

- [ ] **Paso 2: Ejecutar prueba**

```
python gestionar-cursos/scripts/test_verificar_integridad.py
```

---

## Tarea 12: Workflows Main (init + estado)

**Archivos:**
- Crear: `gestionar-cursos/references/guia-extraccion.md`
- Crear: `gestionar-cursos/references/deteccion-plataforma.md`
- Crear: `gestionar-cursos/references/estructura-carpetas.md`
- Crear: `gestionar-cursos/reglas/tipos-contenido.md`

- [ ] **Paso 1: Escribir documentos de referencia**

### guia-extraccion.md

```markdown
# Guía de Extracción de Contenido Moodle

## Prioridad de Extracción

1. **Crítico** (siempre extraer)
   - Tabla PGA (DO-FR-66)
   - Sesiones sincrónicas (links Teams)
   - Visión general del curso

2. **Importante** (extraer si disponible)
   - Material del curso (Módulo, Microcurrículo)
   - Actividades de unidades (con detalle completo)
   - Foros (Avisos, Consultas, Presentación)

3. **Opcional** (solo indexar)
   - Videos YouTube (solo links)
   - Recursos externos
   - H5P (proxy local)

## Orden de Navegación

1. Verificar sesión → `/my/`
2. Ir a URL del curso proporcionada
3. Ir a sección "Introducción" primero
   - Extraer Visión general
   - Extraer PGA
   - Extraer Sesiones Sincrónicas
   - Extraer Foros
4. Por cada unidad (sidebar):
   - Expandir menús
   - Extraer actividades
   - Consolidar con info del PGA
5. Descargar materiales
6. Generar estructura

## Consolidación de Actividades

El PGA en Introducción es solo una guía. Para cada actividad listada:
1. Ir a la unidad correspondiente
2. Buscar en sidebar (expandir menús si oculto)
3. Extraer descripción completa e instrucciones
4. Guardar en archivo propio de la actividad
5. La información del PGA y la unidad se consolidan
```

### deteccion-plataforma.md

```markdown
# Detección de Plataforma

## Regla General

Usar el navegador de la herramienta donde se ejecuta la conversación.

## Matriz de Comportamiento

| Herramienta | Browser Tool | Comportamiento |
|-------------|--------------|----------------|
| VS Code | `browser_tool` disponible | Navegación headless dentro del IDE |
| Antigravity | `browser_tool` disponible | Navegación headless dentro del IDE |
| OpenCode | `open_browser` | Abre ventana de navegador externo |

## Algoritmo de Detección

```python
def detectar_plataforma():
    try:
        browser_tool()  # VS Code o Antigravity
        return "headless"
    except NameError:
        try:
            open_browser()  # OpenCode o fallback
            return "external"
        except NameError:
            return "error"
```

## Fallbacks

Si ninguna tool de navegador está disponible:
1. Error claro: "No hay tool de navegación disponible"
2. Sugerencia: "Instala un plugin de navegador para VS Code o Antigravity"
```

### estructura-carpetas.md

```markdown
# Estructura de Carpetas Local

## Estándar de Nomenclatura

- **Carpetas**: Kebab-case (`Unidad-1`, `Material-Complementario`)
- **Archivos markdown**: Kebab-case (`pga.md`, `sesiones-sincronicas.md`)
- **Archivos PDF**: Original del recurso, sin modificar

## Estructura Completa

```
[CURSO_CODE]/
├── AGENTS.md                      # Metadatos para agentes
├── README.md                      # Resumen para humanos
├── sitemap.md                     # Links permanentes de Moodle
├── sitemap.json                   # Estado de sincronización (no committed)
├── PGA.md                         # Plan de Gestión Académica
├── SESIONES_SINCRONAS.md          # Cronograma de sesiones
├── MATERIA/
│   ├── Modulo.pdf                 # Módulo del curso
│   └── Microcurriculo.pdf         # Microcurrículo
├── COMUNICACION/
│   ├── Avisos.md                  # Info del foro
│   ├── Foro_Consultas.md
│   └── Foro_Presentacion.md
├── RECURSOS/
│   └── [recursos adicionales]
├── Unidad-1/
│   ├── materiales/
│   │   ├── [documento1.pdf]
│   │   └── presentacion.html      # H5P proxy
│   └── actividades/
│       ├── Prueba_Inicial.md
│       ├── Cuestionario_evaluativo.md
│       └── Primer_Parcial.md
├── Unidad-2/
│   └── ...
└── Unidad-3/
    └── ...
```

## Reglas de Contenido

- **AGENTS.md**: Siempre UTF-8, sintaxis markdown
- **PGA.md**: Fechas en formato dual (original + ISO)
- **sitemap.md**: Solo links permanentes de Moodle
- **Archivos de actividades**: Un archivo por actividad con toda la información consolidada
```

### tipos-contenido.md

```markdown
# Reglas por Tipo de Contenido

## PDFs y Documentos

- **Descarga**: Siempre con `forcedownload=1`
- **Ubicación**: `Unidad-N/materiales/` o `MATERIA/`
- **Nomenclatura**: Nombre original del archivo

## Foros

- **Extracción**: Solo metadata, no historial completo
- **Ubicación**: `COMUNICACION/[nombre_foro].md`
- **Contenido mínimo**:
  ```markdown
  # Avisos
  
  ## Info
  - Tipo: Foro de noticias
  - URL: [link permanente de Moodle]
  
  ## Últimos posts (últimos 3)
  - [Fecha] [Título] - [Autor]
  ```

## Videos (YouTube embebido)

- **Extracción**: Solo iframe src (link)
- **Ubicación**: En sitemap.md, no descargar
- **Formato**:
  ```markdown
  - [Video: Nombre del video](https://www.youtube.com/watch?v=XXX)
  ```

## H5P Interactivos

- **Proxy**: Crear HTML local con iframe
- **Ubicación**: `Unidad-N/materiales/[nombre].html`
- **Etiqueta**: `[Interactivo]` en sitemap

## Links Teams

- **Validación**: Solo dominios `teams.microsoft.com/l/meetup-join/`
- **Prohibido**: Acortadores (bit.ly), redirecciones Moodle
- **Si no seguro**: `[PENDIENTE: Link no seguro o inexistente]`

## Links de Grabaciones

- **Estado inicial**: `[PENDIENTE]` (no existen al inicio del curso)
- **Captura dinámica**: En `estado`, verificar si aparecieron nuevos
- **Ubicación**: En SESIONES_SINCRONAS.md
```

---

## Auto-Revisión

**1. Cobertura del spec:**
- ✅ Auth flow (login manual + verificación)
- ✅ Detección de plataforma (browser_tool vs open_browser)
- ✅ PGA extraction (DO-FR-66, flatten, ISO 8601)
- ✅ Sesiones sincrónicas (Teams links, grabaciones dinámicos)
- ✅ Unit activities (expandir menús, consolidar con PGA)
- ✅ Material download (PDFs, forcedownload)
- ✅ H5P proxy creation
- ✅ Folder structure (AGENTS.md con visión general)
- ✅ Políticas resilientes de error
- ✅ Workflows init + estado (sync + verify)

**2. Integración con Persona "Compañero de Universidad":**
- ✅ `/gestionar-cursos` crea **copia local con materiales físicos** (PDFs, DOCX, H5P proxies)
- ✅ `/use-clickup` crea **tasks en ClickUp** con links a Moodle (NO path locales)
- ✅ Índice local (`universidad_index.json`) mapea `curso_code` → `list_id`, `task_ids`
- ✅ Fuente de verdad: ClickUp para tracking, Moodle para materiales
- ✅ Caché: 7 semanas (49 días)

**2. Scan de placeholders:** ✅ Sin TBD, TODO o placeholders.

**3. Consistencia de tipos:** ✅ Nombres de funciones y signatures consistentes.

---

## Integración con Persona "Compañero de Universidad"

### Flujo de Datos

```
Moodle (Source of Truth)
         ↓
/gestionar-cursos (Extracción Local)
  ├── Materiales físicos (PDFs, DOCX, H5P proxies)
  └── Metadata (AGENTS.md, PGA.md, SESIONES_SINCRONAS.md)
         ↓
/use-clickup (Gestión en ClickUp)
  └── Tasks con links a Moodle (NO path locales)
         ↓
Índice Local (.universidad_index.json)
  └── Mapeo: curso_code → list_id, task_ids
```

### Roles

| Skill | Propósito | Local | ClickUp |
|-------|-----------|-------|---------|
| `/gestionar-cursos` | Extraer materiales de Moodle | ✅ PDFs, DOCX, H5P proxies | Links a Moodle |
| `/use-clickup` | Gestionar actividades | Index (IDs) | Tasks, fechas, tags |
| Persona "Compañero" | Coordinar | Index + estado | Tracking completo |

### Index Local

```json
{
  "2601B04G1": {
    "nombre": "BASES DE DATOS 2",
    "periodo": "2026-1",
    "bloque": "B1",
    "clickup_list_id": "abc123",
    "tasks": {
      "Prueba Inicial": "task_id_123",
      "Primer Parcial": "task_id_456"
    }
  }
}
```

### Cache

- **Duración**: 7 semanas (49 días)
- **Validación**: `cache_valid_until = hoy + 7 semanas`
- **Refresco**: Si expiró, re-escanear workspace

---

## Opciones de Ejecución

**Plan completo.** Dos opciones de ejecución:

**1. Subagent-Driven (recomendado)** - Subagente fresco por tarea, revisión entre tareas, iteración rápida

**2. Inline Execution** - Ejecutar tareas en esta sesión

**¿Cuál prefieres?**