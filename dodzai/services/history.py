"""Persistent conversation history storage."""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from ..models import Conversation, Message
from ..utils.paths import app_history_path


class ConversationHistory:
    """Store conversations on disk as JSON."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else app_history_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conversations: Dict[str, Conversation] = {}
        self._load()

    # ------------------------------------------------------------------
    def _load(self) -> None:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                for payload in data.get("conversations", []):
                    convo = Conversation.from_dict(payload)
                    self._conversations[convo.identifier] = convo
            except Exception:
                self._conversations = {}

    def _flush(self) -> None:
        data = {"conversations": [c.to_dict() for c in self._conversations.values()]}
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    def list(self) -> List[Conversation]:
        return sorted(self._conversations.values(), key=lambda c: c.identifier)

    def get(self, identifier: str) -> Optional[Conversation]:
        return self._conversations.get(identifier)

    def create(self, provider: str, model: str, title: Optional[str] = None) -> Conversation:
        identifier = str(uuid.uuid4())
        conversation = Conversation(identifier=identifier, provider=provider, model=model, title=title or "New Chat")
        self._conversations[identifier] = conversation
        self._flush()
        return conversation

    def append(self, identifier: str, message: Message) -> None:
        conversation = self._conversations.setdefault(
            identifier, Conversation(identifier=identifier, provider="unknown", model="unknown", title="Chat")
        )
        conversation.append(message)
        self._flush()

    def save(self, conversation: Conversation) -> None:
        self._conversations[conversation.identifier] = conversation
        self._flush()

    def rename(self, identifier: str, title: str) -> None:
        if identifier in self._conversations:
            self._conversations[identifier].title = title
            self._flush()

    def delete(self, identifier: str) -> None:
        if identifier in self._conversations:
            del self._conversations[identifier]
            self._flush()

    def to_dict(self) -> Dict[str, List[Dict]]:
        return {"conversations": [conversation.to_dict() for conversation in self._conversations.values()]}
