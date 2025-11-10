"""Abstractions for LLM providers used by DodzAI."""
from __future__ import annotations

import abc
import random
import textwrap
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

from ..models import Message, MessageRole, ModelInfo, ProviderCapabilities


class ProviderError(RuntimeError):
    """Raised when a provider level error occurs."""


@dataclass
class ChatResponse:
    """Container returned by :meth:`LLMProvider.complete`."""

    message: Message
    raw: Optional[object] = None


class LLMProvider(abc.ABC):
    """Abstract base class that all provider implementations inherit from."""

    name: str
    capabilities: ProviderCapabilities
    default_model: Optional[str]

    def __init__(self, name: str, capabilities: ProviderCapabilities, default_model: Optional[str] = None) -> None:
        self.name = name
        self.capabilities = capabilities
        self.default_model = default_model

    # ------------------------------------------------------------------
    # Capabilities
    # ------------------------------------------------------------------
    def has_capability(self, feature: str) -> bool:
        return self.capabilities.supports(feature)

    # ------------------------------------------------------------------
    # Models
    # ------------------------------------------------------------------
    @abc.abstractmethod
    def list_models(self) -> Sequence[ModelInfo]:
        """Return the available models for the provider."""

    # ------------------------------------------------------------------
    # Chat completion
    # ------------------------------------------------------------------
    @abc.abstractmethod
    def complete(self, messages: Sequence[Message], *, model: Optional[str] = None, **kwargs) -> ChatResponse:
        """Generate a chat completion for ``messages``."""

    # ------------------------------------------------------------------
    # Multimodal functionality
    # ------------------------------------------------------------------
    def generate_image(self, prompt: str, *, model: Optional[str] = None, **kwargs) -> Optional[str]:
        raise ProviderError(f"{self.name} does not support image generation")

    def analyze_image(self, prompt: str, image_path: str, *, model: Optional[str] = None, **kwargs) -> ChatResponse:
        raise ProviderError(f"{self.name} does not support vision analysis")

    def transcribe_audio(self, audio_path: str, *, model: Optional[str] = None, **kwargs) -> str:
        raise ProviderError(f"{self.name} does not support speech-to-text")

    def text_to_speech(self, text: str, *, voice: Optional[str] = None, **kwargs) -> Optional[str]:
        raise ProviderError(f"{self.name} does not support text-to-speech")

    # ------------------------------------------------------------------
    # Tooling
    # ------------------------------------------------------------------
    def execute_tools(self, instructions: str, tools: Iterable["Tool"], *, model: Optional[str] = None, **kwargs) -> ChatResponse:
        raise ProviderError(f"{self.name} does not support tool execution")

    # ------------------------------------------------------------------
    # Helper utilities
    # ------------------------------------------------------------------
    def _fallback_completion(self, prompt: str) -> ChatResponse:
        """Return a deterministic but friendly response when offline."""

        templates = [
            "I am operating in offline mode so I cannot reach the {provider} API right now.\n"
            "Here is a quick summary of your prompt instead:\n\n"
            "{summary}",
            "Unable to contact {provider}.  Here's what I understood from your request:\n\n{summary}",
            "DodzAI is currently offline.  Based on your last message, this is the gist:\n\n{summary}",
        ]
        summary = textwrap.shorten(prompt.strip().replace("\n", " "), 240, placeholder="…") or "No prompt provided."
        content = random.choice(templates).format(provider=self.name, summary=summary)
        return ChatResponse(message=Message(role=MessageRole.ASSISTANT, content=content))


class OfflineEchoProvider(LLMProvider):
    """Tiny provider used when no remote models are configured."""

    def __init__(self) -> None:
        super().__init__(
            name="Offline Echo",
            capabilities=ProviderCapabilities(chat=True, images=True, vision=False, audio=False, tools=True),
            default_model="echo",
        )

    def list_models(self) -> Sequence[ModelInfo]:
        return [ModelInfo(name="echo", display_name="Echo (offline)")]

    def complete(self, messages: Sequence[Message], *, model: Optional[str] = None, **kwargs) -> ChatResponse:
        prompt = messages[-1].content if messages else ""
        response = f"[offline mode] You said: {prompt}"
        return ChatResponse(message=Message(role=MessageRole.ASSISTANT, content=response))

    def generate_image(self, prompt: str, *, model: Optional[str] = None, **kwargs) -> Optional[str]:
        from ..utils.images import create_placeholder_image

        return create_placeholder_image(prompt)

    def analyze_image(self, prompt: str, image_path: str, *, model: Optional[str] = None, **kwargs) -> ChatResponse:
        description = textwrap.dedent(
            f"""
            Offline analysis summary for {image_path}:
            - Prompt: {prompt or 'None provided'}
            - Result: Placeholder analysis generated locally.
            """
        ).strip()
        return ChatResponse(message=Message(role=MessageRole.ASSISTANT, content=description))

    def execute_tools(self, instructions: str, tools: Iterable["Tool"], *, model: Optional[str] = None, **kwargs) -> ChatResponse:
        from ..agents import AgentPlan, AgentRuntime

        runtime = AgentRuntime(tools=list(tools))
        plan = AgentPlan(steps=[instructions])
        result = runtime.execute(plan)
        return ChatResponse(message=Message(role=MessageRole.ASSISTANT, content=result.output))


# circular import safe imports
from ..agents import Tool  # noqa: E402  (import at end of file)
