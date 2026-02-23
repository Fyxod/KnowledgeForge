import json
from core.llm.output_schemas.technical_analysis_outputs import TechnicalAnalysisLLMOutput


def technical_analysis_prompt(document: str | list[dict]):
    """
    Build a chat prompt to extract technical analysis from a source document,
    with output structured to match TechnicalAnalysisLLMOutput.

    Unlike the technical roadmap (which generates a forward-looking plan),
    this prompt focuses on extracting what IS in the document — technical
    decisions, architecture, stack, aspirations — and then provides
    analytical commentary.

    Args:
        document: The source context (raw text or extracted summary) to analyze.

    Returns:
        A list of chat messages (role/parts) ready for the LLM client.
    """
    schema_json = json.dumps(
        TechnicalAnalysisLLMOutput.model_json_schema(), indent=2
    )

    contents = [
        {
            "role": "system",
            "parts": (
                "You are an expert technology analyst specializing in technical document assessment "
                "and architecture evaluation.\n"
                "Your task has TWO distinct parts:\n"
                "  PART 1 — EXTRACTION: Carefully extract the technical content that IS present in the document.\n"
                "  PART 2 — ASSESSMENT: Provide your own analytical commentary based on what you extracted.\n\n"
                "General Guidance:\n"
                "- For PART 1 fields, extract ONLY what is present or clearly implied in the document. Do NOT invent technologies or decisions.\n"
                "- For PART 2 fields (forward_looking_assessment), provide your expert analysis.\n"
                "- Be comprehensive yet concise (target ~500-1000 words across textual fields).\n"
                "- Use precise technical language; avoid generic filler.\n"
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
                "- analysis_title: Auto-generate a concise, professional title summarizing the technical analysis.\n"
                "- executive_overview: One paragraph summarizing the document's technical content and purpose.\n"
                "- technical_scope:\n"
                "  • domains_covered: 3-8 technical domains addressed in the document.\n"
                "  • technology_stack: 3-10 technologies, frameworks, or tools mentioned.\n"
                "  • architecture_overview: Describe the architecture as presented or implied.\n"
                "- technical_decisions: 3-6 key technical decisions with rationale and implications.\n"
                "- technical_strengths: 3-6 strengths with evidence from the document.\n"
                "- technical_concerns: 3-6 concerns or limitations with impact and evidence.\n"
                "- innovation_elements: 2-5 innovations with maturity level (experimental/prototype/production).\n"
                "- technical_aspirations:\n"
                "  • stated_goals: 3-6 explicit technical goals.\n"
                "  • implied_direction: The implied technical direction.\n"
                "  • alignment_assessment: How well goals align with the current technical state.\n"
                "- implementation_readiness:\n"
                "  • ready_components: 3-6 components ready for implementation.\n"
                "  • gaps_to_address: 3-6 gaps needing attention.\n"
                "  • dependencies: 3-6 key dependencies.\n"
                "- forward_looking_assessment: YOUR analytical assessment with:\n"
                "  • scalability_outlook: Assessment of scalability.\n"
                "  • technology_evolution: How the tech approach might evolve.\n"
                "  • recommended_focus_areas: 3-6 areas to focus on.\n"
                "  • overall_assessment: Comprehensive paragraph with your analytical view.\n"
                "- llm_inferred_additions: 0-2 optional sections with additional insights.\n\n"
                "Formatting Note:\n"
                "- Deliver JSON fields only. Use concise strings and lists.\n"
                "- Embed brief markdown inside string values only if it improves clarity.\n"
            ),
        },
        {
            "role": "system",
            "parts": (
                "QUALITY BAR:\n"
                "- Ground all PART 1 content strictly in the document; do not fabricate.\n"
                "- For PART 2 (forward assessment), combine document insights with broader technology trends.\n"
                "- Clearly distinguish between what the document states vs. what you infer.\n"
                "- Evaluate technical choices objectively — note both strengths and risks.\n"
                "- Ensure internal consistency across decisions, aspirations, and readiness.\n"
            ),
        },
        {
            "role": "user",
            "parts": (
                f"CONTEXT (document excerpt or summary):\n\n{document}\n\n"
                "TASK: Analyze this document to extract technical decisions, architecture, technology stack, "
                "strengths, concerns, and aspirations. Then provide your analytical assessment including "
                "scalability outlook, evolution potential, and recommended focus areas. "
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
