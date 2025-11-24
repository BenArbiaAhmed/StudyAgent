from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain.agents.middleware import AgentState, before_model, after_model
from typing_extensions import NotRequired
from typing import Any
from langgraph.runtime import Runtime
from typing import TypedDict
from response_format.flashcards_response_format import FlashcardDeck


class AgentState(TypedDict):
    source_text: str
    deck: FlashcardDeck
    critique: str
    revision_needed: bool
    iteration_count: int