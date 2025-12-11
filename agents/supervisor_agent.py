from typing import Annotated, TypedDict, Literal, Any
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, AnyMessage
from prompts.system_prompts.supervisor_agent_prompt import SUPERVISOR_SYSTEM_PROMPT
from agents.analyzer_agent import analyzer_agent
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
        
        # Extract the first valid keyword found using word boundaries
        match = re.search(r'\b(analyzer|rag|flashcards|flashcard|end)\b', response)
        if match:
            # Normalize 'flashcard' to 'flashcards'
            keyword = match.group(1)
            if keyword == "flashcard":
                keyword = "flashcards"
            return {"next": keyword}
        
        # If we find the exact word at the start (legacy fallback)
        match_start = re.match(r'^(analyzer|rag|flashcards|end)', response)
        if match_start:
            return {"next": match_start.group(1)}
        
        # Ultimate fallback - default to RAG if we have a document, otherwise end
        print(f"Warning: Could not parse supervisor response: '{response}'. Defaulting to 'rag'.")
        return {"next": "rag" if state.get("pdf_markdown") else "end"}
        
    except Exception as e:
        print(f"Supervisor error: {e}. Defaulting to 'end'.")
        return {"next": "end"}


    
def decide_next_agent(state: SupervisorState):
    return state["next"]


def analyzer_node(state: SupervisorState): 
    try:
        pdf_content = state.get("pdf_markdown", "")
        if state["messages"]:
            last_message = state["messages"][-1].content
        else:
            last_message = ""
        
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
    except Exception as e:
        error_msg = f"Error in analyzer: {str(e)}"
        print(error_msg)
        return {"messages": [AIMessage(content=f"I encountered an error while analyzing the document: {str(e)}")]}

def rag_node(state: SupervisorState):
    print("--- RAG Node Working ---")
    try:
        vector_store = state.get("vector_store") 
        
        if vector_store is None:
            return {"messages": [AIMessage(content="I cannot perform RAG because no document has been processed.")]}

        retrieve_context = create_retrieve_context_tool(vector_store)
        
        rag_agent = create_rag_agent(retrieve_context)
        
        result = rag_agent.invoke({"messages": state["messages"]}) 
        
        last_message = result["messages"][-1]
        content = last_message.content
        
        if isinstance(content, list):
            text_content = ""
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_content += block.get("text", "")
            content = text_content
        
        return {"messages": [AIMessage(content=content)]}
    except Exception as e:
        error_msg = f"Error in RAG: {str(e)}"
        print(error_msg)
        return {"messages": [AIMessage(content=f"I encountered an error while searching the document: {str(e)}")]}

def flashcards_node(state: SupervisorState):
    print("Flashcards Pipeline Working\n")
    try:
        if not state.get("pdf_markdown"):
            return {"messages": [AIMessage(content="I cannot generate flashcards because no document has been processed.")]}
        
        result = flashcards_app.invoke({
            "source_text": state["pdf_markdown"],
            "deck": None,
            "critique": None,
            "revision_needed": False,
            "iteration_count": 0
        })
        
        if not result.get("deck") or not result["deck"].cards:
            return {"messages": [AIMessage(content="I couldn't generate flashcards from the provided content. Please try again.")]}
        
        deck_str = "\n".join([f"**Q:** {c.front}\n**A:** {c.back}\n" 
                             for c in result["deck"].cards])
        
        response = f"Here are your flashcards ({len(result['deck'].cards)} cards):\n\n{deck_str}"
        return {"messages": [AIMessage(content=response)]}
    except Exception as e:
        error_msg = f"Error generating flashcards: {str(e)}"
        print(error_msg)
        return {"messages": [AIMessage(content=f"I encountered an error while generating flashcards: {str(e)}")]}

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