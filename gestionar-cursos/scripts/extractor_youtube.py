"""
Extractor de subtítulos y resúmenes de videos YouTube via yt-dlp + LLM.

Requisitos:
    pip install yt-dlp
    Variable OPENROUTER_API_KEY en .env para resúmenes LLM.

Configuración LLM centralizada en openrouter.json (perfil 'youtube_summarizer').
"""

import json
import os
import re
import subprocess
import tempfile

YOUTUBE_URL_PATTERN = re.compile(
    r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]{11})'
)


def _check_ytdlp() -> bool:
    """Verifica que yt-dlp esté instalado."""
    try:
        subprocess.run(
            ["yt-dlp", "--version"], capture_output=True, timeout=5, check=True
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def _detectar_idioma_original(url: str) -> str:
    """Detecta idioma original del video via yt-dlp --dump-json.

    Returns:
        Código de idioma (ej: 'es', 'en') o 'en' como fallback.
    """
    try:
        result = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-playlist", url],
            capture_output=True, timeout=30, check=True,
        )
        info = json.loads(result.stdout)
        # YouTube expone el idioma en 'language' o 'original_language'
        lang = info.get("language") or info.get("original_language") or ""
        if lang and lang != "unknown":
            return lang
    except Exception:
        pass
    return "en"


def extraer_subtitulos(url: str, lang: str = "") -> str | None:
    """Extrae subtítulos de video YouTube como texto plano.

    Usa el idioma original del video (detectado automáticamente).

    Args:
        url: URL del video YouTube.
        lang: Código de idioma (si se omite, se detecta automáticamente).

    Returns:
        Texto de subtítulos o None si falla.
    """
    if not _check_ytdlp():
        return None

    video_id_match = YOUTUBE_URL_PATTERN.search(url)
    if not video_id_match:
        return None
    video_id = video_id_match.group(1)

    if not lang:
        lang = _detectar_idioma_original(url)

    output_template = os.path.join(
        tempfile.gettempdir(), f"yt_sub_{video_id}"
    )

    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--skip-download",
                "--write-auto-sub",
                "--sub-lang", lang,
                "--convert-subs", "srt",
                "--output", output_template,
                url,
            ],
            capture_output=True,
            timeout=60,
        )
        if result.returncode != 0:
            fallbacks = []
            if lang != "en":
                fallbacks.append("en")
            if "-" in lang:
                fallbacks.append(lang.split("-")[0])
            for fb in fallbacks:
                result2 = subprocess.run(
                    [
                        "yt-dlp",
                        "--skip-download",
                        "--write-auto-sub",
                        "--sub-lang", fb,
                        "--convert-subs", "srt",
                        "--output", output_template,
                        url,
                    ],
                    capture_output=True,
                    timeout=60,
                )
                if result2.returncode == 0:
                    lang = fb
                    break
            else:
                return None

        srt_path = f"{output_template}.{lang}.srt"
        if not os.path.isfile(srt_path):
            import glob as _glob
            candidates = _glob.glob(f"{output_template}*.srt")
            if candidates:
                srt_path = candidates[0]
            else:
                return None

        texto = _parsear_srt(srt_path)
        _limpiar_temp(output_template)
        return texto
    except Exception:
        _limpiar_temp(output_template)
        return None


def _parsear_srt(srt_path: str) -> str:
    """Convierte archivo SRT a texto plano, eliminando timestamps y números."""
    lineas = []
    with open(srt_path, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue
            if linea.isdigit():
                continue
            if "-->" in linea:
                continue
            lineas.append(linea)
    texto = " ".join(lineas)
    texto = re.sub(r'<[^>]+>', '', texto)
    texto = re.sub(r'♪.*?♪', '', texto)
    texto = re.sub(r'\[.*?\]', '', texto)
    return texto.strip()


def _limpiar_temp(base_path: str):
    """Elimina archivos temporales de subtítulos."""
    import glob as _glob
    for f in _glob.glob(f"{base_path}*"):
        with __import__('contextlib').suppress(OSError):
            os.remove(f)


def resumir_subtitulos(texto: str, modelo: str = "") -> str | None:
    """Envía subtítulos a LLM para resumir.

    Usa perfil 'youtube_summarizer' de openrouter.json.

    Args:
        texto: Texto de subtítulos.
        modelo: Anula el modelo del perfil.

    Returns:
        Resumen en markdown o None si falla.
    """
    from llm_api import completar

    texto_truncado = texto[:12000]
    return completar(
        "youtube_summarizer",
        texto_truncado,
        modelo=modelo,
    )


def detectar_youtube_en_texto(texto: str) -> list[str]:
    """Extrae todas las URLs de YouTube encontradas en un texto."""
    return [m.group(0) for m in YOUTUBE_URL_PATTERN.finditer(texto)]


def procesar_video_youtube(
    url: str,
    ruta_salida: str,
    nombre_actividad: str,
) -> str | None:
    """Pipeline completo: extrae subtítulos, resume con LLM, guarda .md.

    Args:
        url: URL del video YouTube.
        ruta_salida: Directorio donde guardar el resumen.
        nombre_actividad: Nombre de la actividad asociada.

    Returns:
        Ruta del archivo .md generado o None.
    """
    subtitulos = extraer_subtitulos(url)
    if not subtitulos:
        print(f"    [yellow]No se pudieron extraer subtítulos de:[/yellow] {url}")
        return None

    resumen = resumir_subtitulos(subtitulos)
    if not resumen:
        resumen = subtitulos[:4000]

    safe_name = re.sub(r'[<>"/\\|?*:]', '-', nombre_actividad).strip()
    safe_name = safe_name.replace(" ", "_")[:80]
    ruta_md = os.path.join(ruta_salida, f"{safe_name}_YouTube.md")

    os.makedirs(ruta_salida, exist_ok=True)
    with open(ruta_md, "w", encoding="utf-8") as f:
        f.write(f"# Resumen: {nombre_actividad}\n\n")
        f.write(f"**Video:** {url}\n\n")
        f.write("## Resumen (LLM)\n\n")
        f.write(resumen)
        f.write("\n\n---\n\n")
        f.write("## Subtítulos completos\n\n")
        f.write(subtitulos[:10000])

    print(f"  [green]Resumen YouTube guardado:[/green] {ruta_md}")
    return ruta_md
