import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from core.parsers.main import extract_document
    print("Successfully imported core.parsers.main.extract_document")
except ImportError as e:
    print(f"ImportError: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Exception: {e}")
    sys.exit(1)
