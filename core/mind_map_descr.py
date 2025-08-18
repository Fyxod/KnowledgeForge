from __future__ import annotations
import json
import aiofiles
from pydantic import BaseModel, Field, RootModel
from core.llm.client import invoke_llm
from core.constants import NODE_DESCRIPTION_LLM
from typing import List, Optional
from core.embeddings.retriever import get_user_retriever
# class for generating mind maps
import time
import asyncio

# read json file
class FlatNode(BaseModel):
    id: str
    title: str
    parent_id: Optional[str] = None


class FlatNodeWithDescription(BaseModel):
    id: str
    title: str
    description: str

class FlatNodeWithDescriptionOutput(BaseModel):
    output: List[FlatNodeWithDescription]


# Process the data as needed


async def add_descriptions(user_id: str, thread_id: str, document_id: str):
    async with aiofiles.open("mind_map_output.json", "r") as f:
        contents = await f.read()
        data = json.loads(contents)
        
        print(data)
        print("**"*20)
        index = 0
        before_for = time.time()
        for node in data["output"]:
            doc_retriever = get_user_retriever(user_id, thread_id, document_id, k=25)
            start_time = time.time()
            relevant_text = await doc_retriever.ainvoke(node["title"], k=25)
            relevant_str = "\n\n".join([doc.page_content for doc in relevant_text])
            end_time = time.time()
            print(f"Retrieval time: {end_time - start_time} seconds")
            prompt = build_node_prompt(node["title"], relevant_str, node["id"])
            llm_res_bef = time.time()
            response: FlatNodeWithDescription = await invoke_llm(
                contents=prompt,
                model=NODE_DESCRIPTION_LLM,
                response_schema=FlatNodeWithDescription,
            )
            llm_res_aft = time.time()
            print(f"LLM response time: {llm_res_aft - llm_res_bef} seconds")
            if node["id"] == response.id:
                node["description"] = response.description
                print(f"Updated description for node {node['id']}: {node['description']}")
            else:
                print(f"Failed to update description for node {node['id']}")
                print(f"Expected ID: {node['id']}, but got: {response.id}")
            print("INDEX:", index)
            index += 1
            await asyncio.sleep(1)
        after_for = time.time()
        print("Total time taken:", after_for - before_for)
        async with aiofiles.open("mind_map_output_with_descriptions.json", "w") as f:
            await f.write(json.dumps(data, indent=2))
        return data


def build_node_prompt(node_title: str, relevant_text: str, node_id: str):
    return f"""
        You are to write a clear, concise, and informative description of 40-50 words for the given mind map node.
        The description should explain what the concept means. It should be useful to the user, no blabbering about anything else.
        Take reference from the provided context but don't reference them in the description itself.

        Node id: {node_id}
        Node title: {node_title}
        Source text: {relevant_text}

        """

asyncio.run(add_descriptions("user1_916a6f", "ce11f8d7-fcc4-407a-b842-477d981575e9", "7efc3a2d-0f7d-4004-b611-fee02e0f158f"))
