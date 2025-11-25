from langchain.tools import tool
from agents.rag_agent import rag_agent
from agents.analyzer_agent import analyzer_agent
from workflows.flashcards_workflow import flashcards_app


@tool
def generate_flashcards(request: str) -> str:
    """Generate flashcards from course material.

    Use this when the user wants to create flashcards.
    Handles flashcards generation, criticism and refinement.

    Input: Natural language request (e.g., 'Make Anki flashcards for this course')
    """
    result = flashcards_app.invoke({
    "source_text": request,
    "deck": None,
    "critique": None,
    "revision_needed": False,
    "iteration_count": 0
    })

    final_deck = result["deck"]
    return final_deck


@tool
def extract_key_points(request: str) -> str:
    """Extract key concepts from course material.

    Use this when the user wants to get the most important information / concepts from the studying material.
    Handles concepts extraction, and web search for missing or unclear information.

    Input: Natural language request (e.g., 'What should i retail from this material')
    """
    result = analyzer_agent.invoke({
    "messages": [{"role": "user", "content": request}]
    })
    return result["messages"][-1].text


@tool
def answer_user_questions_from_material(request: str) -> str:
    """Answer the user's questions with information from the course material.

    Use this when the user wants to get answers directly from information provided by the material.
    Handles Retrieval Augmented Generation question answering.

    Input: Natural language request (e.g., 'What is the quadratic formula ?')
    """
    result = rag_agent.invoke({
        "messages": [{"role": "user", "content": request}]
    })
    return result["messages"][-1].text