"""
Prompt templates for the Excel Skill.
"""

from typing import List, Optional


def excel_plan_prompt(
    user_request: str,
    available_schema: Optional[str],
    available_documents: Optional[List[dict]],
) -> str:
    """
    Build the prompt for generating an ExcelSkillPlan.

    The LLM receives the user's natural-language request along with
    available data sources (SQL schema and/or document table info)
    and must produce a structured plan for the Excel workbook.
    """
    schema_section = ""
    if available_schema:
        schema_section = (
            "\n## Available Spreadsheet Data (SQL Queryable)\n"
            "The following tables are loaded in a SQLite database. "
            "You can reference these in `source_query` fields using standard SQL SELECT statements.\n\n"
            f"```\n{available_schema}\n```\n"
        )

    docs_section = ""
    if available_documents:
        doc_lines = []
        for doc in available_documents:
            tables_info = ""
            if doc.get("tables"):
                tables_info = f" — contains {doc['table_count']} table(s)"
            doc_lines.append(
                f"- **{doc['title']}** (ID: {doc['doc_id']}, type: {doc['type']}){tables_info}"
            )
        docs_section = (
            "\n## Available Documents\n"
            "These documents are uploaded in the thread. "
            "Tables extracted from PDFs/PPTX can be used as data sources.\n\n"
            + "\n".join(doc_lines)
            + "\n"
        )

    return (
        "You are an Excel workbook planner. Given a user's request and available data sources, "
        "create a detailed plan for an Excel (.xlsx) file.\n\n"
        "## Rules\n"
        "1. Each sheet must have a clear purpose and descriptive name (max 31 chars).\n"
        "2. For columns sourced from spreadsheet data, write a SQL SELECT query in `source_query`.\n"
        "   - Use standard SQLite syntax. Only SELECT queries are allowed.\n"
        "   - Mark each column's `source` as `sql` when it comes from the query result.\n"
        "3. For computed columns, use `formula:<excel_formula>` with row-relative references "
        "(e.g., `formula:=C2*D2` will be applied to each row).\n"
        "4. For columns requiring language understanding (sentiment, categorization, summarization), "
        "use `nlp:<instruction>` (e.g., `nlp:classify as positive/negative/neutral`).\n"
        "5. For constant values, use `static:<value>`.\n"
        "6. Use `group_by` and `aggregations` for pivot-table-style summaries "
        "(e.g., group_by=['region'], aggregations={'revenue': 'sum', 'orders': 'count'}).\n"
        "7. If the user asks for charts, specify them with proper column references.\n"
        "8. Keep the file name short, lowercase, with underscores (no spaces).\n"
        "9. When the user asks to 'export all data' or 'download the spreadsheet', "
        "create a single sheet with `SELECT * FROM <table>` as the source query.\n"
        "10. For document-extracted tables (PDFs/PPTX), use `source` as `extract:<doc_id>` on columns.\n"
        f"{schema_section}"
        f"{docs_section}"
        f"\n## User Request\n{user_request}\n\n"
        "Return ONLY a valid JSON object matching the required schema. "
        "No markdown fencing, no commentary, no text before or after the JSON.\n"
    )


def excel_nlp_column_prompt(
    column_instruction: str,
    input_data: List[str],
    column_name: str,
) -> str:
    """
    Build the prompt for NLP-based column interpretation.

    The LLM receives a batch of text values and must return
    one interpreted value per input row.
    """
    # Limit to prevent context overflow — process in batches externally
    data_str = "\n".join(f"{i+1}. {val}" for i, val in enumerate(input_data))

    return (
        f"You are a data analyst. For each input row below, apply this instruction: **{column_instruction}**\n\n"
        f"Column name: {column_name}\n\n"
        f"## Input Data ({len(input_data)} rows)\n"
        f"{data_str}\n\n"
        "## Rules\n"
        f"1. Return exactly {len(input_data)} values in the `values` list, one per input row, in the same order.\n"
        "2. Each value should be a short string (1-3 words for classifications, or a brief phrase).\n"
        "3. Be consistent — use the same label for similar inputs.\n"
        "4. If an input is empty or unclear, return 'N/A'.\n\n"
        "Return ONLY a valid JSON object matching the required schema. "
        "No markdown fencing, no commentary.\n"
    )
