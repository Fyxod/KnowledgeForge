"""
Technical roadmap prompt builders.

NOTE: Do NOT embed the JSON schema here — invoke_llm() already injects
the schema via PydanticOutputParser.get_format_instructions().  Embedding
it twice causes the LLM to echo the schema definition back instead of
producing actual roadmap data.
"""


def technical_roadmap_foundation_prompt(document: str | list[dict], n_years: int = 5):
    """
    Phase 1 prompt: generate title, vision, current state, and technology domains.
    Produces a TechnicalRoadmapFoundation.
    """
    horizon = max(int(n_years), 5)

    contents = [
        {
            "role": "system",
            "parts": (
                "You are an expert technology strategist and systems architect.\n"
                "Analyze the provided document and synthesize the strategic foundation\n"
                f"for a {horizon}-year Technology Roadmap.\n\n"
                "FIELD GUIDELINES:\n"
                "- roadmap_title: Concise, professional title summarizing the technology direction.\n"
                "- overall_vision.goal: 1-2 sentences on the long-term technology goal.\n"
                "- overall_vision.success_metrics: 3-5 measurable KPIs.\n"
                "- current_state_analysis.summary: 2-3 sentences on current maturity.\n"
                "- current_state_analysis.key_challenges: 3-5 major blockers.\n"
                "- current_state_analysis.existing_capabilities: 3-6 technologies or tools in use.\n"
                "- technology_domains: 4-6 items; each with domain_name and a 1-sentence description.\n\n"
                "QUALITY:\n"
                "- Synthesize document insights with broader domain trends.\n"
                "- Keep descriptions concise and data-driven.\n"
                "- Do not repeat the document verbatim.\n"
            ),
        },
        {
            "role": "user",
            "parts": (
                f"DOCUMENT:\n\n{document}\n\n"
                f"Generate the foundation (title, vision, current state, domains) for a {horizon}-year Technology Roadmap."
            ),
        },
    ]

    return contents


def technical_roadmap_analysis_prompt(
    document: str | list[dict],
    n_years: int,
    foundation_json: str,
):
    """
    Phase 2 prompt: generate enablers, risks, innovations, tabular summary,
    and inferred additions grounded by the foundation.
    Produces a TechnicalRoadmapAnalysis.
    """
    horizon = max(int(n_years), 5)

    contents = [
        {
            "role": "system",
            "parts": (
                "You are an expert technology strategist and systems architect.\n"
                "You have already produced the foundation for a Technology Roadmap.\n"
                "Now generate the analysis layer aligned with that foundation.\n\n"
                "FIELD GUIDELINES:\n"
                "- key_technology_enablers: 4-6 items; each with enabler name and 1-sentence impact.\n"
                "- risks_and_mitigations: 4-6 items; each with risk and 1-sentence mitigation.\n"
                "- innovation_opportunities: 3-5 items; each with idea, 1-sentence description, "
                "and maturity_level (experimental / prototype / scalable).\n"
                "- tabular_summary: 3 rows (short/mid/long term); each with time_frame and 3-4 key_points.\n"
                "- llm_inferred_additions: 0-2 optional value-add sections (or null).\n\n"
                "QUALITY:\n"
                "- Enablers and risks must align with the technology domains from the foundation.\n"
                "- Tabular summary should preview the phased roadmap direction.\n"
                "- Keep descriptions concise.\n"
            ),
        },
        {
            "role": "user",
            "parts": (
                f"FOUNDATION (already generated):\n{foundation_json}\n\n"
                f"DOCUMENT:\n{document}\n\n"
                f"Generate the analysis layer (enablers, risks, innovations, summary) for the {horizon}-year roadmap."
            ),
        },
    ]

    return contents


def technical_roadmap_phases_prompt(
    document: str | list[dict],
    n_years: int,
    foundation_json: str,
):
    """
    Phase 3 prompt: generate the phased_roadmap grounded by the foundation.
    Produces a TechnicalPhasedRoadmapOutput.
    """
    horizon = max(int(n_years), 5)

    contents = [
        {
            "role": "system",
            "parts": (
                "You are an expert technology strategist and systems architect.\n"
                "You have already produced a technical roadmap foundation.\n"
                "Now generate the detailed phased roadmap aligned with that foundation.\n\n"
                "FIELD GUIDELINES:\n"
                "- phased_roadmap has three phases: short_term, mid_term, long_term.\n"
                "- Each phase contains:\n"
                "  • time_frame: e.g., '0-2 years' (short), '2-5 years' (mid), '5+ years' (long).\n"
                "  • focus_areas: 3-5 focus areas.\n"
                "  • key_initiatives: 3-5 items; each with initiative, objective (1 sentence), expected_outcome (1 sentence).\n"
                "  • dependencies: 3-6 items (technologies, skills, integrations).\n"
                "- Phase intent: short_term = productionizing mature patterns; "
                "mid_term = scaling and adoption; long_term = R&D and disruptive bets.\n\n"
                "QUALITY:\n"
                "- Initiatives must align with the technology domains from the foundation.\n"
                "- Outcomes must be measurable and align with the vision's success_metrics.\n"
            ),
        },
        {
            "role": "user",
            "parts": (
                f"FOUNDATION (already generated):\n{foundation_json}\n\n"
                f"DOCUMENT:\n{document}\n\n"
                f"Generate the detailed phased roadmap (short/mid/long term) for the {horizon}-year horizon."
            ),
        },
    ]

    return contents
