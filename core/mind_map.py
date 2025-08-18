import os
from core.llm.client import invoke_llm
from core.constants import QUERY_LLM
from typing import List, Optional
import asyncio
import aiofiles
import json
import time
from core.models.document import Document
from core.llm.outputs import MindMapOutput, FlatNodeWithDescriptionOutput
import json
import aiofiles
from pydantic import BaseModel, Field, RootModel
from core.llm.client import invoke_llm
from core.constants import NODE_DESCRIPTION_LLM
from typing import List, Optional
from core.embeddings.retriever import get_user_retriever
from core.llm.outputs import FlatNodeWithDescriptionOutput
import time
import asyncio

async def create_mind_map(document: Document, user_id: str, thread_id: str):
    """
    Function to invoke the LLM for generating a mind map.
    Retries the LLM call up to 3 times if an error occurs.
    """
    incomplete_mind_map_dir = f"data/{user_id}/threads/{thread_id}/incomplete_mind_maps"
    os.makedirs(incomplete_mind_map_dir, exist_ok=True)
    prompt = build_mind_maps_node_prompt(document)
    total_start = time.time()
    max_retries = 3
    for attempt in range(max_retries):
        try:
            start = time.time()
            print(f"invoking mind map node creation llm (attempt {attempt + 1})")
            print(prompt)
            response = await invoke_llm(
                model=QUERY_LLM,
                response_schema=MindMapOutput,
                contents=prompt
            )
            end = time.time()
            response = MindMapOutput.model_validate(response)
            print(response)
            print(f"Mind map generation took {end - start} seconds.")
            with open("mind_map_output.json", "w") as f:
                f.write(response.model_dump_json())
            print("mind map saved")
            async with aiofiles.open(
                f"{incomplete_mind_map_dir}/{document.file_name}_mind_map.json", "w"
            ) as f:
                await f.write(response.model_dump_json())
            print("entering description function")
            await add_node_descriptions(response, user_id, thread_id, document)
            break  # Success, exit loop
        except Exception as e:
            print(f"Error during mind map generation (attempt {attempt + 1}): {e}")
            await asyncio.sleep(5)
            if attempt == max_retries - 1:
                print("Max retries reached. Mind map generation failed.")
        total_end = time.time()
        print(f"Total time taken for mind map generation: {total_end - total_start} seconds")

DESCRIPTION_PROCESSING_BATCH_SIZE = 4

async def add_node_descriptions(mind_map: MindMapOutput, user_id: str, thread_id: str, document: Document):
        mind_map_dir = f"data/{user_id}/threads/{thread_id}/mind_maps"
        os.makedirs(mind_map_dir, exist_ok=True)
        data = mind_map.model_dump()

        print("**" * 20)
        before_for = time.time()
        output_nodes = data["output"]
        total_nodes = len(output_nodes)
        for batch_start in range(0, total_nodes, DESCRIPTION_PROCESSING_BATCH_SIZE):
            batch_nodes = output_nodes[batch_start : batch_start + DESCRIPTION_PROCESSING_BATCH_SIZE]
            batch_relevant_texts = []
            # Retrieve relevant text for each node in the batch
            for node in batch_nodes:
                doc_retriever = get_user_retriever(
                    user_id, thread_id, document.id, k=25
                )
                start_time = time.time()
                relevant_text = await doc_retriever.ainvoke(node["title"], k=25)
                relevant_str = "\n\n".join([doc.page_content for doc in relevant_text])
                end_time = time.time()
                print(
                    f"Retrieval time: {end_time - start_time} seconds for node {node['id']}"
                )
                batch_relevant_texts.append(relevant_str)
            prompt = build_mind_maps_description_prompt(batch_nodes, batch_relevant_texts)
            llm_res_bef = time.time()
            response: FlatNodeWithDescriptionOutput = await invoke_llm(
                contents=prompt,
                model=NODE_DESCRIPTION_LLM,
                response_schema=FlatNodeWithDescriptionOutput,
            )
            llm_res_aft = time.time()
            print(
                f"LLM response time: {llm_res_aft - llm_res_bef} seconds for batch {batch_start // DESCRIPTION_PROCESSING_BATCH_SIZE}"
            )
            
            # Update nodes with descriptions
            for i, node in enumerate(batch_nodes):
                resp_node = response.output[i] if i < len(response.output) else None
                if resp_node and node["id"] == resp_node.id:
                    node["description"] = resp_node.description
                    print(
                        f"Updated description for node {node['id']}"
                    )
                else:
                    print(f"Failed to update description for node {node['id']}")
                    if resp_node:
                        print(f"Expected ID: {node['id']}, but got: {resp_node.id}")
            await asyncio.sleep(1)
        after_for = time.time()
        print("Total time taken:", after_for - before_for)
        async with aiofiles.open("mind_map_output_with_descriptions.json", "w") as f:
            await f.write(json.dumps(data, indent=2))
        print("saved mind_map_output_with_descriptions.json")
        async with aiofiles.open(f"{mind_map_dir}/{document.file_name}_mind_map.json", "w") as f:
            await f.write(json.dumps(data, indent=2))

def build_mind_maps_node_prompt(document: Document):
    def word_count(text: str) -> int:
        return len(text.split())

    if hasattr(document, "full_text") and word_count(document.full_text) < 1000:
        text = document.full_text
    elif hasattr(document, "summary") and document.summary:
        text = document.summary
    else:
        text = document.title

    return f"""
You are to create a hierarchical outline (mind map structure) from the provided text.
The output must be in JSON with the following rules:
- Keys: title, children
- Preserve the logical hierarchy of concepts.
- Children must be nested under their parent topic.

Text:
{text}

Output only JSON:
"""

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