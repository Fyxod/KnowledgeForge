import os
import sys
import re
from langchain_ollama import ChatOllama

# Add the project directory to path so we can import internal modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.utils.llm_output_sanitizer import sanitize_llm_json
from core.config import settings
from core.constants import PORT1

def run_llm_test(model_name: str, port: int):
    print(f"\n{'='*70}")
    print(f" TESTING MODEL : {model_name} on Port {port}")
    print(f"{'='*70}\n")
    
    try:
        # 1. Initialize the client exactly as in core.llm.configurations.local_llm.MyServerLLM
        base_url = f"{settings.LOCAL_BASE_URL}:{port}"
        print(f"[*] Initializing ChatOllama client for {model_name} at {base_url}...")
        client = ChatOllama(
            model=model_name,
            base_url=base_url,
            timeout=1000
        )
        
        # 2. Define a prompt asking for JSON
        prompt = """
        Please provide a short JSON response containing the following information about the capital of France.
        Your response MUST be exclusively valid JSON. Do not include any other text, markdown formatting, or explanations.
        
        Schema:
        {
            "capital": "string",
            "population": "number"
        }
        """
        print("\n[PROMPT]")
        print(prompt.strip())
        
        # 3. Call the model
        print("\n[*] Sending request to model (this may take a moment)...")
        response = client.invoke(prompt)
        
        raw_output = response.content
        print("\n[RAW LLM OUTPUT]")
        print("-" * 50)
        print(raw_output)
        print("-" * 50)
        
        # 4. Apply regex cleaning exactly as in local_llm.py
        print("\n[*] Applying Regex Cleaners (stripping <think> and <reasoning> tags)...")
        cleaned_text = re.sub(r"<think>.*?</think>", "", raw_output, flags=re.DOTALL)
        cleaned_text = re.sub(r"<reasoning>.*?</reasoning>", "", cleaned_text, flags=re.DOTALL)
        cleaned_text = cleaned_text.strip()
        
        print("\n[POST-REGEX CLEANED OUTPUT]")
        print("-" * 50)
        print(cleaned_text)
        print("-" * 50)
        
        # 5. Apply JSON sanitization from llm_output_sanitizer.py
        print("\n[*] Applying JSON Sanitizer (core.utils.llm_output_sanitizer.sanitize_llm_json)...")
        sanitized_json_str = sanitize_llm_json(cleaned_text)
        
        print("\n[FINAL EXTRACTED JSON STRING]")
        print("-" * 50)
        print(sanitized_json_str)
        print("-" * 50)
        
        print(f"\n[SUCCESS] Test completed for {model_name}.")
        
    except Exception as e:
        import traceback
        print(f"\n[ERROR] Failed to test {model_name}: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    print("WARNING: Make sure you have pulled BOTH models in Ollama before running this script.")
    print("Example: 'ollama pull gpt-oss:20b-50k-8k' and 'ollama pull qwen3.5:27b'\n")
    
    # Test our existing gpt-oss model (using PORT1 as default in constants)
    run_llm_test("gpt-oss:20b-50k-8k", port=PORT1)
    
    # Test qwen3.5:27b model
    run_llm_test("qwen3.5:27b", port=PORT1)
