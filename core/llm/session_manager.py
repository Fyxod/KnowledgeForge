"""
Session manager – lightweight bookkeeping for active inference sessions.

A session represents one user+thread combination.  The actual per-provider
state (KV cache, conversation history) lives inside each provider; this
module provides the canonical ``session_id`` and a central reset function.
"""

import logging
from typing import Dict, Optional

from core.llm.providers.registry import reset_all_sessions

logger = logging.getLogger(__name__)


class SessionManager:
    """Central registry of active inference sessions."""

    def __init__(self) -> None:
        self._sessions: Dict[str, dict] = {}

    @staticmethod
    def make_session_id(user_id: str, thread_id: str) -> str:
        """Canonical session key."""
        return f"{user_id}_{thread_id}"

    def register(self, session_id: str, metadata: Optional[dict] = None) -> None:
        self._sessions[session_id] = metadata or {}
        logger.info(f"Session registered: {session_id}")

    def get(self, session_id: str) -> Optional[dict]:
        return self._sessions.get(session_id)

    def remove(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        logger.info(f"Session removed: {session_id}")

    def reset(self, session_id: str) -> None:
        """Reset all provider state for this session and de-register it."""
        reset_all_sessions(session_id)
        self._sessions.pop(session_id, None)
        logger.info(f"Session fully reset: {session_id}")

    def list_sessions(self) -> list[str]:
        return list(self._sessions.keys())


# Global singleton
session_manager = SessionManager()
