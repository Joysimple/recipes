import re

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from .config import Config
from .fonts import FontManager


class RecipePDF(FPDF):
    def __init__(self, config: Config = Config()):
        super().__init__(format="A4")
        self.config = config
        self.set_margin(self.config.MARGIN_LEFT)
        self.set_auto_page_break(auto=True, margin=self.config.MARGIN_BOTTOM)

        self.font_manager = FontManager()
        self.font_manager.register_fonts(self)

        self.set_font("CustomFont", size=self.config.BODY_FONT_SIZE)
        self.set_text_color(*self.config.COLOR_BLACK)
        self.set_draw_color(*self.config.COLOR_BLACK)

    def write_styled(
        self, text, size=None, bullet=True, indent=0, base_style="", align="J"
    ):
        if size is None:
            size = self.config.BODY_FONT_SIZE
        if not text.strip():
            return

        # Clean up escaped markdown characters (e.g., \* becomes *, \< becomes <)
        text = text.replace("\\*", "*").replace("\\<", "<")

        # Save original margins
        original_l_margin = self.l_margin
        original_r_margin = self.r_margin

        # Calculate block-level left margin for auto-wraps (safety)
        new_l_margin = original_l_margin + indent
        self.set_left_margin(new_l_margin)
        self.set_x(new_l_margin)

        # 1. Parse text into unbreakable 'word' tokens
        parts = re.split(r"(\*\*\*.*?\*\*\*|\*\*.*?\*\*|\*.*?\*)", text)
        fragments = []
        for part in parts:
            if not part:
                continue
            if part.startswith("***") and part.endswith("***"):
                style, content = "BI", part[3:-3]
            elif part.startswith("**") and part.endswith("**"):
                style = "BI" if "I" in base_style else "B"
                content = part[2:-2]
            elif part.startswith("*") and part.endswith("*"):
                # Always non-bold italic for * markers
                style, content = "I", part[1:-1]
            else:
                style, content = base_style, part
            fragments.append({"text": content, "style": style})

        # Group fragments into Word objects
        words = []
        current_word_fragments = []
        for frag in fragments:
            sub_parts = re.split(r"(\s+)", frag["text"])
            for sp in sub_parts:
                if not sp:
                    continue
                if sp.isspace():
                    if current_word_fragments:
                        words.append({"fragments": current_word_fragments})
                        current_word_fragments = []
                else:
                    current_word_fragments.append({"text": sp, "style": frag["style"]})
        if current_word_fragments:
            words.append({"fragments": current_word_fragments})

        # 2. Add bullet if needed
        bullet_w = 0
        if bullet:
            self.set_font("CustomFont", "B", size)
            bullet_str = " • "
            self.write(7, bullet_str)
            bullet_w = self.get_string_width(bullet_str)

        # 3. Assemble lines manually for justification/alignment
        lines = []
        current_line = []
        current_line_w = 0
        # available width depends on the bullet only for the first line
        # but for simplicity in multi-line blocks, we assume bullet takes space
        available_w = self.epw - bullet_w - 0.1

        self.set_font("CustomFont", base_style, size)
        space_w = self.get_string_width(" ")

        for word in words:
            # Calculate word width
            word_w = 0
            for f in word["fragments"]:
                self.set_font("CustomFont", f["style"], size)
                word_w += self.get_string_width(f["text"])
            word["width"] = word_w

            if current_line and (current_line_w + space_w + word_w > available_w):
                lines.append(
                    {
                        "words": current_line,
                        "width": current_line_w,
                        "available": available_w,
                    }
                )
                current_line = []
                current_line_w = 0
                available_w = self.epw - 0.1  # Subsequent lines use full width

            current_line.append(word)
            if current_line_w > 0:
                current_line_w += space_w
            current_line_w += word_w

        if current_line:
            lines.append(
                {
                    "words": current_line,
                    "width": current_line_w,
                    "available": available_w,
                    "last": True,
                }
            )

        # 4. Render lines
        self.set_right_margin(0)  # Disable auto-wrap
        for i, line in enumerate(lines):
            is_last = line.get("last", False)
            # Determine effective alignment for this specific line
            line_align = align
            if align == "JR":
                line_align = "R" if is_last else "J"

            # Calculate start X for this line
            if line_align == "R":
                start_x = self.w - original_r_margin - line["width"]
            elif line_align == "C":
                start_x = new_l_margin + (line["available"] - line["width"]) / 2
            else:
                # Left / Justify
                start_x = new_l_margin + (bullet_w if i == 0 else 0)

            self.set_x(start_x)

            num_words = len(line["words"])
            num_gaps = num_words - 1
            extra_per_gap = 0
            if line_align == "J" and not is_last and num_gaps > 0:
                extra_per_gap = (line["available"] - line["width"]) / num_gaps

            for j, word in enumerate(line["words"]):
                for f in word["fragments"]:
                    self.set_font("CustomFont", f["style"], size)
                    self.write(7, f["text"])
                if j < num_gaps:
                    gap_w = space_w + (extra_per_gap if line_align == "J" else 0)
                    self.set_x(self.get_x() + gap_w)
            self.ln(7)

        # Restore margins
        self.set_right_margin(original_r_margin)
        self.set_left_margin(original_l_margin)
        self.ln(2)

    def draw_section_header(self, text):
        self.ln(6)
        self.set_font("CustomFont", "B", self.config.SECTION_HEADER_FONT_SIZE)
        header_text = text.upper()

        # 1. Calculate height by getting the actual number of lines
        line_height = 8
        available_text_w = self.epw - 7
        # We get the list of lines to be absolutely sure about the count
        # In fpdf2 2.8.7, multi_cell with output="LINES" returns a list of line objects
        lines_list = self.multi_cell(
            available_text_w,
            line_height,
            header_text,
            align="L",
            dry_run=True,
            output="LINES",
        )
        num_lines = len(lines_list)
        total_h = max(8, num_lines * line_height)

        # 2. Handle page break
        if self.get_y() + total_h > 275:
            self.add_page()

        curr_y = self.get_y()

        # 3. Draw rectangles
        # Grey background
        self.set_fill_color(*self.config.COLOR_GREY_LIGHT)
        self.rect(self.l_margin, curr_y, self.epw, total_h, style="F")
        # Black accent bar
        self.set_fill_color(*self.config.COLOR_BLACK)
        self.rect(self.l_margin, curr_y, 3, total_h, style="F")

        # 4. Render text using the SAME explicit width
        self.set_x(self.l_margin + 7)
        self.multi_cell(
            available_text_w,
            line_height,
            header_text,
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        self.ln(2)

    def draw_subsection_header(self, text):
        self.ln(4)
        self.set_font("CustomFont", "B", self.config.SUBSECTION_HEADER_FONT_SIZE)
        header_text = text.upper()

        # Calculate height with explicit line count
        line_height = 8
        lines_list = self.multi_cell(
            self.epw, line_height, header_text, align="L", dry_run=True, output="LINES"
        )
        num_lines = len(lines_list)
        total_h = num_lines * line_height

        if self.get_y() + total_h > 280:
            self.add_page()

        self.multi_cell(
            self.epw, line_height, header_text, new_x=XPos.LMARGIN, new_y=YPos.NEXT
        )
        self.ln(1)

    def write_inline_styled(self, text, size=None, default_style=""):
        if size is None:
            size = self.config.BODY_FONT_SIZE
        if not text:
            return

        # Clean up escaped markdown characters
        text = text.replace("\\*", "*").replace("\\<", "<")

        parts = re.split(r"(\*\*\*.*?\*\*\*|\*\*.*?\*\*|\*.*?\*)", text)
        for part in parts:
            if not part:
                continue
            if part.startswith("***") and part.endswith("***"):
                self.set_font("CustomFont", "BI", size)
                self.write(8, part[3:-3])
            elif part.startswith("**") and part.endswith("**"):
                style = "BI" if "I" in default_style else "B"
                self.set_font("CustomFont", style, size)
                self.write(8, part[2:-2])
            elif part.startswith("*") and part.endswith("*"):
                # Always non-bold italic for * markers
                self.set_font("CustomFont", "I", size)
                self.write(8, part[1:-1])
            else:
                self.set_font("CustomFont", default_style, size)
                self.write(8, part)

    def get_styled_width(self, text, size=None, default_style=""):
        if size is None:
            size = self.config.BODY_FONT_SIZE
        if not text:
            return 0

        # Clean up escaped markdown characters
        text = text.replace("\\*", "*").replace("\\<", "<")

        total_w = 0
        parts = re.split(r"(\*\*\*.*?\*\*\*|\*\*.*?\*\*|\*.*?\*)", text)
        for part in parts:
            if not part:
                continue
            if part.startswith("***") and part.endswith("***"):
                self.set_font("CustomFont", "BI", size)
                total_w += self.get_string_width(part[3:-3])
            elif part.startswith("**") and part.endswith("**"):
                style = "BI" if "I" in default_style else "B"
                self.set_font("CustomFont", style, size)
                total_w += self.get_string_width(part[2:-2])
            elif part.startswith("*") and part.endswith("*"):
                # Always non-bold italic for * markers
                self.set_font("CustomFont", "I", size)
                total_w += self.get_string_width(part[1:-1])
            else:
                self.set_font("CustomFont", default_style, size)
                total_w += self.get_string_width(part)
        return total_w

    def draw_ingredient_line(self, name, quantity):
        if self.get_y() > 270:
            self.add_page()
        curr_y = self.get_y()

        # Clean up escaped characters
        name = name.replace("\\*", "*").replace("\\<", "<")
        quantity = quantity.replace("\\*", "*").replace("\\<", "<")

        stripped_name = name.strip()
        is_footnote = False
        if stripped_name.startswith("*"):
            if not quantity.strip():
                is_footnote = True
            elif re.match(r"^\*+\s+", stripped_name):
                is_footnote = True
        if is_footnote:
            self.set_x(self.l_margin)
            full_text = (
                f"{name.strip()}: {quantity.strip()}"
                if quantity.strip()
                else name.strip()
            )
            self.write_styled(
                full_text,
                size=self.config.FOOTNOTE_FONT_SIZE,
                bullet=False,
                indent=0,
                base_style="I",
            )
            return

        # --- Standard Ingredient Line ---
        # 1. Calculate widths
        clean_name = re.sub(r"\*\*\*|\*\*|\*", "", name).replace("\\", "").strip()
        name_width = self.get_string_width(clean_name) + 3
        qty_width = self.get_styled_width(
            quantity, size=self.config.BODY_FONT_SIZE, default_style="B"
        )

        # 2. Check if combined width exceeds line capacity
        if name_width + qty_width > self.epw - 10:
            # Entry is too long, use "Condensed Justified-to-Right" layout
            full_text = f"{name.strip()}: {quantity.strip()}"
            self.write_styled(
                full_text,
                size=self.config.BODY_FONT_SIZE,
                bullet=False,
                indent=0,
                base_style="B",  # Make everything bold by default
                align="JR",  # Justify all lines, Right-align the last one
            )
        else:
            # Standard single line rendering with dots
            self.set_x(self.l_margin)
            self.write_inline_styled(
                name, size=self.config.BODY_FONT_SIZE, default_style="B"
            )
            prev_r_margin = self.r_margin
            self.set_right_margin(0)
            self.set_x(self.w - prev_r_margin - qty_width)
            self.write_inline_styled(
                quantity, size=self.config.BODY_FONT_SIZE, default_style="B"
            )
            self.set_right_margin(prev_r_margin)
            self.set_draw_color(*self.config.COLOR_GREY_MEDIUM)
            self.set_line_width(0.1)
            line_y = curr_y + 5.5
            end_x = self.w - prev_r_margin - qty_width - 2
            if end_x > self.l_margin + name_width:
                self.set_dash_pattern(dash=0.5, gap=1.5)
                self.line(self.l_margin + name_width, line_y, end_x, line_y)
                self.set_dash_pattern()
            self.ln(7)

    def draw_boxed_section(self, title, content_lines):
        self.ln(5)
        clean_content = [line.strip() for line in content_lines if line.strip()]
        if not clean_content:
            return
        if self.get_y() > 250:
            self.add_page()
        self.set_font("CustomFont", "B", self.config.BODY_FONT_SIZE)
        self.cell(0, 6, title.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        for line in clean_content:
            text = line.lstrip("* ").lstrip("- ").lstrip("• ").strip()
            self.write_styled(text, size=self.config.FOOTNOTE_FONT_SIZE, bullet=True)
        self.ln(5)
