import json
from typing import List, Optional

from core.llm.output_schemas.document_creator_outputs import (
    DocumentOutlineOutput,
    DocumentReviewOutput,
    SectionContentOutput,
    SectionIterationOutput,
)

# Shared JSON output rules appended to every prompt
_JSON_RULES = (
    "OUTPUT RULES\n"
    "- Output must be valid JSON only, no markdown fencing or trailing commas.\n"
    "- Newlines inside string values MUST be written as \\n (escaped), NOT as actual line breaks.\n"
    '- Double quotes inside string values MUST be escaped as \\".\n'
    "- Backslashes inside string values MUST be escaped as \\\\.\n"
    "- Include all top-level keys, even if some arrays are empty.\n"
)

# Section count guidance per length preference
_LENGTH_GUIDANCE = {
    "short": "Create 4-6 focused sections.",
    "medium": "Create 7-12 well-structured sections.",
    "detailed": "Create 12-20 comprehensive sections.",
}


def build_outline_prompt(
    document_type: str,
    audience: str,
    tone: str,
    length_preference: str,
    rag_context: str,
    document_titles: List[str],
    custom_instructions: Optional[str] = None,
) -> list[dict]:
    """Build a prompt to generate a document outline from source materials."""
    schema_json = json.dumps(DocumentOutlineOutput.model_json_schema(), indent=2)
    length_hint = _LENGTH_GUIDANCE.get(length_preference, _LENGTH_GUIDANCE["medium"])

    contents = [
        {
            "role": "system",
            "parts": (
                "You are an expert document architect. Your task is to create "
                "a structured outline for a document based on provided source materials.\n\n"
                f"DOCUMENT TYPE: {document_type}\n"
                f"TARGET AUDIENCE: {audience}\n"
                f"TONE: {tone}\n"
                f"LENGTH GUIDANCE: {length_hint}\n\n"
                "Guidelines:\n"
                "- Create sections that logically flow from introduction to conclusion.\n"
                "- Each section should have a clear, distinct purpose with no overlap.\n"
                "- Suggest appropriate content formats: 'prose' for narratives, "
                "'bullets' for key points, 'table' for comparisons, 'mixed' for combinations.\n"
                "- Ensure the outline covers the key themes from the source materials.\n"
                "- Include 3-5 key_points per section describing what should be covered.\n"
                "- For presentations, keep sections concise (one key idea per section/slide).\n"
                "- For reports, include introduction, body sections, and conclusion.\n\n"
                "OUTPUT REQUIREMENT:\n"
                "Return the entire response strictly as a valid JSON object matching the schema below.\n"
                "Do NOT include markdown, comments, or text outside the JSON object.\n\n"
                f"OUTPUT SCHEMA:\n```json\n{schema_json}\n```\n\n"
                + _JSON_RULES
            ),
        },
        {
            "role": "user",
            "parts": (
                f"SOURCE DOCUMENTS: {', '.join(document_titles)}\n\n"
                f"RELEVANT CONTENT FROM SOURCES:\n{rag_context}\n\n"
                + (
                    f"CUSTOM INSTRUCTIONS: {custom_instructions}\n\n"
                    if custom_instructions
                    else ""
                )
                + "Create a structured document outline based on the source materials above.\n"
                "Remember: Return ONLY a valid JSON object."
            ),
        },
    ]
    return contents


def build_section_prompt(
    section_title: str,
    section_description: str,
    content_format: str,
    section_guidance: Optional[str],
    rag_context: str,
    compact_outline: str,
    previous_summary: str,
    terminology: str,
    style_excerpt: Optional[str],
    audience: str,
    tone: str,
) -> list[dict]:
    """Build a prompt to generate content for a single document section."""
    schema_json = json.dumps(SectionContentOutput.model_json_schema(), indent=2)

    style_guidance = ""
    if style_excerpt:
        style_guidance = (
            f"\nSTYLE REFERENCE (match this writing style):\n"
            f'"""{style_excerpt}"""\n'
        )

    contents = [
        {
            "role": "system",
            "parts": (
                "You are generating one section of a larger document. "
                "Write content that fits naturally within the document structure.\n\n"
                f"DOCUMENT OUTLINE:\n{compact_outline}\n\n"
                f"PREVIOUS SECTION SUMMARY:\n{previous_summary}\n\n"
                + (f"KEY TERMINOLOGY:\n{terminology}\n\n" if terminology else "")
                + f"AUDIENCE: {audience}\n"
                f"TONE: {tone}\n"
                + style_guidance
                + "\nGuidelines:\n"
                "- Write content that flows naturally from the previous section.\n"
                "- Use consistent terminology as defined above.\n"
                "- Ground all claims in the provided source context.\n"
                "- Match the specified content format (prose/bullets/table/mixed).\n"
                "- Do NOT include content that belongs in other sections.\n"
                "- For 'bullets' format, provide content as bullet_points list.\n"
                "- For 'table' format, provide table_data with headers and rows.\n"
                "- For 'mixed', provide both prose content and bullet_points.\n"
                "- Include a key_takeaway: one sentence summarizing the section.\n"
                "- Include speaker_notes if this is a presentation.\n\n"
                "OUTPUT REQUIREMENT:\n"
                "Return the entire response strictly as a valid JSON object matching the schema below.\n"
                "Do NOT include markdown, comments, or text outside the JSON object.\n\n"
                f"OUTPUT SCHEMA:\n```json\n{schema_json}\n```\n\n"
                + _JSON_RULES
            ),
        },
        {
            "role": "user",
            "parts": (
                f"SECTION TO GENERATE:\n"
                f"Title: {section_title}\n"
                f"Description: {section_description}\n"
                f"Content Format: {content_format}\n"
                + (
                    f"Additional Guidance: {section_guidance}\n"
                    if section_guidance
                    else ""
                )
                + f"\nSOURCE CONTEXT:\n{rag_context}\n\n"
                "Generate the content for this section.\n"
                "Remember: Return ONLY a valid JSON object."
            ),
        },
    ]
    return contents


def build_section_iteration_prompt(
    section_title: str,
    current_content: str,
    current_bullets: Optional[List[str]],
    feedback: str,
    rag_context: str,
    audience: str,
    tone: str,
) -> list[dict]:
    """Build a prompt for regenerating a section based on user feedback."""
    schema_json = json.dumps(SectionIterationOutput.model_json_schema(), indent=2)

    current_text = current_content
    if current_bullets:
        current_text += "\n\nBullet Points:\n" + "\n".join(
            f"- {b}" for b in current_bullets
        )

    contents = [
        {
            "role": "system",
            "parts": (
                "You are revising a section of a document based on user feedback. "
                "Preserve the section's purpose and factual grounding while "
                "applying the requested changes.\n\n"
                f"AUDIENCE: {audience}\n"
                f"TONE: {tone}\n\n"
                "Guidelines:\n"
                "- Apply the user's feedback precisely.\n"
                "- Maintain factual accuracy grounded in source context.\n"
                "- Preserve the overall structure unless the feedback asks to change it.\n"
                "- Describe what you changed in the changes_made field.\n\n"
                "OUTPUT REQUIREMENT:\n"
                "Return the entire response strictly as a valid JSON object matching the schema below.\n"
                "Do NOT include markdown, comments, or text outside the JSON object.\n\n"
                f"OUTPUT SCHEMA:\n```json\n{schema_json}\n```\n\n"
                + _JSON_RULES
            ),
        },
        {
            "role": "user",
            "parts": (
                f"SECTION: {section_title}\n\n"
                f"CURRENT CONTENT:\n{current_text}\n\n"
                f"USER FEEDBACK: {feedback}\n\n"
                f"SOURCE CONTEXT:\n{rag_context}\n\n"
                "Revise this section according to the feedback.\n"
                "Remember: Return ONLY a valid JSON object."
            ),
        },
    ]
    return contents


def build_review_prompt(
    outline_summary: str,
    sections_summary: str,
) -> list[dict]:
    """Build a prompt for quality self-review of the generated document."""
    schema_json = json.dumps(DocumentReviewOutput.model_json_schema(), indent=2)

    contents = [
        {
            "role": "system",
            "parts": (
                "You are a document quality reviewer. Evaluate the generated document for "
                "coherence, completeness, and consistency.\n\n"
                "Review criteria:\n"
                "1. COHERENCE: Do sections flow logically? Are transitions smooth?\n"
                "2. COMPLETENESS: Does the document cover all points from the outline?\n"
                "3. CONSISTENCY: Is terminology used consistently? Is the tone uniform?\n"
                "4. QUALITY: Are there sections that feel thin, repetitive, or off-topic?\n\n"
                "Score each criterion 1-10 and flag specific issues with suggestions.\n"
                "Set approved=true only if all scores are >= 6 and there are no critical issues.\n\n"
                "OUTPUT REQUIREMENT:\n"
                "Return the entire response strictly as a valid JSON object matching the schema below.\n"
                "Do NOT include markdown, comments, or text outside the JSON object.\n\n"
                f"OUTPUT SCHEMA:\n```json\n{schema_json}\n```\n\n"
                + _JSON_RULES
            ),
        },
        {
            "role": "user",
            "parts": (
                f"DOCUMENT OUTLINE:\n{outline_summary}\n\n"
                f"SECTION CONTENTS:\n{sections_summary}\n\n"
                "Review this document and provide your quality assessment.\n"
                "Remember: Return ONLY a valid JSON object."
            ),
        },
    ]
    return contents
