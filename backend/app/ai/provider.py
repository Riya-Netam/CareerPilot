"""Provider-independent LLM interface. Ollama is the default local provider.

Business logic never calls Ollama directly; it asks get_provider(). To add another provider
later, implement LLMProvider and return it from get_provider().
"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod

import httpx

from app.core.config import get_settings


class AIUnavailable(Exception):
    """The model could not be reached, timed out, or returned unusable output."""


class LLMProvider(ABC):
    name: str
    model: str

    @abstractmethod
    def is_available(self) -> tuple[bool, str]:
        """Return (ok, human-readable detail)."""

    @abstractmethod
    def generate(self, system: str, prompt: str, *, json_mode: bool = False, max_tokens: int = 900) -> str: ...


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, base_url: str, model: str, timeout: int):
        self.base_url, self.model, self.timeout = base_url.rstrip("/"), model, timeout

    def is_available(self) -> tuple[bool, str]:
        try:
            r = httpx.get(f"{self.base_url}/api/tags", timeout=3)
            r.raise_for_status()
            names = [m.get("name", "") for m in r.json().get("models", [])]
        except Exception:
            return False, "Ollama is not reachable"
        if not any(n == self.model or n.split(":")[0] == self.model for n in names):
            return False, f"Model '{self.model}' is not downloaded (run: ollama pull {self.model})"
        return True, "ready"

    def generate(self, system: str, prompt: str, *, json_mode: bool = False, max_tokens: int = 900) -> str:
        body = {"model": self.model, "system": system, "prompt": prompt, "stream": False,
                "options": {"temperature": 0.3, "num_predict": max_tokens}}
        if json_mode:
            body["format"] = "json"
        try:
            r = httpx.post(f"{self.base_url}/api/generate", json=body, timeout=self.timeout)
            r.raise_for_status()
            text = (r.json().get("response") or "").strip()
        except httpx.TimeoutException as e:
            raise AIUnavailable("The model took too long to respond") from e
        except Exception as e:
            raise AIUnavailable("The model could not be reached") from e
        if not text:
            raise AIUnavailable("The model returned an empty response")
        return text


def get_provider() -> LLMProvider | None:
    s = get_settings()
    if not s.AI_ENABLED:
        return None
    return OllamaProvider(s.OLLAMA_BASE_URL, s.OLLAMA_MODEL, s.AI_TIMEOUT_SECONDS)


def parse_json_object(text: str) -> dict:
    """Parse model output as JSON, tolerating code fences. Raises AIUnavailable if malformed."""
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise AIUnavailable("The model returned malformed output") from e
    if not isinstance(data, dict):
        raise AIUnavailable("The model returned an unexpected format")
    return data
