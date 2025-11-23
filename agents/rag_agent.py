from langchain.agents import create_agent
from prompts.system_prompts.rag_agent_prompt import SYSTEM_PROMPT
from middleware.dynamic_model import basic_model, dynamic_model_selection
from tools.analyzer_tools.semantic_search import setup_for_rag, create_retrieve_context_tool

vector_store = setup_for_rag("./data/logique.pdf", "pdf")
retrieve_context = create_retrieve_context_tool(vector_store)
tools = [retrieve_context]
agent = create_agent(
    basic_model, tools,
    system_prompt=SYSTEM_PROMPT,
    middleware=[dynamic_model_selection]
)

query = (
    "Quelle est la porté d'un quantificateur ?"
)

for event in agent.stream(
    {"messages": [{"role": "user", "content": query}]},
    stream_mode="values",
):
    event["messages"][-1].pretty_print()