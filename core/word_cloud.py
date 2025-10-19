import json
import os
import re
import time
from io import BytesIO
from typing import List
import aiofiles
from pydantic import Field, BaseModel
from wordcloud import WordCloud
import matplotlib
from core.config import settings
import nltk
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from nltk.corpus import stopwords
from core.constants import Ollama_STOP_WORDS_EXTRACTION_LLM
from core.models.document import Documents
from app.socket_handler import sio

from core.llm.client import invoke_llm

if settings.MODE == "development":
    nltk.download("stopwords")

async def generate_word_cloud(text: str, stop_words: list[str], max_words: int = 1000):
    """
    Generates a word cloud from a text with custom stop words.
    Returns a PNG image in a BytesIO buffer.
    """
    text = clean_text(text)

    wc = WordCloud(
        width=1000,
        height=600,
        background_color="white",
        colormap="viridis",
        stopwords=stop_words,
        max_words=max_words,
        contour_color="steelblue",
        contour_width=2,
    ).generate(text)

    fig = plt.figure(figsize=(12, 6))
    plt.imshow(wc, interpolation="bilinear")
    plt.axis("off")
    plt.tight_layout(pad=0)

    buf = BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    plt.close(fig)
    return buf


def clean_text(text: str) -> str:
    # Lowercase + replace newlines
    text = text.lower().replace("\n", " ")

    # Replace " n" or " u" artifacts from newlines/conversions
    text = re.sub(r"\bn\b", " ", text)  # remove lone 'n'
    text = re.sub(r"\bu\b", " ", text)  # remove lone 'u'
    text = re.sub(r"\br\b", " ", text)  # remove lone 'r'

    # Remove unicode escapes
    text = re.sub(r"\\u[0-9a-fA-F]{4}", " ", text)

    # Replace non-letters with spaces
    text = re.sub(r"[^a-z\s]", " ", text)

    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text).strip()

    # Define stopwords
    stop_words = set(stopwords.words("english"))
    custom_stopwords = {
        "u",
        "n",
        "r",
        "ur",
        "nthe",
        "said",
        "like",
        "cyou",
        "nhe",
        "ni",
        "ci",
        "us",
        "introduction",
        "conclusion",
        "method",
        "results",
        "page",
        "image",
        "img",
        "png",
        "jpg",
        "svg",
        "[",
        "]",
        "[]",
    }
    stop_words.update(custom_stopwords)

    # Remove stopwords
    filtered_words = [word for word in text.split() if word not in stop_words]

    return " ".join(filtered_words)


class StopWordOutput(BaseModel):
    stopwords: List[str] = Field(
        description="List of stop words extracted from the text."
    )


async def create_stop_words(parsed_data: Documents):
    stop_words_dir = (
        f"data/{parsed_data.user_id}/threads/{parsed_data.thread_id}/stop_words"
    )
    os.makedirs(stop_words_dir, exist_ok=True)
    import asyncio

    documents = parsed_data.documents
    batch_size = 3
    for i in range(0, len(documents), batch_size):
        batch_docs = documents[i : i + batch_size]

        async def process_doc(doc):
            doc_text = doc.full_text
            doc_text = clean_text(doc_text)
            await sio.emit(
                f"{parsed_data.user_id}/progress",
                {"message": f"Creating stop words for {doc.title}"},
            )
            stop_words = await get_stop_words_llm(doc_text)
            save_dict = {
                "user_id": parsed_data.user_id,
                "thread_id": parsed_data.thread_id,
                "document_id": doc.id,
                "stop_words": stop_words,
            }
            json_content = json.dumps(save_dict, ensure_ascii=False, indent=2)
            async with aiofiles.open(
                f"{stop_words_dir}/{doc.file_name}_stop_words.json",
                "w",
                encoding="utf-8",
            ) as f:
                await f.write(json_content)

            await sio.emit(
                f"{parsed_data.user_id}/progress",
                {"message": f"Stop words creation for {doc.title} completed"},
            )

        # Run batch in parallel
        await asyncio.gather(*(process_doc(doc) for doc in batch_docs))
        print(
            f"Processed batch {i//batch_size + 1}: docs {i+1} to {min(i+batch_size, len(documents))}"
        )
    print(f"Stop words created and saved in {stop_words_dir}" * 10)


def limit_words(text, max_words=5000):
    words = text.split()  # Split text into words (whitespace-based)
    if len(words) > max_words:
        words = words[:max_words]  # Cut off after max_words
    return " ".join(words)


async def get_stop_words_llm(text: str) -> list[str]:
    words = text.split()
    batch_size = 5000
    stopwords_set = set()
    num_batches = (len(words) + batch_size - 1) // batch_size
    for batch_idx in range(num_batches):
        batch_words = words[batch_idx * batch_size : (batch_idx + 1) * batch_size]
        batch_text = " ".join(batch_words)
        prompt = f"""
You are an expert in text processing and natural language processing.
Your task is to identify stop words from the given text so they can be excluded when generating a word cloud.

<<<TEXT START>>>
{batch_text}
<<<TEXT END>>>

Guidelines:
1. Only identify words that are truly generic and carry little to no meaning on their own.
2. These include:
   - Function words (e.g., "the", "and", "or", "of", "to", "in", "for", "on").
   - Auxiliary verbs and modal verbs (e.g., "is", "are", "was", "were", "be", "been", "being", 
     "do", "does", "did", "can", "could", "would", "should", "shall", "will", "may", "might", "must").
   - Basic pronouns (e.g., "I", "you", "he", "she", "it", "we", "they", "me", "him", "her", "them").
   - Articles and determiners (e.g., "a", "an", "the", "this", "that", "these", "those").
   - Very generic adverbs/adjectives with no contextual meaning (e.g., "very", "really", "just").
   - Discourse fillers (e.g., "oh", "uh", "um", "well", "yes", "no", "okay").
3. DO NOT include:
   - Proper nouns (names of people, characters, places, organizations, mythological beings, etc.).
   - Any noun, verb, or adjective that conveys concrete meaning (e.g., "city", "battle", "prophecy", "fire", "blue").
   - Words that may be common but are thematically relevant in context.
   - Technical or domain-specific terms.
4. Err on the side of keeping words if unsure — only remove words that are universally considered stop words.
5. Return only the list of identified stop words, with no explanation or extra formatting.
"""

        for i in range(4):
            try:
                start_time = time.time()
                response: StopWordOutput = await invoke_llm(
                    contents=prompt,
                    response_schema=StopWordOutput,
                    remove_thinking=True,
                    ollama_model=Ollama_STOP_WORDS_EXTRACTION_LLM.model,
                    port=Ollama_STOP_WORDS_EXTRACTION_LLM.port,
                )

                stopwords_set.update(response.stopwords)
                print(f"Stop words extracted for batch {batch_idx+1}")
                end_time = time.time()
                print(
                    f"Batch {batch_idx+1} processing time: {end_time - start_time:.2f} seconds"
                )
                break
            except Exception:
                print(
                    f"Error extracting stop words for batch {batch_idx+1}, retrying...",
                    i + 1,
                )
                continue

    return list(stopwords_set)

