from linkup_monitor.monitor import MonitoredLinkupClient, LinkupClient
from linkup_monitor.add_types import SearchInput
from linkup_monitor.postgres_client import PostgresClient
from llama_index.core.llms import ChatMessage
from pydantic import BaseModel, Field
from llama_index.llms.groq import Groq
from typing import Tuple
import json

with open("/run/secrets/groq_key", "r") as f:
    groq_api_key = f.read()
f.close()

with open("/run/secrets/linkup_key", "r") as g:
    linkup_api_key = g.read()
g.close()

with open("/run/secrets/postgres_user", "r") as h:
    postgres_user = h.read()
h.close()

with open("/run/secrets/postgres_db", "r") as i:
    postgres_db = i.read()
i.close()

with open("/run/secrets/postgres_password", "r") as j:
    postgres_password = j.read()
j.close()

with open("/run/secrets/postgres_host", "r") as k:
    postgres_host = k.read()
k.close()

linkup_client = LinkupClient(api_key=linkup_api_key)
postgres_client = PostgresClient(host=postgres_host, port=5432, user=postgres_user, database=postgres_db, password=postgres_password)
monitored_client = MonitoredLinkupClient(linkup_client=linkup_client, postgres_client=postgres_client)

class EvaluateContext(BaseModel):
    context_is_ok: int = Field(description="Is the context relevant to the question? Give a score between 0 and 100")
    reasons: str = Field(description="Explanations for the given evaluation")

class ExpandedQuery(BaseModel):
    queries: list[str] = Field(description="The list of three queries in which we expanded the original one")

llm = Groq(model="meta-llama/llama-4-scout-17b-16e-instruct", api_key=groq_api_key)
llm_eval = llm.as_structured_llm(EvaluateContext)
llm_expand = llm.as_structured_llm(ExpandedQuery)
llm_guard = Groq(model="meta-llama/llama-guard-4-12b", api_key=groq_api_key)

hazard_categories = {
    "S1": "Violent Crimes",
    "S2": "Non-Violent Crimes",
    "S3": "Sex-Related Crimes",
    "S4": "Child Sexual Exploitation",
    "S5": "Defamation",
    "S6": "Specialized Advice",
    "S7": "Privacy",
    "S8": "Intellectual Property",
    "S9": "Indiscriminate Weapons",
    "S10": "Hate",
    "S11": "Suicide & Self-Harm",
    "S12": "Sexual Content",
    "S13": "Elections",
    "S14": "Code Interpreter Abuse"
}

async def guard_prompt(prompt: str) -> Tuple[bool, str]:
    messages = [ChatMessage.from_str(content=prompt)]
    response = await llm_guard.achat(messages)
    txt = response.message.blocks[0].text
    if txt != "safe":
        category = txt.split("\n")[1]
        return False, f"Your prompt contains content which is linkable to: {hazard_categories[category]}\n\nI cannot reply to prompts containing this kind of content, so please provide me with something else"
    return True, "Prompt is safe"  

async def expand_query(query: str) -> list:
    """Useful to expand a query into three sub-queries to search the web with and gather as much information as possible about the original query
    
    Args:
        query (str): the query to be expanded"""
    messages = [ChatMessage.from_str(content="You are a query expansion assistant. Given a query about a topic, you should produce a list of three queries that can be run against the web and would maximize the yield of precise information retrieved from the web about the original query.", role="system"), ChatMessage.from_str(content=f"Can you expand ths query?:'{query}'", role="user"),]
    response = await llm_expand.achat(messages)
    json_response = json.loads(response.message.blocks[0].text)
    return json_response["queries"]

async def deepsearch(query: str) -> str:
    """Useful to search for precise information in the depths of the web when you need to answer advanced and/or complicated questions by the user about a topic they are trying to research.
    
    Args:
        query (str): the query to be searched"""
    response = monitored_client.search(
        data=SearchInput(query=query, output_type='sourcedAnswer', depth='deep')
    )
    answer = response.answer
    sources = response.sources
    bibliography = [f"- [{source.name}]({source.url})" for source in sources]
    sb = "\n".join(bibliography)
    return f"<details>\n\t<summary><b>Sources</b></summary>\n\n{sb}\n\n</details>\n\n{answer}"


async def evaluate_context(original_prompt: str = Field(description="Original prompt provided by the user"), context: str = Field(description="Contextual information from the web")) -> str:
    """
    Useful for evaluating the relevance of retrieved contextual information in light of the user's prompt.

    This tool takes the original user prompt and contextual information as input, and evaluates the relevance of the contextual information. It returns a formatted string with the evaluation scores and reasons for the evaluations.

    Args:
        original_prompt (str): Original prompt provided by the user.
        context (str): Contextual information from the web.
    """
    messages = [ChatMessage.from_str(content=original_prompt, role="user"), ChatMessage.from_str(content=f"Here is some context that I found that might be useful for replying to the user:\n\n{context}", role="assistant"), ChatMessage.from_str(content="Can you please evaluate the relevance of the contextual information (giving it a score between 0 and 100) in light or my original prompt? You should also tell me the reasons for your evaluations.", role="user")]
    response = await llm_eval.achat(messages)
    json_response = json.loads(response.message.blocks[0].text)
    final_response = f"The context provided for the user's prompt is {json_response['context_is_ok']}% relevant.\nThese are the reasons why you are given these evaluations:\n{json_response['reasons']}"
    return final_response

