from pydantic import BaseModel, Field
from typing import List


class SummarizerLLMOutputSingle(BaseModel):
    summary: str = Field(description="The summary of the document.")


class SummarizerLLMOutputCombination(BaseModel):
    summary: str = Field(description="The summary of the document.")


class SummarizerLLMOutput(BaseModel):
    summaries: List[SummarizerLLMOutputSingle] = Field(
        description="List of summaries for each document."
    )


class GlobalSummarizerLLMOutput(BaseModel):
    title: str = Field(
        description="A concise and descriptive title for the collection of documents."
    )
    summary: str = Field(
        description="The global summary of all provided document summaries."
    )
