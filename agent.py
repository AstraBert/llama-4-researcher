from tools import deepsearch, evaluate_context, expand_query, guard_prompt
from llama_index.llms.groq import Groq
from llama_index.core.agent.workflow import FunctionAgent, AgentWorkflow, ToolCall, ToolCallResult

with open("/run/secrets/groq_key", "r") as f:
    groq_api_key = f.read()
f.close()

llm = Groq(model="meta-llama/llama-4-scout-17b-16e-instruct", api_key=groq_api_key)

researcher_agent = FunctionAgent(
    llm=llm,
    name = "ResearcherAgent",
    description="An agent that researches the web and creates essays about a given topic based on the information it found",
    system_prompt=f"You are the ResearcherAgent. Your task is to search the web for information about a given topic specified by the user, evsaluate the informmation you retrieved, and finally produce an essay about the topic, making sure to always referencing sources.\n\nPlease, before answering, make sure to understand the context in which the user is acting.\n\nYour workflow must be the following:\n\n1. Expand the query that the user provides you with employing the 'expand_query' tool with, as argument, the original user's query.\n2. Now that you have expanded the query into sub-queries, run the 'deepsearch' tool for each of these queries, retrieving context from the web\n3. Once you gathered information from the web for a sub-query, run the 'evaluate_context' tool. This will tell you how relevant the context is and the reasons for the evaluation. You can keep all the contexts that are more than 70% relevant.\n4. After you have gathered all the information, produce an essay about the topic you are given, basing on the collected context and making sure to cite the sources.\n\nOnce you are done, close the workflow and return the essay to the user.\n\nIMPORTANT INSTRUCTIONS:\n\n- You MUST ALWAYS evaluate the context retrieved from the web",
    tools = [expand_query, deepsearch, evaluate_context],
)

workflow = AgentWorkflow(agents = [researcher_agent], root_agent=researcher_agent.name)

