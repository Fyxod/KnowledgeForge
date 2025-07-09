import asyncio
import json
from typing import List, Literal, Optional, Dict, Any

from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import MessagesPlaceholder, ChatPromptTemplate, HumanMessagePromptTemplate
class AbortGraphExecution(Exception):
    pass
from langgraph.graph import (
    StateGraph,
    add_messages,
    END,
    START
)

from pydantic import BaseModel, Field

from core.llm import llm
from core.search_tool import search_tool
from core.schemas.user import UserModel
from core.vectorstore import get_user_retriever
import time

RETRIEVER = "retriever"
GENERATE = "generate"
WEB_SEARCH = "web_search"
REPHRASE = "rephrase"
ANSWER = "answer"
ROUTER = "router"
FAILURE = "failure"
REWRITE_QUERY= "rewrite_query"
    
# main_prompt = ChatPromptTemplate.from_messages(
#     [
#         SystemMessage(
#             content="You are a helpful assistant that answers questions based on the provided documents."
#         ),
#         SystemMessage(
#             content="Give the best possible answer using the context if it is possible"
#         ),
#         SystemMessage(
#             content="If the question is not answerable based on the provided documents, you should rephrase the question to make it more specific or initiate a web search for queries that you think are relevant."
#         ),
#         SystemMessage(
#             content="If you are unsure about the answer, you should rephrase the question to make it more specific or initiate a web search for queries that you think are relevant."
#         ),
#         MessagesPlaceholder(variable_name="messages"),
#         HumanMessagePromptTemplate.from_template(
#             "Here is the retrieved context according to the question: {documents}"
#         ),
#         HumanMessagePromptTemplate.from_template("{question}"),
#     ]
# )

main_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content=(
                "You are a helpful assistant that answers questions based on the provided documents. "
                "Use the retrieved context to give the best possible answer. "
                "If the question is answerable using the provided documents, provide a direct and specific answer using relevant details."
            )
        ),
        SystemMessage(
            content=(
                "Only if the question truly cannot be answered using the documents, then ask for clarification or suggest a web search. "
                "Do not default to asking for clarification if relevant information is available in the context."
            )
        ),
        MessagesPlaceholder(variable_name="messages"),
        HumanMessagePromptTemplate.from_template(
            "Here is the retrieved context according to the question:\n{documents}"
        ),
        HumanMessagePromptTemplate.from_template("{question}"),
    ]
)

# not providing context to the rephrase prompt
rephrase_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content=(
                "You are a helpful assistant that rephrases vague or overly broad questions to make them clearer and more specific. "
                "You should aim to make the question easier to answer using a set of documents or contextual data."
            )
        ),
        SystemMessage(
            content=(
                "Make sure the rephrased question is still aligned with the original user's intent, but avoids ambiguity. "
                "Prefer questions that mention specific entities, topics, or constraints when possible."
            )
        ),
        HumanMessagePromptTemplate.from_template("Original question: {original_question}"),
    ]
)

rewrite_query_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content=(
                "You are a helpful assistant tasked with rewriting user messages for semantic vector search. "
                "Your job is to convert a potentially vague or follow-up question into a clear, standalone query that can be used for document retrieval. "
                "Preserve the user's intent without adding new information."
            )
        ),
        SystemMessage(
            content=(
                "If the user's message already makes sense on its own, return it unchanged. "
                "If the message is ambiguous, contains spelling errors, or appears to reference previous assistant responses, use the previous turn to clarify it."
                "Fix small typos and normalize the message if necessary."
            )
        ),
        SystemMessage(
            content=(
                "The goal is to maximize the relevance and specificity of the query for use with a vector-based semantic search engine."
            )
        ),
        MessagesPlaceholder(variable_name="recent_history"),
        HumanMessagePromptTemplate.from_template(
            "User's current message: {question}\n\nRewritten query for semantic search:"
        ),
    ]
)



# providing context to the rephrase prompt
# rephrase_prompt2 = ChatPromptTemplate.from_messages(
#     [
#         SystemMessage(
#             content=(
#                 "You are a helpful assistant that rephrases vague or broad questions to make them clearer and more specific. "
#                 "You may use the provided context to help shape the question, but only if it helps clarify the user's intent."
#             )
#         ),
#         SystemMessage(
#             content=(
#                 "Do not introduce information that is not relevant to the original question or not supported by the context."
#             )
#         ),
#         HumanMessagePromptTemplate.from_template("Original question: {original_question}"),
#         HumanMessagePromptTemplate.from_template("Here is the context:\n{documents}"),
#     ]
# )


# maybe add descriptions to each field
class AgentState(BaseModel):
    user_id: str
    thread_id: str
    question: str
    original_question: str
    messages: List[BaseMessage]
    documents: List[Dict[str, Any]] = Field(default_factory=list)
    web_search: bool = False
    search_queries: List[str] = Field(default_factory=list)
    search_queries_results: List[Dict[str, Any]] = Field(default_factory=list)
    answer: Optional[str] = None
    documents_used: List[str] = Field(default_factory=list)
    attempts: int = 0
    rephrases: int = 0
    web_search_attempts: int = 0
    action: Optional[Literal["answer", "rephrase_question", "web_search"]] = None
    retrieval_query: Optional[str] = None
    # This is used to determine the next step in the state graph
    next: Optional[str] = None
    
MAX_REPHRASE = 2
MAX_WEB_SEARCH = 2


async def parallel_search(queries, tool):
    tasks = [tool.ainvoke(query) for query in queries]
    results = await asyncio.gather(*tasks)
    return results

class MainLLMOutput(BaseModel):
    answer: str = Field(description="The answer to the user's question.")
    action: Literal["answer", "rephrase_question", "web_search"] = Field(
        description="The action to take based on the answer."
    )
    documents_used: Optional[List[str]] = Field(
        default=None,
        description="List of document ids of documents used to generate the answer, if applicable.",
    )
    web_search_queries: Optional[List[str]] = Field(
        default=None,
        description="List of 2-3 web search queries used to generate the answer, if applicable.",
    )
class REPHRASELLMOutput(BaseModel):
    rephrased_question: str = Field(
        description="The rephrased question based on the original question."
    )

class REWRITELLMOutput(BaseModel):
    rewritten_query: str = Field(
        description="The rewritten query for semantic vector search based on the user's message."
    )


def build_main_prompt(state: AgentState) -> ChatPromptTemplate:
    """
    Builds the main prompt for the agent based on the current state.
    """
    print(state)
    if state.web_search:
        documents = state.search_queries_results
    else:
        documents = state.documents
    recent_chats =  get_recent_history(state.messages, turns=5) # fine tune the no of turns

    return main_prompt.format_messages(
        messages=recent_chats,
        documents=documents,
        question=state.question,
    )

def build_rephrase_prompt(state: AgentState) -> ChatPromptTemplate:
    """ Builds the rephrase prompt for the agent based on the current state.
    """
    return rephrase_prompt.format_messages(
        original_question=state.question,
        # documents=state.get("documents", []),  # not providing context to the rephrase prompt
    )

def build_rewrite_prompt(state: AgentState) -> ChatPromptTemplate:
    """ Builds the rewrite prompt for the agent based on the current state.
    """
    recent_history = get_recent_history(state.messages, turns=5)
    prompt = rewrite_query_prompt.format_messages(
        question=state.question,
        recent_history=recent_history,
    )
    print("Rewrite prompt: ", prompt)
    return prompt
    

async def generate(state: AgentState) -> AgentState:
    prompt = build_main_prompt(state)
    with open("formatted_prompt.txt", "w", encoding="utf-8") as f:
        for msg in prompt:
            role = msg.__class__.__name__.replace("Message", "").upper()
            f.write(f"{role}:\n{msg.content}\n\n{'-'*40}\n\n")
        
    structured_llm = llm.with_structured_output(MainLLMOutput)
    start_time = time.time()
    result: MainLLMOutput = await structured_llm.ainvoke(prompt)
    end_time = time.time()
    print("LLM result: ", result)
    print(f"LLM response time: {end_time - start_time:.2f} seconds")
    with open("llm_result.json", "w", encoding="utf-8") as f:
        json.dump(result.model_dump(), f, indent=4)
    state.messages.append(HumanMessage(content=state.question)) # controversial
    state.messages.append(AIMessage(content=result.answer))
    state.messages.append(AIMessage("Action: " + result.action))
    state.answer = result.answer
    state.action = result.action
    state.documents_used = result.documents_used or []
    state.search_queries = result.web_search_queries or []
    state.attempts += 1
    return state

async def rephrase_question(state: AgentState) -> AgentState:
    prompt = build_rephrase_prompt(state)
    with open("rephrase_prompt.txt", "w", encoding="utf-8") as f:
        for msg in prompt:
            role = msg.__class__.__name__.replace("Message", "").upper()
            f.write(f"{role}:\n{msg.content}\n\n{'-'*40}\n\n")

    structured_llm = llm.with_structured_output(REPHRASELLMOutput)
    start_time = time.time()
    result: REPHRASELLMOutput = await structured_llm.ainvoke(prompt)
    end_time = time.time()
    print("Rephrase result: ", result)
    print(f"Rephrase response time: {end_time - start_time:.2f} seconds")
    print("Rephrase prompt: ", prompt)
    rephrased = result.rephrased_question
    with open("rephrase_result.json", "w", encoding="utf-8") as f:
        json.dump(result.model_dump(), f, indent=4)

    state.messages.append(
        HumanMessage(
            content=f"Rephrasing question: {state.question}"
        )
    )
    state.question = rephrased
    state.rephrases += 1
    # state.messages.append(HumanMessage(content=rephrased))
    return state

async def web_search(state: AgentState) -> AgentState:
    queries = state.search_queries

    results = await parallel_search(queries, search_tool)
    print("Web search results: ", results)
    with open("web_search_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)
    state.web_search = True
    state.documents = []
    state.messages.append(
        HumanMessage(content=f"Web search initiated for queries: {queries}")
    )
    state.web_search_attempts += 1
    state.search_queries_results = results

    state.messages.append(HumanMessage(content=f"Web search results: {results}"))

    return state

def failure(state: AgentState) -> AgentState:
    """ 
    Handles the failure case when no action can be taken.
    """
    failure_message = (
        "I am unable to answer your question at this time. "
        "Please try rephrasing or asking a different question."
    )
    state.messages.append(AIMessage(content=failure_message))
    state.answer = failure_message
    # state["action"] = "failure"
    return END

async def failure(state: AgentState) -> AgentState:
    failure_message = (
        "I am unable to answer your question at this time. "
        "Please try rephrasing or asking a different question."
    )
    state.messages.append(AIMessage(content=failure_message))
    state.answer = failure_message
    return state

def get_recent_history(full_history: List[Dict[str, str]], turns: int = 2) -> List[Dict[str, str]]:
    """
    Returns the most recent conversation turns from the full history.
    Each turn consists of a user message and an assistant response.
    """
    if len(full_history) < turns * 2:
        return full_history
    # Get the last 'turns' pairs of user and AI messages
    recent_history = full_history[-(turns * 2):]
    return recent_history

async def rewrite_query(state: AgentState) -> AgentState:
    """
    Rewrites the user's question for semantic vector search.
    This function uses the most recent conversation turns to rewrite the question.
    """
    prompt = build_rewrite_prompt(state)
    with open("rewrite_query.txt", "w", encoding="utf-8") as f:
        for msg in prompt:
            role = msg.__class__.__name__.replace("Message", "").upper()
            f.write(f"{role}:\n{msg.content}\n\n{'-'*40}\n\n")

    structured_llm = llm.with_structured_output(REWRITELLMOutput)
    start_time = time.time()
    result: REWRITELLMOutput = await structured_llm.ainvoke(prompt)
    end_time = time.time()
    print("Rewrite result: ", result)
    print(f"Rewrite response time: {end_time - start_time:.2f} seconds")
    rewritten_query = result.rewritten_query
    with open("rewrite_result.json", "w", encoding="utf-8") as f:
        json.dump(result.model_dump(), f, indent=4)
    # state.messages.append(
    #     HumanMessage(
    #         content=f"Rewriting question for semantic search: {state.question}"
    #     )
    # )
    # state.messages.append(HumanMessage(content=f"Rewritten query: {rewritten_query}"))
    state.retrieval_query = rewritten_query
    return state

async def retriever(state: AgentState) -> AgentState:
    """ Retrieves documents based on the user's question.
    This is a placeholder function that simulates document retrieval.
    """
    print("SLEEPING "*8)
    start_time = time.time()
    doc_retriever = get_user_retriever(state.user_id, k=10) # try different k values
    end_time = time.time()
    print(f"Initialized retriever in {end_time - start_time:.2f} seconds for user {state.user_id}")

    start_time = time.time()
    retrieved_docs = await doc_retriever.ainvoke(state.retrieval_query or state.question)
    end_time = time.time()
    print(f"Retrieved {len(retrieved_docs)} documents in {end_time - start_time:.2f} seconds for user {state.user_id}")
    retrieved_docs = [doc.model_dump() for doc in retrieved_docs]
    # print("docs retrieved: ", retrieved_docs)
    with open(f"retrieved_docs_{state.user_id}.json", "w") as f:
        json.dump(retrieved_docs, f)
    state.documents = retrieved_docs
    return state

# def router(state: AgentState) -> str:
#     if state["action"] == "answer":
#         print("Answering the question")
#         return {"next" : ANSWER}
#     elif state["action"] == "rephrase_question":
#         if state.get("rephrases", 0) < MAX_REPHRASE:
#             print("Rephrasing the question")
#             return {"next": REPHRASE}
#         else:
#             print("Max rephrases reached, initiating web search")
#             return {"next": WEB_SEARCH
#                     if state.get("web_search_attempts", 0) < MAX_WEB_SEARCH
#                     else {"next": FAILURE}}

#     elif state["action"] == "web_search":
#         print("Initiating web search")
#         return (
#             {"next": WEB_SEARCH} if state.get("web_search_attempts", 0) < MAX_WEB_SEARCH else {"next": FAILURE}
#         )
#     return ANSWER



def router(state: AgentState) -> str: 
    if state.action == "answer":
        print("Answering the question")
        return ANSWER 

    elif state.action == "rephrase_question":
        if state.rephrases < MAX_REPHRASE:
            print("Rephrasing the question")
            return REPHRASE
        else:
            print("Max rephrases reached, returning failure")
            return FAILURE

    elif state.action == "web_search":
        print("Initiating web search")
        if state.web_search_attempts < MAX_WEB_SEARCH:
            return WEB_SEARCH
        else:
            return FAILURE

    return ANSWER
# Building the state graph

graph_builder = StateGraph(AgentState)

graph_builder.add_node(REWRITE_QUERY, rewrite_query)
graph_builder.add_node(RETRIEVER, retriever)
graph_builder.add_node(GENERATE, generate)
graph_builder.add_node(ROUTER, router)
graph_builder.add_node(REPHRASE, rephrase_question)
graph_builder.add_node(WEB_SEARCH, web_search)
graph_builder.add_node(ANSWER, lambda state: END)
graph_builder.add_node(FAILURE, failure)

graph_builder.set_entry_point(REWRITE_QUERY)

graph_builder.add_edge(REWRITE_QUERY, RETRIEVER)
graph_builder.add_edge(RETRIEVER, GENERATE)

graph_builder.add_conditional_edges(
    GENERATE,
    router,
    {
        ANSWER: END,      
        REPHRASE: REPHRASE,
        WEB_SEARCH: WEB_SEARCH,
        FAILURE: FAILURE,
    }
)
graph_builder.add_edge(REPHRASE, REWRITE_QUERY)
graph_builder.add_edge(WEB_SEARCH, GENERATE)
graph_builder.add_edge(FAILURE, END)

Agent = graph_builder.compile()
