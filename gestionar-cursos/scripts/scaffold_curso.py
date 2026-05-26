"""
Crea la estructura de carpetas completa para un curso.
Genera todos los archivos de metadatos.
"""

import os
import re


def _render_docs_introductorios(docs: list[dict]) -> str:
    """Renderiza la lista de documentos introductorios como markdown."""
    if not docs:
        return "_No se encontraron documentos introductorios._"

    bloques = []
    for doc in docs:
        nombre = doc.get("nombre", "Documento")
        texto = doc.get("texto", "")
        bloques.append(f"### {nombre}\n\n{texto}")
    return "\n\n".join(bloques)


def extraer_codigo_desde_url(url: str) -> str:
    """Extrae un identificador de curso desde la URL de Moodle."""
    m = re.search(r'[?&]id=(\d+)', url)
    if m:
        return f"CURSO_{m.group(1)}"
    parts = url.rstrip('/').split('/')
    if parts:
        last = parts[-1].replace('.php', '').replace('view', '')
        if last and last != 'course':
            return last.upper()
    return "CURSO"


def nombre_carpeta_curso(codigo: str, nombre: str) -> str:
    """Construye nombre de carpeta: '[CODIGO]-nombre-en-kebab-case'.

    Sanitiza caracteres inválidos para Windows.
    """
    nombre_kebab = _a_kebab_case(nombre)
    if not nombre_kebab or codigo.upper() in nombre_kebab.upper():
        return codigo
    return f"{codigo}-{nombre_kebab}"


def _a_kebab_case(texto: str) -> str:
    """Convierte texto a kebab-case: 'HUMANIDADES II (DISTANCIA Y VIRTUALIDAD)' -> 'humanidades-ii-distancia-y-virtualidad'."""
    texto = re.sub(r'[<>"/\\|?*]', '-', texto)
    texto = re.sub(r'[()\[\]{}]', ' ', texto)
    texto = re.sub(r'\s+', '-', texto.strip())
    texto = re.sub(r'-+', '-', texto)
    return texto.upper().strip('-')


def _sanitizar_nombre_carpeta(nombre: str) -> str:
    """Elimina caracteres inválidos para nombres de carpeta en Windows."""
    nombre = re.sub(r'[<>"/\\|?*]', '-', nombre)
    nombre = re.sub(r'\s+', ' ', nombre).strip()
    return nombre


def crear_estructura_curso(datos_curso: dict, ruta_base: str) -> bool:
    """Crea estructura de carpetas y archivos para un curso."""
    curso_code = datos_curso.get("codigo", "CURSO_DESCONOCIDO")
    curso_nombre = datos_curso.get("nombre", "")
    nombre_dir = nombre_carpeta_curso(curso_code, curso_nombre)
    ruta_curso = os.path.join(ruta_base, nombre_dir)

    os.makedirs(ruta_curso, exist_ok=True)

    crear_subdirectorios(ruta_curso, datos_curso.get("unidades", []))

    generar_agents_md(ruta_curso, datos_curso)
    generar_sitemap_md(ruta_curso, datos_curso)
    generar_pga_md(ruta_curso, datos_curso.get("pga", []))
    generar_context_md(ruta_curso, datos_curso)

    return True


def crear_subdirectorios(ruta_curso: str, unidades: list[dict]):
    """Crea todos los subdirectorios necesarios.

    Filtra secciones introductorias (Inicio, Introduccion) porque sus
    materiales van a MATERIA/ y su contenido a AGENTS.md/CONTEXT.md.
    """
    subdirs = ["COMUNICACION", "MATERIA"]
    intro_keywords = ("inicio", "introduccion", "introducción", "presentacion", "presentación")

    for unidad in unidades:
        nombre_raw = unidad.get("nombre", "")
        nombre_unidad = _sanitizar_nombre_carpeta(nombre_raw).replace(" ", "-")
        nombre_lower = nombre_unidad.lower()
        # No crear subdirectorios para secciones introductorias
        if any(kw in nombre_lower for kw in intro_keywords):
            continue
        subdirs.append(f"{nombre_unidad}/materiales")
        subdirs.append(f"{nombre_unidad}/actividades")
        subdirs.append(f"{nombre_unidad}/contenido")

    for subdir in subdirs:
        os.makedirs(os.path.join(ruta_curso, subdir), exist_ok=True)


def _render_metadatos(meta: dict) -> str:
    """Renderiza metadatos extraídos por LLM como markdown."""
    if not meta:
        return "_Metadatos no disponibles. Se poblarán tras procesar documentos introductorios._"

    bloques = []
    if meta.get("objetivos"):
        bloques.append("### Objetivos\n" + "\n".join(f"- {o}" for o in meta["objetivos"]))
    if meta.get("competencias"):
        bloques.append("### Competencias\n" + "\n".join(f"- {c}" for c in meta["competencias"]))
    if meta.get("metodologia"):
        bloques.append(f"### Metodología\n{meta['metodologia']}")
    if meta.get("criterios_evaluacion"):
        bloques.append("### Criterios de Evaluación\n" +
                       "\n".join(f"- {c}" for c in meta["criterios_evaluacion"]))
    if meta.get("unidades_tematicas"):
        bloques.append("### Unidades Temáticas\n" +
                       "\n".join(f"- {u}" for u in meta["unidades_tematicas"]))
    if meta.get("bibliografia"):
        bloques.append("### Bibliografía\n" +
                       "\n".join(f"- {b}" for b in meta["bibliografia"]))
    return "\n\n".join(bloques) if bloques else "_Sin metadatos extraídos._"


def generar_agents_md(ruta: str, datos: dict):
    """Genera AGENTS.md como índice simple de la estructura local."""
    nombre = datos.get("nombre", "Curso")
    codigo = datos.get("codigo", "")
    url = datos.get("url", "")
    periodo = datos.get("periodo", "")
    bloque = datos.get("bloque", "")
    semanas = datos.get("semanas", "")
    fecha_inicio = datos.get("fecha_inicio", "")
    fecha_fin = datos.get("fecha_fin", "")
    unidades = datos.get("unidades", [])
    sesiones = datos.get("sesiones", [])
    vision_general = datos.get("vision_general", "")
    metadatos = datos.get("metadatos_llm", {})

    # Limitar visión general a un párrafo breve
    vision_breve = vision_general.split("\n")[0] if vision_general else ""
    if len(vision_breve) > 300:
        vision_breve = vision_breve[:297] + "..."

    contenido = f"""# {nombre}

> Índice de curso para agentes. Ver detalles en CONTEXT.md.

## Identidad
- **CODIGO**: {codigo}
- **URL**: {url}
- **PERIODO**: {periodo or '[PENDIENTE]'}
- **BLOQUE**: {bloque or '[PENDIENTE]'}
- **SEMANAS**: {semanas or '[PENDIENTE]'}
- **INICIO**: {fecha_inicio or '[PENDIENTE]'}
- **FIN**: {fecha_fin or '[PENDIENTE]'}
- **CLICKUP_LIST_ID**: {datos.get('clickup_list_id') or '[PENDIENTE]'}
- **INICIALIZADO**: {datos.get('fecha_inicializacion', '')}

## Resumen
{vision_breve or '_Sin resumen disponible._'}

## Metadatos del Curso
{_render_metadatos(metadatos)}

## Sesiones Sincrónicas

| Descripción | Link Teams | Fecha | Hora | Grabaciones |
|-------------|------------|-------|------|-------------|
"""
    if sesiones:
        for s in sesiones:
            contenido += (
                f"| {s.get('descripcion', '')} | {s.get('link_teams', '')} | "
                f"{s.get('fecha', '')} | {s.get('hora', '')} | {s.get('link_grabaciones', '')} |\n"
            )
    else:
        contenido += "| _Sin sesiones_ | | | | |\n"

    contenido += """
## Índice Local
"""
    if unidades:
        for u in unidades:
            nombre_unidad = _sanitizar_nombre_carpeta(u.get("nombre", "")).replace(" ", "-")
            contenido += (
                f"- [{u.get('nombre', '')}]({nombre_unidad}/)\n"
                f"  - [Materiales]({nombre_unidad}/materiales/)\n"
                f"  - [Actividades]({nombre_unidad}/actividades/)\n"
            )

    contenido += """
## Archivos de Contexto
- [CONTEXT](CONTEXT.md)
- [PGA](PGA.md)
- [SITEMAP](SITEMAP.md)
- [COMUNICACION](COMUNICACION/)
"""

    ruta_agents = os.path.join(ruta, "AGENTS.md")
    with open(ruta_agents, "w", encoding="utf-8") as f:
        f.write(contenido)


def generar_sitemap_md(ruta: str, datos: dict):
    """Genera SITEMAP.md con links permanentes de Moodle y locales."""
    course_url = datos.get("url", "")
    secciones = datos.get("secciones", [])

    contenido = "# Sitemap del Curso\n\n"
    contenido += "## Secciones Moodle\n\n"

    for sec in secciones:
        nombre = sec.get("nombre", "")
        sec_url = sec.get("url", "")
        if sec_url:
            contenido += f"- [{nombre}]({sec_url})\n"
        elif course_url:
            # Fallback: link al curso sin section
            contenido += f"- [{nombre}]({course_url})\n"
        else:
            contenido += f"- {nombre}\n"

    contenido += "\n## Archivos Locales\n\n"
    contenido += "- [AGENTS](AGENTS.md)\n"
    contenido += "- [CONTEXT](CONTEXT.md)\n"
    contenido += "- [PGA](PGA.md)\n"

    ruta_sitemap = os.path.join(ruta, "SITEMAP.md")
    with open(ruta_sitemap, "w", encoding="utf-8") as f:
        f.write(contenido)


def generar_pga_md(ruta: str, pga_data: list[dict]):
    """Genera PGA.md usando el parser."""
    from parsear_pga import generar_markdown_pga

    contenido = generar_markdown_pga(pga_data)

    ruta_pga = os.path.join(ruta, "PGA.md")
    with open(ruta_pga, "w", encoding="utf-8") as f:
        f.write(contenido)


def generar_context_md(ruta: str, datos: dict):
    """Genera CONTEXT.md con todo el contenido extenso del curso."""
    nombre = datos.get("nombre", "Curso")
    vision = datos.get("vision_general", "")
    docs = datos.get("docs_introductorios", [])
    pga = datos.get("pga", [])
    sesiones = datos.get("sesiones", [])

    contenido = f"""# Contexto del Curso: {nombre}

## Vision General
{vision or '_No disponible._'}

## Documentos Introductorios
{_render_docs_introductorios(docs)}

## Plan de Gestion Academica (PGA)
"""
    if pga:
        from parsear_pga import generar_markdown_pga
        contenido += generar_markdown_pga(pga)
    else:
        contenido += "_PGA no disponible._\n"

    contenido += "\n## Sesiones Sincronicas\n\n"
    if sesiones:
        from parsear_sesiones import generar_markdown_sesiones
        contenido += generar_markdown_sesiones(sesiones)
    else:
        contenido += "_Sin sesiones sincronicas._\n"

    ruta_context = os.path.join(ruta, "CONTEXT.md")
    with open(ruta_context, "w", encoding="utf-8") as f:
        f.write(contenido)
