from typing import Annotated, TypedDict, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, AnyMessage
from prompts.system_prompts.supervisor_agent_prompt import SUPERVISOR_SYSTEM_PROMPT
from agents.analyzer_agent import analyzer_agent
from agents.rag_agent import rag_agent
from workflows.flashcards_workflow import flashcards_app

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from middleware.dynamic_model import basic_model

class SupervisorState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    pdf_markdown: str
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

supervisor_chain = supervisor_prompt | basic_model.with_structured_output(RouteDecision)

def supervisor_node(state: SupervisorState):
    messages = state["messages"]
    result = supervisor_chain.invoke({"messages": messages})
    return {"next": result.next}

def decide_next_agent(state: SupervisorState):
    return state["next"]

def analyzer_node(state: SupervisorState):
    print("Analyzer Node Working\n")
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
    return {"messages": [AIMessage(content=str(result))]}

def rag_node(state: SupervisorState):
    print("Rag Node Working\n")
    pdf_content = state.get("pdf_markdown", "")
    enhanced_messages = state["messages"].copy()
    
    if pdf_content:
        enhanced_messages.append(HumanMessage(
            content=f"Context:\n\n<pdf_content>\n{pdf_content}\n</pdf_content>"
        ))
    
    result = rag_agent.invoke({"messages": enhanced_messages})
    return {"messages": [AIMessage(content=result)]}

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

workflow.add_edge("analyzer", "supervisor")
workflow.add_edge("rag", "supervisor")
workflow.add_edge("flashcards", "supervisor")

supervisor_app = workflow.compile()

# Test
from tools.analyzer_tools.pdf_loader import extract_pdf_content

pdf_path = "C:/Users/ahmed/Projects/multi-purpose-ai-agent/data/logique.pdf"
markdown = extract_pdf_content(pdf_path)

initial_state = {
    "messages": [HumanMessage(content="Can you tell me what this document is about?")],
    "pdf_markdown": markdown,
    "next": "supervisor"
}

for chunk in supervisor_app.stream(initial_state, stream_mode="values"):
    if "messages" in chunk:
        chunk["messages"][-1].pretty_print()