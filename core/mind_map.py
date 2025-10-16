import os
import time
import json
import asyncio

import aiofiles
from typing import List

from core.constants import (
    GPU_NODE_DESCRIPTION_LLM,
    GPU_NODE_GENERATION_LLM,
)
from core.embeddings.retriever import get_user_retriever
from core.llm.client import invoke_llm
from core.llm.outputs import (
    FlatNodeWithDescriptionOutput,
    MindMapOutput,
    Node,
    GlobalMindMap,
)
from core.models.document import Documents
from app.socket_handler import sio
from core.utils.extra_done_check import mark_extra_done
from core.word_cloud import create_stop_words
from core.llm.unload_ollama_model import unload_ollama_model


async def create_mind_map_global(parsed_data: Documents):
    """
    Function to invoke the LLM for generating a mind map.
    Retries the LLM call up to 8 times if an error occurs.
    """
    await sio.emit(
        f"{parsed_data.user_id}/progress",
        {"message": f"Started global mind map generation"},
    )
    incomplete_mind_map_dir = f"data/{parsed_data.user_id}/threads/{parsed_data.thread_id}/incomplete_mind_maps"
    os.makedirs(incomplete_mind_map_dir, exist_ok=True)
    prompt = build_mind_maps_node_prompt_global(parsed_data)
    total_start = time.time()
    max_retries = 8
    mind_map_emit_topic = (
        f"{parsed_data.user_id}/{parsed_data.thread_id}/mind_map/progress"
    )

    # Setup for continuous message broadcasting
    current_message = {"message": "Initializing mind map generation..."}
    broadcast_task = None
    stop_broadcast = asyncio.Event()

    async def broadcast_message():
        """Continuously broadcast the current message every 1 second"""
        while not stop_broadcast.is_set():
            await sio.emit(mind_map_emit_topic, current_message)
            try:
                await asyncio.wait_for(stop_broadcast.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

    async def update_message(new_message: dict):
        """Update the current message and restart broadcasting"""
        nonlocal current_message, broadcast_task
        current_message = new_message
        if broadcast_task and not broadcast_task.done():
            stop_broadcast.set()
            await broadcast_task
            stop_broadcast.clear()
        broadcast_task = asyncio.create_task(broadcast_message())

    # Start initial broadcast
    broadcast_task = asyncio.create_task(broadcast_message())
    for attempt in range(max_retries):
        try:
            await update_message(
                {"message": f"Attempt {attempt + 1} of creating mind map"}
            )
            start = time.time()
            print(f"invoking mind map node creation llm (attempt {attempt + 1})")

            await update_message({"message": f"Nodes creation in progress..."})

            response: MindMapOutput = await invoke_llm(
                response_schema=MindMapOutput,
                contents=prompt,
                gpu_model=GPU_NODE_GENERATION_LLM.model,
                port=GPU_NODE_GENERATION_LLM.port,
            )

            end = time.time()
            print(
                f"Mind map node titles generation completed in {end - start} seconds."
            )

            await update_message(
                {
                    "message": f"Mind map node titles generation completed in {end - start} seconds."
                }
            )

            data_dict = response.model_dump()
            json_content = json.dumps(data_dict, indent=2, ensure_ascii=False)

            proper_mind_map_dir = (
                f"data/{parsed_data.user_id}/threads/{parsed_data.thread_id}/mind_maps"
            )
            os.makedirs(proper_mind_map_dir, exist_ok=True)

            for node in data_dict["mind_map"]:
                node["description"] = ""

            mind_map_incomplete: GlobalMindMap = build_mindmap_global(
                data_dict["mind_map"], parsed_data.user_id, parsed_data.thread_id
            )

            mind_map_incomplete_dict = mind_map_incomplete.model_dump()

            async with aiofiles.open(
                f"{proper_mind_map_dir}/{parsed_data.user_id}_{parsed_data.thread_id}_global_mind_map.json",
                "w",
                encoding="utf-8",
            ) as f:
                await f.write(
                    json.dumps(mind_map_incomplete_dict, indent=2, ensure_ascii=False)
                )

            async with aiofiles.open(
                f"{incomplete_mind_map_dir}/{parsed_data.user_id}_{parsed_data.thread_id}_global_mind_map.json",
                "w",
                encoding="utf-8",
            ) as f:
                await f.write(json_content)

            print("Starting to add node descriptions for Global mind map...")
            await sio.emit(
                f"{parsed_data.user_id}/progress",
                {"message": f"Global mind map nodes generation complete"},
            )
            await sio.emit(
                f"{parsed_data.user_id}/progress",
                {"message": f"Creating node descriptions for GLOBAL mind map"},
            )
            await update_message(
                {"message": f"Node descriptions creation in progress..."}
            )
            await add_node_descriptions_global(response, parsed_data, update_message)
            # asyncio.create_task(create_stop_words(parsed_data.model_copy()))
            await sio.emit(
                f"{parsed_data.user_id}/progress",
                {"message": f"Created node descriptions for GLOBAL mind map"},
            )
            total_end = time.time()

            print(
                f"Total time taken for mind map generation: {total_end - total_start} seconds"
            )
            await update_message(
                {
                    "message": f"Total time taken for mind map generation: {total_end - total_start} seconds"
                }
            )
            await asyncio.sleep(5)

            # Stop broadcasting and send final completion message
            stop_broadcast.set()
            if broadcast_task and not broadcast_task.done():
                await broadcast_task

            await sio.emit(
                mind_map_emit_topic,
                {
                    "completed": True,
                },
            )
            break
        except Exception as e:
            print(f"Error during mind map generation (attempt {attempt + 1}): {e}")
            await update_message(
                {
                    "message": f"Error during mind map generation (attempt {attempt + 1}): {e}"
                }
            )
            await asyncio.sleep(5)
            if attempt == max_retries - 1:
                print("Max retries reached. Mind map generation failed.")
                await update_message(
                    {"message": f"Max retries reached. Mind map generation failed."}
                )
                await sio.emit(
                    f"{parsed_data.user_id}/progress",
                    {"message": f"Failed to create GLOBAL mind map"},
                )
                await sio.emit(
                    f"{parsed_data.user_id}/{parsed_data.thread_id}/global_mind_map",
                    {"document_id": parsed_data.id, "status": False},
                )


DESCRIPTION_PROCESSING_BATCH_SIZE = 4
PARALLEL_LLM_CALLS = 2


async def add_node_descriptions_global(
    mind_map: MindMapOutput,
    parsed_data: Documents,
    update_message_callback=None,
):
    """
    Processes node descriptions in batches, with each batch of 4 nodes, and up to `PARALLEL_LLM_CALLS` batches processed in parallel.
    """
    mind_map_dir = f"data/{parsed_data.user_id}/threads/{parsed_data.thread_id}/descriptions_mind_maps"
    os.makedirs(mind_map_dir, exist_ok=True)

    proper_mind_map_dir = (
        f"data/{parsed_data.user_id}/threads/{parsed_data.thread_id}/mind_maps"
    )
    os.makedirs(proper_mind_map_dir, exist_ok=True)

    data = mind_map.model_dump()

    output_nodes = data["mind_map"]
    total_nodes = len(output_nodes)

    # Prepare batches
    batches = [
        output_nodes[i : i + DESCRIPTION_PROCESSING_BATCH_SIZE]
        for i in range(0, total_nodes, DESCRIPTION_PROCESSING_BATCH_SIZE)
    ]

    doc_retriever = get_user_retriever(parsed_data.user_id, parsed_data.thread_id, k=8)

    async def update_mind_map(data):
        try:
            for node in data["mind_map"]:
                if "description" not in node or not node["description"]:
                    node["description"] = ""

            mind_map_obj: GlobalMindMap = build_mindmap_global(
                data["mind_map"], parsed_data.user_id, parsed_data.thread_id
            )

            data_dict = mind_map_obj.model_dump()

            async with aiofiles.open(
                f"{proper_mind_map_dir}/{parsed_data.user_id}_{parsed_data.thread_id}_global_mind_map.json",
                "w",
                encoding="utf-8",
            ) as f:
                await f.write(json.dumps(data_dict, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"Error in update_mind_map: {e}")
            raise

    async def process_batch(batch_nodes, batch_idx):
        if update_message_callback:
            await update_message_callback(
                {
                    "message": f"Creating descriptions for batch {batch_idx + 1} of {len(batches)}"
                }
            )
        batch_relevant_texts = []
        for node in batch_nodes:
            start_time = time.time()
            relevant_text = await doc_retriever.ainvoke(node["title"])
            relevant_str = "\n\n".join([doc.page_content for doc in relevant_text])
            end_time = time.time()
            print(
                f"Retrieval time: {end_time - start_time} seconds for node {node['id']} of GLOBAL mind map"
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
                    gpu_model=GPU_NODE_DESCRIPTION_LLM.model,
                    port=GPU_NODE_DESCRIPTION_LLM.port,
                )
                llm_res_aft = time.time()
                print(
                    f"LLM response time: {llm_res_aft - llm_res_bef} seconds for mind map batch {batch_idx} (attempt {batch_attempt + 1})"
                )
                await sio.emit(
                    f"{parsed_data.user_id}/progress",
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
                await update_mind_map(data)
                break
            except Exception as e:
                print(
                    f"Error during description generation for batch {batch_idx} - GLOBAL MIND MAP (attempt {batch_attempt + 1}): {e}"
                )
                await asyncio.sleep(2)
                if batch_attempt == max_batch_retries - 1:
                    print(
                        f"Max retries reached for batch {batch_idx} - GLOBAL MIND MAP. Skipping batch."
                    )
                    await sio.emit(
                        f"{parsed_data.user_id}/progress",
                        {
                            "message": f"Failed to create descriptions for batch {batch_idx} - GLOBAL MIND MAP"
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

    async with aiofiles.open(
        f"{mind_map_dir}/{parsed_data.user_id}_{parsed_data.thread_id}_global_mind_map.json",
        "w",
        encoding="utf-8",
    ) as f:
        await f.write(json.dumps(data, indent=2, ensure_ascii=False))

    print("Mind map built successfully")
    await sio.emit(
        f"{parsed_data.user_id}/progress",
        {"message": f"GLOBAL Mind map built successfully"},
    )

    await update_mind_map(data)
    asyncio.create_task(delayed_mark(parsed_data))


async def delayed_mark(parsed_data: Documents):
    await asyncio.sleep(60)
    await unload_ollama_model(
        GPU_NODE_DESCRIPTION_LLM.model, GPU_NODE_DESCRIPTION_LLM.port
    )
    await asyncio.sleep(20)
    modified = mark_extra_done(parsed_data.user_id, parsed_data.thread_id, True)
    if modified:
        print("Marked thread as extra_done")
    else:
        print("Failed to mark thread as extra_done")


def build_mind_maps_node_prompt_global(parsed_data: Documents):
    def word_count(text: str) -> int:
        return len(text.split())

    final_text = ""
    for document in parsed_data.documents:

        if hasattr(document, "full_text") and word_count(document.full_text) < 1000:
            print("Using full text for mind map creation")
            text = document.full_text
        elif hasattr(document, "summary") and document.summary:
            print("Using summary for mind map creation")
            text = document.summary
        else:
            print("Using title for mind map creation")
            words = document.full_text.split()[:15000]
            text = " ".join(words)
        final_text += f"\n{document.title}\n\n{text}\n\n"

    return f"""
Respond with a valid JSON of nodes (max_limit: 100).
You are to create a mind map node structure from the provided text. 
The output must be in JSON with the following rules:
- Each node must contain: id, title, and parent_id.
- id: a unique identifier for the node.
- title: the text label for the node.
- parent_id: the id of the parent node, or null if it is a root node.
- Preserve the logical hierarchy of concepts by linking nodes through parent_id.

Guidelines:
- Try to balance breadth and depth: some branches should expand into 4-6 levels where natural.
- Break down complex topics into smaller sub-concepts, examples, or details, instead of grouping them all as direct children of the root.
- Cover each document really well in detail.
- Do not exceed the max limit of 100 nodes.
- Keep only 1 root node if possible.

Text: {final_text}
"""


def build_mind_maps_description_prompt(nodes, relevant_texts):
    prompt = f"""
        You are to write clear, concise, and informative descriptions of 40-50 words for each of the following mind map nodes.
        For each node, the description should explain what the concept means. It should be useful to the user, no blabbering about anything else.
        Take reference and help from the provided source text for each node but don't reference them in the description itself.
    """
    for i, node in enumerate(nodes):
        prompt += f"\nNode {i+1}:\n  Node id: {node['id']}\n  Node title: {node['title']}\n  Source text: {relevant_texts[i]}\n"
    return prompt


def build_mindmap_global(
    flat_nodes: List[dict],
    user_id: str,
    thread_id: str,
) -> GlobalMindMap:
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

    return GlobalMindMap(user_id=user_id, thread_id=thread_id, roots=roots)
