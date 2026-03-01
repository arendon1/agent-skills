"""Abstraction layer for LLM providers used for skill improvement."""

import abc
import os
from typing import Optional, List, Dict, Any


class BaseLLMClient(abc.ABC):
    """Abstract base for LLM clients."""

    @abc.abstractmethod
    def create_message(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Create a completion and return the text content."""
        pass


class AnthropicClient(BaseLLMClient):
    """Claude/Anthropic client."""

    def __init__(self, api_key: Optional[str] = None):
        import anthropic

        self.client = anthropic.Anthropic(api_key=api_key)

    def create_message(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
        system_prompt: Optional[str] = None,
    ) -> str:
        # Anthropic uses system as a parameter, not as a message role
        resp = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=messages,
            system=system_prompt if system_prompt else "",
        )
        return resp.content[0].text


class GoogleGeminiClient(BaseLLMClient):
    """Gemini/Google client."""

    def __init__(self, api_key: Optional[str] = None):
        import google.generativeai as genai

        if api_key:
            genai.configure(api_key=api_key)
        self.genai = genai

    def create_message(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
        system_prompt: Optional[str] = None,
    ) -> str:
        m = self.genai.GenerativeModel(
            model_name=model, system_instruction=system_prompt
        )

        # Convert messages from Anthropic format to Gemini format
        history = []
        for msg in messages[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            history.append({"role": role, "parts": [msg["content"]]})

        chat = m.start_chat(history=history)
        resp = chat.send_message(messages[-1]["content"])
        return resp.text


def get_llm_client(provider: Optional[str] = None) -> BaseLLMClient:
    """Factory to get the correct LLM client based on ENV or provider name."""
    # Heuristic for determining provider
    prov = provider.lower() if provider else ""

    if prov == "anthropic" or "claude" in prov:
        return AnthropicClient()
    elif prov == "google" or prov == "gemini" or "gemini" in prov:
        return GoogleGeminiClient()

    # Auto-detect via environment keys
    if os.environ.get("GOOGLE_API_KEY"):
        return GoogleGeminiClient()
    if os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicClient()

    # Default to Anthropic for backward compatibility if possible
    try:
        return AnthropicClient()
    except:
        # Fallback to a stub or error
        raise ValueError(
            "Could not determine LLM provider. Set GOOGLE_API_KEY or ANTHROPIC_API_KEY."
        )
