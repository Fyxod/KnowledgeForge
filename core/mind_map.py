import os
import time
import json
import asyncio

import aiofiles
from typing import List

from core.constants import (
    Ollama_NODE_GENERATION_LLM,
    Ollama_NODE_DESCRIPTION_LLM,
)
from core.embeddings.retriever import get_user_retriever
from core.llm.client import invoke_llm
from core.llm.outputs import FlatNodeWithDescriptionOutput, MindMapOutput, Node, MindMap
from core.models.document import Document
from app.socket_handler import sio


async def create_mind_map(document: Document, user_id: str, thread_id: str):
    """
    Function to invoke the LLM for generating a mind map.
    Retries the LLM call up to 3 times if an error occurs.
    """
    await sio.emit(
        f"{user_id}/progress", {"message": f"Creating mind map for {document.title}"}
    )
    incomplete_mind_map_dir = f"data/{user_id}/threads/{thread_id}/incomplete_mind_maps"
    os.makedirs(incomplete_mind_map_dir, exist_ok=True)
    prompt = build_mind_maps_node_prompt(document)
    total_start = time.time()
    max_retries = 8
    for attempt in range(max_retries):
        try:
            await sio.emit(
                f"{user_id}/progress",
                {
                    "message": f"Attempt {attempt + 1} of creating mind map for {document.title}"
                },
            )
            start = time.time()
            print(f"invoking mind map node creation llm (attempt {attempt + 1})")
            response: MindMapOutput = await invoke_llm(
                response_schema=MindMapOutput,
                contents=prompt,
                ollama_model=Ollama_NODE_GENERATION_LLM.model,
                port=Ollama_NODE_GENERATION_LLM.port,
            )
            end = time.time()
            print(f"Mind map node titles generation completed in {end - start} seconds.")


            data_dict = response.model_dump()
            json_content = json.dumps(data_dict, indent=2, ensure_ascii=False)

            async with aiofiles.open(
                f"{incomplete_mind_map_dir}/{document.file_name}_mind_map.json",
                "w",
                encoding="utf-8",
            ) as f:
                await f.write(json_content)

            await sio.emit(
                f"{user_id}/progress",
                {"message": f"Mind map nodes creation completed for {document.title}"},
            )
            await sio.emit(
                f"{user_id}/progress",
                {"message": f"Creating node descriptions for {document.title}"},
            )
            await add_node_descriptions(response, user_id, thread_id, document)
            await sio.emit(
                f"{user_id}/progress",
                {"message": f"Created node descriptions for {document.title}"},
            )
            break  # Success, exit loop
        except Exception as e:
            print(f"Error during mind map generation (attempt {attempt + 1}): {e}")
            await asyncio.sleep(5)
            if attempt == max_retries - 1:
                print("Max retries reached. Mind map generation failed.")
                await sio.emit(
                    f"{user_id}/progress",
                    {"message": f"Failed to create mind map for {document.title}"},
                )
                await sio.emit(
                    f"{user_id}/{thread_id}/mind_map",
                    {"document_id": document.id, "status": False},
                )
        total_end = time.time()
        print(
            f"Total time taken for mind map generation for {document.title}: {total_end - total_start} seconds"
        )


def load_document_from_json(path: str) -> Document:
    # Open and read the JSON file
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Parse the JSON into a Document object
    return Document(**data)


DESCRIPTION_PROCESSING_BATCH_SIZE = 4
PARALLEL_LLM_CALLS = 1


async def add_node_descriptions(
    mind_map: MindMapOutput,
    user_id: str,
    thread_id: str,
    document: Document,
):
    """
    Processes node descriptions in batches, with each batch of 4 nodes, and up to `PARALLEL_LLM_CALLS` batches processed in parallel.
    """
    mind_map_dir = f"data/{user_id}/threads/{thread_id}/descriptions_mind_maps"
    os.makedirs(mind_map_dir, exist_ok=True)

    proper_mind_map_dir = f"data/{user_id}/threads/{thread_id}/mind_maps"
    os.makedirs(proper_mind_map_dir, exist_ok=True)

    data = mind_map.model_dump()

    before_for = time.time()
    output_nodes = data["mind_map"]
    total_nodes = len(output_nodes)

    # Prepare batches
    batches = [
        output_nodes[i : i + DESCRIPTION_PROCESSING_BATCH_SIZE]
        for i in range(0, total_nodes, DESCRIPTION_PROCESSING_BATCH_SIZE)
    ]

    doc_retriever = get_user_retriever(user_id, thread_id, document.id, k=8)

    async def process_batch(batch_nodes, batch_idx):
        batch_relevant_texts = []
        for node in batch_nodes:
            start_time = time.time()
            relevant_text = await doc_retriever.ainvoke(node["title"])
            relevant_str = "\n\n".join([doc.page_content for doc in relevant_text])
            end_time = time.time()
            print(
                f"Retrieval time: {end_time - start_time} seconds for node {node['id']}"
            )
            batch_relevant_texts.append(relevant_str)

        max_batch_retries = 4
        for batch_attempt in range(max_batch_retries):
            try:
                prompt = build_mind_maps_description_prompt(
                    batch_nodes, batch_relevant_texts
                )
                llm_res_bef = time.time()
                response: FlatNodeWithDescriptionOutput = await invoke_llm(
                    contents=prompt,
                    response_schema=FlatNodeWithDescriptionOutput,
                    ollama_model=Ollama_NODE_DESCRIPTION_LLM.model,
                    port=Ollama_NODE_DESCRIPTION_LLM.port,
                )
                llm_res_aft = time.time()
                print(
                    f"LLM response time: {llm_res_aft - llm_res_bef} seconds for batch {batch_idx} (attempt {batch_attempt + 1})"
                )
                await sio.emit(
                    f"{user_id}/progress",
                    {
                        "message": f"Created descriptions for batch {batch_idx} (attempt {batch_attempt + 1})"
                    },
                )

                for i, node in enumerate(batch_nodes):
                    resp_node = (
                        response.mind_map[i] if i < len(response.mind_map) else None
                    )
                    if resp_node and node["id"] == resp_node.id:
                        node["description"] = resp_node.description
                        print(f"Updated description for node {node['id']}")
                    else:
                        print(f"Failed to update description for node {node['id']}")
                        if resp_node:
                            print(f"Expected ID: {node['id']}, but got: {resp_node.id}")
                break
            except Exception as e:
                print(
                    f"Error during description generation for batch {batch_idx} (attempt {batch_attempt + 1}): {e}"
                )
                await asyncio.sleep(2)
                if batch_attempt == max_batch_retries - 1:
                    print(f"Max retries reached for batch {batch_idx}. Skipping batch.")
                    await sio.emit(
                        f"{user_id}/progress",
                        {
                            "message": f"Failed to create descriptions for batch {batch_idx}"
                        },
                    )

    batch_count = len(batches)
    batch_idx = 0
    while batch_idx < batch_count:
        current_group = []
        for i in range(PARALLEL_LLM_CALLS):
            if batch_idx + i < batch_count:
                current_group.append(
                    process_batch(batches[batch_idx + i], batch_idx + i)
                )
        if current_group:
            await asyncio.gather(*current_group)
        batch_idx += PARALLEL_LLM_CALLS

    after_for = time.time()
    print("Total time taken:", after_for - before_for)

    async with aiofiles.open(
        f"{mind_map_dir}/{document.file_name}_mind_map.json", "w", encoding="utf-8"
    ) as f:
        await f.write(json.dumps(data, indent=2, ensure_ascii=False))

    mind_map: MindMap = build_mindmap(data["mind_map"], user_id, thread_id, document.id)
    await sio.emit(
        f"{user_id}/progress",
        {"message": f"Mind map built successfully for {document.title}"},
    )

    print("Mind map built successfully")
    await sio.emit(
        f"{user_id}/{thread_id}/mind_map", {"document_id": document.id, "status": True}
    )
    data_dict = mind_map.model_dump()
    json_content = json.dumps(data_dict, indent=2, ensure_ascii=False)

    async with aiofiles.open(
        f"{proper_mind_map_dir}/{document.file_name}_mind_map.json",
        "w",
        encoding="utf-8",
    ) as f:
        await f.write(json_content)


def build_mind_maps_node_prompt(document: Document):
    def word_count(text: str) -> int:
        return len(text.split())

    if hasattr(document, "full_text") and word_count(document.full_text) < 1000:
        print("Using full text for mind map creation")
        text = document.full_text
    elif hasattr(document, "summary") and document.summary:
        print("Using summary for mind map creation")
        text = document.summary
    else:
        print("Using title for mind map creation")
        text = document.title

    return f"""
Respond with a valid JSON of nodes(max_limit: 50).
You are to create a mind map node structure from the provided text. 
The output must be in JSON with the following rules:
- Each node must contain: id, title, and parent_id.
- id: a unique identifier for the node.
- title: the text label for the node.
- parent_id: the id of the parent node, or null if it is a root node.
- Preserve the logical hierarchy of concepts by linking nodes through parent_id.
Text: {text}
Do not exceed the max limit of 50 nodes.

"""


# Return valid json as told


# - Try to keep only 1 root node


def build_mind_maps_description_prompt(nodes, relevant_texts):
    prompt = f"""
        You are to write clear, concise, and informative descriptions of 40-50 words for each of the following mind map nodes.
        For each node, the description should explain what the concept means. It should be useful to the user, no blabbering about anything else.
        Take reference and help from the provided source text for each node but don't reference them in the description itself.

        Nodes:
    """
    for i, node in enumerate(nodes):
        prompt += f"\nNode {i+1}:\n  Node id: {node['id']}\n  Node title: {node['title']}\n  Source text: {relevant_texts[i]}\n"
    return prompt


def build_mindmap(
    flat_nodes: List[dict], user_id: str, thread_id: str, document_id: str
) -> MindMap:
    # Convert dicts into Node objects
    nodes = {n["id"]: Node(**n, children=[]) for n in flat_nodes}

    roots = []

    # Assign children to parents
    for node in nodes.values():
        if node.parent_id:
            parent = nodes.get(node.parent_id)
            if parent:
                parent.children.append(node)
        else:
            roots.append(node)

    return MindMap(
        user_id=user_id, thread_id=thread_id, document_id=document_id, roots=roots
    )
