from pathlib import Path
from typing import List, Optional

from fpdf import FPDF


class FontManager:
    """Handles cross-platform font discovery and registration."""

    POSSIBLE_DIRS = [
        Path("/System/Library/Fonts/Supplemental"),  # MacOS
        Path("/Library/Fonts"),  # MacOS Alternative
        Path("/usr/share/fonts/truetype/msttcorefonts"),  # Ubuntu/Debian
        Path("/usr/share/fonts/msttcorefonts"),  # Other Linux
        Path("fonts"),  # Local folder
    ]

    def __init__(self):
        self.fonts = {}
        self._discover_fonts()

    def _find_font_file(self, filenames: List[str]) -> Optional[Path]:
        for d in self.POSSIBLE_DIRS:
            for f in filenames:
                path = d / f
                if path.exists():
                    return path
        return None

    def _discover_fonts(self):
        reg_path = self._find_font_file(["Arial.ttf", "arial.ttf", "Arial Unicode.ttf"])
        if not reg_path:
            raise FileNotFoundError(
                "Could not find Arial fonts. Please ensure they are installed."
            )

        bold_path = (
            self._find_font_file(["Arial Bold.ttf", "Arial_Bold.ttf", "arialbd.ttf"])
            or reg_path
        )
        ital_path = (
            self._find_font_file(["Arial Italic.ttf", "Arial_Italic.ttf", "ariali.ttf"])
            or reg_path
        )
        bold_ital_path = (
            self._find_font_file(
                ["Arial Bold Italic.ttf", "Arial_Bold_Italic.ttf", "arialbi.ttf"]
            )
            or reg_path
        )

        self.fonts = {
            "": reg_path,
            "B": bold_path,
            "I": ital_path,
            "BI": bold_ital_path,
        }

    def register_fonts(self, pdf: FPDF):
        for style, path in self.fonts.items():
            pdf.add_font("CustomFont", style, str(path))
