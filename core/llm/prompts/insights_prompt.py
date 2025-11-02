def insights_prompt(document: str | list[dict]):
    """
    Build a chat prompt to generate an Insights summary strictly as JSON,
    aligned with the schema defined by InsightsLLMOutput in core.llm.outputs.

    Args:
            document: The source context (raw text or extracted summary) to analyze.

    Returns:
            A list of chat messages (role/parts) ready for the LLM client.
    """

    contents = [
        {
            "role": "system",
            "parts": (
                "You are an expert analyst specializing in extracting insights, critiques, and innovation directions from technical and strategic documents.\n\n"
                "Your task is to analyze the provided document(s) and generate a JSON-structured summary of insights, covering discussion points, strengths, improvement areas, and innovation opportunities. You may also propose pseudocode or algorithmic outlines if applicable.\n\n"
                "OUTPUT REQUIREMENT:\n"
                "Return the entire response strictly as a valid JSON object.\n"
                "Do NOT include markdown, comments, or text outside the JSON object.\n\n"
                "OUTPUT RULES\n"
                "- Output must be valid JSON only, no markdown or trailing commas.\n"
                "- Include all top-level keys, even if some arrays are empty.\n"
                "- Synthesize from document content and enrich with relevant domain knowledge.\n"
                "- Be concise yet insightful; avoid generic summaries.\n"
                '- If pseudocode is possible (e.g., algorithm, workflow, or process), include it in the "pseudocode_or_technical_outline" array.\n'
                "- Keep tone analytical, factual, and professional.\n\n"
                "QUALITY BAR:\n"
                "- Ground insights in the provided content; augment with accurate domain knowledge where relevant.\n"
                "- Prefer specificity and actionable language; avoid vague claims.\n"
                "- Keep lists concise (3-6 items when applicable).\n"
                "- Maintain internal consistency across points and recommendations.\n"
            ),
        },
        {
            "role": "user",
            "parts": (
                "CONTEXT (Document content or extracted summary):\n\n"
                f"{document}\n\n"
                "TASK\n"
                "Generate a comprehensive insight summary using the above JSON structure.\n"
                "Remember: Return ONLY a valid JSON object with all top-level keys present (use empty arrays where needed)."
            ),
        },
    ]

    return contents
