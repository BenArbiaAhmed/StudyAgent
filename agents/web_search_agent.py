from dotenv import load_dotenv
from langchain.agents import create_agent
from prompts.system_prompts.web_search_prompt import SYSTEM_PROMPT
from tools.web_search_tools import web_search
from data_classes.search_response_format import ResponseFormat
from langchain.agents.structured_output import ProviderStrategy
from data_classes.context import Context
from memory.memory import checkpointer
from middleware.dynamic_model import basic_model, dynamic_model_selection
from middleware.dynamic_system_prompt import user_role_prompt
from middleware.handle_errors import handle_tool_errors
from middleware.search_context import SearchContextMiddleware

load_dotenv()

seen_tool_calls = set()
seen_content = set()


agent = create_agent(
    model=basic_model,
    system_prompt=SYSTEM_PROMPT,
    tools=[web_search],
    context_schema=Context,
    response_format=ResponseFormat,
    checkpointer=checkpointer,
    middleware=[handle_tool_errors, user_role_prompt, dynamic_model_selection, SearchContextMiddleware()]
)

# `thread_id` is a unique identifier for a given conversation.
config = {"configurable": {"thread_id": "2"}}
context = Context(
    user_id="1",
    user_role="beginner"
    )

#uncomment to invoke instead of stream
# response = agent.invoke(
#     {"messages": [{"role": "user", "content": f"What is Tunisia known for ?"}],
#      "search_history": [],
#      "previous_results": {}
#      },
#     config=config,
#     context=context
# )

for chunk in agent.stream({"messages": [{"role": "user", "content": f"What is Tunisia known for ?"}],
     "search_history": [],
     "previous_results": {}
     },
    config=config,
    context=context, stream_mode="values"):
    # Each chunk contains the full state at that point
    latest_message = chunk["messages"][-1]
    
    # Handle tool calls
    if hasattr(latest_message, 'tool_calls') and latest_message.tool_calls:
        for tc in latest_message.tool_calls:
            tc_id = tc.get('id', str(tc))
            if tc_id not in seen_tool_calls:
                print(f"Calling tool: {tc['name']}")
                seen_tool_calls.add(tc_id)
    
    # Handle content
    elif latest_message.content:
        content_hash = hash(str(latest_message.content))
        if content_hash not in seen_content:
            print(f"Agent: {latest_message.content}")
            seen_content.add(content_hash)
