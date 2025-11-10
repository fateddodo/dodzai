"""OpenAI provider implementation."""
from __future__ import annotations

import os
from typing import Sequence

from ..models import Message, MessageRole, ModelInfo, ProviderCapabilities
from ..utils.images import create_placeholder_image
from .base import ChatResponse, LLMProvider


class OpenAIProvider(LLMProvider):
    """Provider wrapper around the official ``openai`` Python client."""

    _DEFAULT_MODELS = [
        ModelInfo(name="gpt-4o-mini", display_name="GPT-4o mini", supports_images=True, supports_vision=True),
        ModelInfo(name="gpt-4o", display_name="GPT-4o", supports_images=True, supports_vision=True),
        ModelInfo(name="gpt-3.5-turbo", display_name="GPT-3.5 Turbo"),
        ModelInfo(name="o4-mini", display_name="o4 mini", supports_images=True, supports_vision=True),
        ModelInfo(name="dall-e-3", display_name="DALL·E 3", supports_images=True),
    ]

    def __init__(self, api_key: str | None = None) -> None:
        capabilities = ProviderCapabilities(chat=True, images=True, vision=True, audio=True, tools=True)
        super().__init__(name="OpenAI", capabilities=capabilities, default_model="gpt-4o-mini")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._client = None
        self._load_client()

    # ------------------------------------------------------------------
    def _load_client(self) -> None:
        if not self.api_key:
            return
        # Prefer the new ``openai`` SDK shipped with ``OpenAI`` client.
        try:  # pragma: no cover - optional dependency
            from openai import OpenAI  # type: ignore

            self._client = OpenAI(api_key=self.api_key)
            return
        except Exception:
            pass
        # Fallback to legacy style ``openai`` module.
        try:  # pragma: no cover - optional dependency
            import openai  # type: ignore

            openai.api_key = self.api_key
            self._client = openai
        except Exception:
            self._client = None

    # ------------------------------------------------------------------
    def list_models(self) -> Sequence[ModelInfo]:
        return list(self._DEFAULT_MODELS)

    # ------------------------------------------------------------------
    def complete(self, messages: Sequence[Message], *, model: str | None = None, **kwargs) -> ChatResponse:
        prompt = messages[-1].content if messages else ""
        if not self._client:
            return self._fallback_completion(prompt)

        chosen_model = model or self.default_model or self._DEFAULT_MODELS[0].name
        payload = [{"role": message.role.value, "content": message.content} for message in messages]

        try:  # pragma: no cover - network interaction
            if hasattr(self._client, "responses"):
                response = self._client.responses.create(model=chosen_model, input=payload, **kwargs)
                text = ""
                for item in getattr(response, "output", []):
                    if getattr(item, "type", "") != "message":
                        continue
                    for segment in getattr(item, "content", []):
                        if getattr(segment, "type", "") == "output_text":
                            text += getattr(segment, "text", "")
                if not text:
                    text = getattr(response, "output_text", "")
            else:
                # Legacy client
                response = self._client.ChatCompletion.create(model=chosen_model, messages=payload, **kwargs)
                choice = response["choices"][0]
                message = choice.get("message") or {}
                text = message.get("content", "")
            if not text:
                text = "OpenAI returned an empty response."
            return ChatResponse(message=Message(role=MessageRole.ASSISTANT, content=text), raw=response)
        except Exception:  # pragma: no cover - offline fallback
            return self._fallback_completion(prompt)

    # ------------------------------------------------------------------
    def generate_image(self, prompt: str, *, model: str | None = None, **kwargs) -> str | None:
        if not self._client:
            return create_placeholder_image(prompt)

        chosen_model = model or "dall-e-3"
        try:  # pragma: no cover - network interaction
            if hasattr(self._client, "images"):
                response = self._client.images.generate(model=chosen_model, prompt=prompt, **kwargs)
                data = getattr(response, "data", [])
                if data:
                    # Save base64 string to disk if provided; fall back to placeholder
                    item = data[0]
                    if "b64_json" in item:
                        from ..utils.images import save_base64_image

                        return save_base64_image(item["b64_json"], suffix="-openai.png")
                    if "url" in item:
                        return item["url"]
        except Exception:
            pass
        return create_placeholder_image(prompt)

    # ------------------------------------------------------------------
    def analyze_image(self, prompt: str, image_path: str, *, model: str | None = None, **kwargs) -> ChatResponse:
        if not self._client:
            return self._fallback_completion(f"Vision request: {prompt} ({image_path})")
        chosen_model = model or self.default_model or "gpt-4o-mini"
        messages = [
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_path}},
            ]}
        ]
        try:  # pragma: no cover - network interaction
            if hasattr(self._client, "responses"):
                response = self._client.responses.create(model=chosen_model, input=messages, **kwargs)
                text = getattr(response, "output_text", "") or "OpenAI returned an empty response."
            else:
                response = self._client.ChatCompletion.create(model=chosen_model, messages=messages, **kwargs)
                text = response["choices"][0]["message"].get("content", "")
            return ChatResponse(message=Message(role=MessageRole.ASSISTANT, content=text), raw=response)
        except Exception:
            return self._fallback_completion(f"Vision request: {prompt} ({image_path})")

    # ------------------------------------------------------------------
    def transcribe_audio(self, audio_path: str, *, model: str | None = None, **kwargs) -> str:
        if not self._client:
            return f"[offline transcription placeholder] {os.path.basename(audio_path)}"
        chosen_model = model or "gpt-4o-mini-transcribe"
        try:  # pragma: no cover - network interaction
            if hasattr(self._client, "audio"):
                response = self._client.audio.transcriptions.create(model=chosen_model, file=open(audio_path, "rb"))
                return getattr(response, "text", "")
        except Exception:
            pass
        return f"[offline transcription placeholder] {os.path.basename(audio_path)}"

    # ------------------------------------------------------------------
    def text_to_speech(self, text: str, *, voice: str | None = None, **kwargs) -> str | None:
        if not self._client:
            return None
        chosen_voice = voice or "alloy"
        try:  # pragma: no cover - network interaction
            if hasattr(self._client, "audio"):
                response = self._client.audio.speech.create(
                    model="gpt-4o-mini-tts",
                    voice=chosen_voice,
                    input=text,
                    **kwargs,
                )
                # Some clients return binary data directly while others expose ``b64_json``
                if hasattr(response, "stream"):
                    return response.stream_to_file()
                data = getattr(response, "data", None)
                if data and "b64_json" in data[0]:
                    from ..utils.images import save_base64_audio

                    return save_base64_audio(data[0]["b64_json"], suffix="-openai.mp3")
        except Exception:
            pass
        return None
