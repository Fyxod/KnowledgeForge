"""
Provider registry – singleton factory for inference providers.

get_provider()        → primary provider (Ollama / Remote GPU depending on config)
get_gemini_provider() → Gemini fallback (or None if disabled)
reset_all_sessions()  → clears session state across every registered provider
"""

import logging
from typing import Optional

from core.config import settings
from core.constants import (
    FALLBACK_GEMINI_MODEL,
    MAIN_MODEL,
    PORT1,
    PORT2,
    SWITCHES,
)
from core.llm.providers.base import InferenceProvider
from core.llm.providers.gemini import GeminiProvider
from core.llm.providers.ollama import OllamaProvider
from core.llm.providers.remote_gpu import RemoteGPUProvider

logger = logging.getLogger(__name__)

# Singleton cache
_providers: dict[str, InferenceProvider] = {}

API_KEYS = [
    settings.API_KEY_1,
    settings.API_KEY_2,
    settings.API_KEY_3,
    settings.API_KEY_4,
    settings.API_KEY_5,
    settings.API_KEY_6,
]


def get_provider(port: int = PORT1) -> InferenceProvider:
    """Return (or create) the primary inference provider for *port*."""

    if SWITCHES["REMOTE_GPU"]:
        key = f"remote_gpu_{port}"
        if key not in _providers:
            _providers[key] = RemoteGPUProvider(
                query_url=settings.QUERY_URL,
                model=MAIN_MODEL,
                port=port,
            )
        return _providers[key]

    key = f"ollama_{port}"
    if key not in _providers:
        _providers[key] = OllamaProvider(
            base_url=settings.LOCAL_BASE_URL,
            model=MAIN_MODEL,
            port=port,
        )
    return _providers[key]


def get_gemini_provider() -> Optional[GeminiProvider]:
    """Return the Gemini provider if ``FALLBACK_TO_GEMINI`` is enabled."""

    if not SWITCHES["FALLBACK_TO_GEMINI"]:
        return None

    key = "gemini"
    if key not in _providers:
        valid = [k for k in API_KEYS if k and k.strip()]
        if not valid:
            logger.warning("No valid Gemini API keys configured")
            return None
        _providers[key] = GeminiProvider(  # type: ignore[assignment]
            api_keys=valid,
            model=FALLBACK_GEMINI_MODEL,
        )
    return _providers[key]  # type: ignore[return-value]


def reset_all_sessions(session_id: str) -> None:
    """Reset the given session across **all** registered providers."""
    for provider in _providers.values():
        provider.reset_session(session_id)
    logger.info(f"All provider sessions reset for {session_id}")
