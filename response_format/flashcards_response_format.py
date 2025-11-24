from pydantic import BaseModel, Field
from typing import List

class Flashcard(BaseModel):
    front: str = Field(description="Question or concept")
    back: str = Field(description="Answer or definition")

class FlashcardDeck(BaseModel):
    cards: List[Flashcard]

class Critique(BaseModel):
    """The output of the Critic node."""
    critique_text: str = Field(description="Specific feedback on what to fix.")
    needs_revision: bool = Field(description="True if the deck needs changes, False if perfect.")