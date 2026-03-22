import tiktoken

map = {
    "qwen3:14b": "cl100k_base",
    "qwen3:8b": "cl100k_base",
    "qwen3:4b": "cl100k_base",
    "gpt-oss:20b": "o200k_base",
    "gpt-oss:20b-50k-8k": "o200k_base",
    # Qwen3.5-9B (vLLM unified mode) — uses its own BPE, cl100k_base is the
    # closest available tiktoken encoding (both are byte-level BPE, ~10% variance).
    "Qwen/Qwen3.5-9B": "cl100k_base",
    "cyankiwi/Qwen3.5-9B-AWQ-4bit": "cl100k_base",
}


def count_tokens(text: str, gpu_model: str = "gpt-oss:20b") -> int:
    encoding_name = map.get(gpu_model, "o200k_base")
    try:
        encoding = tiktoken.get_encoding(encoding_name)
    except ValueError:
        print(f"Warning: Unknown tiktoken encoding {encoding_name}, falling back to cl100k_base")
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))
