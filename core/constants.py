from core.config import settings
from core.models.gpu_config import GPULLMConfig

# SETTINGS
SWITCHES = {
    "MIND_MAP": False,  # For long documents, mind map will be better if SUMMARIZATION = True
    # For Cpu based testing we suggest to keep both False to avoid much load on CPU
    "SUMMARIZATION": False,  # Summary is used by model to get a general idea of the document and for generation of nodes in mind map
    "FALLBACK_TO_GEMINI": False,  # Fallback to Gemini if Ollama fails
    "FALLBACK_TO_OPENAI": False,  # Fallback to OpenAI if BOTH Ollama and Gemini fails
    "DECOMPOSITION": True,  # Decomposition of query into sub-queries. This also serves as rewriting the query according to the context of the previous chat history.
    # This can be turned off if all the queries are independent and do not need context from previous chats.
    "REMOTE_GPU": settings.REMOTE_GPU,  # Use remote GPU LLMs
    # please refer to core/Setup_Local_ollama.md for setting up local LLM server
    "CORRECTIVE_RETRIEVAL": True,  # Phase 2.1: CRAG-style re-retrieval on low-confidence results
    "HYDE": False,  # Phase 2.3: Hypothetical Document Embeddings (adds ~2-5s query latency)
    "DOCUMENT_CREATOR": True,  # Interactive document generation (PPTX/DOCX/PDF)
}

CHUNK_COUNT = 12  # Number of chunks to retrieve from vector DB for each query

# Adaptive Retrieval Parameters
MIN_CHUNKS_PER_DOC = 10  # Minimum chunks to retrieve per document
MAX_TOTAL_CHUNKS = (
    50  # Reduced from 100: reranking selects best chunks, fewer = faster LLM generation
)


EASYOCR_WORKERS = (
    10  # Number of parallel workers for EasyOCR (adjust based on your CPU/GPU power)
)
TESSERACT_WORKERS = (
    50  # Number of parallel workers for Tesseract OCR (adjust based on your CPU power)
)
EASYOCR_GPU = (
    True  # GPU mode: ~4-7x faster OCR, uses only ~200MB VRAM (negligible on 48GB)
)

PORT1 = 11434  # port where ollama is running
PORT2 = 11435  # port where second ollama instance is running

MAIN_MODEL = (
    settings.MAIN_MODEL
)  # Set in .env file, e.g. "gpt-oss:20b-50k-8k" or "qwen3:14b-39500-8k"
# MAIN_MODEL = "gpt-oss:20b-50k-8k"
# QWEN3_14B = "qwen3:14b-39500-8k"

# GPU LLM configurations
GPU_QUERY_LLM = GPULLMConfig(model=MAIN_MODEL, port=PORT2)
GPU_QUERY_LLM2 = GPULLMConfig(model=MAIN_MODEL, port=PORT1)
GPU_DECOMPOSITION_LLM = GPULLMConfig(model=MAIN_MODEL, port=PORT2)
GPU_COMBINATION_LLM = GPULLMConfig(model=MAIN_MODEL, port=PORT2)
GPU_DOC_SUMMARIZER_LLM = GPULLMConfig(model=MAIN_MODEL, port=PORT1)
GPU_GLOBAL_SUMMARIZER_LLM = GPULLMConfig(model=MAIN_MODEL, port=PORT1)
GPU_STOP_WORDS_EXTRACTION_LLM = GPULLMConfig(model=MAIN_MODEL, port=PORT1)
GPU_NODE_GENERATION_LLM = GPULLMConfig(model=MAIN_MODEL, port=PORT1)
GPU_NODE_DESCRIPTION_LLM = GPULLMConfig(model=MAIN_MODEL, port=PORT1)
GPU_STRATEGIC_ROADMAP_LLM = GPULLMConfig(model=MAIN_MODEL, port=PORT1)
GPU_TECHNICAL_ROADMAP_LLM = GPULLMConfig(model=MAIN_MODEL, port=PORT1)
GPU_INSIGHTS_LLM = GPULLMConfig(model=MAIN_MODEL, port=PORT1)
GPU_STRATEGIC_ANALYSIS_LLM = GPULLMConfig(model=MAIN_MODEL, port=PORT1)
GPU_TECHNICAL_ANALYSIS_LLM = GPULLMConfig(model=MAIN_MODEL, port=PORT1)
GPU_EVALUATOR_LLM = GPULLMConfig(model=MAIN_MODEL, port=PORT1)  # CRAG evaluator
GPU_HYDE_LLM = GPULLMConfig(model=MAIN_MODEL, port=PORT1)  # HyDE hypothesis generation
GPU_ENTITY_PROFILE_LLM = GPULLMConfig(model=MAIN_MODEL, port=PORT1)  # Entity profile generation
GPU_TRIPLE_EXTRACTION_LLM = GPULLMConfig(model=MAIN_MODEL, port=PORT1)  # Triple extraction

# Document Creator LLM configurations
GPU_DOC_OUTLINE_LLM = GPULLMConfig(model=MAIN_MODEL, port=PORT1)  # Outline generation
GPU_DOC_SECTION_LLM = GPULLMConfig(model=MAIN_MODEL, port=PORT2)  # Section content generation
GPU_DOC_REVIEW_LLM = GPULLMConfig(model=MAIN_MODEL, port=PORT1)  # Quality self-review
GPU_DOC_ITERATE_LLM = GPULLMConfig(model=MAIN_MODEL, port=PORT2)  # Section iteration

IMAGE_PARSER_LLM = "gemma3:12b"
VLM_MODEL = "qwen3-vl:8b"  # Vision Language Model for slide/complex PDF extraction
# Fallback LLM models
# Used if SWITCHES["FALLBACK_TO_GEMINI"] = True
FALLBACK_GEMINI_MODEL = "gemini-2.5-flash"

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
SQL_QUERY = "sql_query"
EVALUATOR = "evaluator"  # Phase 2.1: CRAG corrective retrieval evaluator node
MAX_WEB_SEARCH = 2
MAX_SQL_RETRIES = 6
MAX_RETRIEVAL_ATTEMPTS = 2  # Phase 2.1: Max re-retrieval attempts on low confidence
INTERNAL = "Internal"
EXTERNAL = "External"
