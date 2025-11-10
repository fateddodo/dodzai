"""Utilities for managing provider instances."""
from __future__ import annotations

from typing import Dict, Iterable, Iterator, List, Optional

from ..models import WorkspaceSettings
from .base import LLMProvider, OfflineEchoProvider
from .google import GoogleProvider
from .huggingface import HuggingFaceProvider
from .ollama import OllamaProvider
from .openai import OpenAIProvider


class ProviderRegistry:
    """Simple registry that stores provider instances by name."""

    def __init__(self, providers: Optional[Iterable[LLMProvider]] = None) -> None:
        self._providers: Dict[str, LLMProvider] = {}
        if providers:
            for provider in providers:
                self.register(provider)

    def register(self, provider: LLMProvider) -> None:
        self._providers[provider.name] = provider

    def unregister(self, name: str) -> None:
        self._providers.pop(name, None)

    def get(self, name: str) -> Optional[LLMProvider]:
        return self._providers.get(name)

    def __contains__(self, name: str) -> bool:
        return name in self._providers

    def __iter__(self) -> Iterator[LLMProvider]:
        return iter(self._providers.values())

    # Convenience helpers -------------------------------------------------
    def names(self) -> List[str]:
        return sorted(self._providers.keys())

    def select_default(self, settings: Optional[WorkspaceSettings]) -> LLMProvider:
        if settings and settings.default_provider and settings.default_provider in self._providers:
            return self._providers[settings.default_provider]
        # fall back to first provider or offline echo
        return next(iter(self._providers.values()))


def build_default_registry(settings: Optional[WorkspaceSettings] = None) -> ProviderRegistry:
    """Construct a registry populated with all supported providers."""

    providers: List[LLMProvider] = []
    settings = settings or WorkspaceSettings(username="anonymous")

    providers.append(OpenAIProvider(api_key=settings.get_api_key("openai")))
    providers.append(GoogleProvider(api_key=settings.get_api_key("google")))
    providers.append(HuggingFaceProvider(api_token=settings.get_api_key("huggingface")))
    providers.append(OllamaProvider())

    # Always ensure there is an offline fallback
    providers.append(OfflineEchoProvider())

    # Deduplicate providers that may have same name due to missing credentials
    registry = ProviderRegistry()
    for provider in providers:
        if provider.name not in registry:
            registry.register(provider)
    return registry
