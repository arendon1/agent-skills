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