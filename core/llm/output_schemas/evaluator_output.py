"""Phase 2.1: CRAG Corrective Retrieval — Evaluator LLM output schema."""

from typing import Literal, Optional

from pydantic import Field

from core.llm.output_schemas.base import LLMOutputBase


class EvaluatorLLMOutput(LLMOutputBase):
    verdict: Literal["sufficient", "ambiguous", "insufficient"] = Field(
        description=(
            "Assessment of whether the retrieved chunks are sufficient to answer the query. "
            "'sufficient' = chunks contain the needed information, proceed to answer. "
            "'ambiguous' = chunks are partially relevant, re-retrieve with the refined query. "
            "'insufficient' = chunks are not relevant at all, fall back to alternative retrieval."
        )
    )
    refined_query: Optional[str] = Field(
        default=None,
        description=(
            "A refined version of the original query that may retrieve better results. "
            "Required when verdict is 'ambiguous' or 'insufficient'. Use synonyms and "
            "alternative terminology (e.g., 'deliverables' instead of 'objectives')."
        ),
    )
    reasoning: str = Field(
        description="Brief explanation of why this verdict was chosen (1-2 sentences)."
    )
