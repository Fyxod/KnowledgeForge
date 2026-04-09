def doc_batch_prompt(
    chunks: str,
    user_question: str,
    batch_number: int,
    total_batches: int,
    generative_mode: bool = False,
) -> str:
    """
    Lightweight prompt for processing one batch of document chunks.
    Used in MapReduce when the total retrieved context exceeds the model context window.

    When generative_mode is True, instructs the LLM to CREATE content (scripts,
    talking points) from the excerpts rather than extracting/describing them.
    """
    if generative_mode:
        instructions = (
            "**Instructions (Content Creation Mode):**\n"
            "1. Generate the requested content (script, talking points, narration) "
            "using ONLY the document excerpts shown above.\n"
            "2. For each slide/section in these excerpts, write the actual content "
            "the user asked for — do NOT describe what the slides contain.\n"
            "3. Maintain the document's slide/section ordering.\n"
            "4. If these excerpts don't contain slide/page content, respond with exactly: [NO RELEVANT INFO]\n"
            "5. Other batches cover other slides — results will be combined in order.\n"
        )
    else:
        instructions = (
            "**Instructions:**\n"
            "1. Answer the user's question using ONLY the document excerpts shown above.\n"
            "2. Be thorough — extract all relevant facts, figures, and insights from these excerpts.\n"
            "3. If the excerpts are not relevant to the question, respond with exactly: [NO RELEVANT INFO]\n"
            "4. Do NOT speculate about content in other batches.\n"
            "5. Attribute information to document titles when known.\n"
        )

    return (
        "You are analyzing a subset of document excerpts to answer a user's question.\n\n"
        f"This is batch {batch_number} of {total_batches}. You are seeing a subset of the full document set. "
        "Other batches are being processed in parallel and results will be combined.\n\n"
        f"**User Question:** {user_question}\n\n"
        f"**Document Excerpts (batch {batch_number}/{total_batches}):**\n{chunks}\n\n"
        f"{instructions}\n"
        "Return ONLY a valid JSON object:\n"
        '{"answer": "your answer based on this batch of document excerpts"}'
    )
