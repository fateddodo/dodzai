"""Core data models used across the DodzAI application.

The project focuses on providing a high level, provider agnostic interface
for a large collection of language models.  The data classes defined in this
module are intentionally lightweight and serialisable so they can be safely
stored as JSON and exchanged between the user interface, persistence layer
and provider implementations.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class MessageRole(str, Enum):
    """Enumeration describing the role of a message in a conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """A single conversational message.

    Attributes
    ----------
    role:
        The :class:`MessageRole` associated with the message.
    content:
        The textual content of the message.  Multimodal providers may attach
        additional metadata to describe non-text input, such as references to
        uploaded images or audio.
    metadata:
        Free-form metadata that providers may use to store tool call
        arguments, partial streaming state and other contextual details.
    """

    role: MessageRole
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise the message into a JSON compatible dictionary."""

        payload = asdict(self)
        payload["role"] = self.role.value
        return payload

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Construct a :class:`Message` from a serialised payload."""

        role = MessageRole(data["role"])
        return cls(role=role, content=data["content"], metadata=data.get("metadata", {}))


@dataclass
class ModelInfo:
    """Description of an available model exposed by a provider."""

    name: str
    display_name: Optional[str] = None
    context_length: Optional[int] = None
    family: Optional[str] = None
    supports_images: bool = False
    supports_vision: bool = False
    supports_audio: bool = False

    def label(self) -> str:
        """Return a user friendly label for dropdown menus."""

        if self.display_name and self.display_name != self.name:
            return f"{self.display_name} ({self.name})"
        return self.name


@dataclass
class ProviderCapabilities:
    """Flags that describe which features a provider offers."""

    chat: bool = True
    images: bool = False
    vision: bool = False
    audio: bool = False
    tools: bool = False

    def supports(self, feature: str) -> bool:
        """Return whether a capability is enabled.

        Parameters
        ----------
        feature:
            Case insensitive name of the capability (``chat``, ``images``,
            ``vision``, ``audio`` or ``tools``).
        """

        feature = feature.lower()
        return getattr(self, feature, False)


@dataclass
class Conversation:
    """A persisted conversation consisting of a list of messages."""

    identifier: str
    provider: str
    model: str
    title: str
    messages: List[Message] = field(default_factory=list)

    def append(self, message: Message) -> None:
        self.messages.append(message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "identifier": self.identifier,
            "provider": self.provider,
            "model": self.model,
            "title": self.title,
            "messages": [m.to_dict() for m in self.messages],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Conversation":
        return cls(
            identifier=data["identifier"],
            provider=data["provider"],
            model=data["model"],
            title=data.get("title", data["identifier"]),
            messages=[Message.from_dict(item) for item in data.get("messages", [])],
        )


@dataclass
class WorkspaceSettings:
    """Persisted configuration associated with a user profile."""

    username: str
    mode: str = "online"
    provider_keys: Dict[str, str] = field(default_factory=dict)
    default_provider: Optional[str] = None
    default_model: Optional[str] = None

    def set_api_key(self, provider: str, value: str) -> None:
        self.provider_keys[provider] = value

    def get_api_key(self, provider: str) -> Optional[str]:
        return self.provider_keys.get(provider)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "username": self.username,
            "mode": self.mode,
            "provider_keys": dict(self.provider_keys),
            "default_provider": self.default_provider,
            "default_model": self.default_model,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkspaceSettings":
        return cls(
            username=data["username"],
            mode=data.get("mode", "online"),
            provider_keys=dict(data.get("provider_keys", {})),
            default_provider=data.get("default_provider"),
            default_model=data.get("default_model"),
        )


def ensure_workspace_dir(base: Optional[Path] = None) -> Path:
    """Return the workspace directory, creating it if necessary."""

    base = Path(base) if base else Path.home() / ".dodzai"
    base.mkdir(parents=True, exist_ok=True)
    return base
