from typing import List


def strategic_roadmap_prompt(document: str | list[dict], n_years: int):
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
                "- vision_and_end_goal.success_criteria: 3-5 measurable success criteria.\n"
                "- current_baseline.summary: Brief As-Is based on the document; include material context.\n"
                "- current_baseline.swot: 3-5 bullets per list (keep concise).\n"
                "- strategic_pillars: Identify 3-5 pillars (e.g., Technology Evolution, Capability Building, Market Expansion, AI Integration).\n"
                "- phased_roadmap: Provide at least 3 phases (e.g., Phase 1 Year 1; Phase 2 Years 2-3; Phase 3 Years 4-5).\n"
                "  • For each phase include: 3-5 key_objectives; 3-5 key_initiatives; and 3-5 expected_outcomes.\n"
                "  • Mention dependencies and risks implicitly via initiatives/outcomes wording; keep outcomes measurable (KPIs).\n"
                "- enablers_and_dependencies: List enabling technologies, skills/resources, and stakeholders/partners.\n"
                "- risks_and_mitigation: Top 3-5 risks with clear mitigation strategies.\n"
                "- key_metrics_and_milestones: Add measurable checkpoints per year or phase (3-6 total entries).\n"
                "- future_opportunities: Predict beyond-horizon shifts (3-6).\n"
                "- llm_inferred_additions: 0-2 optional sections with valuable insights.\n\n"
                "Formatting Note:\n"
                "- Although the roadmap narrative uses headings and tables conceptually, you MUST deliver JSON fields only.\n"
                "- Use concise strings and lists; embed brief markdown (e.g., bullets, emphasis) inside string values only if it improves clarity.\n"
            ),
        },
        {
            "role": "system",
            "parts": (
                "QUALITY BAR:\n"
                "- Integrate insights from the document with broader domain knowledge and trends.\n"
                "- Keep dependencies, risks, and KPIs realistic and aligned with the horizon.\n"
                "- Ensure internal consistency across goals, phases, initiatives, and metrics.\n"
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
