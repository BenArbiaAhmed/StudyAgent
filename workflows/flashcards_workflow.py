from langchain_google_genai import ChatGoogleGenerativeAI
from memory.flashcards_agent_state import AgentState
from langchain_core.prompts import ChatPromptTemplate
from response_format.flashcards_response_format import FlashcardDeck, Critique
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.5,
)


def generator_node(state: AgentState):
    """First pass generation."""
    print("GENERATING CARDS")
    prompt = ChatPromptTemplate.from_template(
        "Generate high-quality flashcards based on this text: {text}"
    )
    chain = prompt | llm.with_structured_output(FlashcardDeck)
    result = chain.invoke({"text": state["source_text"]})
    
    return {"deck": result, "iteration_count": 1}

def critic_node(state: AgentState):
    """Reviews the cards for quality."""
    print("CRITIQUING CARDS")
    deck_content = "\n".join([f"Q: {c.front} | A: {c.back}" for c in state["deck"].cards])
    
    prompt = ChatPromptTemplate.from_template(
        """You are a harsh educational critic. Review these flashcards:
        {deck}
        
        Criteria:
        1. Answers must be concise (under 20 words).
        2. No "Yes/No" questions allowed.
        3. Information must be accurate based on the source text.
        
        If they violate these rules, set 'needs_revision' to True."""
    )
    
    chain = prompt | llm.with_structured_output(Critique)
    result = chain.invoke({"deck": deck_content})
    
    return {
        "critique": result.critique_text, 
        "revision_needed": result.needs_revision
    }

def refiner_node(state: AgentState):
    """Fixes the cards based on feedback."""
    print("REFINING CARDS")
    deck_content = "\n".join([f"Q: {c.front} | A: {c.back}" for c in state["deck"].cards])
    
    prompt = ChatPromptTemplate.from_template(
        """Refine these flashcards based on the critique.
        
        Original Text: {source}
        Current Cards: {deck}
        Critique: {critique}
        
        Output the corrected FlashcardDeck."""
    )
    
    chain = prompt | llm.with_structured_output(FlashcardDeck)
    result = chain.invoke({
        "source": state["source_text"],
        "deck": deck_content,
        "critique": state["critique"]
    })
    
    return {"deck": result, "iteration_count": state["iteration_count"] + 1}


def should_continue(state: AgentState):
    """Decides whether to loop or end."""
    if state["iteration_count"] > 3:
        print("MAX ITERATIONS REACHED")
        return "end"
    
    if state["revision_needed"]:
        return "refine"
    
    print("QUALITY CHECKS PASSED")
    return "end"

workflow = StateGraph(AgentState)

workflow.add_node("generator", generator_node)
workflow.add_node("critic", critic_node)
workflow.add_node("refiner", refiner_node)

workflow.set_entry_point("generator")

workflow.add_edge("generator", "critic")
workflow.add_conditional_edges(
    "critic",
    should_continue,
    {
        "refine": "refiner",
        "end": END
    }
)
workflow.add_edge("refiner", "critic")

app = workflow.compile()

# Run the workflow
result = app.invoke({
    "source_text": """"
    """,
    "deck": None,
    "critique": None,
    "revision_needed": False,
    "iteration_count": 0
})

final_deck = result["deck"]
for card in final_deck.cards:
    print(f"Q: {card.front}")
    print(f"A: {card.back}\n")