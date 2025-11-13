from core.models.gpu_config import GPULLMConfig
from core.config import settings

# SETTINGS
SWITCHES = {
    "MIND_MAP": True,  # For long documents, mind map will be better if SUMMARIZATION = True
    # For Cpu based testing we suggest to keep both False to avoid much load on CPU
    "SUMMARIZATION": True,  # Summary is used by model to get a general idea of the document and for generation of nodes in mind map
    "FALLBACK_TO_GEMINI": False,  # Fallback to Gemini if Ollama fails
    "FALLBACK_TO_OPENAI": False,  # Fallback to OpenAI if BOTH Ollama and Gemini fails
    "DECOMPOSITION": True,  # Decomposition of query into sub-queries. This also serves as rewriting the query according to the context of the previous chat history.
                            # This can be turned off if all the queries are independent and do not need context from previous chats.

    "REMOTE_GPU": settings.REMOTE_GPU,  # Use remote GPU LLMs
    # please refer to core/Setup_Local_ollama.md for setting up local LLM server
}
CHUNK_COUNT = 12  # Number of chunks to retrieve from vector DB for each query

PORT1 = 11434  # port where ollama is running
PORT2 = 11435  # port where second ollama instance is running

GPT_OSS_20B = "gpt-oss:20b-50k-8k"
QWEN3_14B = "qwen3:14b-39500-8k"

# GPU LLM configurations
GPU_QUERY_LLM = GPULLMConfig(model=GPT_OSS_20B, port=PORT2)
GPU_QUERY_LLM2 = GPULLMConfig(model=GPT_OSS_20B, port=PORT1)
GPU_DECOMPOSITION_LLM = GPULLMConfig(model=GPT_OSS_20B, port=PORT2)
GPU_COMBINATION_LLM = GPULLMConfig(model=GPT_OSS_20B, port=PORT2)
GPU_DOC_SUMMARIZER_LLM = GPULLMConfig(model=GPT_OSS_20B, port=PORT1)
GPU_GLOBAL_SUMMARIZER_LLM = GPULLMConfig(model=GPT_OSS_20B, port=PORT1)
GPU_STOP_WORDS_EXTRACTION_LLM = GPULLMConfig(model=GPT_OSS_20B, port=PORT1)
GPU_NODE_GENERATION_LLM = GPULLMConfig(model=GPT_OSS_20B, port=PORT1)
GPU_NODE_DESCRIPTION_LLM = GPULLMConfig(model=GPT_OSS_20B, port=PORT1)
GPU_STRATEGIC_ROADMAP_LLM = GPULLMConfig(model=GPT_OSS_20B, port=PORT1)
GPU_TECHNICAL_ROADMAP_LLM = GPULLMConfig(model=GPT_OSS_20B, port=PORT1)
GPU_INSIGHTS_LLM = GPULLMConfig(model=GPT_OSS_20B, port=PORT1)

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
SELF_KNOWLEDGE = "self_knowledge"
MAX_WEB_SEARCH = 2
INTERNAL = "Internal"
EXTERNAL = "External"
