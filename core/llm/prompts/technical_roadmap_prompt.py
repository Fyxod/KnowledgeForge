from typing import List


def technical_roadmap_prompt(document: str | list[dict], n_years: int = 5):
    """
    Build a chat prompt to generate a Technology Roadmap from a source document,
    with output structured to match TechnicalRoadmapLLMOutput in
    core.llm.output_schemas.technical_roadmap_outputs.

    Args:
            document: The source context (raw text or extracted summary) to ground the roadmap.
            n_years: The number of years to plan ahead for the roadmap horizon (minimum 5).

    Returns:
            A list of chat messages (role/parts) ready for the LLM client.
    """
    horizon = max(int(n_years), 5)

    contents = [
        {
            "role": "system",
            "parts": (
                "You are an expert technology strategist and systems architect.\n"
                "Analyze the provided document and synthesize a forward-looking,\n"
                "technically grounded, time-phased Technology Roadmap."
            ),
        },
        {
            "role": "system",
            "parts": (
                "OUTPUT REQUIREMENT\n"
                "Return the entire response strictly as a valid JSON object.\n"
                "No markdown, explanations, or comments outside the JSON.\n\n"
                "OUTPUT RULES\n"
                "- Output must be valid JSON (no markdown or trailing commas).\n"
                "- Include all top-level keys even if empty (use [] or null).\n"
                "- Keep concise, data-driven, and professional tone.\n"
                "- Ensure Short / Mid / Long Term phases clearly distinguish technical maturity, complexity, and innovation depth.\n"
                "- Include tabular_summary with key points for quick visualization.\n"
                "- Avoid repeating text from the document verbatim; synthesize and enrich.\n"
            ),
        },
        {
            "role": "system",
            "parts": (
                "STRUCTURE AND CONTENT RULES:\n"
                f"- Roadmap horizon: next {horizon} years (minimum horizon is 5+ years).\n"
                "- roadmap_title: Concise, professional title summarizing the technology direction.\n"
                "- overall_vision: { goal, success_metrics[3-6 KPIs] }.\n"
                "- current_state_analysis: { summary, key_challenges[3-6], existing_capabilities[3-10] }.\n"
                "- technology_domains: List of { domain_name, description } across major areas (e.g., AI infra, data platform, security).\n"
                "- phased_roadmap: { short_term, mid_term, long_term } where each phase contains:\n"
                "  • time_frame: e.g., '0-2 years' (short), '2-5 years' (mid), '5+ years' (long).\n"
                "  • focus_areas: 3-6 focus areas.\n"
                "  • key_initiatives: 3-6 items; each { initiative, objective, expected_outcome }.\n"
                "  • dependencies: 3-8 items (technologies, skills, integrations).\n"
                "  Phase intent: short_term = productionizing mature patterns; mid_term = scaling and adoption; long_term = R&D, next-gen, disruptive bets.\n"
                "- key_technology_enablers: 4-8 items; each { enabler, impact }.\n"
                "- risks_and_mitigations: 4-8 items; each { risk, mitigation }.\n"
                "- innovation_opportunities: 3-6 items; each { idea, description, maturity_level in [experimental, prototype, scalable] }.\n"
                "- tabular_summary: 3 rows (short/mid/long), each { time_frame, key_points[3-5] }.\n"
                "- llm_inferred_additions: Optional list; if none, include as [] with 0-2 concise value-add sections.\n\n"
                "QUALITY BAR\n"
                "- Integrate document insights with broader domain trends (architectural patterns, platform choices, ops, security, compliance).\n"
                "- Keep outcomes measurable and aligned to the horizon; ensure consistency across objectives, initiatives, and KPIs.\n"
                "- Use decisive, actionable language; avoid generic filler or self-reference.\n"
            ),
        },
        {
            "role": "user",
            "parts": (
                "CONTEXT (Document content or extracted summary):\n\n"
                f"{document}\n\n"
                "TASK\n"
                f"Generate a Technology Roadmap for the next {horizon} years following the above JSON schema.\n"
                "Return ONLY a valid JSON object with all top-level keys present (use [] or null where needed)."
            ),
        },
    ]

    return contents
