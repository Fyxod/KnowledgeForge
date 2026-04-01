"""
Strategic roadmap prompt builders.

NOTE: Do NOT embed the JSON schema here — invoke_llm() already injects
the schema via PydanticOutputParser.get_format_instructions().  Embedding
it twice causes the LLM to echo the schema definition back instead of
producing actual roadmap data.
"""


def strategic_roadmap_foundation_prompt(document: str | list[dict], n_years: int):
    """
    Phase 1 prompt: generate title, vision, baseline, and strategic pillars.
    Produces a StrategicRoadmapFoundation.
    """
    contents = [
        {
            "role": "system",
            "parts": (
                "You are an expert strategy and planning assistant.\n"
                f"Analyze the provided document and synthesize the strategic foundation for a {n_years}-year roadmap.\n\n"
                "FIELD GUIDELINES:\n"
                "- roadmap_title: Concise, professional title summarizing the vision.\n"
                "- vision_and_end_goal.description: One paragraph describing the ultimate state.\n"
                "- vision_and_end_goal.success_criteria: 3-5 measurable success criteria.\n"
                "- current_baseline.summary: Brief As-Is (2-3 sentences).\n"
                "- current_baseline.swot: 3-4 bullets per list (strengths, weaknesses, opportunities, threats).\n"
                "- strategic_pillars: 3-5 pillars; each with pillar_name and a 1-sentence description.\n\n"
                "QUALITY:\n"
                "- Synthesize document insights with broader domain knowledge and trends.\n"
                "- Keep goals realistic and aligned with the horizon.\n"
                "- Use decisive, actionable language; avoid generic filler.\n"
                "- Do not repeat the document verbatim.\n"
            ),
        },
        {
            "role": "user",
            "parts": (
                f"DOCUMENT:\n\n{document}\n\n"
                f"Generate the foundation (title, vision, baseline, pillars) for a {n_years}-year strategic roadmap."
            ),
        },
    ]

    return contents


def strategic_roadmap_analysis_prompt(
    document: str | list[dict],
    n_years: int,
    foundation_json: str,
):
    """
    Phase 2 prompt: generate enablers, risks, metrics, opportunities,
    and inferred additions grounded by the foundation.
    Produces a StrategicRoadmapAnalysis.
    """
    contents = [
        {
            "role": "system",
            "parts": (
                "You are an expert strategy and planning assistant.\n"
                "You have already produced the foundation for a strategic roadmap.\n"
                "Now generate the analysis layer aligned with that foundation.\n\n"
                "FIELD GUIDELINES:\n"
                "- enablers_and_dependencies: technologies (3-5), skills_and_resources (3-5), stakeholders (3-5).\n"
                "- risks_and_mitigation: 3-5 items; each with risk and 1-sentence mitigation_strategy.\n"
                "- key_metrics_and_milestones: 3-5 items; each with year_or_phase and 2-4 metrics.\n"
                "- future_opportunities: 3-5 beyond-horizon predictions (strings).\n"
                "- llm_inferred_additions: 0-2 optional value-add sections with section_title and content.\n\n"
                "QUALITY:\n"
                "- Enablers and risks must align with the strategic pillars from the foundation.\n"
                "- Metrics must align with the vision's success criteria.\n"
                "- Keep descriptions concise.\n"
            ),
        },
        {
            "role": "user",
            "parts": (
                f"FOUNDATION (already generated):\n{foundation_json}\n\n"
                f"DOCUMENT:\n{document}\n\n"
                f"Generate the analysis layer (enablers, risks, metrics, opportunities) for the {n_years}-year roadmap."
            ),
        },
    ]

    return contents


def strategic_roadmap_phases_prompt(
    document: str | list[dict],
    n_years: int,
    foundation_json: str,
):
    """
    Phase 3 prompt: generate the phased_roadmap grounded by the foundation.
    Produces a StrategicPhasedRoadmapOutput.
    """
    contents = [
        {
            "role": "system",
            "parts": (
                "You are an expert strategy and planning assistant.\n"
                "You have already produced a strategic roadmap foundation.\n"
                "Now generate the detailed phased roadmap aligned with that foundation.\n\n"
                "FIELD GUIDELINES:\n"
                "- phased_roadmap: At least 3 phases (e.g., Phase 1 Year 1; Phase 2 Years 2-3; Phase 3 Years 4-5).\n"
                "- Each phase contains:\n"
                "  • phase: Label like 'Phase 1'.\n"
                "  • time_frame: e.g., 'Year 1' or 'Years 2-3'.\n"
                "  • key_objectives: 3-5 objectives.\n"
                "  • key_initiatives: 3-5 major actions.\n"
                "  • expected_outcomes: 3-5 measurable results (KPIs).\n\n"
                "QUALITY:\n"
                "- Initiatives must align with the strategic pillars from the foundation.\n"
                "- Outcomes must be measurable and align with the vision's success criteria.\n"
            ),
        },
        {
            "role": "user",
            "parts": (
                f"FOUNDATION (already generated):\n{foundation_json}\n\n"
                f"DOCUMENT:\n{document}\n\n"
                f"Generate the detailed phased roadmap (at least 3 phases) for the {n_years}-year horizon."
            ),
        },
    ]

    return contents
