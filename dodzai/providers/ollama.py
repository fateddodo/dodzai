"""Local Ollama provider implementation."""
from __future__ import annotations

import json
import os
from typing import Sequence

from ..models import Message, MessageRole, ModelInfo, ProviderCapabilities
from .base import ChatResponse, LLMProvider

try:  # pragma: no cover - optional dependency
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore


class OllamaProvider(LLMProvider):
    """Interact with local Ollama models via the HTTP API."""

    def __init__(self, base_url: str | None = None) -> None:
        capabilities = ProviderCapabilities(chat=True, images=False, vision=False, audio=False, tools=False)
        super().__init__(name="Ollama", capabilities=capabilities, default_model="llama3.2")
        self.base_url = base_url or os.getenv("OLLAMA_HOST", "http://localhost:11434")

    # ------------------------------------------------------------------
    def list_models(self) -> Sequence[ModelInfo]:
        models: list[ModelInfo] = []
        if requests is None:
            return [ModelInfo(name=self.default_model, display_name="Ollama (offline)")]
        try:  # pragma: no cover - network interaction
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            response.raise_for_status()
            data = response.json()
            for item in data.get("models", []):
                models.append(ModelInfo(name=item.get("name", "unknown"), display_name=item.get("name")))
        except Exception:
            models.append(ModelInfo(name=self.default_model, display_name="Ollama (unavailable)"))
        return models

    # ------------------------------------------------------------------
    def complete(self, messages: Sequence[Message], *, model: str | None = None, **kwargs) -> ChatResponse:
        prompt = messages[-1].content if messages else ""
        chosen_model = model or self.default_model
        if requests is None:
            return self._fallback_completion(prompt)
        try:  # pragma: no cover - network interaction
            payload = {
                "model": chosen_model,
                "messages": [{"role": m.role.value, "content": m.content} for m in messages],
                "stream": False,
            }
            response = requests.post(f"{self.base_url}/api/chat", data=json.dumps(payload), timeout=30)
            response.raise_for_status()
            data = response.json()
            message = data.get("message", {})
            text = message.get("content", "")
            if not text:
                text = data.get("response", "")
            if not text:
                text = json.dumps(data)
            return ChatResponse(message=Message(role=MessageRole.ASSISTANT, content=text), raw=data)
        except Exception:
            return self._fallback_completion(prompt)
