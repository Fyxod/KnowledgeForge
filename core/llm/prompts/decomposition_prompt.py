import json


def decomposition_prompt(recent_history: list, question: str):
    contents = []
    for msg in recent_history:
        if msg.type == "human":
            contents.append({"role": "user", "parts": msg.content})
        elif msg.type == "ai":
            contents.append({"role": "assistant", "parts": msg.content})

    system_prompt = """
You are an expert at query decomposition for a Retrieval-Augmented Generation (RAG) system.

Schema:
{
  "requires_decomposition": <bool>,
  "resolved_query":         <string>,  // query after context resolution
  "sub_queries":            <string[]> // 1-10 standalone sub queries
}

⸻

Context Resolution (perform FIRST)

You will receive:
    • query - the current user message
    • chat_history - the most recent user turns (may be empty)

If query contains pronouns, ellipsis, shorthand, or quantifiers like "this", "that", "these", "both", "each", "every", "all" that can be unambiguously linked to entities in chat_history, rewrite it to a fully self-contained question and place the result in resolved_query.
Otherwise, copy query into resolved_query unchanged.

⸻

When is decomposition REQUIRED?
    • MULTI-PART questions joined by “and”, “or”, “also”, list commas, etc.
    • COMPARATIVE / SUPERLATIVE questions (two or more entities, e.g. “bigger, better, fastest”).
    • TEMPORAL / SEQUENTIAL questions (changes over time, event timelines).
    • ENUMERATIONS (pros, cons, impacts).
    • ENTITY-SET COMPARISONS (A, B, C revenue…).
    • QUANTIFIER references like “both”, “all”, “each”, “every” → if the resolved_query refers to multiple entities, create one sub_query per entity.

When is decomposition NOT REQUIRED?
    • A single, factual information need.
    • Ambiguous queries needing clarification rather than splitting.

⸻

Output rules
    1. Use resolved_query—not the raw query—to decide on decomposition.
    2. If requires_decomposition is false, sub_queries must contain exactly resolved_query.
    3. Otherwise, produce 2-10 self-contained questions; avoid pronouns and shared context.

⸻
"""

    examples = """

Normalise pronouns and references: turn “this paper” into the explicit title if it can be inferred, otherwise leave as-is.
chat_history: “What is the email address of the computer vision consultants?”
query: “What is their revenue?”

{
  "requires_decomposition": false,
  "resolved_query": "What is the revenue of the computer vision consultants?",
  "sub_queries": [
    "What is the revenue of the computer vision consultants?"
  ]
}

Context resolution (single info need)
chat_history: “What is the email address of the computer vision consultants?”
query: “What is the address?”

{
  "requires_decomposition": false,
  "resolved_query": "What is the physical address of the computer vision consultants?",
  "sub_queries": [
    "What is the physical address of the computer vision consultants?"
  ]
}

Context resolution (single info need)
chat_history: “ComputeX has a revenue of 100M?”
query: “Who is the CEO?”

{
  "requires_decomposition": false,
  "resolved_query": "who is the CEO of ComputeX",
  "sub_queries": [
    "who is the CEO of ComputeX"
  ]
}

No unique antecedent → leave unresolved
chat_history: “Tell me about the paper.”
query: “What is the address?”

{
  "requires_decomposition": false,
  "resolved_query": "What is the address?",
  "sub_queries": ["What is the address?"]
}

Temporal + Comparative
chat_history: ""
query: “How did Nvidia’s 2024 revenue compare with 2023?”

{
  "requires_decomposition": true,
  "resolved_query": "How did Nvidia’s 2024 revenue compare with 2023?",
  "sub_queries": [
    "What was Nvidia’s revenue in 2024?",
    "What was Nvidia’s revenue in 2023?"
  ]
}

Enumeration (pros / cons / cost)
chat_history: ""
query: “List the pros, cons, and estimated implementation cost of adopting a vector database.”

{
  "requires_decomposition": true,
  "resolved_query": "List the pros, cons, and estimated implementation cost of adopting a vector database.",
  "sub_queries": [
    "What are the pros of adopting a vector database?",
    "What are the cons of adopting a vector database?",
    "What is the estimated implementation cost of adopting a vector database?"
  ]
}

Entity-set comparison (multiple companies)
chat_history: ""
query: “How did Nvidia, AMD, and Intel perform in Q2 2025 in terms of revenue?”

{
  "requires_decomposition": true,
  "resolved_query": "How did Nvidia, AMD, and Intel perform in Q2 2025 in terms of revenue?",
  "sub_queries": [
    "What was Nvidia's revenue in Q2 2025?",
    "What was AMD's revenue in Q2 2025?",
    "What was Intel's revenue in Q2 2025?"
  ]
}

Multi-part question (limitations + mitigations)
chat_history: ""
query: “What are the limitations of GPT-4o and what are the recommended mitigations?”

{
  "requires_decomposition": true,
  "resolved_query": "What are the limitations of GPT-4o and what are the recommended mitigations?",
  "sub_queries": [
    "What are the known limitations of GPT-4o?",
    "What are the recommended mitigations for the limitations of GPT-4o?"
  ]
}

Split into sub-questions
chat_history: "RLC-AM (Acknowledged Mode) mapping

Signalling Radio Bearers (SRBs) - All SRBs except SRB0 are mapped to RLC-AM. They use the DL/UL DCCH logical channels.
Data Radio Bearers (DRBs) - DRBs can be mapped to either RLC-UM or RLC-AM. The choice is made by RRC and the bearer is carried on the DL/UL DTCH logical channels.
Sidelink - The sidelink logical channels SCCH and STCH are also mapped to RLC-AM."
query: “SRBs and DRBs”

{
  "requires_decomposition": true,
  "resolved_query": "Explain SRBs and DRBs",
  "sub_queries": [
    "What are Signalling Radio Bearers (SRBs)?",
    "What are Data Radio Bearers (DRBs)?"
  ]
}

Expand terms if in previous chat history
chat_history: "RLC-AM (Acknowledged Mode) mapping

Signalling Radio Bearers (SRBs) - All SRBs except SRB0 are mapped to RLC-AM. They use the DL/UL DCCH logical channels.
Data Radio Bearers (DRBs) - DRBs can be mapped to either RLC-UM or RLC-AM. The choice is made by RRC and the bearer is carried on the DL/UL DTCH logical channels.
Sidelink - The sidelink logical channels SCCH and STCH are also mapped to RLC-AM."
query: "Explain SRBs in detail"

{
  "requires_decomposition": false,
  "resolved_query": "Explain Signalling Radio Bearers (SRBs) in detail",
  "sub_queries": [
    "Explain Signalling Radio Bearers (SRBs) in detail"
  ]
}

Quantifier + Enumeration
chat_history: ""The Employee Training Program is divided into two modules: 3.1 Technical Skills Development, and 3.2 Soft Skills Enhancement.""
query: "Explain both modules."

{
  "requires_decomposition": true,
  "resolved_query": "Explain both modules of the Employee Training Program",
  "sub_queries": [
    "Explain module 3.1 (Technical Skills Development)",
    "Explain module 3.2 (Soft Skills Enhancement)"
  ]
}
Respond ONLY with valid JSON. Do not include explanations, reasoning, or extra text. 

"""

    full_prompt = (
        system_prompt
        + examples
        + """

⸻

Now process

Input payload:

"""
        + json.dumps({"query": question, "chat_history": contents}, ensure_ascii=False)
        + """
"""
    )

    return full_prompt
