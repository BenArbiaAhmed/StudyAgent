from dotenv import load_dotenv
from langchain.agents import create_agent
from prompts.system_prompts.weather_forecast_prompt import SYSTEM_PROMPT
from tools.weather_forecast_tools import *
from response_format.weather_response_format import WeatherResponseFormat
from memory.memory import checkpointer
from middleware.dynamic_model import basic_model, dynamic_model_selection
from middleware.handle_errors import handle_tool_errors

load_dotenv()

agent = create_agent(
    model=basic_model,
    system_prompt=SYSTEM_PROMPT,
    tools=[get_weather_for_location],
    context_schema=Context,
    response_format=WeatherResponseFormat,
    checkpointer=checkpointer,
    middleware=[handle_tool_errors, dynamic_model_selection]
)

def run_cli_agent():
    config = {"configurable": {"thread_id": "1"}}
    context = Context(user_id="1")
    
    print("=" * 60)
    print("Weather Forecast Agent (with puns!)")
    print("=" * 60)
    print("Type 'quit', 'exit', or 'bye' to end the conversation\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye!")
            break
        
        if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye']:
            print("\nAgent: Thanks for chatting! Stay weather-wise!")
            break
        
        if not user_input:
            continue
        
        print()
        
        try:
            seen_tool_calls = set()
            final_structured_response = None
            
            for chunk in agent.stream(
                {
                    "messages": [{"role": "user", "content": user_input}],
                    "search_history": [],
                    "previous_results": {}
                },
                config=config,
                context=context,
                stream_mode="values"
            ):
                latest_message = chunk["messages"][-1]
                
                if hasattr(latest_message, 'tool_calls') and latest_message.tool_calls:
                    for tc in latest_message.tool_calls:
                        tc_id = tc.get('id', str(tc))
                        if tc_id not in seen_tool_calls:
                            print(f"Calling tool: {tc['name']}")
                            seen_tool_calls.add(tc_id)
                
                if 'structured_response' in chunk:
                    final_structured_response = chunk['structured_response']
            
            if final_structured_response:
                print(f"Agent: {final_structured_response.punny_response}")
                
                if final_structured_response.weather_conditions:
                    print(f"Weather: {final_structured_response.weather_conditions}")
            
            print()              
        except Exception as e:
            print(f"Error: {str(e)}\n")

if __name__ == "__main__":
    run_cli_agent()