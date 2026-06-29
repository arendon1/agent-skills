"""
LLM API abstraction layer.

Expone funciones que los scripts del skill usan para LLM.
En entorno de agente (VS Code / OpenCode IDE) usa el LLM nativo del agente.
En terminal fallback a OpenRouter via openrouter_client.

Jerarquía:
  1. Agente nativo (builtins.llm_complete, sin costo extra)
  2. OpenRouter (openrouter_client, requiere OPENROUTER_API_KEY)
"""

import builtins


def _agent_has_llm() -> bool:
    """Verifica si el agente inyectó tool de LLM nativa."""
    return getattr(builtins, "llm_complete", None) is not None


def set_cache_dir(path: str):
    """Establece directorio de caché compartido."""
    from openrouter_client import set_cache_dir as _set
    _set(path)


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
    """Envía mensaje al LLM (agente nativo si disponible, sino OpenRouter).

    Misma firma que openrouter_client.completar() para drop-in replacement.
    """
    if _agent_has_llm():
        return _completar_agente(
            profile_name, user_message,
            instruccion=instruccion, modelo=modelo,
        )

    from openrouter_client import completar as _or_completar
    return _or_completar(
        profile_name, user_message,
        instruccion=instruccion, modelo=modelo,
        system_prompt=system_prompt,
        temperature=temperature if temperature is not None else None,
        max_tokens=max_tokens,
        timeout=timeout,
    )


def _completar_agente(
    profile_name: str,
    user_message: str,
    *,
    instruccion: str = "",
    modelo: str = "",
) -> str | None:
    """Usa la tool llm_complete inyectada por el agente."""
    from openrouter_client import get_profile
    profile = get_profile(profile_name)
    system = profile.get("system_prompt", "")

    user_msg = f"{instruccion}\n\n{user_message}" if instruccion else user_message

    try:
        fn = builtins.llm_complete
        return fn(system_prompt=system, user_message=user_msg)
    except Exception as e:
        print(f"[WARN] Agente LLM falló ({profile_name}): {e}")
        from openrouter_client import completar as _or_completar
        return _or_completar(profile_name, user_message, instruccion=instruccion)
