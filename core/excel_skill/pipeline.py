"""
Excel Skill Pipeline — orchestrates plan → extract → assemble.

LLM is called only for:
  1. Planning (generate_excel_plan) — decide what sheets/columns/charts to create
  2. NLP columns (nlp_interpret_column) — when a column requires language understanding

Everything else (SQL queries, Excel assembly, formulas, charts) is deterministic.
"""

import json
import os
import re
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd

from core.constants import GPU_EXCEL_NLP_LLM
from core.excel_skill.assembler import assemble_excel
from core.excel_skill.data_extractor import (
    extract_from_documents,
    extract_from_spreadsheet,
    get_document_info,
)
from core.excel_skill.planner import generate_excel_plan
from core.llm.client import invoke_llm
from core.llm.output_schemas.excel_skill_outputs import (
    ExcelSkillPlan,
    NLPColumnResult,
    SheetSpec,
)
from core.llm.prompts.excel_skill_prompts import excel_nlp_column_prompt
from core.services.sqlite_manager import SQLiteManager


@dataclass
class ExcelSkillResult:
    """Result of an Excel skill execution."""

    file_name: str
    file_path: str
    download_url: str
    description: str
    sheet_count: int
    total_rows: int


# NLP batch size — process this many rows per LLM call to stay within context
NLP_BATCH_SIZE = 100


def _sanitize_export_name(name: str) -> str:
    """Convert the requested workbook name into a filesystem-safe base name."""
    safe_name = re.sub(r"[^\w\s\-.]", "", name).strip()
    return re.sub(r"\s+", "_", safe_name) or "export"


def _build_unique_export_filename(export_dir: str, plan_file_name: str) -> str:
    """Create a unique .xlsx filename so saved exports never overwrite each other."""
    base_name = _sanitize_export_name(plan_file_name)

    while True:
        candidate = f"{base_name}_{uuid.uuid4().hex[:8]}.xlsx"
        if not os.path.exists(os.path.join(export_dir, candidate)):
            return candidate


def _ensure_sqlite_loaded(user_id: str, thread_id: str) -> None:
    """
    Ensure spreadsheet data is loaded into SQLiteManager for this thread.

    In-memory SQLite connections are lost on server restart or worker switch.
    This mirrors the reload logic in app/routes/query.py to recover them.
    """
    key = (user_id, thread_id)
    if key in SQLiteManager._connections:
        # Check if the connection actually has tables
        if SQLiteManager.has_spreadsheet_data(user_id, thread_id):
            return

    # Try to reload from uploaded files
    try:
        from core.database import db

        user = db.users.find_one({"threads." + thread_id: {"$exists": True}})
        if not user:
            return

        thread = user.get("threads", {}).get(thread_id)
        if not thread:
            return

        spreadsheet_files = []
        for doc in thread.get("documents", []):
            fname = doc.get("file_name", "").lower()
            if fname.endswith(".xlsx") or fname.endswith(".xls") or fname.endswith(".csv"):
                file_path = f"data/{user_id}/threads/{thread_id}/uploads/{doc['file_name']}"
                if os.path.exists(file_path):
                    spreadsheet_files.append({
                        "path": file_path,
                        "file_name": doc["file_name"],
                        "doc_id": doc.get("docId"),
                    })

        if spreadsheet_files:
            print(f"[ExcelSkill] Reloading {len(spreadsheet_files)} spreadsheet(s) into SQLite")
            SQLiteManager.reload_from_files(user_id, thread_id, spreadsheet_files)
    except Exception as e:
        print(f"[ExcelSkill] SQLite reload error: {e}")


async def generate_excel(
    user_request: str,
    user_id: str,
    thread_id: str,
    source_doc_ids: Optional[List[str]] = None,
    prior_sql_query: Optional[str] = None,
) -> ExcelSkillResult:
    """
    Main entry point: generate an Excel file from a user request.

    Pipeline:
      1. Gather available data sources (SQL schema + document info)
      2. LLM generates an ExcelSkillPlan
      3. Extract data deterministically (SQL + parsed doc tables)
      4. Process any NLP columns via LLM callback
      5. Assemble the .xlsx file via openpyxl
      6. Return download info

    Args:
        prior_sql_query: A SQL query already executed in this conversation
            whose filtered result set the Excel should reflect. Forwarded
            to the planner as an advisory hint.
    """
    # ── 1. Gather data sources ──
    _ensure_sqlite_loaded(user_id, thread_id)
    schema = SQLiteManager.get_schema(user_id, thread_id)
    doc_info = get_document_info(user_id, thread_id, source_doc_ids)

    # ── 2. LLM: generate plan ──
    plan = await generate_excel_plan(
        user_request=user_request,
        available_schema=schema,
        available_documents=doc_info if doc_info else None,
        prior_sql_query=prior_sql_query,
    )

    print(
        f"[ExcelSkill] Plan: {plan.file_name} — "
        f"{len(plan.sheets)} sheet(s), "
        f"charts={'yes' if plan.charts else 'no'}, "
        f"summary={plan.summary_sheet}"
    )

    # ── 3. Extract data ──
    sheet_data: Dict[str, pd.DataFrame] = {}
    total_rows = 0

    # Pre-extract document tables (keyed by both doc_id and title for flexible matching)
    doc_tables = extract_from_documents(user_id, thread_id, source_doc_ids)

    for sheet_spec in plan.sheets:
        df = await _extract_sheet_data(
            sheet_spec=sheet_spec,
            user_id=user_id,
            thread_id=thread_id,
            doc_tables=doc_tables,
        )

        # ── 4. Process NLP columns ──
        for col_spec in sheet_spec.columns:
            if col_spec.source.startswith("nlp:"):
                instruction = col_spec.source[len("nlp:"):]
                df = await _process_nlp_column(
                    df=df,
                    column_name=col_spec.name,
                    instruction=instruction,
                )

        # Add static columns
        for col_spec in sheet_spec.columns:
            if col_spec.source.startswith("static:"):
                static_value = col_spec.source[len("static:"):]
                df[col_spec.name] = static_value

        sheet_data[sheet_spec.sheet_name] = df
        total_rows += len(df)

    # ── 5. Assemble Excel ──
    export_dir = f"data/{user_id}/threads/{thread_id}/excel_exports"
    os.makedirs(export_dir, exist_ok=True)

    output_file_name = _build_unique_export_filename(export_dir, plan.file_name)
    output_path = os.path.join(export_dir, output_file_name)

    assemble_excel(plan, sheet_data, output_path)

    # ── 6. Return result ──
    download_url = f"/excel-skill/download/{thread_id}/{output_file_name}"

    return ExcelSkillResult(
        file_name=output_file_name,
        file_path=output_path,
        download_url=download_url,
        description=plan.description,
        sheet_count=len(plan.sheets),
        total_rows=total_rows,
    )


async def _extract_sheet_data(
    sheet_spec: SheetSpec,
    user_id: str,
    thread_id: str,
    doc_tables: Dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    Extract data for a single sheet based on its specification.

    Tries multiple strategies in order:
      1. SQL query (if source_query is set)
      2. Document table matching by doc_id or title
      3. First available document table (universal fallback)
    """
    # ── Strategy 1: SQL source ──
    if sheet_spec.source_query:
        df = await extract_from_spreadsheet(
            user_id=user_id,
            thread_id=thread_id,
            sql_query=sheet_spec.source_query,
        )
        if not df.empty:
            # Apply filter_condition if specified and not already in the SQL
            if sheet_spec.filter_condition and "WHERE" not in sheet_spec.source_query.upper():
                try:
                    df = df.query(sheet_spec.filter_condition)
                except Exception as e:
                    print(f"[ExcelSkill] filter_condition failed ({sheet_spec.filter_condition}): {e}")
            return df
        else:
            print(
                f"[ExcelSkill] SQL query returned 0 rows for sheet '{sheet_spec.sheet_name}': "
                f"{sheet_spec.source_query[:100]}"
            )

    # ── Strategy 2: Document table matching ──
    if doc_tables:
        # Build a lookup: doc_id → list of (key, DataFrame)
        # doc_tables keys are like "Title" or "Title (table 2)"
        # The extract_from_documents function also stores doc_id in a parallel index
        for col_spec in sheet_spec.columns:
            if col_spec.source.startswith("extract:"):
                target_id = col_spec.source[len("extract:"):]
                # Try matching by doc_id (stored in the key metadata)
                for key, df in doc_tables.items():
                    if not df.empty and (target_id in key or target_id.lower() in key.lower()):
                        print(f"[ExcelSkill] Matched doc table '{key}' via extract:{target_id}")
                        return df

        # No specific extract: columns found or no match — try any available table
        for key, df in doc_tables.items():
            if not df.empty:
                print(f"[ExcelSkill] Using first available doc table: '{key}' ({len(df)} rows)")
                return df

    # ── Strategy 3: Universal fallback — if we have ANY doc tables, use the largest ──
    if doc_tables:
        best_key, best_df = max(doc_tables.items(), key=lambda item: len(item[1]))
        if not best_df.empty:
            print(
                f"[ExcelSkill] Fallback: using largest doc table '{best_key}' ({len(best_df)} rows)"
            )
            return best_df

    # Nothing worked — return empty DataFrame with column names from spec
    print(f"[ExcelSkill] WARNING: No data found for sheet '{sheet_spec.sheet_name}'")
    col_names = [c.name for c in sheet_spec.columns]
    return pd.DataFrame(columns=col_names)


def _rows_to_strings(df: pd.DataFrame) -> list[str]:
    """Convert each DataFrame row into a readable 'Col: val | Col: val' string."""
    cols = list(df.columns)
    rows = []
    for _, row in df.iterrows():
        parts = [f"{c}: {row[c]}" for c in cols if pd.notna(row[c]) and str(row[c]).strip()]
        rows.append(" | ".join(parts) if parts else "(empty row)")
    return rows


async def _process_nlp_column(
    df: pd.DataFrame,
    column_name: str,
    instruction: str,
) -> pd.DataFrame:
    """
    Process an NLP column by sending full row data to the LLM in batches.

    The LLM interprets each row according to the instruction
    (e.g., "classify sentiment as positive/negative/neutral").
    """
    if df.empty:
        df[column_name] = []
        return df

    if len(df.columns) == 0:
        df[column_name] = "N/A"
        return df

    # Send ALL columns so the LLM can analyze the full row context
    input_data = _rows_to_strings(df)

    # Process in batches
    all_values = []
    for batch_start in range(0, len(input_data), NLP_BATCH_SIZE):
        batch = input_data[batch_start : batch_start + NLP_BATCH_SIZE]

        try:
            prompt = excel_nlp_column_prompt(
                column_instruction=instruction,
                input_data=batch,
                column_name=column_name,
            )

            result = await invoke_llm(
                gpu_model=GPU_EXCEL_NLP_LLM.model,
                response_schema=NLPColumnResult,
                contents=prompt,
                port=GPU_EXCEL_NLP_LLM.port,
            )
            result = NLPColumnResult.model_validate(result)

            # Ensure correct length
            values = result.values
            if len(values) < len(batch):
                values.extend(["N/A"] * (len(batch) - len(values)))
            elif len(values) > len(batch):
                values = values[: len(batch)]

            all_values.extend(values)

        except Exception as e:
            print(f"[ExcelSkill] NLP column error: {e}")
            all_values.extend(["Error"] * len(batch))

    df[column_name] = all_values[: len(df)]
    return df
