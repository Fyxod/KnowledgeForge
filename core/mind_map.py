from __future__ import annotations
from pydantic import BaseModel, Field, RootModel
from core.llm.client import invoke_llm
from core.constants import QUERY_LLM
from typing import List, Optional
# class for generating mind maps
import asyncio
# class Node(BaseModel):
#     title: str
#     children: list["Node"] | None = Field(default=None)

class Node(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    children: List['Node'] = []  # Recursive type hint

class FlatNode(BaseModel):
    id: str
    title: str
    parent_id: Optional[str] = None
    
class MindMapOutput(BaseModel):
    output: List[FlatNode] = Field(description="The generated mind map structure.")


FlatNode.model_rebuild()

async def run_mind_map():
    """
    Function to invoke the LLM for generating a mind map.
    This function will use the prompt defined above to generate a mind map structure.
    """

    # Invoke the LLM with the prompt
    response: MindMapOutput = await invoke_llm(
        model=QUERY_LLM,
        response_schema=MindMapOutput,
        contents=prompt
    )
    print(response)
    with open("mind_map_output.json", "w") as f:
        f.write(response.model_dump_json())
    with open("mind_map_output.txt", "w") as f:
        f.write(response.model_dump())
    return response

    
# Prompt-related code for generating mind map instructions

DOCUMENT_TEXT = """
Percy Jackson, a troubled twelve-year-old with ADHD and dyslexia, experiences a series of bizarre events that reveal his true identity as a demigod. During a school trip, his pre-algebra teacher, Mrs. Dodds, transforms into a monster (a Fury) and attacks him. Percy instinctively uses a pen-turned-sword, Riptide, given by his Latin teacher, Mr. Brunner, to vaporize her. The world then acts as if Mrs. Dodds never existed. Percy later overhears Mr. Brunner (revealed to be Chiron, a centaur) and his best friend Grover (a satyr) discussing his demigod nature and a looming \"summer solstice deadline.\" On the bus home, an encounter with the Fates, who cut a thread of life, terrifies Grover. Percy's mother, Sally, reveals she must send him to a special camp for his safety, explaining his father was a god. At their Montauk cabin, a Minotaur attacks, and Sally sacrifices herself, dissolving into golden light, to protect Percy. Percy, fueled by rage, defeats the Minotaur.\n\nPercy arrives at Camp Half-Blood, a sanctuary for demigods. He learns the Greek gods are real and active in the modern world. He meets Annabeth Chase, a daughter of Athena, and is initially placed in the Hermes cabin for \"undetermined\" campers. During a Capture the Flag game, Percy's latent powers manifest when he is doused in water, healing his wounds and granting him enhanced strength. A hellhound attack leads to a glowing trident appearing over his head, claiming him as a son of Poseidon, one of the forbidden \"Big Three\" children. Chiron reveals Zeus's master lightning bolt has been stolen, and Zeus blames Poseidon, believing Percy was the thief. Percy accepts a quest to the Underworld to clear his name and rescue his mother, receiving a prophecy from the Oracle: he will go west, face a turned god, find what was stolen, be betrayed by a friend, and fail to save what matters most.\n\nJoined by Annabeth and Grover, Percy journeys west. They narrowly escape the Furies on a bus and defeat Medusa at her \"Garden Gnome Emporium,\" where Percy discovers the Underworld's entrance address in Los Angeles. After a time-distorting stay at the Lotus Casino, they lose five days. In Santa Monica, a Nereid (sea spirit) gives Percy three magical pearls and warns him \"not to trust the gifts.\" They reach the Underworld's entrance, bribing Charon and using Annabeth's quick thinking to bypass Cerberus. Inside Hades's palace, Percy finds the master bolt in his backpack, realizing he was framed. Hades reveals he holds Sally hostage. Percy uses the pearls to escape with his friends, leaving his mother behind, determined to return for her.\n\nSurfacing in Santa Monica Bay, Percy confronts Ares, the god of war. Ares confesses he orchestrated the theft of both the master bolt and Hades's Helm of Darkness, manipulating Percy to deliver the bolt to Hades and instigate a war among the gods. Ares admits he was influenced by a voice from Tartarus (Kronos). Percy challenges Ares to a duel, defeats him by striking his heel, and retrieves the helm. The Furies appear, confirming Percy's innocence and taking the helm back to Hades. Percy, Annabeth, and Grover fly to Olympus, where Percy returns the bolt to Zeus. Zeus, though still wary, accepts the bolt and spares Percy. Poseidon confirms Sally's safe return and hints at a choice awaiting Percy.\n\nBack at Camp Half-Blood, Percy is celebrated. Grover earns his searcher's license and departs on his quest for Pan. The prophecy's lines seem fulfilled, except for the betrayal. This is revealed when Luke, Percy's friend and mentor, confesses his allegiance to Kronos. Luke admits to stealing the bolt and helm, manipulating Ares, and cursing the flying shoes to drag Percy into Tartarus. He unleashes a pit scorpion on Percy, who is gravely wounded but saved by Chiron. Annabeth decides to return home to her father. Percy, after much deliberation, chooses to return to the mortal world for the school year, promising to come back to camp next summer, ready to face the rising threat of Kronos. His mother, now free from Gabe (who was turned into a statue by Medusa's head), embarks on a new life as an artist and writer.
"""


prompt = f"""
You are to create a hierarchical outline (mind map structure) from the provided text.
The output must be in JSON with the following rules:
- Keys: title, children
- Preserve the logical hierarchy of concepts.
- Children must be nested under their parent topic.

Text:
{DOCUMENT_TEXT}

Output only JSON:
"""

# asyncio.run(run_mind_map())
