"""
Data extraction for the Excel Skill.

Pulls tabular data from two sources:
  1. SQLiteManager — spreadsheet data already loaded into SQL tables
  2. Parsed document JSON — tables extracted from PDFs/PPTX during upload
"""

import json
import os
import re
from typing import Dict, List, Optional

import pandas as pd

from core.services.sqlite_manager import SQLiteManager


async def extract_from_spreadsheet(
    user_id: str,
    thread_id: str,
    sql_query: str,
) -> pd.DataFrame:
    """
    Execute a SQL query against the user's spreadsheet data and return a DataFrame.

    Args:
        user_id: User identifier.
        thread_id: Thread identifier.
        sql_query: SQL SELECT query to execute.

    Returns:
        pandas DataFrame with the query results. Empty DataFrame on error.
    """
    result = SQLiteManager.execute_query(user_id, thread_id, sql_query)

    if not result.get("success"):
        error = result.get("error", "Unknown error")
        print(f"[ExcelSkill:data_extractor] SQL error: {error}")
        return pd.DataFrame()

    # Re-execute with pandas for clean DataFrame (execute_query returns markdown)
    key = (user_id, thread_id)
    if key not in SQLiteManager._connections:
        return pd.DataFrame()

    conn = SQLiteManager._connections[key]
    try:
        df = pd.read_sql_query(sql_query, conn)
        return df
    except Exception as e:
        print(f"[ExcelSkill:data_extractor] DataFrame read error: {e}")
        return pd.DataFrame()


def extract_from_documents(
    user_id: str,
    thread_id: str,
    doc_ids: Optional[List[str]] = None,
) -> Dict[str, pd.DataFrame]:
    """
    Extract tables from parsed document JSON files.

    Scans the parsed directory for document JSON files and extracts
    any tabular data found in the text content (using simple heuristics
    for markdown-style tables or structured page content).

    Args:
        user_id: User identifier.
        thread_id: Thread identifier.
        doc_ids: Optional list of document IDs to filter. If None, all docs are scanned.

    Returns:
        Dict mapping "doc_title (table N)" → DataFrame for each table found.
    """
    parsed_dir = f"data/{user_id}/threads/{thread_id}/parsed"
    tables = {}

    if not os.path.exists(parsed_dir):
        return tables

    for filename in os.listdir(parsed_dir):
        if not filename.endswith(".json"):
            continue

        file_path = os.path.join(parsed_dir, filename)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        doc_id = data.get("id", "")
        if doc_ids and doc_id not in doc_ids:
            continue

        doc_title = data.get("title", filename.replace(".json", ""))
        full_text = data.get("full_text", "")

        # Extract markdown-style tables from the text
        extracted = _extract_markdown_tables(full_text)
        for i, df in enumerate(extracted):
            key = f"{doc_title}" if len(extracted) == 1 else f"{doc_title} (table {i+1})"
            tables[key] = df

    return tables


def _extract_markdown_tables(text: str) -> List[pd.DataFrame]:
    """
    Extract markdown-style pipe tables from text content.

    Handles tables with format:
    | Header1 | Header2 |
    |---------|---------|
    | val1    | val2    |
    """
    tables = []
    lines = text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Look for a line that starts with | and contains |
        if line.startswith("|") and line.count("|") >= 3:
            table_lines = [line]
            j = i + 1

            # Collect consecutive table lines
            while j < len(lines):
                next_line = lines[j].strip()
                if next_line.startswith("|") and "|" in next_line[1:]:
                    table_lines.append(next_line)
                    j += 1
                elif not next_line:
                    j += 1  # skip empty lines within table
                else:
                    break

            if len(table_lines) >= 3:  # header + separator + at least 1 data row
                df = _parse_pipe_table(table_lines)
                if df is not None and not df.empty:
                    tables.append(df)

            i = j
        else:
            i += 1

    return tables


def _parse_pipe_table(lines: List[str]) -> Optional[pd.DataFrame]:
    """Parse a markdown pipe table into a DataFrame."""
    try:
        # Parse header
        header_line = lines[0]
        headers = [
            cell.strip() for cell in header_line.strip("|").split("|")
        ]
        headers = [h for h in headers if h]

        if not headers:
            return None

        # Skip separator line (---|----|----)
        data_start = 1
        if len(lines) > 1 and re.match(r"^\|[\s\-:|]+\|$", lines[1].strip()):
            data_start = 2

        # Parse data rows
        rows = []
        for line in lines[data_start:]:
            if re.match(r"^\|[\s\-:|]+\|$", line.strip()):
                continue  # skip separator lines
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            cells = cells[:len(headers)]  # trim to header count
            # Pad if needed
            while len(cells) < len(headers):
                cells.append("")
            rows.append(cells)

        if not rows:
            return None

        return pd.DataFrame(rows, columns=headers)

    except Exception as e:
        print(f"[ExcelSkill:data_extractor] Table parse error: {e}")
        return None


def get_document_info(
    user_id: str,
    thread_id: str,
    source_doc_ids: Optional[List[str]] = None,
) -> List[dict]:
    """
    Get metadata about available documents in the thread.

    Returns a list of dicts with title, doc_id, type, and table count
    for use in the LLM planning prompt.
    """
    parsed_dir = f"data/{user_id}/threads/{thread_id}/parsed"
    docs = []

    if not os.path.exists(parsed_dir):
        return docs

    for filename in os.listdir(parsed_dir):
        if not filename.endswith(".json"):
            continue

        file_path = os.path.join(parsed_dir, filename)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        doc_id = data.get("id", "")
        if source_doc_ids and doc_id not in source_doc_ids:
            continue

        doc_type = data.get("type", "unknown")
        full_text = data.get("full_text", "")
        table_count = len(_extract_markdown_tables(full_text))

        docs.append({
            "doc_id": doc_id,
            "title": data.get("title", filename.replace(".json", "")),
            "type": doc_type,
            "table_count": table_count,
            "tables": table_count > 0,
            "has_sql_data": data.get("has_sql_data", False),
        })

    return docs
