"""
Conversation Memory Service
Stores recent chat history per phone number so the LLM has context
of the ongoing conversation. Uses an in-memory store with TTL expiry.
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# How many recent messages to keep per user
MAX_HISTORY_PER_USER = 10

# How long to keep history before expiring (4 hours)
HISTORY_TTL_SECONDS = 4 * 60 * 60


@dataclass
class ConversationEntry:
    """A single message in the conversation."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: float = field(default_factory=time.time)


class ConversationStore:
    """Thread-safe in-memory conversation history store."""

    def __init__(self):
        self._store: dict[str, list[ConversationEntry]] = defaultdict(list)
        self._last_access: dict[str, float] = {}

    def add_message(self, phone: str, role: str, content: str):
        """Add a message to the conversation history."""
        self._cleanup_expired()

        entry = ConversationEntry(role=role, content=content)
        self._store[phone].append(entry)
        self._last_access[phone] = time.time()

        # Trim to max history
        if len(self._store[phone]) > MAX_HISTORY_PER_USER:
            self._store[phone] = self._store[phone][-MAX_HISTORY_PER_USER:]

        logger.debug(
            f"Added {role} message for {phone} "
            f"(history length: {len(self._store[phone])})"
        )

    def get_history(self, phone: str) -> list[dict]:
        """
        Get conversation history for a phone number.
        
        Returns:
            List of dicts with 'role' and 'content' keys,
            formatted for LLM message arrays.
        """
        self._cleanup_expired()

        if phone not in self._store:
            return []

        self._last_access[phone] = time.time()

        return [
            {"role": entry.role, "content": entry.content}
            for entry in self._store[phone]
        ]

    def get_history_as_text(self, phone: str) -> str:
        """
        Get conversation history formatted as readable text
        for inclusion in the system prompt.
        """
        history = self.get_history(phone)
        if not history:
            return "No previous messages in this conversation."

        lines = ["CONVERSATION HISTORY (most recent messages):"]
        for msg in history:
            role_label = "Customer" if msg["role"] == "user" else "You (Bot)"
            lines.append(f"  {role_label}: {msg['content']}")

        return "\n".join(lines)

    def _cleanup_expired(self):
        """Remove conversations that have exceeded TTL."""
        now = time.time()
        expired = [
            phone for phone, last in self._last_access.items()
            if now - last > HISTORY_TTL_SECONDS
        ]
        for phone in expired:
            del self._store[phone]
            del self._last_access[phone]
            logger.debug(f"Expired conversation history for {phone}")


# Singleton instance
_conversation_store: Optional[ConversationStore] = None


def get_conversation_store() -> ConversationStore:
    """Get or create the singleton conversation store."""
    global _conversation_store
    if _conversation_store is None:
        _conversation_store = ConversationStore()
        logger.info("Conversation memory store initialized")
    return _conversation_store
