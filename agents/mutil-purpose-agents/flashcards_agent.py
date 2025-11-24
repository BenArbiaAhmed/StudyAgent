from langchain.agents import create_agent
from middleware.dynamic_model import basic_model, dynamic_model_selection
from response_format.flashcards_response_format import FlashcardDeck

agent=create_agent(
    model=basic_model,
    middleware=[dynamic_model_selection],
    tools=[],
)