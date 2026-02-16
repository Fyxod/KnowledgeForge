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

    if mode == INTERNAL:
        # Build system prompt based on answer style
        if answer_style == "brief":
            system_prompt = (
                "You are an expert assistant that answers questions based on the provided **documents**.\n"
                "Your job is to give clear, concise, and brief answers using Markdown formatting.\n\n"
                "### Guidelines for Brief Answers\n"
                "- Use **headings** (##, ###) for major sections.\n"
                "- Use **bullet points** and **numbered lists** to organize ideas concisely.\n"
                "- Keep explanations **short and to the point**.\n"
                "- Focus on the most important information only.\n"
                "- Avoid unnecessary details or elaboration.\n"
                "- Merge overlapping ideas and remove redundancy.\n"
                "- Rely **strictly** on the supplied data (documents, summaries, conversation history). Never use self-knowledge or unstated assumptions.\n"
                "- If the provided data is insufficient to answer, clearly state: *I cannot answer based on the provided data.*\n"
                "### Context Handling\n"
                "- Extract the most relevant information from the documents.\n"
                "- Provide a **direct and concise answer**.\n"
                "- If multiple sources contradict, mention it briefly.\n"
                "- Do not use your own knowledge outside the provided data in your answers in any case.\n"
                "- Only use the information present in the provided data to answer the question.\n\n"
                "### Output Structure Example\n"
                "```\n"
                "## Overview\n"
                "(Brief explanation)\n\n"
                "## Key Points\n"
                "- **Point 1:** Brief explanation...\n"
                "- **Point 2:** Brief explanation...\n"
                "- **Point 3:** Brief explanation...\n"
                "```\n"
            )
        else:  # detailed (default)
            system_prompt = (
                "You are an expert assistant that answers questions based on the provided **documents**.\n"
                "Your job is to create **clear, structured, and comprehensive answers** using Markdown formatting.\n\n"
                "### Guidelines for Detailed Answers\n"
                "- Use **headings (##, ###)** for major sections.\n"
                "- Use **bullet points** and **numbered lists** to organize ideas.\n"
                "- Highlight important terms in **bold** and examples in *italics*.\n"
                "- Provide **detailed explanations** for each point.\n"
                "- Include relevant examples, comparisons, and clarifications.\n"
                "- Extract and use as much relevant information as possible from the documents.\n"
                "- Provide context and background where helpful.\n"
                "- Merge overlapping ideas but maintain comprehensive coverage.\n"
                "- Rely **strictly** on the supplied data (documents, summaries, conversation history). Never use self-knowledge or unstated assumptions.\n"
                "- If the provided data is insufficient to answer, clearly state: *I cannot answer based on the provided data.* Do not fabricate or infer beyond the supplied information.\n"
                "### Context Handling\n"
                "- Extract and use as much relevant information as possible from the documents.\n"
                "- If the question can be answered using the provided context, give a **direct, detailed, and specific answer**.\n"
                "- Provide comprehensive explanations with examples and context.\n"
                "- If multiple sources contradict, mention it clearly using a note block.\n"
                "- Do not use your own knowledge outside the provided data in your answers in any case.\n"
                "- Only use the information present in the provided data to answer the question.\n\n"
                "### Document References\n"
                "- **IMPORTANT**: When referencing documents in your answer, ALWAYS use the **document name/title** (shown at the top of each chunk), NOT the document ID.\n"
                "- Document IDs are for internal tracking only and should NOT appear in your answers.\n"
                '- Example: Refer to "SRIB AI Visual Quality Enhancements_Y2025_Project_Closure_PPT" instead of "document 73c47".\n'
                "- This provides a much better user experience.\n\n"
                "### Output Structure Example\n"
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

        contents.append(
            {
                "role": "system",
                "parts": system_prompt,
            }
        )

        # Retrieved context
        if chunks:
            contents.append(
                {
                    "role": "system",
                    "parts": f"**Document Chunks (Context):**\n{chunks}\n",
                }
            )

        # Conversation history
        for m in messages:
            if m.type == "human":
                contents.append({"role": "user", "parts": m.content})
            elif m.type == "ai":
                contents.append({"role": "assistant", "parts": m.content})

        # Optional summary
        if summary:
            contents.append(
                {
                    "role": "system",
                    "parts": f"**Summary Reference:**\n{summary}\n",
                }
            )

    elif mode == EXTERNAL:
        # Build system prompt based on answer style
        if answer_style == "brief":
            system_prompt = (
                "You are an expert assistant that answers questions using the provided **documents** and any supplied **external data** (such as web search results).\n"
                "Your task is to create **concise, well-structured Markdown answers** that are clear and to the point.\n\n"
                "### Guidelines for Brief Answers\n"
                "- Structure your answers with **sections, bullets, and bolded keywords**.\n"
                "- Keep explanations **short and concise**.\n"
                "- Focus on the most important information only.\n"
                "- Always **prioritize information from documents** over web results.\n"
                "- Never rely on self-knowledge or unstated assumptions; confine answers to the provided data sources.\n"
                "- If conflicting data exists, state it briefly: *Some sources provide conflicting information...*\n"
                "- If the provided data cannot answer the question, state explicitly: *I cannot answer based on the provided data.*\n\n"
                "### Output Structure Example\n"
                "```\n"
                "## Overview\n"
                "(Brief explanation)\n\n"
                "## Key Points\n"
                "- **Document Insight:** Brief point...\n"
                "- **Web Insight:** Brief point...\n\n"
                "## Summary\n"
                "(Concise conclusion)\n"
                "```\n"
            )
        else:  # detailed (default)
            system_prompt = (
                "You are an expert assistant that answers questions using the provided **documents** and any supplied **external data** (such as web search results).\n"
                "Your task is to create **comprehensive, well-structured Markdown answers** that are clear and detailed.\n\n"
                "### Guidelines for Detailed Answers\n"
                "- Structure your answer with **sections, bullets, and bolded keywords**.\n"
                "- Provide **detailed explanations** for each point.\n"
                "- Include relevant examples, comparisons, and clarifications.\n"
                "- Extract and use as much relevant information as possible from documents and web sources.\n"
                "- Provide context and background where helpful.\n"
                "- Always **prioritize information from documents** over web results.\n"
                "- Never rely on self-knowledge or unstated assumptions; confine answers to the provided data sources.\n"
                "- If conflicting data exists, state clearly: *Some sources provide conflicting information...*\n"
                "- If the provided data cannot answer the question, state explicitly: *I cannot answer based on the provided data.*\n\n"
                "### Document References\n"
                "- **IMPORTANT**: When referencing documents in your answer, ALWAYS use the **document name/title** (shown at the top of each chunk), NOT the document ID.\n"
                "- Document IDs are for internal tracking only and should NOT appear in your answers.\n"
                '- Example: Refer to "SRIB AI Visual Quality Enhancements_Y2025_Project_Closure_PPT" instead of "document 73c47".\n'
                "- This provides a much better user experience.\n\n"
                "### Output Structure Example\n"
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

        contents.append(
            {
                "role": "system",
                "parts": system_prompt,
            }
        )

        # Retrieved context
        if chunks:
            contents.append(
                {
                    "role": "system",
                    "parts": f"**Document Chunks (Context):**\n{chunks}\n",
                }
            )

        # Initial external sources
        if initial_search_results:
            contents.append(
                {
                    "role": "system",
                    "parts": f"**Initial External Knowledge Sources:**\n{initial_search_results}\n",
                }
            )

        # Conversation history
        for m in messages:
            if m.type == "human":
                contents.append({"role": "user", "parts": m.content})
            elif m.type == "ai":
                contents.append({"role": "assistant", "parts": m.content})

        # Summary context
        if summary:
            contents.append(
                {
                    "role": "system",
                    "parts": f"**Summary Reference:**\n{summary}\n",
                }
            )

        # Web search results
        if web_search_results:
            contents.append(
                {
                    "role": "system",
                    "parts": f"**Web Search Results:**\n{web_search_results}\n",
                }
            )

        # Initial web answer
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

    else:
        raise ValueError("Invalid mode. Mode must be either 'INTERNAL' or 'EXTERNAL'.")

    contents.append(
        {
            "role": "system",
            "parts": "Don't give too much importance to the title while giving answer as titles are just the filenames which might be vague or unrelated to the content of the documents.",
        }
    )

    # --- Spreadsheet SQL schema (if available) ---
    if spreadsheet_schema:
        contents.append(
            {
                "role": "system",
                "parts": (
                    "###  Spreadsheet Data (SQL Queryable)\n"
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

    # --- SQL query result from a previous iteration ---
    if sql_result:
        contents.append(
            {
                "role": "system",
                "parts": (
                    "###  SQL Query Result\n"
                    "A SQL query was executed on the spreadsheet data. Here is the result:\n\n"
                    f"{sql_result}\n\n"
                    "Use this result to formulate your final answer to the user's question. "
                    "Present the data clearly using Markdown tables or formatted text."
                ),
            }
        )

    # Defining actions
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
            "parts": "Please return your response **only** in a valid JSON format containing the final synthesized Markdown answer.",
        }
    )

    return contents
