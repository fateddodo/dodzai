"""Conversation orchestration layer."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from ..models import Conversation, Message, MessageRole
from ..providers import ChatResponse, LLMProvider, ProviderRegistry
from .history import ConversationHistory


@dataclass
class ConversationResult:
    conversation: Conversation
    response: ChatResponse


class ConversationManager:
    """Coordinate interactions between the UI, providers and history store."""

    def __init__(self, registry: ProviderRegistry, history: ConversationHistory) -> None:
        self.registry = registry
        self.history = history
        self.active_id: Optional[str] = None

    # ------------------------------------------------------------------
    def start(self, provider_name: str, model: Optional[str] = None, *, title: Optional[str] = None) -> Conversation:
        provider = self._require_provider(provider_name)
        model = model or provider.default_model or provider.list_models()[0].name
        conversation = self.history.create(provider.name, model, title=title)
        self.active_id = conversation.identifier
        return conversation

    def load(self, identifier: str) -> Optional[Conversation]:
        conversation = self.history.get(identifier)
        if conversation:
            self.active_id = identifier
        return conversation

    def send_message(
        self,
        provider_name: str,
        content: str,
        *,
        model: Optional[str] = None,
        conversation_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> ConversationResult:
        provider = self._require_provider(provider_name)
        conversation = self._ensure_conversation(provider, model=model, conversation_id=conversation_id)

        user_message = Message(role=MessageRole.USER, content=content, metadata=metadata or {})
        conversation.append(user_message)
        self.history.append(conversation.identifier, user_message)

        response = provider.complete(conversation.messages, model=conversation.model)
        assistant_message = response.message
        conversation.append(assistant_message)
        self.history.append(conversation.identifier, assistant_message)
        return ConversationResult(conversation=conversation, response=response)

    def run_tools(
        self,
        provider_name: str,
        instructions: str,
        tools: Iterable["Tool"],
        *,
        model: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> ConversationResult:
        provider = self._require_provider(provider_name)
        conversation = self._ensure_conversation(provider, model=model, conversation_id=conversation_id)

        tool_message = Message(role=MessageRole.USER, content=instructions)
        conversation.append(tool_message)
        self.history.append(conversation.identifier, tool_message)

        response = provider.execute_tools(instructions, tools, model=conversation.model)
        assistant_message = response.message
        conversation.append(assistant_message)
        self.history.append(conversation.identifier, assistant_message)
        return ConversationResult(conversation=conversation, response=response)

    # ------------------------------------------------------------------
    def _ensure_conversation(
        self, provider: LLMProvider, *, model: Optional[str], conversation_id: Optional[str]
    ) -> Conversation:
        if conversation_id:
            loaded = self.history.get(conversation_id)
            if loaded:
                self.active_id = conversation_id
                if model and loaded.model != model:
                    loaded.model = model
                return loaded
        if self.active_id:
            loaded = self.history.get(self.active_id)
            if loaded and loaded.provider == provider.name:
                if model and loaded.model != model:
                    loaded.model = model
                return loaded
        return self.start(provider.name, model=model)

    def _require_provider(self, name: str) -> LLMProvider:
        provider = self.registry.get(name)
        if not provider:
            raise ValueError(f"Provider '{name}' is not registered")
        return provider


from ..agents import Tool  # noqa: E402  (import at end of file)
