from langchain.agents.middleware import AgentMiddleware
from langchain.tools import ToolRuntime

class SearchContextMiddleware(AgentMiddleware):
    class State:
        search_history: list
        previous_results: dict
    
    state_schema = State
    
    def before_model(self, state, runtime: ToolRuntime):
        search_history = state.get('search_history', [])
        messages = state.get('messages', [])
        if search_history:
            context = f"Previous searches in this session: {', '.join(search_history[-3:])}."
            return {
                "messages": messages + [{
                    "role": "system",
                    "content": f"{context} Use this context to provide more relevant answers."
                }]
            }
        return None
    
    def after_model(self, state, runtime):
        search_history = state.get('search_history', [])
        messages = state.get('messages', [])
        latest_message = messages[-1] if messages else None
        if hasattr(latest_message, 'tool_calls') and latest_message.tool_calls:
            for tool_call in latest_message.tool_calls:
                if tool_call.get('name') == 'web_search':
                    query = tool_call.get('args', {}).get('query', '')
                    return {
                        "search_history": search_history + [query]
                    }
        return None