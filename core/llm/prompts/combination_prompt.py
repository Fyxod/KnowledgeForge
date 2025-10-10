import json

def combination_prompt(query: str, sub_answers: list) -> str:
    sub_answers_json = json.dumps(sub_answers, indent=2, ensure_ascii=False)
    prompt = f"""
You are an expert assistant for a Retrieval-Augmented Generation (RAG) system.

Your job is to synthesize multiple partial answers into one coherent, well-structured response.

Inputs:
- Resolved_query: "{query}"
- Sub_answers:
{sub_answers_json}  

Instructions:
1. Use the Resolved_query as the *main question* you are answering.
2. Read all Sub_answers carefully.
3. Combine them into a single, natural response that directly answers the Resolved_query.
4. Remove redundancy, but keep all distinct insights.
5. If Sub_answers contradict, note the discrepancy clearly.
6. If any Sub_answer is missing or empty, state that information was not found.
7. Maintain clarity, conciseness, and factual tone.
8. Retain the formatting of any lists/headings/bullets etc from Sub_answers.
9. Ensure the final answer is in **clear, structured Markdown** with good headings, bullet points, bold text etc wherever applicable for readability.
Output:
Return only the final synthesized answer, written for the end user, without repeating the Resolved_query.
"""

    return prompt
