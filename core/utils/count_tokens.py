import tiktoken

map = {
    "qwen3:14b": "cl100k_base",
    "qwen3:8b": "cl100k_base",
    "qwen3:4b": "cl100k_base",
    "gpt-oss:20b": "o200k_harmony",
    "gpt-oss:20b-50k-8k": "o200k_harmony",
}


def count_tokens(text: str, gpu_model: str = "gpt-oss:20b") -> int:
    encoding = tiktoken.get_encoding(map.get(gpu_model, "o200k_harmony"))
    return len(encoding.encode(text))
