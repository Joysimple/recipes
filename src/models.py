from dataclasses import dataclass, field
from typing import List


@dataclass
class RecipeSection:
    title: str
    body: List[str]
    is_ingredients: bool = False


@dataclass
class Recipe:
    title: str
    subtitle: str = ""
    sections: List[RecipeSection] = field(default_factory=list)
    start_page: int = 0
