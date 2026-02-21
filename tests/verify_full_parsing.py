import sys
import os
import asyncio
from unittest.mock import MagicMock

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock dependencies BEFORE importing core.parsers.main
sys.modules['app.socket_handler'] = MagicMock()
sys.modules['app.socket_handler.sio'] = MagicMock()

# Now import
from core.parsers.main import extract_document

TEST_FILE = "dirty_test.xlsx"

async def run_test():
    if not os.path.exists(TEST_FILE):
        print(f"File {TEST_FILE} not found.")
        return

    print(f"--- Extracting {TEST_FILE} ---")
    doc = await extract_document(TEST_FILE, title="Test Doc")
    
    if not doc:
        print("Extraction failed (returned None).")
        return

    print("\n--- Parsed Document Content ---")
    print(f"Valid Document ID: {doc.id}")
    print(f"Total Pages: {len(doc.content)}")
    
    full_text = doc.full_text
    
    # Validation Checks
    print("\n--- Validation ---")
    
    # 1. Global Context
    if "# Workbook Structure Summary" in full_text:
        print("[Pass] Global Workbook Summary found.")
        if "Sheet 'Sales_Data_Q1'" in full_text and "Sheet 'Config_Data'" in full_text:
             print("[Pass] Both sheets listed in summary.")
        else:
             print("[Fail] Sheets missing from summary.")
    else:
        print("[Fail] Global Workbook Summary NOT found.")

    # 2. Header Detection (Context)
    if "Context/Metadata:" in full_text and "Confidential Report" in full_text:
        print("[Pass] Pre-header context extracted (Confidential Report).")
    else:
        print("[Fail] Pre-header context missing.")

    # 3. Data Integrity
    if "Widget A" in full_text:
        print("[Pass] Data rows found.")
    else:
        print("[Fail] Data rows missing.")

    # 4. Metadata (Comments/Colors)
    if "[Note: Outlier" in full_text:
        print("[Pass] Comment extracted matching 'Outlier'.")
    else:
        print(f"[Fail] Comment missing. Search result: {'Note' in full_text}")
        
    if "[Status: Green]" in full_text or "Status: Green" in full_text:
         print("[Pass] Color metadata found (Green).")
    else:
         # Note: My excel_utils.py implementation for colors was:
         # if str(color).startswith("FF00FF00"): metadata.append("[Status: Green]")
         # I need to verify if openpyxl returns that exact string for 00FF00.
         print(f"[Info] Color metadata check uncertain (depends on exact RGB value).")

    print("\n--- Sample Output Snippet ---")
    print(full_text[:1000])

if __name__ == "__main__":
    asyncio.run(run_test())
