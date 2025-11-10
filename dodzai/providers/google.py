"""Google Gemini provider implementation."""
from __future__ import annotations

import os
from typing import Sequence

from ..models import Message, MessageRole, ModelInfo, ProviderCapabilities
from ..utils.images import create_placeholder_image
from .base import ChatResponse, LLMProvider


class GoogleProvider(LLMProvider):
    """Wrapper around Google Vertex AI Gemini models.

    The implementation gracefully degrades to offline simulation when the
    required ``google-cloud-aiplatform`` dependency or authentication
    environment variables are not present.
    """

    _DEFAULT_MODELS = [
        ModelInfo(name="gemini-1.5-pro", display_name="Gemini 1.5 Pro", supports_images=True, supports_vision=True),
        ModelInfo(name="gemini-1.5-flash", display_name="Gemini 1.5 Flash", supports_images=True, supports_vision=True),
    ]

    def __init__(self, api_key: str | None = None, project: str | None = None, location: str | None = None) -> None:
        capabilities = ProviderCapabilities(chat=True, images=True, vision=True, audio=False, tools=True)
        super().__init__(name="Google Gemini", capabilities=capabilities, default_model="gemini-1.5-flash")
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.project = project or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location or os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        self._client = None
        self._load_client()

    # ------------------------------------------------------------------
    def _load_client(self) -> None:
        if not self.api_key and not (self.project and self.location):
            return
        try:  # pragma: no cover - optional dependency
            from google.cloud import aiplatform  # type: ignore

            aiplatform.init(project=self.project, location=self.location)
            self._client = aiplatform.gapic.PredictionServiceClient()
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

        # Vertex AI expects a simple text prompt for most basic use cases.
        text_prompt = "\n\n".join(message.content for message in messages if message.content)
        endpoint = model or self.default_model or self._DEFAULT_MODELS[0].name
        instance = {"prompt": text_prompt}
        try:  # pragma: no cover - network interaction
            prediction = self._client.predict(
                endpoint=f"projects/{self.project}/locations/{self.location}/publishers/google/models/{endpoint}",
                instances=[instance],
                parameters=kwargs.get("parameters", {}),
            )
            text = "".join(prediction.predictions[0].get("content", [])) if prediction.predictions else ""
            if not text:
                text = str(prediction)
            return ChatResponse(message=Message(role=MessageRole.ASSISTANT, content=text), raw=prediction)
        except Exception:
            return self._fallback_completion(prompt)

    # ------------------------------------------------------------------
    def generate_image(self, prompt: str, *, model: str | None = None, **kwargs) -> str | None:
        if not self._client:
            return create_placeholder_image(prompt)
        endpoint = model or "imagen-3.0-generate"
        instance = {"prompt": prompt}
        try:  # pragma: no cover - network interaction
            prediction = self._client.predict(
                endpoint=f"projects/{self.project}/locations/{self.location}/publishers/google/models/{endpoint}",
                instances=[instance],
            )
            if prediction.predictions:
                data = prediction.predictions[0]
                if isinstance(data, dict) and "bytesBase64Encoded" in data:
                    from ..utils.images import save_base64_image

                    return save_base64_image(data["bytesBase64Encoded"], suffix="-google.png")
        except Exception:
            pass
        return create_placeholder_image(prompt)

    # ------------------------------------------------------------------
    def analyze_image(self, prompt: str, image_path: str, *, model: str | None = None, **kwargs) -> ChatResponse:
        if not self._client:
            return self._fallback_completion(f"Vision request: {prompt} ({image_path})")

        endpoint = model or self.default_model or self._DEFAULT_MODELS[0].name
        instance = {
            "prompt": prompt,
            "image": {"bytesBase64Encoded": self._read_file(image_path)},
        }
        try:  # pragma: no cover - network interaction
            prediction = self._client.predict(
                endpoint=f"projects/{self.project}/locations/{self.location}/publishers/google/models/{endpoint}",
                instances=[instance],
            )
            text = "".join(prediction.predictions[0].get("content", [])) if prediction.predictions else ""
            if not text:
                text = str(prediction)
            return ChatResponse(message=Message(role=MessageRole.ASSISTANT, content=text), raw=prediction)
        except Exception:
            return self._fallback_completion(f"Vision request: {prompt} ({image_path})")

    # ------------------------------------------------------------------
    @staticmethod
    def _read_file(path: str) -> str:
        with open(path, "rb") as handle:
            import base64

            return base64.b64encode(handle.read()).decode("ascii")
