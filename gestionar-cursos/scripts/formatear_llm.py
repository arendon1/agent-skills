"""
Formateo de texto crudo via LLM.

Usa llm_api (agente nativo → OpenRouter fallback).
El LLM devuelve JSON con clean_text + metadata estructurados.
Los metadatos se acumulan para que el caller los recupere.
"""

import json

from llm_api import completar

_metadatos: list[dict] = []


def formatear_texto_llm(
    texto_crudo: str,
    instruccion: str = "",
    modelo: str = "",
) -> str:
    """Envía texto crudo a OpenRouter para formateo + extracción de metadatos.

    Usa perfil 'document_formatter' de openrouter.json.
    Parsea la respuesta JSON del LLM, extrae clean_text y acumula metadata.

    Args:
        texto_crudo: Texto extraído de documento.
        instruccion: Instrucción adicional.
        modelo: Anula el modelo del perfil.

    Returns:
        Texto formateado (clean_text), o el original si falla.
    """
    result = completar(
        "document_formatter",
        texto_crudo,
        instruccion=instruccion,
        modelo=modelo,
    )
    if result is None:
        return texto_crudo

    parsed = _parse_json_response(result)
    if parsed:
        texto = parsed.get("clean_text", "")
        meta = parsed.get("metadata", {})
        if meta:
            _metadatos.append(meta)
        return texto if texto else texto_crudo

    return result  # fallback: devolver respuesta cruda si no es JSON


def obtener_metadatos() -> list[dict]:
    """Retorna y limpia los metadatos acumulados de documentos procesados."""
    global _metadatos
    datos = list(_metadatos)
    _metadatos = []
    return datos


def _parse_json_response(texto: str) -> dict | None:
    """Intenta parsear respuesta LLM como JSON. Soporta markdown code fences."""
    texto = texto.strip()
    if texto.startswith("```"):
        lines = texto.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        texto = "\n".join(lines).strip()
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        return None
