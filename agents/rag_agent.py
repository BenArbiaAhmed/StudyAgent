from langchain.agents import create_agent
from prompts.system_prompts.rag_agent_prompt import SYSTEM_PROMPT
from middleware.dynamic_model import basic_model, dynamic_model_selection
from tools.analyzer_tools.semantic_search import setup_for_rag, create_retrieve_context_tool


def create_rag_agent(retrieve_context):
    """Factory function to create the RAG agent with a specified PDF path."""
    tools = [retrieve_context]
    rag_agent = create_agent(
        basic_model, tools,
        system_prompt=SYSTEM_PROMPT,
        middleware=[dynamic_model_selection]
    )
    return rag_agent

# query = (
#     "Quelle est la porté d'un quantificateur ?"
# )

# for event in rag_agent.stream(
#     {"messages": [{"role": "user", "content": query}]},
#     stream_mode="values",
# ):
#     event["messages"][-1].pretty_print()