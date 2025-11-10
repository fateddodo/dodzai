"""Hugging Face text generation provider."""
from __future__ import annotations

import os
from typing import Sequence

from ..models import Message, MessageRole, ModelInfo, ProviderCapabilities
from ..utils.images import create_placeholder_image
from .base import ChatResponse, LLMProvider


class HuggingFaceProvider(LLMProvider):
    """Provider that interacts with the Hugging Face Inference API."""

    _DEFAULT_MODELS = [
        ModelInfo(name="mistralai/Mistral-7B-Instruct-v0.2", display_name="Mistral 7B Instruct"),
        ModelInfo(name="meta-llama/Llama-3.1-8B-Instruct", display_name="Llama 3.1 8B"),
    ]

    def __init__(self, api_token: str | None = None) -> None:
        capabilities = ProviderCapabilities(chat=True, images=True, vision=False, audio=False, tools=False)
        super().__init__(name="Hugging Face", capabilities=capabilities, default_model=self._DEFAULT_MODELS[0].name)
        self.api_token = api_token or os.getenv("HUGGINGFACE_API_TOKEN")
        self._client = None
        self._load_client()

    def _load_client(self) -> None:
        if not self.api_token:
            return
        try:  # pragma: no cover - optional dependency
            from huggingface_hub import InferenceClient  # type: ignore

            self._client = InferenceClient(token=self.api_token)
        except Exception:
            self._client = None

    def list_models(self) -> Sequence[ModelInfo]:
        return list(self._DEFAULT_MODELS)

    def complete(self, messages: Sequence[Message], *, model: str | None = None, **kwargs) -> ChatResponse:
        prompt = messages[-1].content if messages else ""
        if not self._client:
            return self._fallback_completion(prompt)

        text_prompt = "\n\n".join(
            f"{message.role.value.title()}: {message.content}" for message in messages if message.content
        )
        chosen_model = model or self.default_model or self._DEFAULT_MODELS[0].name
        try:  # pragma: no cover - network interaction
            response = self._client.text_generation(
                text_prompt,
                model=chosen_model,
                max_new_tokens=kwargs.get("max_new_tokens", 512),
                temperature=kwargs.get("temperature", 0.7),
            )
            text = getattr(response, "generated_text", None)
            if isinstance(response, str):
                text = response
            elif isinstance(response, dict):
                text = response.get("generated_text")
            if not text:
                text = str(response)
            return ChatResponse(message=Message(role=MessageRole.ASSISTANT, content=text), raw=response)
        except Exception:
            return self._fallback_completion(prompt)

    def generate_image(self, prompt: str, *, model: str | None = None, **kwargs) -> str | None:
        if not self._client:
            return create_placeholder_image(prompt)
        chosen_model = model or "stabilityai/stable-diffusion-xl-base-1.0"
        try:  # pragma: no cover - network interaction
            image = self._client.text_to_image(prompt=prompt, model=chosen_model, **kwargs)
            path = create_placeholder_image(prompt)  # fallback path for saving PIL image
            try:
                image.save(path)
                return path
            except Exception:
                return path
        except Exception:
            return create_placeholder_image(prompt)
