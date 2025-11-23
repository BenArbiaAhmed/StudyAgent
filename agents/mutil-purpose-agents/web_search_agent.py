from dotenv import load_dotenv
from langchain.agents import create_agent
from prompts.system_prompts.web_search_prompt import SYSTEM_PROMPT
from tools.analyzer_tools.web_search_tool import web_search
from response_format.web_search_response_format import WebSearchResponseFormat
from data_classes.context import Context
from memory.memory import checkpointer
from middleware.dynamic_model import basic_model, dynamic_model_selection
from middleware.dynamic_system_prompt import user_role_prompt
from middleware.handle_errors import handle_tool_errors
from middleware.search_context import SearchContextMiddleware
from utils.rate_limit import rate_limiter

load_dotenv()

seen_tool_calls = set()
seen_content = set()


agent = create_agent(
    model=basic_model,
    system_prompt=SYSTEM_PROMPT,
    tools=[web_search],
    context_schema=Context,
    response_format=WebSearchResponseFormat,
    checkpointer=checkpointer,
    # rate_limiter=rate_limiter,
    middleware=[handle_tool_errors, user_role_prompt, dynamic_model_selection, SearchContextMiddleware()]
)

# `thread_id` is a unique identifier for a given conversation.
config = {"configurable": {"thread_id": "2"}}
context = Context(
    user_id="1",
    user_role="beginner"
    )


def run_cli_agent():
    config = {"configurable": {"thread_id": "1"}}
    context = Context(user_id="1",user_role="intermediate")
    
    print("=" * 60)
    print("Web Search Agent")
    print("=" * 60)
    print("Type 'quit', 'exit', or 'bye' to end the conversation\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye!")
            break
        
        if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye']:
            print("\nAgent: Thanks for chatting! Stay curious!")
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
                print(f"Agent: {final_structured_response.information}")
                
                if final_structured_response.sources:
                    print(f"Sources: {final_structured_response.sources}")
            
            print()              
        except Exception as e:
            print(f"Error: {str(e)}\n")

if __name__ == "__main__":
    run_cli_agent()
