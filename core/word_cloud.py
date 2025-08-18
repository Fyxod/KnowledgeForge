import json
import os
import re
import time
from io import BytesIO
from typing import List
from pydantic import Field, BaseModel
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from nltk.corpus import stopwords
import nltk
from core.constants import STOP_WORDS_EXTRACTION_LLM
from core.models.document import Documents

nltk.download("stopwords")
from core.llm.client import invoke_llm


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
    fig.savefig(buf, format='png')
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
    for doc in parsed_data.documents:
        doc_text = doc.full_text
        doc_text = clean_text(doc_text)
        stop_words = await get_stop_words_llm(doc_text)
        save_dict = {
            "user_id": parsed_data.user_id,
            "thread_id": parsed_data.thread_id,
            "document_id": doc.id,
            "stop_words": stop_words,
        }
        with open(
            f"{stop_words_dir}/{doc.file_name}_stop_words.json", "w", encoding="utf-8"
        ) as f:
            json.dump(save_dict, f)
    print(f"Stop words created and saved in {stop_words_dir}" * 10)


async def get_stop_words_llm(text: str) -> list[str]:
    words = text.split()
    batch_size = 40000
    stopwords_set = set()
    num_batches = (len(words) + batch_size - 1) // batch_size
    for batch_idx in range(num_batches):
        batch_words = words[batch_idx * batch_size : (batch_idx + 1) * batch_size]
        batch_text = " ".join(batch_words)
        prompt = f"""
    You are an expert in text processing and natural language processing.
    Your task is to extract stop words from the given text.

    <<<TEXT START>>>
    {batch_text}
    <<<TEXT END>>>

    Your task:
    1. Identify words that are uninformative or “stopword-like” in this context.
    2. These include: common function words (like “the”, “and”, “is”), filler verbs (like “said”, “would”, “could”), dialogue markers, or generic academic terms (like “introduction”, “method”) depending on the genre of the text.
    3. Do not include meaningful domain-specific words (e.g., character names, technical terms, or thematic keywords).
            """
        for i in range(3):
            try:
                start_time = time.time()
                response: StopWordOutput = await invoke_llm(
                    contents=prompt,
                    model=STOP_WORDS_EXTRACTION_LLM,
                    response_schema=StopWordOutput,
                    remove_thinking=True,
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
    try:
        with open("stop_words.json", "w", encoding="utf-8") as file:
            json.dump(list(stopwords_set), file)
            print(f"Stop words extracted and saved to stop_words.json")
    except Exception as e:
        print("Error saving stop words:", e)
    return list(stopwords_set)
