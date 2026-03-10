"""
Excel Skill Pipeline — orchestrates plan → extract → assemble.

LLM is called only for:
  1. Planning (generate_excel_plan) — decide what sheets/columns/charts to create
  2. NLP columns (nlp_interpret_column) — when a column requires language understanding

Everything else (SQL queries, Excel assembly, formulas, charts) is deterministic.
"""

import os
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


async def generate_excel(
    user_request: str,
    user_id: str,
    thread_id: str,
    source_doc_ids: Optional[List[str]] = None,
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
        user_request: Natural-language request from the user.
        user_id: User identifier.
        thread_id: Thread identifier.
        source_doc_ids: Optional list of document IDs to use as sources.

    Returns:
        ExcelSkillResult with file path and download URL.
    """
    # ── 1. Gather data sources ──
    schema = SQLiteManager.get_schema(user_id, thread_id)
    doc_info = get_document_info(user_id, thread_id, source_doc_ids)

    # ── 2. LLM: generate plan ──
    plan = await generate_excel_plan(
        user_request=user_request,
        available_schema=schema,
        available_documents=doc_info if doc_info else None,
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

    # Pre-extract document tables (for sheets referencing doc data)
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
    output_path = os.path.join(export_dir, f"{plan.file_name}.xlsx")

    assemble_excel(plan, sheet_data, output_path)

    # ── 6. Return result ──
    download_url = f"/excel-skill/download/{thread_id}/{plan.file_name}.xlsx"

    return ExcelSkillResult(
        file_name=f"{plan.file_name}.xlsx",
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

    Handles three source types:
      - SQL query → extract from SQLiteManager
      - Document extraction → use pre-extracted doc tables
      - Mixed → combine sources
    """
    # Try SQL source first
    if sheet_spec.source_query:
        df = await extract_from_spreadsheet(
            user_id=user_id,
            thread_id=thread_id,
            sql_query=sheet_spec.source_query,
        )
        if not df.empty:
            return df

    # Try document table extraction
    has_extract_cols = any(
        c.source.startswith("extract:") for c in sheet_spec.columns
    )
    if has_extract_cols and doc_tables:
        # Find matching document table
        for col_spec in sheet_spec.columns:
            if col_spec.source.startswith("extract:"):
                doc_id = col_spec.source[len("extract:"):]
                # Match by doc_id prefix in table keys
                for key, df in doc_tables.items():
                    if doc_id in key and not df.empty:
                        return df

        # If no specific match, return the first available table
        for df in doc_tables.values():
            if not df.empty:
                return df

    # Fallback: empty DataFrame with column names from spec
    col_names = [c.name for c in sheet_spec.columns if c.source == "sql"]
    return pd.DataFrame(columns=col_names) if col_names else pd.DataFrame()


async def _process_nlp_column(
    df: pd.DataFrame,
    column_name: str,
    instruction: str,
) -> pd.DataFrame:
    """
    Process an NLP column by sending text data to the LLM in batches.

    The LLM interprets each row according to the instruction
    (e.g., "classify sentiment as positive/negative/neutral").
    """
    if df.empty:
        df[column_name] = []
        return df

    # Determine which column to use as input (use the first text column)
    text_cols = df.select_dtypes(include=["object", "string"]).columns
    if len(text_cols) == 0:
        df[column_name] = "N/A"
        return df

    input_col = text_cols[0]
    input_data = df[input_col].fillna("").astype(str).tolist()

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
