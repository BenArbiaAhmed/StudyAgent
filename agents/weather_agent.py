from dotenv import load_dotenv
from langchain.agents import create_agent
from prompts.system_prompts.weather_forecast_prompt import SYSTEM_PROMPT
from tools.weather_forecast_tools import *
from data_classes.weather_response_format import ResponseFormat
from langchain.agents.structured_output import ProviderStrategy
from memory.memory import checkpointer
from middleware.dynamic_model import basic_model, dynamic_model_selection
from middleware.handle_errors import handle_tool_errors

load_dotenv()



agent = create_agent(
    model=basic_model,
    system_prompt=SYSTEM_PROMPT,
    tools=[get_user_location, get_weather_for_location],
    context_schema=Context,
    response_format=ResponseFormat,
    checkpointer=checkpointer,
    middleware=[handle_tool_errors, dynamic_model_selection]
)

# `thread_id` is a unique identifier for a given conversation.
config = {"configurable": {"thread_id": "1"}}
context = Context(user_id="1")

response = agent.invoke(
    {"messages": [{"role": "user", "content": f"what is the weather in M'saken ?"}]},
    config=config,
    context=context
)

print(response['structured_response'])