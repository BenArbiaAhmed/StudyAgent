from typing import Annotated, TypedDict, Literal, Any
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, AnyMessage
from prompts.system_prompts.supervisor_agent_prompt import SUPERVISOR_SYSTEM_PROMPT
from agents.analyzer_agent import analyzer_agent
from agents.rag_agent import create_rag_agent
from workflows.flashcards_workflow import flashcards_app
from agents.rag_agent import create_rag_agent
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from middleware.dynamic_model import basic_model
from tools.analyzer_tools.semantic_search import create_retrieve_context_tool
import re
class SupervisorState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    pdf_markdown: str
    vector_store: Any 
    next: Literal["analyzer", "rag", "flashcards", "end"]

class RouteDecision(BaseModel):
    """Decision on which agent to route to next"""
    next: Literal["analyzer", "rag", "flashcards", "end"] = Field(
        description="The next agent to route to based on user intent"
    )

# Create supervisor chain
supervisor_prompt = ChatPromptTemplate.from_messages([
    ("system", SUPERVISOR_SYSTEM_PROMPT),
    ("placeholder", "{messages}")
])

# supervisor_chain = supervisor_prompt | basic_model.with_structured_output(RouteDecision)

# def supervisor_node(state: SupervisorState):
#     messages = state["messages"]
#     result = supervisor_chain.invoke({"messages": messages})
#     return {"next": result.next}

supervisor_chain = supervisor_prompt | basic_model

def supervisor_node(state: SupervisorState):
    messages = state["messages"]
    
    try:
        result = supervisor_chain.invoke({"messages": messages})
        response = result.content.strip().lower()
        
        # Extract the first valid keyword found
        if "flashcards" in response or "flashcard" in response:
            return {"next": "flashcards"}
        elif "analyzer" in response:
            return {"next": "analyzer"}
        elif "rag" in response:
            return {"next": "rag"}
        elif "end" in response:
            return {"next": "end"}
        
        # If we find the exact word at the start
        match = re.match(r'^(analyzer|rag|flashcards|end)', response)
        if match:
            return {"next": match.group(1)}
        
        # Fallback
        print(f"⚠️ Could not parse: '{response}', defaulting to rag")
        return {"next": "rag"}
        
    except Exception as e:
        print(f"⚠️ Supervisor error: {e}")
        return {"next": "rag"}



def decide_next_agent(state: SupervisorState):
    return state["next"]


def analyzer_node(state: SupervisorState): 
    pdf_content = state.get("pdf_markdown", "")
    last_message = state["messages"][-1].content
    
    combined_message = HumanMessage(
        content=f"""{last_message}
        Here is the PDF content to analyze:
        <pdf_content>
        {pdf_content}
        </pdf_content>
        Please analyze this content and extract key concepts."""
    )
    
    result = analyzer_agent.invoke({"messages": [combined_message]})
    
    if isinstance(result, dict) and "messages" in result:
        response_content = result["messages"][-1].content
    else:
        response_content = str(result)

    return {"messages": [AIMessage(content=response_content)]}

def rag_node(state: SupervisorState):
    print("--- RAG Node Working ---")
    vector_store = state.get("vector_store") 
    
    if vector_store is None:
        return {"messages": [AIMessage(content="I cannot perform RAG because no document has been processed.")]}

    retrieve_context = create_retrieve_context_tool(vector_store)
    tools = [retrieve_context]
    
    rag_agent = create_rag_agent(
        retrieve_context
    )
    
    result = rag_agent.invoke({"messages": state["messages"]}) 
    
    last_message = result["messages"][-1]
    content = last_message.content

    return {"messages": [AIMessage(content=content)]}

def flashcards_node(state: SupervisorState):
    print("Flashcards Pipeline Working\n")
    result = flashcards_app.invoke({
        "source_text": state["pdf_markdown"],
        "deck": None,
        "critique": None,
        "revision_needed": False,
        "iteration_count": 0
    })
    
    deck_str = "\n".join([f"**Q:** {c.front}\n**A:** {c.back}\n" 
                         for c in result["deck"].cards])
    
    response = f"Here are your flashcards ({len(result['deck'].cards)} cards):\n\n{deck_str}"
    return {"messages": [AIMessage(content=response)]}

# Build workflow
workflow = StateGraph(SupervisorState)

workflow.add_node("supervisor", supervisor_node)
workflow.add_node("analyzer", analyzer_node)
workflow.add_node("rag", rag_node)
workflow.add_node("flashcards", flashcards_node)

workflow.set_entry_point("supervisor")

workflow.add_conditional_edges(
    "supervisor",
    decide_next_agent,
    {
        "analyzer": "analyzer",
        "rag": "rag",
        "flashcards": "flashcards",
        "end": END
    }
)

workflow.add_edge("analyzer", END)
workflow.add_edge("rag", END)
workflow.add_edge("flashcards", END)

supervisor_app = workflow.compile()


# pdf_path = "C:/Users/ahmed/Projects/multi-purpose-ai-agent/data/logique.pdf"
# markdown = extract_pdf_content(pdf_path)

# initial_state = {
#     "messages": [HumanMessage(content="Génerer des flashcards pour ce pdf")],
#     "pdf_markdown": markdown,
#     "next": "supervisor"
# }

# for chunk in supervisor_app.stream(initial_state, stream_mode="values"):
#     if "messages" in chunk:
#         last_message = chunk["messages"][-1]
        
#         # Only print AI messages (skip human messages with context)
#         if isinstance(last_message, AIMessage):
#             last_message.pretty_print()