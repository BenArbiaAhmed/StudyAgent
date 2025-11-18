from dataclasses import dataclass
from typing import TypedDict

@dataclass
class Context(TypedDict):
    """Custom runtime context schema."""
    user_id: str
    user_role: str