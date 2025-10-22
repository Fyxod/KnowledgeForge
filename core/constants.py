from core.models.ollama_config import OllamaLLMConfig

# Ollama model name for local deployment
OLLAMA_MODEL = "qwen3:8b"

# SETTINGS
SWITCHES = {
    "MIND_MAP": False,  # For long documents, mind map will be better if SUMMARIZATION = True
    # For Cpu based testing we suggest to keep both False to avoid much load on CPU
    "SUMMARIZATION": False,  # Summary is used by model to get a general idea of the document and for generation of nodes in mind map
    "FALLBACK_TO_GEMINI": False,  # Fallback to Gemini if Ollama fails
    "FALLBACK_TO_OPENAI": False,  # Fallback to OpenAI if BOTH Ollama and Gemini fails
    "DECOMPOSITION": False,  # Decomposition of query into sub-queries if applicable.
}
CHUNK_COUNT = 6 # Number of chunks to retrieve from vector DB for each query

PORT = 11434  # Default port for Ollama API


# Ollama LLM configurations
Ollama_QUERY_LLM = OllamaLLMConfig(model=OLLAMA_MODEL, port=PORT)
Ollama_QUERY_LLM2 = OllamaLLMConfig(model=OLLAMA_MODEL, port=PORT)
Ollama_DECOMPOSITION_LLM = OllamaLLMConfig(model=OLLAMA_MODEL, port=PORT)
Ollama_COMBINATION_LLM = OllamaLLMConfig(model=OLLAMA_MODEL, port=PORT)
Ollama_DOC_SUMMARIZER_LLM = OllamaLLMConfig(model=OLLAMA_MODEL, port=PORT)
Ollama_GLOBAL_SUMMARIZER_LLM = OllamaLLMConfig(model=OLLAMA_MODEL, port=PORT)
Ollama_STOP_WORDS_EXTRACTION_LLM = OllamaLLMConfig(model=OLLAMA_MODEL, port=PORT)
Ollama_NODE_GENERATION_LLM = OllamaLLMConfig(model=OLLAMA_MODEL, port=PORT)
Ollama_NODE_DESCRIPTION_LLM = OllamaLLMConfig(model=OLLAMA_MODEL, port=PORT)

IMAGE_PARSER_LLM = "gemma3:12b"
# Fallback LLM models
# Used if SWITCHES["FALLBACK_TO_GEMINI"] = True
FALLBACK_GEMINI_MODEL = "gemini-2.0-flash"

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
