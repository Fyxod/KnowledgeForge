from core.models.gpu_config import GPULLMConfig

SWITCHES = {
    "MIND_MAP": True,  # For long documents, mind map will be better if SUMMARIZATION = True
    # For Cpu based testing we suggest to keep both False to avoid much load on CPU
    "SUMMARIZATION": True,  # Summary is used by model to get a general idea of the document and for generation of nodes in mind map
    "FALLBACK_TO_GEMINI": True,  # Fallback to Gemini if Ollama fails
    "FALLBACK_TO_OPENAI": True,  # Fallback to OpenAI if BOTH Ollama and Gemini fails
}


PORT1 = 11434
PORT2 = 11435

GPT_OSS_20B = "gpt-oss:20b-50k-8k"
QWEN3_14B = "qwen3:14b-39500-8k"

# GPU LLM configurations
GPU_QUERY_LLM = GPULLMConfig(model=GPT_OSS_20B, port=PORT2)
GPU_QUERY_LLM2 = GPULLMConfig(model=GPT_OSS_20B, port=PORT1)
GPU_DECOMPOSITION_LLM = GPULLMConfig(model=GPT_OSS_20B, port=PORT2)
GPU_COMBINATION_LLM = GPULLMConfig(model=GPT_OSS_20B, port=PORT2)
GPU_DOC_SUMMARIZER_LLM = GPULLMConfig(model=QWEN3_14B, port=PORT1)
GPU_GLOBAL_SUMMARIZER_LLM = GPULLMConfig(model=QWEN3_14B, port=PORT1)
GPU_STOP_WORDS_EXTRACTION_LLM = GPULLMConfig(model=GPT_OSS_20B, port=PORT2)
GPU_NODE_GENERATION_LLM = GPULLMConfig(model=GPT_OSS_20B, port=PORT2)
GPU_NODE_DESCRIPTION_LLM = GPULLMConfig(model=QWEN3_14B, port=PORT1)

# Fallback LLM models
# Used if SWITCHES["FALLBACK_TO_GEMINI"] = True
SUMMARIZER_LLM = "gemini-2.0-flash"
QUERY_LLM = "gemini-2.5-flash"
DECOMPOSITION_LLM = "gemini-2.0-flash"
COMBINATION_LLM = "gemini-2.0-flash"
NODE_GENERATION_LLM = "gemini-2.5-flash"
NODE_DESCRIPTION_LLM = "gemini-2.0-flash"
STOP_WORDS_EXTRACTION_LLM = "gemini-2.5-flash"
IMAGE_PARSER_LLM = "gemma-lat:latest"

# Used if SWITCHES["FALLBACK_TO_OPENAI"] = True
FALLBACK_OPENAI_MODEL = "gpt-4o-mini"

# Graph constants used in agent
RETRIEVER = "retriever"
GENERATE = "generate"
WEB_SEARCH = "web_search"
ANSWER = "answer"
ROUTER = "router"
FAILURE = "failure"
GLOBAL_SUMMARIZER = "global_summarizer"
DOCUMENT_SUMMARIZER = "document_summarizer"
MAX_WEB_SEARCH = 2
INTERNAL = "Internal"
EXTERNAL = "External"
