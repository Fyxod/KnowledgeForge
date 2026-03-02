"""Phase 2.3: HyDE — Hypothetical Document Embeddings output schema."""

from pydantic import Field

from core.llm.output_schemas.base import LLMOutputBase


class HyDELLMOutput(LLMOutputBase):
    hypothetical_document: str = Field(
        description=(
            "A hypothetical passage that would appear in a document that answers "
            "the user's query. Write it as if it is a real excerpt from a relevant "
            "document, using domain-specific terminology and factual-sounding language. "
            "Keep it between 50-150 words."
        )
    )
