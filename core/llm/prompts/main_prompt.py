from typing import Any, Dict, List, Optional
from core.constants import INTERNAL, EXTERNAL


def detect_answer_style(question: str) -> str:
    """
    Detect the desired answer style based on keywords in the question.

    Returns:
        'brief'    - User wants a concise answer (keywords: "3 bullet points", "summarize", "brief", "short", "concise")
        'detailed' - User wants a detailed answer (keywords: "detailed", "elaborate", "explain in detail", "comprehensive")
        'normal'   - Default to detailed answers
    """
    question_lower = question.lower()

    # Brief answer keywords
    brief_keywords = [
        "3 bullet points",
        "summarize",
        "brief",
        "short",
        "concise",
        "in short",
        "quick summary",
    ]
    for keyword in brief_keywords:
        if keyword in question_lower:
            return "brief"

    # Detailed answer keywords
    detailed_keywords = [
        "detailed",
        "elaborate",
        "explain in detail",
        "comprehensive",
        "in depth",
        "thorough",
    ]
    for keyword in detailed_keywords:
        if keyword in question_lower:
            return "detailed"

    # Default to detailed answers
    return "detailed"


def _build_system_prompt(mode: str, answer_style: str) -> str:
    """
    Build the system prompt from shared components.
    Eliminates the 4-way duplication (INTERNAL×brief, INTERNAL×detailed, EXTERNAL×brief, EXTERNAL×detailed).
    """

    is_brief = answer_style == "brief"
    is_external = mode == EXTERNAL

    # ── Role ──
    if is_external:
        role = (
            "You are an expert assistant that answers questions using the provided **documents** "
            "and any supplied **external data** (such as web search results).\n"
        )
    else:
        role = (
            "You are an expert assistant that answers questions based on the provided **documents**.\n"
        )

    # ── Task ──
    if is_brief:
        task = "Your job is to give clear, concise, and brief answers using Markdown formatting.\n\n"
    else:
        task = "Your job is to create **clear, structured, and comprehensive answers** using Markdown formatting.\n\n"

    # ── Formatting Guidelines ──
    if is_brief:
        guidelines = (
            "### Answer Guidelines\n"
            "- Use **headings** (##, ###) for major sections.\n"
            "- Use **bullet points** and **numbered lists** to organize ideas concisely.\n"
            "- Keep explanations **short and to the point**.\n"
            "- Focus on the most important information only.\n"
            "- Avoid unnecessary details or elaboration.\n"
            "- Merge overlapping ideas and remove redundancy.\n"
        )
    else:
        guidelines = (
            "### Answer Guidelines\n"
            "- Use **headings (##, ###)** for major sections.\n"
            "- Use **bullet points** and **numbered lists** to organize ideas.\n"
            "- Highlight important terms in **bold** and examples in *italics*.\n"
            "- Provide **detailed explanations** for each point.\n"
            "- Include relevant examples, comparisons, and clarifications.\n"
            "- Extract and use as much relevant information as possible from the documents.\n"
            "- Provide context and background where helpful.\n"
            "- Merge overlapping ideas but maintain comprehensive coverage.\n"
        )

    # ── Grounding Rules (single authoritative block) ──
    grounding = (
        "\n### Grounding Rules\n"
        "- Rely **strictly** on the supplied data (documents, summaries, conversation history). "
        "Never use self-knowledge or unstated assumptions.\n"
        "- Do NOT fabricate, infer beyond the supplied information, or use knowledge not present in the provided data.\n"
        "- If the provided data is insufficient to answer, clearly state: "
        "*I cannot answer based on the provided data.*\n"
    )
    if is_external:
        grounding += (
            "- Always **prioritize information from documents** over web results.\n"
            "- If conflicting data exists between document and web sources, "
            "state clearly: *Some sources provide conflicting information...*\n"
        )
    else:
        grounding += (
            "- If multiple sources contradict, mention it clearly using a note block.\n"
        )

    # ── Document References ──
    doc_refs = ""
    if not is_brief:
        doc_refs = (
            "\n### Document References\n"
            "- **IMPORTANT**: When referencing documents in your answer, ALWAYS use the **document name/title** "
            "(shown at the top of each chunk), NOT the document ID.\n"
            "- Document IDs are for internal tracking only and should NOT appear in your answers.\n"
            '- Example: Refer to "Annual Report 2025" instead of "document 73c47".\n'
        )

    # ── Output Structure Example ──
    if is_brief:
        structure = (
            "\n### Output Structure\n"
            "```\n"
            "## Overview\n"
            "(Brief explanation)\n\n"
            "## Key Points\n"
            "- **Point 1:** Brief explanation...\n"
            "- **Point 2:** Brief explanation...\n"
            "- **Point 3:** Brief explanation...\n"
            "```\n"
        )
    else:
        if is_external:
            structure = (
                "\n### Output Structure\n"
                "```\n"
                "## Overview\n"
                "(Comprehensive explanation)\n\n"
                "## Key Information\n"
                "- **Document Insight:** Detailed explanation with context...\n"
                "- **Web Insight:** Detailed explanation with examples...\n\n"
                "## Additional Insights\n"
                "- Examples, comparisons, or clarifications.\n"
                "- Related information from sources.\n\n"
                "## Conflicts or Gaps\n"
                "- *Some sources differ on...*\n\n"
                "## Summary\n"
                "(Comprehensive conclusion)\n"
                "```\n"
            )
        else:
            structure = (
                "\n### Output Structure\n"
                "```\n"
                "## Overview\n"
                "(Comprehensive explanation)\n\n"
                "## Key Details\n"
                "- **Point 1:** Detailed explanation with context...\n"
                "- **Point 2:** Detailed explanation with examples...\n"
                "- **Point 3:** Detailed explanation with clarifications...\n\n"
                "## Additional Insights\n"
                "- *Examples, comparisons, or clarifications.*\n"
                "- *Related information from documents.*\n\n"
                "## Summary\n"
                "(Comprehensive conclusion)\n"
                "```\n"
            )

    return role + task + guidelines + grounding + doc_refs + structure


def main_prompt(
    messages: list,
    chunks: str,
    question: str,
    summary: str,
    mode: str,
    web_search_results: List[Dict[str, Any]] = None,
    initial_search_answer: str = None,
    initial_search_results: List[Dict[str, Any]] = None,
    use_self_knowledge: bool = False,
    spreadsheet_schema: Optional[str] = None,
    sql_result: Optional[str] = None,
):
    contents = []

    # Detect answer style based on question
    answer_style = detect_answer_style(question)

    if mode not in (INTERNAL, EXTERNAL):
        raise ValueError("Invalid mode. Mode must be either 'INTERNAL' or 'EXTERNAL'.")

    # ── System prompt (built from shared components) ──
    system_prompt = _build_system_prompt(mode, answer_style)
    contents.append({"role": "system", "parts": system_prompt})

    # ── Retrieved context ──
    if chunks:
        contents.append(
            {"role": "system", "parts": f"**Document Chunks (Context):**\n{chunks}\n"}
        )

    # ── External-only sources ──
    if mode == EXTERNAL:
        if initial_search_results:
            contents.append(
                {
                    "role": "system",
                    "parts": f"**Initial External Knowledge Sources:**\n{initial_search_results}\n",
                }
            )

    # ── Conversation history ──
    for m in messages:
        if m.type == "human":
            contents.append({"role": "user", "parts": m.content})
        elif m.type == "ai":
            contents.append({"role": "assistant", "parts": m.content})

    # ── Summary context ──
    if summary:
        contents.append(
            {"role": "system", "parts": f"**Summary Reference:**\n{summary}\n"}
        )

    # ── External-only: web search results ──
    if mode == EXTERNAL:
        if web_search_results:
            contents.append(
                {
                    "role": "system",
                    "parts": f"**Web Search Results:**\n{web_search_results}\n",
                }
            )
        if initial_search_answer:
            contents.append(
                {
                    "role": "system",
                    "parts": f"**Initial Web Search Answer:**\n{initial_search_answer}\n",
                }
            )
        contents.append(
            {
                "role": "system",
                "parts": (
                    "If conflicting information exists, always **prioritize document content over web sources.**\n"
                    "If no provided data resolves the question, respond that you cannot answer based on the provided data."
                ),
            }
        )

    # ── Title caveat ──
    contents.append(
        {
            "role": "system",
            "parts": (
                "Titles shown in the document chunks are filenames and may not accurately reflect the document content. "
                "Use them for reference attribution but do not rely on them as indicators of what the document covers."
            ),
        }
    )

    # ── Spreadsheet SQL schema (if available) ──
    if spreadsheet_schema:
        contents.append(
            {
                "role": "system",
                "parts": (
                    "### Spreadsheet Data (SQL Queryable)\n"
                    "The user has uploaded spreadsheet files (Excel/CSV) that have been loaded into a SQL database. "
                    "You can query this data using SQL SELECT statements.\n\n"
                    "**Available Tables and Columns:**\n"
                    f"```\n{spreadsheet_schema}\n```\n\n"
                    "**SQL Query Guidelines:**\n"
                    "- Use the `sql_query` action to run a SQL SELECT query against the spreadsheet data.\n"
                    "- Write standard SQLite-compatible SQL queries.\n"
                    "- Use aggregate functions like COUNT(), SUM(), AVG(), MIN(), MAX() for calculations.\n"
                    "- Use GROUP BY and ORDER BY for grouping and sorting.\n"
                    "- Use WHERE clauses to filter data.\n"
                    "- Use LIKE with wildcards for partial text matching (e.g., WHERE column LIKE '%keyword%').\n"
                    "- Column names and table names are case-sensitive and use underscores instead of spaces.\n"
                    "- Only SELECT queries are allowed (no INSERT, UPDATE, DELETE).\n"
                    "- **CRITICAL — SQL-FIRST RULE**: For ANY question whose answer could exist in the spreadsheet tables above, "
                    "you MUST use the `sql_query` action. This includes but is NOT limited to:\n"
                    "  * Looking up a specific person's details (address, email, phone, etc.)\n"
                    "  * Finding or listing records that match a condition (e.g., students from a state, employees in a department)\n"
                    "  * Searching for a name, value, or keyword in the data\n"
                    "  * Counting, summing, averaging, ranking, or any aggregation\n"
                    "  * Filtering, sorting, or comparing rows\n"
                    "  * ANY data retrieval from tabular/spreadsheet content\n"
                    "  NEVER answer from text chunks when the question relates to spreadsheet data — "
                    "text chunks are incomplete fragments and WILL give wrong or partial results. "
                    "The SQL database contains ALL rows and ALL columns and will give exact, complete results.\n"
                    "- Always provide the `sql_query` field in your response when choosing the `sql_query` action.\n"
                    "- Even if you see some spreadsheet data in the document chunks, ALWAYS use `sql_query` instead. "
                    "The document chunks are only text previews and do NOT contain the full dataset.\n"
                ),
            }
        )

    # ── SQL query result from a previous iteration ──
    if sql_result:
        contents.append(
            {
                "role": "system",
                "parts": (
                    "### SQL Query Result\n"
                    "A SQL query was executed on the spreadsheet data. Here is the result:\n\n"
                    f"{sql_result}\n\n"
                    "Use this result to formulate your final answer to the user's question. "
                    "Present the data clearly using Markdown tables or formatted text."
                ),
            }
        )

    # ── Available actions ──
    sql_action_text = ""
    if spreadsheet_schema:
        sql_action_text = (
            "- **sql_query**: Execute a SQL SELECT query against the spreadsheet data. Use this for ANY question "
            "that can be answered from the uploaded spreadsheet/CSV files — including lookups, searches, filters, "
            "aggregations, listings, and data retrieval. Requires the `sql_query` field with a valid SQLite SELECT statement. "
            "**This should be your DEFAULT choice whenever the question relates to spreadsheet data.**\n"
        )

    contents.append(
        {
            "role": "system",
            "parts": (
                "You can perform the following actions:\n"
                "- **answer**: Directly answer the question using available information.\n"
                + (
                    "- **web_search**: Search for recent or external information not in the documents.\n"
                    if mode == EXTERNAL
                    else ""
                )
                + sql_action_text
                + "- **document_summarizer**: Request a summary of a specific document (requires `document_id`).\n"
                "- **global_summarizer**: Request a collective summary of all documents.\n"
                "- **failure**: Indicate inability to answer with available information.\n"
                "Do not choose an action lightly; only use 'failure' when absolutely necessary.\n"
                "Do not choose any other action other than the ones mentioned above.\n"
            ),
        }
    )

    contents.append(
        {
            "role": "user",
            "parts": "Please use all the provided information to answer the question.",
        }
    )

    # Final user question
    contents.append({"role": "user", "parts": f"**Question:** {question}\n"})

    # JSON formatting requirement
    contents.append(
        {
            "role": "user",
            "parts": "Return ONLY a valid JSON object matching the required schema. No markdown fencing, no commentary.",
        }
    )

    return contents
