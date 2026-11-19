"""Small provider-neutral text generation client using standard library HTTP."""
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import Any

from aero_ops.config.settings import Settings, get_settings


class LLMConfigurationError(RuntimeError):
    """The selected model provider lacks required configuration."""


class LLMRequestError(RuntimeError):
    """A model provider returned an unusable response."""


class LLMClient:
    """Model-neutral completion interface for OpenAI, Anthropic, and Gemini."""

    def __init__(self, settings: Settings | None = None, timeout_seconds: float = 45.0) -> None:
        self.settings = settings or get_settings()
        self.timeout_seconds = timeout_seconds

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        provider = self.settings.model_provider.lower()
        if provider == "mock":
            return "Local mock provider selected. Use verified tool observations to form the dispatch brief."
        if provider == "openai":
            key = self.settings.openai_api_key
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {key}"} if key else {}
            payload = {"model": self.settings.model_name, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]}
        elif provider == "anthropic":
            key = self.settings.anthropic_api_key
            url = "https://api.anthropic.com/v1/messages"
            headers = {"x-api-key": key, "anthropic-version": "2023-06-01"} if key else {}
            payload = {"model": self.settings.model_name, "max_tokens": 1200, "system": system_prompt, "messages": [{"role": "user", "content": user_prompt}]}
        elif provider in {"gemini", "google"}:
            key = self.settings.google_api_key
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.settings.model_name}:generateContent?key={key or ''}"
            headers = {}
            payload = {"systemInstruction": {"parts": [{"text": system_prompt}]}, "contents": [{"role": "user", "parts": [{"text": user_prompt}]}]}
        else:
            raise LLMConfigurationError(f"Unsupported model provider: {provider}")
        if not key:
            raise LLMConfigurationError(f"Set the API key for the selected provider '{provider}' in the environment")
        request = Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json", **headers}, method="POST")
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                data: dict[str, Any] = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
            raise LLMRequestError(f"{provider} request failed with HTTP {exc.code}: {detail}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise LLMRequestError(f"{provider} request failed: {exc}") from exc
        try:
            if provider == "openai":
                return str(data["choices"][0]["message"]["content"])
            if provider == "anthropic":
                return "".join(str(part.get("text", "")) for part in data["content"] if part.get("type") == "text")
            return "".join(str(part.get("text", "")) for part in data["candidates"][0]["content"]["parts"])
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMRequestError(f"{provider} response did not contain text content") from exc
