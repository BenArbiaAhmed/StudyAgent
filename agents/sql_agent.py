from dotenv import load_dotenv
from langchain.agents import create_agent
from memory.memory import checkpointer
from middleware.dynamic_model import basic_model, dynamic_model_selection
from middleware.handle_errors import handle_tool_errors
from utils.database_wrapper import db
from tools.database_tools import create_sql_tools
from prompts.system_prompts.sql_query_prompt import get_system_prompt
from langchain.agents.middleware import HumanInTheLoopMiddleware 
from langgraph.types import Command 

load_dotenv()

tools = create_sql_tools(db, basic_model)
SYSTEM_PROMPT = get_system_prompt(db.dialect, 7)

agent = create_agent(
    model=basic_model,
    system_prompt=SYSTEM_PROMPT,
    tools=tools,
    checkpointer=checkpointer,
    middleware=[
        handle_tool_errors,
        dynamic_model_selection,
        HumanInTheLoopMiddleware( 
            interrupt_on={"sql_db_query": True}, 
            description_prefix="Tool execution pending approval", 
        ), ]
)

config = {"configurable": {"thread_id": "2"}}
question = "Which genre on average has the longest tracks?"

captured_interrupt = None

    
for step in agent.stream(
    {"messages": [{"role": "user", "content": question}]},
    stream_mode="values",
    config=config
):
    if "messages" in step:
        step["messages"][-1].pretty_print()
    elif "__interrupt__" in step:
        captured_interrupt = step["__interrupt__"][0]
        print("\n[!] PAUSED: The agent wants to execute a tool.")
        for request in captured_interrupt.value["action_requests"]:
            print(f"    Request: {request['description']}")


if captured_interrupt:
    print("\n--- User Action Needed ---")
    user_choice = input("Do you want to approve this action? (yes/no): ").strip().lower()
    
    resume_payload = None

    if user_choice in ["y", "yes", "approve"]:
        print(">> Approving...")
        resume_payload = {"decisions": [{"type": "approve"}]}
    else:
        print(">> Rejecting...")
        resume_payload = {"decisions": [{"type": "reject"}]}

    print("--- Resuming Execution ---")
    for step in agent.stream(
        Command(resume=resume_payload),
        config=config,
        stream_mode="values",
    ):
        if "messages" in step:
            step["messages"][-1].pretty_print()
        elif "__interrupt__" in step:
            print("INTERRUPTED AGAIN:")
            interrupt = step["__interrupt__"][0]
            for request in interrupt.value["action_requests"]:
                print(request["description"])
else:
    print("\n--- Conversation Finished (No Interrupts) ---")