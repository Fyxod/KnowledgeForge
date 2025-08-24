import requests
from typing import Any, Dict, List, Optional
from langchain_core.language_models.llms import LLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel


class ExternalApiLLM(LLM):
    """LangChain LLM wrapper for an external API endpoint."""

    api_url: str
    headers: Optional[Dict[str, str]] = None

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs,
    ) -> str:
        payload = {"prompt": prompt, **kwargs}
        resp = requests.post(self.api_url, json=payload, headers=self.headers)

        if resp.status_code != 200:
            raise ValueError(f"API Error {resp.status_code}: {resp.text}")

        data = resp.json()
        
        return data.get("output", "")

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        return {"api_url": self.api_url}

    @property
    def _llm_type(self) -> str:
        return "external_api_llm"


def invoke_llm(model_url: str, response_schema: BaseModel, contents: str, headers: Optional[Dict[str, str]] = None):
    """
    Invokes the external API LLM with structured output.

    Args:
        model_url: API endpoint for the LLM
        response_schema: Pydantic model describing expected response
        contents: User input / prompt
        headers: Optional request headers

    Returns:
        Parsed object according to response_schema
    """
    llm = ExternalApiLLM(api_url=model_url, headers=headers)

    parser = JsonOutputParser(pydantic_object=response_schema)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant that always responds in JSON."),
        ("user", "{input}")
    ])

    chain = prompt | llm.with_structured_output(response_schema)

    return chain.invoke({"input": contents})