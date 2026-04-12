from langchain.agents import create_agent
from middleware.dynamic_model import basic_model, dynamic_model_selection
from response_format.key_concepts_response_format import ConceptList
from memory.memory import checkpointer
from langchain_core.runnables import RunnableLambda
from tools.analyzer_tools.web_search_tool import web_search
from tools.analyzer_tools.firecrawl_tool import web_scrape_for_concepts
from prompts.system_prompts.analyzer_agent_prompt import CONCEPT_EXTRACTION_WITH_SEARCH_PROMPT


analyzer_agent = create_agent(
            model=basic_model,
            tools=[      
                web_search,
                web_scrape_for_concepts
            ],
            response_format=ConceptList,
            system_prompt=CONCEPT_EXTRACTION_WITH_SEARCH_PROMPT
        )

# pdf_content = extract_pdf_content("C:/Users/ahmed/Projects/multi-purpose-ai-agent/data/logique.pdf")

# query = (
#     f"""What should I retain from this PDF ?
#     <pdf_content>
#     {pdf_content}
#     </pdf_content>
#     """
# )

# for event in analyzer_agent.stream(
#     {"messages": [{"role": "user", "content": query}]},
#     stream_mode="values",
# ):
#     event["messages"][-1].pretty_print()