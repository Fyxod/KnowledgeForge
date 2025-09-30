from core.models.gpu_config import GPULLMConfig

# Ollama model name for local deployment
OLLAMA_MODEL = "qwen3:4b"

# SETTINGS
SWITCHES = {
    "MIND_MAP": False,  # For long documents, mind map will be better if SUMMARIZATION = True
    # For Cpu based testing we suggest to keep both False to avoid much load on CPU
    "SUMMARIZATION": False,  # Summary is used by model to get a general idea of the document and for generation of nodes in mind map
    "FALLBACK_TO_GEMINI": False,  # Fallback to Gemini if Ollama fails
    "FALLBACK_TO_OPENAI": False,  # Fallback to OpenAI if BOTH Ollama and Gemini fails
    "DECOMPOSITION": False,  # Decomposition of query into sub-queries if applicable.
}

PORT = 11434  # Default port for Ollama API


# GPU LLM configurations
GPU_QUERY_LLM = GPULLMConfig(model=OLLAMA_MODEL, port=PORT)
GPU_QUERY_LLM2 = GPULLMConfig(model=OLLAMA_MODEL, port=PORT)
GPU_DECOMPOSITION_LLM = GPULLMConfig(model=OLLAMA_MODEL, port=PORT)
GPU_COMBINATION_LLM = GPULLMConfig(model=OLLAMA_MODEL, port=PORT)
GPU_DOC_SUMMARIZER_LLM = GPULLMConfig(model=OLLAMA_MODEL, port=PORT)
GPU_GLOBAL_SUMMARIZER_LLM = GPULLMConfig(model=OLLAMA_MODEL, port=PORT)
GPU_STOP_WORDS_EXTRACTION_LLM = GPULLMConfig(model=OLLAMA_MODEL, port=PORT)
GPU_NODE_GENERATION_LLM = GPULLMConfig(model=OLLAMA_MODEL, port=PORT)
GPU_NODE_DESCRIPTION_LLM = GPULLMConfig(model=OLLAMA_MODEL, port=PORT)

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