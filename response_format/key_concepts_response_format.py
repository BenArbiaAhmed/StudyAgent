from pydantic import BaseModel, Field
from typing import List
from enum import Enum

class DifficultyLevel(str, Enum):
    FOUNDATIONAL = "foundational"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

class Concept(BaseModel):
    name: str = Field(description="Clear, concise concept name")
    definition: str = Field(description="Precise explanation in 2-3 sentences")
    examples: List[str] = Field(default=[], description="Concrete examples")

class ConceptList(BaseModel):
    concepts: List[Concept] = Field(description="List of key concepts extracted from course material")