from langchain.agents import create_agent
from middleware.dynamic_model import basic_model, dynamic_model_selection
from response_format.key_concepts_response_format import ConceptList
from memory.memory import checkpointer
from tools.analyzer_tools.pdf_loader import extract_pdf_content
from langchain_core.runnables import RunnableLambda
from response_format.key_concepts_response_format import ConceptList
from tools.analyzer_tools.web_search_tool import web_search
from prompts.system_prompts.analyzer_agent_prompt import CONCEPT_EXTRACTION_WITH_SEARCH_PROMPT


agent = create_agent(
            model=basic_model,
            tools=[
                extract_pdf_content,      
                web_search   
            ],
            response_format=ConceptList,
            system_prompt=CONCEPT_EXTRACTION_WITH_SEARCH_PROMPT
        )

query = (
    "What should I retain from this PDF: C:/Users/ahmed/Projects/multi-purpose-ai-agent/data/logique.pdf"
)

for event in agent.stream(
    {"messages": [{"role": "user", "content": query}]},
    stream_mode="values",
):
    event["messages"][-1].pretty_print()