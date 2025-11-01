from typing import List


def strategic_roadmap_prompt(document: str, n_years: int):
    """
    Build a chat prompt to generate a strategic roadmap from a source document
    with output structured to match StrategicRoadmapLLMOutput in core.llm.outputs.

    Args:
        document: The source context (raw text or extracted summary) to ground the roadmap.
        n_years: The number of years to plan ahead for the roadmap horizon.

    Returns:
        A list of chat messages (role/parts) ready for the LLM client.
    """
    contents = [
        {
            "role": "system",
            "parts": (
                "You are an expert strategy and planning assistant.\n"
                "Analyze the provided document and synthesize a forward-looking, data-driven roadmap.\n\n"
                "General Guidance:\n"
                "- Be comprehensive yet concise (target ~500-1000 words across textual fields).\n"
                "- Use decisive, actionable language; avoid generic filler.\n"
                "- Never copy the document verbatim—synthesize and enrich.\n"
                "- No self-references or reasoning steps outside the fields.\n"
            ),
        },
        {
            "role": "system",
            "parts": (
                "STRUCTURE AND CONTENT RULES (Map the following to the schema fields):\n"
                f"- Roadmap horizon: next {n_years} years.\n"
                "- roadmap_title: Auto-generate a concise, professional title summarizing the vision.\n"
                "- vision_and_end_goal.description: One paragraph describing the ultimate state (refer to 'Year <n>').\n"
            ),
        },
        {
            "role": "user",
            "parts": (
                f"CONTEXT (document excerpt or summary):\n\n{document}\n\n"
                f"TASK: Generate a {n_years}-year strategic roadmap following the rules above and return ONLY valid JSON."
            ),
        },
    ]

    return contents
