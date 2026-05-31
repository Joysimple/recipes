import re
from pathlib import Path

from .models import Recipe, RecipeSection


class RecipeParser:
    """Parses Markdown content into structured Recipe objects."""

    @staticmethod
    def parse_content(content: str) -> Recipe:
        content = content.replace("\r\n", "\n")
        lines = content.split("\n")

        # Parse title
        title = "Untitled Recipe"
        if lines:
            title_match = re.search(r"^#\s*(.*)", lines[0])
            if title_match:
                title = title_match.group(1).strip()

        # Parse subtitle
        subtitle = ""
        for line in lines[1:5]:
            sub_match = re.search(r"^\*\*(.*)\*\*", line)
            if sub_match:
                subtitle = sub_match.group(1)
                break

        # Parse sections
        sections = []
        raw_sections = re.split(r"\n##\s+", "\n" + content)
        for raw_sec in raw_sections:
            if not raw_sec.strip() or raw_sec.strip().startswith("# "):
                continue

            sec_lines = raw_sec.strip().split("\n")
            header_text = re.sub(r"^\d+\.\s*", "", sec_lines[0].strip())
            body = [line for line in sec_lines[1:] if line.strip()]

            is_ingredients = "ИНГРЕДИЕНТЫ" in header_text.upper()
            sections.append(
                RecipeSection(
                    title=header_text, body=body, is_ingredients=is_ingredients
                )
            )

        return Recipe(title=title, subtitle=subtitle, sections=sections)

    @classmethod
    def parse_file(cls, file_path: Path) -> Recipe:
        content = file_path.read_text(encoding="utf-8")
        return cls.parse_content(content)
