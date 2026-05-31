from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class Config:
    """Centralized layout and style constants."""

    MARGIN_LEFT: int = 20
    MARGIN_RIGHT: int = 20
    MARGIN_TOP: int = 20
    MARGIN_BOTTOM: int = 15

    TITLE_FONT_SIZE: int = 22
    SUBTITLE_FONT_SIZE: int = 10
    SECTION_HEADER_FONT_SIZE: int = 13
    SUBSECTION_HEADER_FONT_SIZE: int = 12
    BODY_FONT_SIZE: int = 11
    FOOTNOTE_FONT_SIZE: int = 10

    COLOR_BLACK: Tuple[int, int, int] = (0, 0, 0)
    COLOR_GREY_LIGHT: Tuple[int, int, int] = (245, 245, 245)
    COLOR_GREY_MEDIUM: Tuple[int, int, int] = (200, 200, 200)
    COLOR_TOC_LINE: Tuple[int, int, int] = (180, 180, 180)
