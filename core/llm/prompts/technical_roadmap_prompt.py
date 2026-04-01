import json
from typing import List

from core.llm.output_schemas.technical_roadmap_outputs import (
    TechnicalRoadmapLLMOutput,
    TechnicalRoadmapFoundation,
    TechnicalRoadmapAnalysis,
    TechnicalPhasedRoadmapOutput,
)


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
    # Auto-generate JSON schema pattern
    schema_json = json.dumps(TechnicalRoadmapLLMOutput.model_json_schema(), indent=2)

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
                "Return the entire response strictly as a valid JSON object matching the schema below.\n"
                "No markdown, explanations, or comments outside the JSON.\n\n"
                "OUTPUT SCHEMA\n"
                f"```json\n{schema_json}\n```\n\n"
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
                "Return ONLY a valid JSON object with all top-level keys present (use [] or null where needed).\n"
                "CRITICAL JSON RULES:\n"
                "- Newlines inside string values MUST be written as \\n (escaped), NOT as actual line breaks.\n"
                '- Double quotes inside string values MUST be escaped as \\".\n'
                "- Backslashes inside string values MUST be escaped as \\\\.\n"
                "- Do NOT use trailing commas after the last item in arrays or objects."
            ),
        },
    ]

    return contents


def technical_roadmap_foundation_prompt(document: str | list[dict], n_years: int = 5):
    """
    Phase 1 prompt: generate title, vision, current state, and technology domains.
    Produces a TechnicalRoadmapFoundation.
    """
    horizon = max(int(n_years), 5)
    schema_json = json.dumps(TechnicalRoadmapFoundation.model_json_schema(), indent=2)

    contents = [
        {
            "role": "system",
            "parts": (
                "You are an expert technology strategist and systems architect.\n"
                "Analyze the provided document and synthesize the strategic foundation\n"
                "for a Technology Roadmap."
            ),
        },
        {
            "role": "system",
            "parts": (
                "OUTPUT REQUIREMENT\n"
                "Return the entire response strictly as a valid JSON object matching the schema below.\n"
                "No markdown, explanations, or comments outside the JSON.\n\n"
                "OUTPUT SCHEMA\n"
                f"```json\n{schema_json}\n```\n\n"
                "OUTPUT RULES\n"
                "- Output must be valid JSON (no markdown or trailing commas).\n"
                "- Include all top-level keys even if empty (use [] or null).\n"
                "- Keep concise, data-driven, and professional tone.\n"
                "- Avoid repeating text from the document verbatim; synthesize and enrich.\n"
            ),
        },
        {
            "role": "system",
            "parts": (
                "STRUCTURE AND CONTENT RULES:\n"
                f"- Roadmap horizon: next {horizon} years (minimum horizon is 5+ years).\n"
                "- roadmap_title: Concise, professional title summarizing the technology direction.\n"
                "- overall_vision: { goal (1-2 sentences), success_metrics[3-5 KPIs] }.\n"
                "- current_state_analysis: { summary (2-3 sentences), key_challenges[3-5], existing_capabilities[3-6] }.\n"
                "- technology_domains: 4-6 items; each { domain_name, description (1 sentence) }.\n\n"
                "IMPORTANT: Do NOT include enablers, risks, innovations, tabular_summary, or phased_roadmap.\n"
                "Those will be generated in subsequent phases.\n\n"
                "QUALITY BAR\n"
                "- Integrate document insights with broader domain trends.\n"
                "- Keep outcomes measurable and aligned to the horizon.\n"
                "- Use decisive, actionable language; avoid generic filler.\n"
            ),
        },
        {
            "role": "user",
            "parts": (
                "CONTEXT (Document content or extracted summary):\n\n"
                f"{document}\n\n"
                "TASK\n"
                f"Generate the foundation (title, vision, current state, domains) for a {horizon}-year Technology Roadmap.\n"
                "Return ONLY a valid JSON object.\n"
                "CRITICAL JSON RULES:\n"
                "- Newlines inside string values MUST be written as \\n (escaped), NOT as actual line breaks.\n"
                '- Double quotes inside string values MUST be escaped as \\".\n'
                "- Backslashes inside string values MUST be escaped as \\\\.\n"
                "- Do NOT use trailing commas after the last item in arrays or objects."
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
    schema_json = json.dumps(TechnicalRoadmapAnalysis.model_json_schema(), indent=2)

    contents = [
        {
            "role": "system",
            "parts": (
                "You are an expert technology strategist and systems architect.\n"
                "You have already produced the foundation for a Technology Roadmap (title, vision, current state, domains).\n"
                "Now generate the analysis layer: enablers, risks, innovations, and summary.\n"
            ),
        },
        {
            "role": "system",
            "parts": (
                "OUTPUT REQUIREMENT\n"
                "Return the entire response strictly as a valid JSON object matching the schema below.\n"
                "No markdown, explanations, or comments outside the JSON.\n\n"
                "OUTPUT SCHEMA\n"
                f"```json\n{schema_json}\n```\n\n"
                "STRUCTURE AND CONTENT RULES:\n"
                f"- Roadmap horizon: next {horizon} years.\n"
                "- key_technology_enablers: 4-6 items; each {{ enabler, impact (1 sentence) }}.\n"
                "- risks_and_mitigations: 4-6 items; each {{ risk, mitigation (1 sentence) }}.\n"
                "- innovation_opportunities: 3-5 items; each {{ idea, description (1 sentence), maturity_level in [experimental, prototype, scalable] }}.\n"
                "- tabular_summary: 3 rows (short/mid/long), each {{ time_frame, key_points[3-4] }}.\n"
                "- llm_inferred_additions: 0-2 concise value-add sections (or null).\n\n"
                "- Enablers and risks must align with the technology domains from the foundation.\n"
                "- Tabular summary should preview the phased roadmap direction.\n"
            ),
        },
        {
            "role": "user",
            "parts": (
                f"FOUNDATION (already generated):\n{foundation_json}\n\n"
                f"ORIGINAL DOCUMENT:\n{document}\n\n"
                "TASK\n"
                f"Generate the analysis layer (enablers, risks, innovations, summary) for the {horizon}-year roadmap.\n"
                "Ensure alignment with the foundation's vision and technology domains.\n"
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
    schema_json = json.dumps(TechnicalPhasedRoadmapOutput.model_json_schema(), indent=2)

    contents = [
        {
            "role": "system",
            "parts": (
                "You are an expert technology strategist and systems architect.\n"
                "You have already produced a technical roadmap foundation (vision, domains, enablers, risks, etc.).\n"
                "Now generate the detailed phased roadmap that aligns with that foundation.\n"
            ),
        },
        {
            "role": "system",
            "parts": (
                "OUTPUT REQUIREMENT\n"
                "Return the entire response strictly as a valid JSON object matching the schema below.\n"
                "No markdown, explanations, or comments outside the JSON.\n\n"
                "OUTPUT SCHEMA\n"
                f"```json\n{schema_json}\n```\n\n"
                "STRUCTURE AND CONTENT RULES:\n"
                f"- Roadmap horizon: next {horizon} years.\n"
                "- phased_roadmap: {{ short_term, mid_term, long_term }} where each phase contains:\n"
                "  • time_frame: e.g., '0-2 years' (short), '2-5 years' (mid), '5+ years' (long).\n"
                "  • focus_areas: 3-5 focus areas.\n"
                "  • key_initiatives: 3-5 items; each {{ initiative, objective (1 sentence), expected_outcome (1 sentence) }}.\n"
                "  • dependencies: 3-6 items (technologies, skills, integrations).\n"
                "  Phase intent: short_term = productionizing mature patterns; mid_term = scaling and adoption; long_term = R&D, next-gen, disruptive bets.\n"
                "- Initiatives must align with the technology domains and enablers from the foundation.\n"
                "- Outcomes must be measurable and align with the vision's success_metrics.\n"
            ),
        },
        {
            "role": "user",
            "parts": (
                f"FOUNDATION (already generated):\n{foundation_json}\n\n"
                f"ORIGINAL DOCUMENT:\n{document}\n\n"
                "TASK\n"
                f"Generate the detailed phased roadmap (short/mid/long term) for the {horizon}-year horizon.\n"
                "Ensure phases align with the technology domains, enablers, and vision from the foundation.\n"
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
