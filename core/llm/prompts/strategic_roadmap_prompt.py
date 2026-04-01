import json
from typing import List

from core.llm.output_schemas.strategic_roadmap_outputs import (
    StrategicRoadmapLLMOutput,
    StrategicRoadmapFoundation,
    StrategicRoadmapAnalysis,
    StrategicPhasedRoadmapOutput,
)


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
    # Auto-generate JSON schema pattern
    schema_json = json.dumps(StrategicRoadmapLLMOutput.model_json_schema(), indent=2)

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
                f"OUTPUT REQUIREMENT:\n"
                f"Return the response strictly as a valid JSON object matching this schema:\n"
                f"```json\n{schema_json}\n```\n\n"
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
                f"TASK: Generate a {n_years}-year strategic roadmap following the rules above and return ONLY valid JSON.\n"
                "CRITICAL JSON RULES:\n"
                "- Newlines inside string values MUST be written as \\n (escaped), NOT as actual line breaks.\n"
                '- Double quotes inside string values MUST be escaped as \\".\n'
                "- Backslashes inside string values MUST be escaped as \\\\.\n"
                "- Do NOT use trailing commas after the last item in arrays or objects."
            ),
        },
    ]

    return contents


def strategic_roadmap_foundation_prompt(document: str | list[dict], n_years: int):
    """
    Phase 1 prompt: generate title, vision, baseline, and strategic pillars.
    Produces a StrategicRoadmapFoundation.
    """
    schema_json = json.dumps(StrategicRoadmapFoundation.model_json_schema(), indent=2)

    contents = [
        {
            "role": "system",
            "parts": (
                "You are an expert strategy and planning assistant.\n"
                "Analyze the provided document and synthesize the strategic foundation for a roadmap.\n\n"
                "General Guidance:\n"
                "- Be comprehensive yet concise.\n"
                "- Use decisive, actionable language; avoid generic filler.\n"
                "- Never copy the document verbatim—synthesize and enrich.\n"
            ),
        },
        {
            "role": "system",
            "parts": (
                f"OUTPUT REQUIREMENT:\n"
                f"Return the response strictly as a valid JSON object matching this schema:\n"
                f"```json\n{schema_json}\n```\n\n"
                "STRUCTURE AND CONTENT RULES:\n"
                f"- Roadmap horizon: next {n_years} years.\n"
                "- roadmap_title: Concise, professional title summarizing the vision.\n"
                "- vision_and_end_goal.description: One paragraph describing the ultimate state (refer to 'Year <n>').\n"
                "- vision_and_end_goal.success_criteria: 3-5 measurable success criteria.\n"
                "- current_baseline.summary: Brief As-Is (2-3 sentences).\n"
                "- current_baseline.swot: 3-4 bullets per list (keep concise).\n"
                "- strategic_pillars: 3-5 pillars; each { pillar_name, description (1 sentence) }.\n\n"
                "IMPORTANT: Do NOT include enablers, risks, metrics, opportunities, or phased_roadmap.\n"
                "Those will be generated in subsequent phases.\n"
            ),
        },
        {
            "role": "system",
            "parts": (
                "QUALITY BAR:\n"
                "- Integrate insights from the document with broader domain knowledge and trends.\n"
                "- Keep goals realistic and aligned with the horizon.\n"
                "- Ensure internal consistency across vision, baseline, and pillars.\n"
            ),
        },
        {
            "role": "user",
            "parts": (
                f"CONTEXT (document excerpt or summary):\n\n{document}\n\n"
                f"TASK: Generate the foundation (title, vision, baseline, pillars) for a {n_years}-year roadmap. Return ONLY valid JSON.\n"
                "CRITICAL JSON RULES:\n"
                "- Newlines inside string values MUST be written as \\n (escaped), NOT as actual line breaks.\n"
                '- Double quotes inside string values MUST be escaped as \\".\n'
                "- Backslashes inside string values MUST be escaped as \\\\.\n"
                "- Do NOT use trailing commas after the last item in arrays or objects."
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
    schema_json = json.dumps(StrategicRoadmapAnalysis.model_json_schema(), indent=2)

    contents = [
        {
            "role": "system",
            "parts": (
                "You are an expert strategy and planning assistant.\n"
                "You have already produced the foundation for a strategic roadmap (title, vision, baseline, pillars).\n"
                "Now generate the analysis layer: enablers, risks, metrics, opportunities, and additions.\n"
            ),
        },
        {
            "role": "system",
            "parts": (
                f"OUTPUT REQUIREMENT:\n"
                f"Return the response strictly as a valid JSON object matching this schema:\n"
                f"```json\n{schema_json}\n```\n\n"
                "STRUCTURE AND CONTENT RULES:\n"
                f"- Roadmap horizon: next {n_years} years.\n"
                "- enablers_and_dependencies: {{ technologies[3-5], skills_and_resources[3-5], stakeholders[3-5] }}.\n"
                "- risks_and_mitigation: 3-5 items; each {{ risk, mitigation_strategy (1 sentence) }}.\n"
                "- key_metrics_and_milestones: 3-5 items; each {{ year_or_phase, metrics[2-4] }}.\n"
                "- future_opportunities: 3-5 beyond-horizon predictions.\n"
                "- llm_inferred_additions: 0-2 concise value-add sections.\n\n"
                "- Enablers and risks must align with the strategic pillars from the foundation.\n"
                "- Metrics must align with the vision's success criteria.\n"
            ),
        },
        {
            "role": "user",
            "parts": (
                f"FOUNDATION (already generated):\n{foundation_json}\n\n"
                f"ORIGINAL DOCUMENT:\n{document}\n\n"
                f"TASK: Generate the analysis layer (enablers, risks, metrics, opportunities) for the {n_years}-year roadmap.\n"
                "Ensure alignment with the foundation's vision and pillars.\n"
                "Return ONLY valid JSON.\n"
                "CRITICAL JSON RULES:\n"
                "- Newlines inside string values MUST be written as \\n (escaped), NOT as actual line breaks.\n"
                '- Double quotes inside string values MUST be escaped as \\".\n'
                "- Backslashes inside string values MUST be escaped as \\\\.\n"
                "- Do NOT use trailing commas after the last item in arrays or objects."
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
    schema_json = json.dumps(StrategicPhasedRoadmapOutput.model_json_schema(), indent=2)

    contents = [
        {
            "role": "system",
            "parts": (
                "You are an expert strategy and planning assistant.\n"
                "You have already produced a strategic roadmap foundation (vision, pillars, risks, etc.).\n"
                "Now generate the detailed phased roadmap that aligns with that foundation.\n"
            ),
        },
        {
            "role": "system",
            "parts": (
                f"OUTPUT REQUIREMENT:\n"
                f"Return the response strictly as a valid JSON object matching this schema:\n"
                f"```json\n{schema_json}\n```\n\n"
                "STRUCTURE AND CONTENT RULES:\n"
                f"- Roadmap horizon: next {n_years} years.\n"
                "- phased_roadmap: At least 3 phases (e.g., Phase 1 Year 1; Phase 2 Years 2-3; Phase 3 Years 4-5).\n"
                "  • For each phase include: 3-5 key_objectives; 3-5 key_initiatives; and 3-5 expected_outcomes.\n"
                "  • Initiatives must align with the strategic pillars from the foundation.\n"
                "  • Outcomes must be measurable (KPIs) and align with the vision's success criteria.\n"
                "  • Mention dependencies and risks implicitly via initiatives/outcomes wording.\n"
            ),
        },
        {
            "role": "user",
            "parts": (
                f"FOUNDATION (already generated):\n{foundation_json}\n\n"
                f"ORIGINAL DOCUMENT:\n{document}\n\n"
                f"TASK: Generate the detailed phased roadmap (at least 3 phases) for the {n_years}-year horizon.\n"
                "Ensure phases align with the strategic pillars, vision, and metrics from the foundation.\n"
                "Return ONLY valid JSON.\n"
                "CRITICAL JSON RULES:\n"
                "- Newlines inside string values MUST be written as \\n (escaped), NOT as actual line breaks.\n"
                '- Double quotes inside string values MUST be escaped as \\".\n'
                "- Backslashes inside string values MUST be escaped as \\\\.\n"
                "- Do NOT use trailing commas after the last item in arrays or objects."
            ),
        },
    ]

    return contents
