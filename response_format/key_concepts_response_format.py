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
    significance: str = Field(description="Why this concept matters")
    difficulty: DifficultyLevel
    prerequisites: List[str] = Field(default=[], description="Required prior concepts")
    key_points: List[str] = Field(description="3-5 essential facts")
    examples: List[str] = Field(default=[], description="Concrete examples")

class ConceptList(BaseModel):
    concepts: List[Concept] = Field(description="List of key concepts extracted from course material")