"""
Excel Skill Pipeline — orchestrates plan → extract → assemble.

LLM is called only for:
  1. Planning (generate_excel_plan) — decide what sheets/columns/charts to create
  2. NLP columns (nlp_interpret_column) — when a column requires language understanding

Everything else (SQL queries, Excel assembly, formulas, charts) is deterministic.

For datasets with >50 rows or >50 unique values, NLP columns use a smart pipeline:
  1. Deduplicate values in the source column
  2. Discover a classification taxonomy from a sample via LLM
  3. Apply taxonomy rules deterministically (keyword matching)
  4. Batch remaining unclassified values through LLM (in parallel)
  5. Map results back to the full dataset
"""

import asyncio
import json
import os
import re
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd

from core.constants import GPU_EXCEL_NLP_LLM, MAIN_MODEL, MODEL_CONTEXT_TOKENS, MODEL_OUTPUT_RESERVE
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
    TaxonomyResult,
)
from core.llm.prompts.excel_skill_prompts import (
    excel_nlp_column_prompt,
    excel_nlp_fallback_prompt,
    excel_taxonomy_discovery_prompt,
)
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


# NLP batch limits — dynamic sizing fills up to the context window budget,
# but never exceeds NLP_BATCH_MAX or goes below NLP_BATCH_MIN.
NLP_BATCH_MAX = 300
NLP_BATCH_MIN = 20

# Token budget for NLP data (context window minus output reserve minus prompt overhead)
_NLP_PROMPT_OVERHEAD_TOKENS = 3000  # system prompt + instruction template

# Brute-force ceiling — datasets at or below this threshold (both total rows
# AND unique values) skip taxonomy discovery and batch everything through LLM.
# Above this, the smart taxonomy pipeline provides consistent labels + dedup.
NLP_BRUTE_FORCE_MAX = 50

# Taxonomy sample size — how many unique values to sample for taxonomy discovery
TAXONOMY_SAMPLE_SIZE = 200

# Parallel concurrency for NLP fallback batches
NLP_PARALLEL_CONCURRENCY = 5


def _estimate_nlp_batch_size(sample_rows: List[str]) -> int:
    """
    Dynamically calculate how many rows fit in one NLP LLM call.

    Samples a few rows, estimates tokens per row via tiktoken, then
    fills the context window budget (model context − output reserve −
    prompt overhead).  Clamps to [NLP_BATCH_MIN, NLP_BATCH_MAX].
    """
    from core.utils.count_tokens import count_tokens

    if not sample_rows:
        return NLP_BATCH_MIN

    # Estimate avg tokens per row from a small sample
    sample_text = "\n".join(sample_rows[: min(20, len(sample_rows))])
    sample_count = min(20, len(sample_rows))
    avg_tokens_per_row = max(
        1, count_tokens(sample_text, MAIN_MODEL) / sample_count
    )

    budget = MODEL_CONTEXT_TOKENS - MODEL_OUTPUT_RESERVE - _NLP_PROMPT_OVERHEAD_TOKENS
    rows = int(budget / avg_tokens_per_row)
    rows = max(NLP_BATCH_MIN, min(NLP_BATCH_MAX, rows))

    print(
        f"[ExcelSkill:nlp] Dynamic batch size: ~{avg_tokens_per_row:.0f} tok/row, "
        f"budget={budget} tok → {rows} rows/batch"
    )
    return rows


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


# Keywords that signal the user wants NLP-based column processing
_NLP_INTENT_KEYWORDS = [
    # Classification
    "classify", "categorize", "categorise", "category", "categories",
    "classification", "reclassify", "subcategor",
    # Labeling / Tagging
    "tag", "label", "annotate", "mark as",
    # Sentiment / Opinion
    "sentiment", "positive negative", "opinion", "tone",
    # Intent / Topic
    "intent", "extract intent", "topic", "theme",
    "group by meaning", "group by type",
    # Text Analysis
    "analyze text", "analyse text", "analyze each",
    "nlp", "language", "interpret",
    "summarize", "summarise",
    # Common request phrasings
    "assign a type", "determine the type", "identify the type",
    "bucket", "cluster", "segment",
    "priority", "severity", "urgency",
]


def _validate_nlp_plan(
    user_request: str,
    plan,
    nlp_columns: list,
) -> None:
    """
    Warn (and auto-fix) when the user clearly wants NLP columns but the
    planner didn't generate any.

    Scans the user request for NLP-intent keywords. If found and the plan
    has zero nlp: columns, converts non-SQL columns (those whose name
    suggests classification/categorization) to nlp: sources.
    """
    request_lower = user_request.lower()
    has_nlp_intent = any(kw in request_lower for kw in _NLP_INTENT_KEYWORDS)

    if not has_nlp_intent or nlp_columns:
        return  # Either no NLP intent, or plan already has NLP columns — nothing to do

    print(
        "[ExcelSkill] WARNING: User request mentions NLP "
        f"({[kw for kw in _NLP_INTENT_KEYWORDS if kw in request_lower]}) "
        "but plan has 0 nlp: columns. Attempting auto-fix..."
    )

    # Find columns that are marked 'sql' but don't exist in any source_query
    # These are likely the ones the planner should have marked as nlp:
    for sheet in plan.sheets:
        sql_cols = set()
        if sheet.source_query:
            # Quick parse: extract column names/aliases from SELECT clause
            select_part = sheet.source_query.upper().split("FROM")[0] if "FROM" in sheet.source_query.upper() else ""
            sql_cols = {
                tok.strip().lower()
                for tok in select_part.replace("SELECT", "").split(",")
                if tok.strip()
            }
            # Also capture aliases: "col AS alias"
            for tok in select_part.replace("SELECT", "").split(","):
                parts = tok.strip().split()
                if len(parts) >= 3 and parts[-2].upper() == "AS":
                    sql_cols.add(parts[-1].strip().lower())

        for col in sheet.columns:
            if col.source != "sql":
                continue
            col_lower = col.name.strip().lower()
            # Check if this column name exists in the SQL result
            col_in_sql = any(col_lower in s for s in sql_cols) if sql_cols else False
            if col_in_sql:
                continue
            # This column is marked 'sql' but doesn't exist in the query — convert to nlp:
            # Use the original user request for a specific instruction
            col.source = (
                f"nlp:{user_request.strip()} — "
                f"produce a value for the '{col.name}' column"
            )
            print(
                f"[ExcelSkill] Auto-fixed column '{col.name}' on sheet "
                f"'{sheet.sheet_name}': sql → {col.source}"
            )


async def generate_excel(
    user_request: str,
    user_id: str,
    thread_id: str,
    source_doc_ids: Optional[List[str]] = None,
    prior_sql_query: Optional[str] = None,
    original_user_query: Optional[str] = None,
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
        original_user_query: The verbatim user query before the generate LLM
            rephrased it into ``user_request``.  Used for NLP-intent detection
            so that keywords like "classify" / "categorize" are not lost.
    """
    # ── 1. Gather data sources ──
    _ensure_sqlite_loaded(user_id, thread_id)
    schema = SQLiteManager.get_schema(user_id, thread_id)
    doc_info = get_document_info(user_id, thread_id, source_doc_ids)

    # ── 2. LLM: generate plan ──
    # If the original user query differs from the (possibly rephrased)
    # user_request, prepend it so the planner sees NLP-intent keywords.
    planner_request = user_request
    if original_user_query and original_user_query.strip().lower() != user_request.strip().lower():
        planner_request = f"{original_user_query}\n\n(Detail: {user_request})"

    plan = await generate_excel_plan(
        user_request=planner_request,
        available_schema=schema,
        available_documents=doc_info if doc_info else None,
        prior_sql_query=prior_sql_query,
    )

    # Log NLP column detection
    nlp_columns = [
        (sheet.sheet_name, col.name, col.source)
        for sheet in plan.sheets
        for col in sheet.columns
        if col.source.startswith("nlp:")
    ]
    print(
        f"[ExcelSkill] Plan: {plan.file_name} — "
        f"{len(plan.sheets)} sheet(s), "
        f"charts={'yes' if plan.charts else 'no'}, "
        f"summary={plan.summary_sheet}, "
        f"nlp_columns={len(nlp_columns)}"
    )
    if nlp_columns:
        for sheet_name, col_name, source in nlp_columns:
            print(f"[ExcelSkill] NLP column: [{sheet_name}] {col_name} → {source}")

    # ── 2b. Validate: detect NLP intent in request but missing NLP columns ──
    # Use the original user query (before the generate LLM rephrased it)
    # so NLP-intent keywords like "classify" / "categorize" are preserved.
    nlp_check_text = original_user_query or user_request
    _validate_nlp_plan(nlp_check_text, plan, nlp_columns)

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
                    original_user_query=original_user_query or user_request,
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


# ─── NLP Column Processing ─────────────────────────────────────────────


async def _process_nlp_column(
    df: pd.DataFrame,
    column_name: str,
    instruction: str,
    original_user_query: str = "",
) -> pd.DataFrame:
    """
    Process an NLP column by sending data to the LLM.

    Routing:
      - Tiny datasets (≤NLP_BRUTE_FORCE_MAX rows AND unique values) use the
        brute-force approach: batch all rows through the LLM sequentially.
      - Everything else uses the smart pipeline: deduplicate → discover
        taxonomy → apply keyword rules → parallel LLM fallback.
    """
    if df.empty:
        df[column_name] = []
        return df

    if len(df.columns) == 0:
        df[column_name] = "N/A"
        return df

    # Estimate unique text values to decide routing
    source_col = _identify_source_column(df, instruction)
    unique_count = df[source_col].fillna("").astype(str).str.strip().nunique()

    # Both total rows AND unique values must be small for brute-force
    if len(df) <= NLP_BRUTE_FORCE_MAX and unique_count <= NLP_BRUTE_FORCE_MAX:
        print(
            f"[ExcelSkill:nlp] Column '{column_name}': {len(df)} rows, "
            f"{unique_count} unique — using brute-force pipeline"
        )
        return await _process_nlp_column_brute(df, column_name, instruction)

    print(
        f"[ExcelSkill:nlp] Column '{column_name}': {len(df)} rows, "
        f"{unique_count} unique — using smart taxonomy pipeline"
    )
    return await _process_nlp_column_smart(
        df, column_name, instruction, original_user_query, source_col
    )


async def _process_nlp_column_brute(
    df: pd.DataFrame,
    column_name: str,
    instruction: str,
) -> pd.DataFrame:
    """Original brute-force NLP pipeline: batch all rows through the LLM."""
    input_data = _rows_to_strings(df)
    batch_size = _estimate_nlp_batch_size(input_data)
    total_batches = (len(input_data) + batch_size - 1) // batch_size

    all_values = []
    for batch_start in range(0, len(input_data), batch_size):
        batch = input_data[batch_start : batch_start + batch_size]
        batch_idx = batch_start // batch_size + 1

        print(
            f"[ExcelSkill:nlp] Column '{column_name}': "
            f"batch {batch_idx}/{total_batches} ({len(batch)} rows)"
        )

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
            print(f"[ExcelSkill:nlp] Batch {batch_idx} error: {e}")
            all_values.extend(["Error"] * len(batch))

    df[column_name] = all_values[: len(df)]
    return df


# ─── Smart NLP Pipeline (Taxonomy-Based) ───────────────────────────────


async def _process_nlp_column_smart(
    df: pd.DataFrame,
    column_name: str,
    instruction: str,
    original_user_query: str = "",
    source_col: Optional[str] = None,
) -> pd.DataFrame:
    """
    Smart NLP pipeline: dedup → taxonomy → keyword rules → parallel fallback.

    Steps:
      1. Identify the best source column (most text content)
      2. Deduplicate values
      3. Sample ~200 values → LLM discovers taxonomy with keyword rules
      4. Apply rules deterministically via word-boundary keyword matching
      5. Batch remaining unclassified values through LLM (in parallel)
      6. Map results back to all rows
    """
    # Step 1: Identify source column (may already be resolved by caller)
    if source_col is None:
        source_col = _identify_source_column(df, instruction)
    print(f"[ExcelSkill:smart_nlp] Source column: '{source_col}'")

    # Step 2: Deduplicate
    raw_values = df[source_col].fillna("").astype(str).str.strip()
    unique_values = raw_values.drop_duplicates().tolist()
    # Remove empty strings
    unique_values = [v for v in unique_values if v]

    print(
        f"[ExcelSkill:smart_nlp] {len(df)} rows → "
        f"{len(unique_values)} unique values in '{source_col}'"
    )

    if not unique_values:
        df[column_name] = "N/A"
        return df

    # Step 3: Taxonomy discovery
    sample_size = min(TAXONOMY_SAMPLE_SIZE, len(unique_values))
    sample_series = pd.Series(unique_values).sample(sample_size, random_state=42)
    sample = sample_series.tolist()

    print(
        f"[ExcelSkill:smart_nlp] Discovering taxonomy from "
        f"{len(sample)} sample values..."
    )

    taxonomy = await _discover_taxonomy(
        sample, instruction, column_name, original_user_query
    )
    print(
        f"[ExcelSkill:smart_nlp] Discovered {len(taxonomy.categories)} categories: "
        f"{', '.join(c.label for c in taxonomy.categories)}"
    )

    # Step 3.5: Pre-compile keyword patterns (word-boundary aware)
    compiled_patterns = _compile_taxonomy_patterns(taxonomy)

    # Step 4: Apply rules deterministically
    classified: Dict[str, str] = {}
    unclassified: List[str] = []

    for val in unique_values:
        label = _apply_taxonomy_rules(val, taxonomy, compiled_patterns)
        if label:
            classified[val] = label
        else:
            unclassified.append(val)

    rule_pct = len(classified) / len(unique_values) * 100 if unique_values else 0
    print(
        f"[ExcelSkill:smart_nlp] Rule-based classification: "
        f"{len(classified)}/{len(unique_values)} ({rule_pct:.0f}%) classified, "
        f"{len(unclassified)} remaining"
    )

    # Step 5: LLM fallback for unclassified (parallel)
    if unclassified:
        category_labels = [c.label for c in taxonomy.categories]
        fallback_results = await _parallel_nlp_classify(
            values=unclassified,
            instruction=instruction,
            column_name=column_name,
            category_labels=category_labels,
            original_user_query=original_user_query,
        )
        classified.update(fallback_results)

    # Step 6: Map back to full DataFrame
    df[column_name] = raw_values.map(classified).fillna("Uncategorized")

    # Log final stats
    value_counts = df[column_name].value_counts()
    top_cats = value_counts.head(5).to_dict()
    print(
        f"[ExcelSkill:smart_nlp] Column '{column_name}' complete — "
        f"top categories: {top_cats}"
    )

    return df


# Column names that typically contain free-text content
_TEXT_COLUMN_HINTS = [
    "description", "summary", "comment", "note", "detail",
    "text", "content", "message", "body", "title", "subject",
    "feedback", "review", "issue", "ticket", "report",
]


def _identify_source_column(df: pd.DataFrame, instruction: str = "") -> str:
    """
    Find the best source column for NLP processing.

    Strategy (in priority order):
      1. If the instruction explicitly mentions a column name that exists
         in the DataFrame, use it.
      2. If a column name matches a known text-content hint (e.g.
         'description', 'summary', 'comment'), prefer it.
      3. Fall back to the column with the longest average string length.
    """
    col_names_lower = {col.lower().strip(): col for col in df.columns}
    instruction_lower = instruction.lower()

    # Strategy 1: Instruction mentions a column name explicitly
    # Check longest names first to avoid "Issue" matching before "Issue Description"
    sorted_cols = sorted(col_names_lower.keys(), key=len, reverse=True)
    for col_lower in sorted_cols:
        if len(col_lower) >= 3 and col_lower in instruction_lower:
            return col_names_lower[col_lower]

    # Strategy 2: Known text-content column name hints
    for hint in _TEXT_COLUMN_HINTS:
        for col_lower, col_original in col_names_lower.items():
            if hint in col_lower:
                try:
                    avg_len = df[col_original].dropna().astype(str).str.len().mean()
                    if avg_len > 20:
                        return col_original
                except Exception:
                    continue

    # Strategy 3: Longest average string length (original heuristic)
    best_col = df.columns[0]
    best_avg_len = 0.0

    for col in df.columns:
        try:
            str_series = df[col].dropna().astype(str)
            if str_series.empty:
                continue
            avg_len = str_series.str.len().mean()
            if avg_len > best_avg_len:
                best_avg_len = avg_len
                best_col = col
        except Exception:
            continue

    return best_col


async def _discover_taxonomy(
    sample_values: List[str],
    instruction: str,
    column_name: str,
    original_user_query: str = "",
) -> TaxonomyResult:
    """
    Ask the LLM to discover a classification taxonomy from sample values.

    Returns a TaxonomyResult with categories and keyword rules.
    """
    prompt = excel_taxonomy_discovery_prompt(
        sample_values=sample_values,
        instruction=instruction,
        column_name=column_name,
        user_context=original_user_query,
    )

    result = await invoke_llm(
        gpu_model=GPU_EXCEL_NLP_LLM.model,
        response_schema=TaxonomyResult,
        contents=prompt,
        port=GPU_EXCEL_NLP_LLM.port,
    )

    return TaxonomyResult.model_validate(result)


def _compile_taxonomy_patterns(
    taxonomy: TaxonomyResult,
) -> List[tuple]:
    """
    Pre-compile keyword patterns for each category.

    Single-word keywords use word boundaries (``\\b``) so "bug" won't match
    "debugging".  Multi-word phrases use plain substring matching since
    words already provide natural boundaries.

    Returns list of ``(category_label, compiled_pattern)`` tuples,
    preserving the taxonomy's category order (most frequent first).
    """
    compiled: List[tuple] = []
    for category in taxonomy.categories:
        patterns: List[str] = []
        for kw in category.keywords:
            kw_lower = kw.lower().strip()
            if not kw_lower:
                continue
            if " " in kw_lower:
                # Multi-word phrase: match as-is
                patterns.append(re.escape(kw_lower))
            else:
                # Single word: word boundaries prevent partial matches
                patterns.append(r"\b" + re.escape(kw_lower) + r"\b")
        if patterns:
            combined = re.compile("|".join(patterns), re.IGNORECASE)
            compiled.append((category.label, combined))
    return compiled


def _apply_taxonomy_rules(
    value: str,
    taxonomy: TaxonomyResult,
    compiled_patterns: Optional[List[tuple]] = None,
) -> Optional[str]:
    """
    Try to classify a value using the taxonomy's keyword rules.

    When *compiled_patterns* is provided (pre-compiled via
    ``_compile_taxonomy_patterns``), uses regex with word boundaries for
    single-word keywords.  Falls back to simple substring matching when
    patterns are ``None``.

    Returns the category label if any keywords match, or ``None``.
    Checks categories in order (most frequent first) — first match wins.
    """
    value_lower = value.lower()

    if compiled_patterns:
        for label, pattern in compiled_patterns:
            if pattern.search(value_lower):
                return label
        return None

    # Fallback: original substring matching
    for category in taxonomy.categories:
        for keyword in category.keywords:
            if keyword.lower() in value_lower:
                return category.label

    return None


async def _parallel_nlp_classify(
    values: List[str],
    instruction: str,
    column_name: str,
    category_labels: List[str],
    original_user_query: str = "",
) -> Dict[str, str]:
    """
    Classify values through the LLM in parallel batches.

    Uses the discovered taxonomy labels to ensure consistency —
    the LLM must pick from the known category labels.
    """
    results: Dict[str, str] = {}
    sem = asyncio.Semaphore(NLP_PARALLEL_CONCURRENCY)

    batch_size = _estimate_nlp_batch_size(values)
    batches = [
        values[i : i + batch_size]
        for i in range(0, len(values), batch_size)
    ]
    total_batches = len(batches)

    print(
        f"[ExcelSkill:smart_nlp] LLM fallback: {len(values)} values "
        f"in {total_batches} batch(es) (~{batch_size}/batch), "
        f"concurrency={NLP_PARALLEL_CONCURRENCY}"
    )

    async def _classify_batch(
        batch: List[str], batch_idx: int
    ) -> Dict[str, str]:
        async with sem:
            print(
                f"[ExcelSkill:smart_nlp] Fallback batch "
                f"{batch_idx}/{total_batches} ({len(batch)} values)"
            )
            try:
                prompt = excel_nlp_fallback_prompt(
                    values=batch,
                    instruction=instruction,
                    column_name=column_name,
                    category_labels=category_labels,
                    user_context=original_user_query,
                )

                result = await invoke_llm(
                    gpu_model=GPU_EXCEL_NLP_LLM.model,
                    response_schema=NLPColumnResult,
                    contents=prompt,
                    port=GPU_EXCEL_NLP_LLM.port,
                )
                result = NLPColumnResult.model_validate(result)

                # Ensure correct length
                result_values = result.values
                if len(result_values) < len(batch):
                    result_values.extend(
                        ["Uncategorized"] * (len(batch) - len(result_values))
                    )
                elif len(result_values) > len(batch):
                    result_values = result_values[: len(batch)]

                return dict(zip(batch, result_values))

            except Exception as e:
                print(f"[ExcelSkill:smart_nlp] Fallback batch {batch_idx} error: {e}")
                return {val: "Uncategorized" for val in batch}

    batch_results = await asyncio.gather(
        *[_classify_batch(batch, idx + 1) for idx, batch in enumerate(batches)]
    )

    for batch_map in batch_results:
        results.update(batch_map)

    return results
