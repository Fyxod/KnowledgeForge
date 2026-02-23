import json
from core.llm.output_schemas.strategic_analysis_outputs import StrategicAnalysisLLMOutput


def strategic_analysis_prompt(document: str | list[dict]):
    """
    Build a chat prompt to extract strategic analysis from a source document,
    with output structured to match StrategicAnalysisLLMOutput.

    Unlike the strategic roadmap (which generates a forward-looking plan),
    this prompt focuses on extracting what IS in the document — the creator's
    strategic intent, positioning, themes, and aspirations — and then provides
    analytical commentary.

    Args:
        document: The source context (raw text or extracted summary) to analyze.

    Returns:
        A list of chat messages (role/parts) ready for the LLM client.
    """
    schema_json = json.dumps(
        StrategicAnalysisLLMOutput.model_json_schema(), indent=2
    )

    contents = [
        {
            "role": "system",
            "parts": (
                "You are an expert strategic analyst specializing in document analysis and strategic assessment.\n"
                "Your task has TWO distinct parts:\n"
                "  PART 1 — EXTRACTION: Carefully extract the strategic content that IS present in the document.\n"
                "  PART 2 — ASSESSMENT: Provide your own analytical commentary based on what you extracted.\n\n"
                "General Guidance:\n"
                "- For PART 1 fields, extract ONLY what is present or clearly implied in the document. Do NOT invent or fabricate strategies.\n"
                "- For PART 2 fields (strategic_gaps_and_observations, forward_looking_assessment), provide your expert analysis.\n"
                "- Be comprehensive yet concise (target ~500-1000 words across textual fields).\n"
                "- Use decisive, analytical language; avoid generic filler.\n"
                "- Never copy the document verbatim — synthesize and interpret.\n"
                "- No self-references or reasoning steps outside the fields.\n"
            ),
        },
        {
            "role": "system",
            "parts": (
                f"OUTPUT REQUIREMENT:\n"
                f"Return the response strictly as a valid JSON object matching this schema:\n"
                f"```json\n{schema_json}\n```\n\n"
                "STRUCTURE AND CONTENT RULES:\n"
                "- analysis_title: Auto-generate a concise, professional title summarizing the analysis.\n"
                "- executive_overview: One paragraph summarizing the document's strategic content and purpose.\n"
                "- strategic_intent:\n"
                "  • vision_statement: Extract the vision or aspiration described/implied in the document.\n"
                "  • stated_objectives: 3-6 explicit objectives mentioned in the document.\n"
                "  • implicit_aspirations: 2-4 aspirations implied but not explicitly stated.\n"
                "- strategic_positioning:\n"
                "  • current_position: Where the org/project currently stands based on the document.\n"
                "  • target_position: Where they aim to be.\n"
                "  • competitive_landscape: Any competitive context mentioned or implied.\n"
                "- key_strategic_themes: 3-6 themes, each with theme name, description, and evidence from the document.\n"
                "- stakeholder_insights: 3-6 stakeholders with role/interest and influence level (high/medium/low).\n"
                "- resources_and_capabilities: 3-6 resources/capabilities with current state and strategic relevance.\n"
                "- identified_risks: 3-5 risks from the document with severity (high/medium/low) and context.\n"
                "- strategic_gaps_and_observations: 3-6 gaps or observations YOU identify as an analyst.\n"
                "- forward_looking_assessment: YOUR analytical assessment with:\n"
                "  • opportunities: 3-5 opportunities you identify.\n"
                "  • recommended_next_steps: 3-5 concrete recommendations.\n"
                "  • potential_challenges: 3-5 challenges you foresee.\n"
                "  • overall_assessment: A comprehensive paragraph with your overall analytical view.\n"
                "- llm_inferred_additions: 0-2 optional sections with additional valuable insights.\n\n"
                "Formatting Note:\n"
                "- Deliver JSON fields only. Use concise strings and lists.\n"
                "- Embed brief markdown (e.g., bullets, emphasis) inside string values only if it improves clarity.\n"
            ),
        },
        {
            "role": "system",
            "parts": (
                "QUALITY BAR:\n"
                "- Ground all PART 1 content strictly in the document; do not fabricate.\n"
                "- For PART 2 (gaps, forward assessment), combine document insights with domain knowledge.\n"
                "- Clearly distinguish between what the document states vs. what you infer.\n"
                "- Keep observations actionable and specific, not vague.\n"
                "- Ensure internal consistency across all sections.\n"
            ),
        },
        {
            "role": "user",
            "parts": (
                f"CONTEXT (document excerpt or summary):\n\n{document}\n\n"
                "TASK: Analyze this document to extract the creator's strategic intent, positioning, themes, "
                "and aspirations. Then provide your analytical assessment including gaps, opportunities, and recommendations. "
                "Return ONLY valid JSON.\n"
                "CRITICAL JSON RULES:\n"
                "- Newlines inside string values MUST be written as \\n (escaped), NOT as actual line breaks.\n"
                "- Double quotes inside string values MUST be escaped as \\\".\n"
                "- Backslashes inside string values MUST be escaped as \\\\.\n"
                "- Do NOT use trailing commas after the last item in arrays or objects."
            ),
        },
    ]

    return contents
