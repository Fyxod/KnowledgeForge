import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.parsers.excel_utils import find_header_row, enrich_dataframe_with_metadata
import pandas as pd
import os

TEST_FILE = "dirty_test.xlsx"
SHEET_NAME = "Sales_Data_Q1"

if not os.path.exists(TEST_FILE):
    print(f"Error: {TEST_FILE} not found. Run generate_test_excel.py first.")
    exit(1)

print(f"--- Analyzing {TEST_FILE} ---")
header_idx, context = find_header_row(TEST_FILE, SHEET_NAME)
print(f"Detected Header Row Index: {header_idx}")
print(f"Context Found:\n{context}")

print("\n--- Reading DataFrame with Detected Header ---")
# header=header_idx means row 'header_idx' is the header.
df = pd.read_excel(TEST_FILE, sheet_name=SHEET_NAME, header=header_idx, engine='openpyxl')
print("Initial Columns:", df.columns.tolist())
print("First few rows:")
print(df.head(3))

print("\n--- Enriching with Metadata (Colors/Comments) ---")
# Note: enrich function requires openpyxl to re-propagate metadata
# We need to implement the enrich function fully first (I mocked it in the artifact).
# Let's check if the one I wrote is importable and runnable.

try:
    # Creating a dummy Workbook for enrichment logic if needed, or just calling the util
    # My excel_utils.py has the implementation, let's call it.
    
    # We need to implement the logic inside enrich_dataframe_with_metadata to actually read the cells
    # The artifact I wrote had the logic in it.
    
    df_enriched = enrich_dataframe_with_metadata(df, TEST_FILE, SHEET_NAME, header_idx)
    print("Enriched Data Sample (Row 3, Col 4 'Revenue' should have comment):")
    # Row 3 in 0-indexed DF is index 2.
    # Data is:
    # 0: 101, Widget A...
    # 1: 102, Widget B...
    # 2: 103, Gadget X... (Revenue 8100 has comment)
    
    # Let's print the specific cell if possible
    if len(df_enriched) > 2 and "Revenue" in df_enriched.columns:
        print(f"Revenue Value at Index 2: {df_enriched.at[2, 'Revenue']}")
        
    print("\n--- Full Enriched DataFrame ---")
    print(df_enriched.to_string())

except Exception as e:
    print(f"Enrichment failed: {e}")
    import traceback
    traceback.print_exc()
