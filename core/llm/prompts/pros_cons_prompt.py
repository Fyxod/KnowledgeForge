from typing import List


def pros_cons_prompt(document: str, count: int):
    """
    Build a chat prompt to extract exactly `count` pros and `count` cons from a source document.

    Args:
            document: The source text (raw content or a summary) to analyze.
            count: The exact number of pros and cons to return.

    Returns:
            A list of chat messages (role/parts) ready for the LLM client.
    """
    contents = [
        {
            "role": "system",
            "parts": (
                "You are an expert analyst. Read the document and extract balanced, evidence-based pros and cons.\n\n"
                "OUTPUT CONTRACT (STRICT):\n"
                "- Return ONLY a valid JSON object with exactly these fields and types:\n"
                "  - pros: List[str] (length == {count})\n"
                "  - cons: List[str] (length == {count})\n"
                "- Do not include any additional fields, text, or commentary.\n"
                "- Each item must be a concise, self-contained statement (8-20 words),\n"
                "  specific to the document, non-redundant, and mutually exclusive.\n"
                "- Avoid hedging and filler; prefer concrete, actionable phrasing.\n"
                "- If evidence is weak, infer cautiously but stay aligned with the document's scope.\n"
            ).format(count=count),
        },
        {
            "role": "system",
            "parts": (
                "QUALITY BAR:\n"
                "- Ground points in the document; integrate relevant domain knowledge when helpful.\n"
                "- Keep language neutral and professional; avoid marketing tone.\n"
                "- Ensure no duplicates across lists and no item exceeds one sentence.\n"
            ),
        },
        {
            "role": "user",
            "parts": (
                f"CONTEXT (document):\n\n{document}\n\n"
                f"TASK: Return ONLY JSON structure as specified above with exactly {count} pros and {count} cons."
            ),
        },
    ]   

    return contents
