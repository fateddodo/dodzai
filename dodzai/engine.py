"""High level orchestration engine for DodzAI."""
from __future__ import annotations

from typing import Iterable, List, Optional

from .agents import AgentPlan, AgentRuntime, PythonTool, Tool, WebRequestTool
from .models import Conversation, WorkspaceSettings
from .providers import ChatResponse, LLMProvider, ProviderRegistry, build_default_registry
from .services import ConversationHistory, ConversationManager, LocalProfileStore, VoiceInterface


class DodzAIEngine:
    """Coordinate provider interactions, persistence and agent tooling."""

    def __init__(
        self,
        *,
        profile_store: Optional[LocalProfileStore] = None,
        history: Optional[ConversationHistory] = None,
        registry: Optional[ProviderRegistry] = None,
    ) -> None:
        self.profile_store = profile_store or LocalProfileStore()
        self.history = history or ConversationHistory()
        self.settings: Optional[WorkspaceSettings] = None
        self.registry = registry or build_default_registry()
        self.conversations = ConversationManager(self.registry, self.history)
        self.voice = VoiceInterface()
        self.agent_runtime = AgentRuntime([PythonTool(), WebRequestTool()])

    # ------------------------------------------------------------------
    # Authentication & settings
    # ------------------------------------------------------------------
    def login(self, username: str, password: str, *, create: bool = False) -> bool:
        if create:
            created = self.profile_store.create_user(username, password)
            if not created:
                return False
        if not self.profile_store.authenticate(username, password):
            return False
        self.settings = self.profile_store.get_settings(username)
        self.registry = build_default_registry(self.settings)
        self.conversations = ConversationManager(self.registry, self.history)
        return True

    def set_mode(self, mode: str) -> None:
        if not self.settings:
            raise RuntimeError("User not authenticated")
        self.settings.mode = mode
        self.profile_store.set_setting(self.settings.username, "mode", mode)

    def set_default_model(self, provider: str, model: str) -> None:
        if not self.settings:
            raise RuntimeError("User not authenticated")
        self.settings.default_provider = provider
        self.settings.default_model = model
        self.profile_store.set_setting(self.settings.username, "default_provider", provider)
        self.profile_store.set_setting(self.settings.username, "default_model", model)

    def store_api_key(self, provider: str, value: str) -> None:
        if not self.settings:
            raise RuntimeError("User not authenticated")
        self.profile_store.set_api_key(self.settings.username, provider, value)
        self.settings.provider_keys[provider] = value
        self.registry = build_default_registry(self.settings)
        self.conversations = ConversationManager(self.registry, self.history)

    # ------------------------------------------------------------------
    # Provider access helpers
    # ------------------------------------------------------------------
    def providers(self) -> List[str]:
        return self.registry.names()

    def provider(self, name: str) -> LLMProvider:
        provider = self.registry.get(name)
        if not provider:
            raise ValueError(f"Unknown provider: {name}")
        return provider

    def models(self, provider_name: str) -> List[str]:
        provider = self.provider(provider_name)
        return [model.label() for model in provider.list_models()]

    # ------------------------------------------------------------------
    # Conversation helpers
    # ------------------------------------------------------------------
    def start_conversation(self, provider_name: str, model: Optional[str] = None, *, title: Optional[str] = None) -> Conversation:
        return self.conversations.start(provider_name, model=model, title=title)

    def send_message(
        self,
        provider_name: str,
        content: str,
        *,
        model: Optional[str] = None,
        conversation_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> ChatResponse:
        result = self.conversations.send_message(
            provider_name,
            content,
            model=model,
            conversation_id=conversation_id,
            metadata=metadata,
        )
        return result.response

    def run_agent(
        self,
        provider_name: str,
        instructions: str,
        *,
        tools: Optional[Iterable[Tool]] = None,
        model: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> ChatResponse:
        runtime = self.agent_runtime
        if tools:
            runtime = AgentRuntime(list(tools))
        plan = AgentPlan(steps=[instructions])
        result = runtime.execute(plan)
        # Record the agent output inside the conversation history for traceability
        conversation_result = self.conversations.send_message(
            provider_name,
            instructions,
            model=model,
            conversation_id=conversation_id,
        )
        assistant_message = conversation_result.response.message
        assistant_message.content += "\n\n" + result.output
        self.history.save(conversation_result.conversation)
        return conversation_result.response

    # ------------------------------------------------------------------
    # Multimodal helpers
    # ------------------------------------------------------------------
    def generate_image(self, provider_name: str, prompt: str, *, model: Optional[str] = None) -> Optional[str]:
        provider = self.provider(provider_name)
        return provider.generate_image(prompt, model=model)

    def analyze_image(
        self,
        provider_name: str,
        prompt: str,
        image_path: str,
        *,
        model: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> ChatResponse:
        provider = self.provider(provider_name)
        result = provider.analyze_image(prompt, image_path, model=model)
        if conversation_id:
            self.history.append(conversation_id, result.message)
        return result

    def transcribe_audio(self, provider_name: str, audio_path: str, *, model: Optional[str] = None) -> str:
        provider = self.provider(provider_name)
        return provider.transcribe_audio(audio_path, model=model)

    def text_to_speech(self, text: str) -> Optional[str]:
        return self.voice.synthesize_to_file(text)

    # ------------------------------------------------------------------
    def conversation_list(self) -> List[Conversation]:
        return self.history.list()

    def conversation(self, identifier: str) -> Optional[Conversation]:
        return self.history.get(identifier)

    def register_tool(self, tool: Tool) -> None:
        self.agent_runtime.register(tool)
