"""
Abstract base class for inference providers.

Each provider implements generate(), stream(), and reset_session()
with consistent logging of prompt/completion tokens, time-to-first-token,
and total generation time.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class GenerateResult:
    """Result from a non-streaming generation call."""

    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    time_to_first_token: float = 0.0
    total_duration: float = 0.0
    context: Optional[List[int]] = None  # Ollama KV cache context


@dataclass
class StreamMetrics:
    """Metrics collected during a streaming call."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    time_to_first_token: float = 0.0
    total_duration: float = 0.0


class InferenceProvider(ABC):
    """Abstract base class for all inference providers.

    Subclasses must implement:
        - generate(): full response in one call
        - stream(): async generator yielding tokens
        - reset_session(): clear per-session state
    """

    @abstractmethod
    async def generate(self, prompt: str, session_id: str) -> GenerateResult:
        """Generate a complete response for the given prompt."""
        ...

    @abstractmethod
    async def stream(self, prompt: str, session_id: str) -> AsyncGenerator[str, None]:
        """Stream response tokens for the given prompt.

        Yields individual tokens/chunks as they are generated.
        """
        ...

    @abstractmethod
    def reset_session(self, session_id: str) -> None:
        """Reset/clear any per-session state (KV cache, history, etc.)."""
        ...
