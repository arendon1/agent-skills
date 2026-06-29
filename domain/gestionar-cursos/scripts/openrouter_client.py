"""
Cliente unificado OpenRouter con configuración desde openrouter.json.

Jerarquía de configuración (menor a mayor prioridad):
  1. openrouter.json (valores base)
  2. Variables de entorno (OPENROUTER_MODEL, OPENROUTER_API_KEY)
  3. Argumentos directos en llamadas a completar()

Uso:
    from openrouter_client import completar

    result = completar("document_formatter", texto_crudo,
                       instruccion="Limpia este documento.")
    result = completar("youtube_summarizer", subtitulos)
"""

import hashlib
import json
import os
import random
import time
from pathlib import Path

import requests

_CONFIG: dict | None = None
_CONFIG_PATH: str | None = None
_CACHE_DIR: str = ""

API_URL = "https://openrouter.ai/api/v1/chat/completions"
AUTH_URL = "https://openrouter.ai/api/v1/auth/key"
RETRY_ATTEMPTS = 3
RETRY_BASE_DELAY = 1.0  # segundos: 1s, 2s, 4s
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
_CREDITOS_VERIFICADOS: dict[str, float] = {}


def _find_config() -> str:
    """Busca openrouter.json hacia arriba desde scripts/."""
    current = Path(__file__).resolve().parent.parent
    config_path = current / "openrouter.json"
    if config_path.is_file():
        return str(config_path)
    return ""


def _load_config() -> dict:
    """Carga y cachea la configuración de openrouter.json."""
    global _CONFIG, _CONFIG_PATH
    if _CONFIG is not None:
        return _CONFIG

    path = _find_config()
    _CONFIG_PATH = path
    if not path:
        _CONFIG = {}
        return _CONFIG

    with open(path, encoding="utf-8") as f:
        _CONFIG = json.load(f)
    return _CONFIG


def _resolve_model(profile: dict) -> str:
    """Resuelve modelo para un perfil: profile.model > env > default_model."""
    config = _load_config()
    modelo = (
        profile.get("model")
        or os.environ.get("OPENROUTER_MODEL")
        or config.get("default_model", "google/gemma-4-31b-it:free")
    )
    return modelo


def _resolve_fallback(profile: dict) -> str:
    """Resuelve fallback: profile.fallback > env fallback > config fallback."""
    config = _load_config()
    fallback = (
        profile.get("fallback")
        or config.get("fallback_model", "google/gemma-4-31b-it")
    )
    return fallback


def set_cache_dir(path: str):
    """Establece directorio para caché de respuestas LLM."""
    global _CACHE_DIR
    _CACHE_DIR = path
    os.makedirs(path, exist_ok=True)


def _cache_key(profile_name: str, system: str, user_msg: str) -> str:
    """Genera hash único para cache key."""
    raw = f"{profile_name}|{system}|{user_msg}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _cache_get(key: str) -> str | None:
    """Lee resultado cacheado si existe."""
    if not _CACHE_DIR:
        return None
    cache_path = os.path.join(_CACHE_DIR, f"{key}.json")
    if os.path.isfile(cache_path):
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f).get("result")
    return None


def _cache_put(key: str, result: str):
    """Guarda resultado en caché."""
    if not _CACHE_DIR:
        return
    cache_path = os.path.join(_CACHE_DIR, f"{key}.json")
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump({"result": result}, f, ensure_ascii=False)


def get_profile(profile_name: str) -> dict:
    """Obtiene configuración de un perfil por nombre."""
    config = _load_config()
    profiles = config.get("profiles", {})
    return profiles.get(profile_name, {})


def _verificar_creditos(api_key: str, threshold: float) -> bool:
    """Verifica créditos disponibles en OpenRouter.

    Cachea resultado por api_key para no repetir la llamada.
    """
    cache_key = api_key[-8:]
    if cache_key in _CREDITOS_VERIFICADOS:
        return _CREDITOS_VERIFICADOS[cache_key] >= threshold

    try:
        resp = requests.get(
            AUTH_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        credits = data.get("data", {}).get("credits_remaining", 0.0)
        _CREDITOS_VERIFICADOS[cache_key] = credits

        if credits < threshold:
            print(f"[WARN] OpenRouter créditos bajos: ${credits:.4f} "
                  f"(umbral: ${threshold:.2f}). Ejecución interrumpida.")
            return False
        print(f"[OK] OpenRouter créditos: ${credits:.4f}")
        return True
    except Exception as e:
        print(f"[WARN] No se pudo verificar créditos OpenRouter: {e}")
        return True  # Si no se puede verificar, permitir intentar


def completar(
    profile_name: str,
    user_message: str,
    *,
    instruccion: str = "",
    modelo: str = "",
    system_prompt: str = "",
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: int | None = None,
) -> str | None:
    """Envía mensaje a OpenRouter usando un perfil predefinido.

    Args:
        profile_name: Nombre del perfil en openrouter.json (ej: 'document_formatter').
        user_message: Texto del usuario (contenido a procesar).
        instruccion: Instrucción adicional prefijada al user_message.
        modelo: Anula el modelo del perfil.
        system_prompt: Anula el system_prompt del perfil.
        temperature: Anula temperatura.
        max_tokens: Anula max_tokens.
        timeout: Anula timeout.

    Returns:
        Respuesta del LLM o None si falla.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return None

    profile = get_profile(profile_name)
    if not profile:
        print(f"[WARN] Perfil '{profile_name}' no encontrado en openrouter.json")
        return None

    config = _load_config()
    api_cfg = config.get("api", {})

    # Verificar créditos si está habilitado
    if api_cfg.get("credit_check", True):
        threshold = float(api_cfg.get("credit_threshold", 0.01))
        if not _verificar_creditos(api_key, threshold):
            return None

    default_timeout = api_cfg.get("timeout", 60)

    model_primary = modelo or _resolve_model(profile)
    model_fallback = _resolve_fallback(profile)
    system = system_prompt or profile.get("system_prompt", "")
    temp = temperature if temperature is not None else profile.get("temperature", 0.3)
    tokens = max_tokens if max_tokens is not None else profile.get("max_tokens", 2000)
    t_out = timeout if timeout is not None else profile.get("timeout", default_timeout)

    user_msg = f"{instruccion}\n\n{user_message}" if instruccion else user_message

    # Caché: verificar antes de llamar al API
    cache_key = _cache_key(profile_name, system, user_msg)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    chunking = profile.get("chunking", {})
    if chunking.get("enabled") and len(user_msg) > chunking.get("max_chars", 8000):
        result = _completar_chunked(
            profile_name, user_msg, system, temp, tokens, t_out,
            model_primary, model_fallback, chunking,
        )
    else:
        result = _completar_single(
            user_msg, system, temp, tokens, t_out,
            model_primary, model_fallback, profile_name,
        )

    if result is not None:
        _cache_put(cache_key, result)
    return result


def _completar_single(
    user_msg: str,
    system: str,
    temp: float,
    tokens: int,
    t_out: int,
    model_primary: str,
    model_fallback: str,
    profile_name: str,
) -> str | None:
    """Envía un único mensaje con reintentos y fallback de modelo."""
    models_to_try = [model_primary]
    if model_fallback and model_fallback != model_primary:
        models_to_try.append(model_fallback)

    for m in models_to_try:
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                resp = requests.post(
                    API_URL,
                    headers={
                        "Authorization": f"Bearer {os.environ.get('OPENROUTER_API_KEY', '')}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": m,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user_msg},
                        ],
                        "temperature": temp,
                        "max_tokens": tokens,
                    },
                    timeout=t_out,
                )

                if resp.status_code in RETRYABLE_STATUSES and attempt < RETRY_ATTEMPTS:
                    delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    jitter = random.uniform(0, delay * 0.5)
                    print(f"[RETRY] {m} devolvió {resp.status_code}, "
                          f"reintento {attempt}/{RETRY_ATTEMPTS} en {delay + jitter:.1f}s")
                    time.sleep(delay + jitter)
                    continue

                resp.raise_for_status()
                data = resp.json()
                if "choices" in data and data["choices"]:
                    return data["choices"][0]["message"]["content"].strip()

                print(f"[WARN] OpenRouter respuesta sin choices ({profile_name}/{m})")
                break

            except requests.Timeout:
                if attempt < RETRY_ATTEMPTS:
                    delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    jitter = random.uniform(0, delay * 0.5)
                    print(f"[RETRY] {m} timeout, "
                          f"reintento {attempt}/{RETRY_ATTEMPTS} en {delay + jitter:.1f}s")
                    time.sleep(delay + jitter)
                else:
                    print(f"[WARN] {m} agotó reintentos por timeout")
                    break
            except requests.RequestException as e:
                if attempt < RETRY_ATTEMPTS:
                    delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    jitter = random.uniform(0, delay * 0.5)
                    print(f"[RETRY] {m} error de red ({e}), "
                          f"reintento {attempt}/{RETRY_ATTEMPTS} en {delay + jitter:.1f}s")
                    time.sleep(delay + jitter)
                else:
                    if m == models_to_try[-1]:
                        print(f"[WARN] OpenRouter falló ({profile_name}/{m}): {e}")
                    break

    return None


def _completar_chunked(
    profile_name: str,
    user_msg: str,
    system: str,
    temp: float,
    tokens: int,
    t_out: int,
    model_primary: str,
    model_fallback: str,
    chunking: dict,
) -> str | None:
    """Divide texto largo en chunks con overlap y procesa secuencialmente."""
    max_chars = chunking.get("max_chars", 8000)
    overlap = chunking.get("overlap", 500)

    chunks = _split_chunks(user_msg, max_chars, overlap)
    print(f"[CHUNK] {profile_name}: {len(user_msg)} chars → {len(chunks)} chunks "
          f"(~{max_chars}c c/u, overlap {overlap})")

    results = []
    for i, chunk in enumerate(chunks, 1):
        print(f"[CHUNK] Procesando chunk {i}/{len(chunks)} "
              f"({len(chunk)} chars)...")
        result = _completar_single(
            chunk, system, temp, tokens, t_out,
            model_primary, model_fallback, profile_name,
        )
        if result:
            results.append(result)
        else:
            results.append(f"[CHUNK {i} FALLIDO]")

    return "\n\n".join(results)


def _split_chunks(text: str, max_chars: int, overlap: int) -> list[str]:
    """Divide texto en chunks de max_chars con overlap entre ellos."""
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunks.append(text[start:end])
        start += max_chars - overlap
    return chunks


def reload_config():
    """Fuerza recarga de openrouter.json (útil tras edición en caliente)."""
    global _CONFIG
    _CONFIG = None
    return _load_config()
