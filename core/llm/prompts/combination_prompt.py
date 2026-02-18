import json


def combination_prompt(query: str, sub_answers: list) -> list:
    """
    Build a chat prompt to synthesize multiple sub-answers into one coherent response.
    Returns the standard message-list format [{role, parts}] used by all other prompts.
    """
    sub_answers_json = json.dumps(sub_answers, indent=2, ensure_ascii=False)

    contents = [
        {
            "role": "system",
            "parts": (
                "You are an expert assistant for a Retrieval-Augmented Generation (RAG) system.\n\n"
                "Your job is to synthesize multiple partial answers into one coherent, well-structured response.\n\n"
                "### Rules\n"
                "1. Use the Resolved_query as the *main question* you are answering.\n"
                "2. Read all Sub_answers carefully.\n"
                "3. Combine them into a single, natural response that directly answers the Resolved_query.\n"
                "4. Remove redundancy, but keep all distinct insights.\n"
                "5. If Sub_answers contradict, note the discrepancy clearly.\n"
                "6. If any Sub_answer is missing or empty, state that information was not found.\n"
                "7. Maintain clarity, conciseness, and factual tone.\n"
                "8. Retain the formatting of any lists/headings/bullets from Sub_answers.\n"
                "9. Ensure the final answer is in **clear, structured Markdown** with headings, bullet points, and bold text for readability.\n"
                "10. Synthesize ONLY from the provided sub-answers. Do not add external knowledge.\n\n"
                "### CRITICAL: Document Naming Rules\n"
                "- **ALWAYS** use the **exact document name/title** as it appears in the sub-answers "
                "(e.g., \"Annual Report 2025\", \"Q3 Financial Summary\").\n"
                "- **NEVER** use generic labels like 'Document 1', 'Document 2', 'the first document', "
                "'the second document', 'the uploaded document', or similar numbered/ordinal references.\n"
                "- If a sub-answer mentions a document by name, PRESERVE that exact name in the combined answer.\n"
                "- Inline citations in `[Document Title, Page X]` format MUST be preserved from sub-answers.\n\n"
                "### Output\n"
                "Return only the final synthesized answer, written for the end user, without repeating the Resolved_query.\n"
            ),
        },
        {
            "role": "user",
            "parts": (
                f"**Resolved_query:** \"{query}\"\n\n"
                f"**Sub_answers:**\n{sub_answers_json}\n\n"
                "Synthesize these into a single, coherent Markdown answer."
            ),
        },
    ]

    return contents
