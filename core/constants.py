from pydantic import BaseModel

# Ollama model name for local deployment
OLLAMA_MODEL = "qwen3:4b"

# SETTINGS
SWITCHES = {
    "MIND_MAP": False,  # For long documents, mind map will be better if SUMMARIZATION = True
    "SUMMARIZATION": False,
    "FALLBACK_TO_GEMINI": False,  # Fallback to Gemini if Ollama fails
    "FALLBACK_TO_OPENAI": False,  # Fallback to OpenAI if BOTH Ollama and Gemini fails
}

PORT = 11434


class GPULLMConfig(BaseModel):
    model: str
    port: int


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
SUMMARIZER_LLM = "gemini-2.0-flash"
QUERY_LLM = "gemini-2.5-flash"
DECOMPOSITION_LLM = "gemini-2.0-flash"
COMBINATION_LLM = "gemini-2.0-flash"
NODE_GENERATION_LLM = "gemini-2.5-flash"
NODE_DESCRIPTION_LLM = "gemini-2.0-flash"
STOP_WORDS_EXTRACTION_LLM = "gemini-2.5-flash"
IMAGE_PARSER_LLM = "gemma-lat:latest"


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
