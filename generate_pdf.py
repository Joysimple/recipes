import os
import glob
import re
from fpdf import FPDF
from fpdf.enums import XPos, YPos


class RecipePDF(FPDF):
    def __init__(self):
        super().__init__(format="A4")
        self.set_margin(20)
        self.set_auto_page_break(auto=True, margin=15)

        # Cross-platform font search
        possible_dirs = [
            "/System/Library/Fonts/Supplemental",  # MacOS
            "/Library/Fonts",  # MacOS Alternative
            "/usr/share/fonts/truetype/msttcorefonts",  # Ubuntu/Debian
            "/usr/share/fonts/msttcorefonts",  # Other Linux
            "fonts",  # Local folder
        ]

        def find_font_file(filenames):
            for d in possible_dirs:
                for f in filenames:
                    path = os.path.join(d, f)
                    if os.path.exists(path):
                        return path
            return None

        reg_path = find_font_file(["Arial.ttf", "arial.ttf", "Arial Unicode.ttf"])
        bold_path = find_font_file(["Arial Bold.ttf", "Arial_Bold.ttf", "arialbd.ttf"])
        ital_path = find_font_file(
            ["Arial Italic.ttf", "Arial_Italic.ttf", "ariali.ttf"]
        )
        bold_ital_path = find_font_file(
            ["Arial Bold Italic.ttf", "Arial_Bold_Italic.ttf", "arialbi.ttf"]
        )

        # Fallback to whatever we found for regular if others missing
        bold_path = bold_path or reg_path
        ital_path = ital_path or reg_path
        bold_ital_path = bold_ital_path or reg_path

        if not reg_path:
            raise FileNotFoundError(
                "Could not find Arial fonts. Please ensure they are installed."
            )

        self.add_font("CustomFont", "", reg_path)
        self.add_font("CustomFont", "B", bold_path)
        self.add_font("CustomFont", "I", ital_path)
        self.add_font("CustomFont", "BI", bold_ital_path)
        self.set_font("CustomFont", size=11)
        self.set_text_color(0, 0, 0)
        self.set_draw_color(0, 0, 0)

    def write_styled(self, text, size=11, bullet=True, indent=0, base_style=""):
        """
        Custom justified text renderer. Handles **bold** and *italic* manually
        to prevent word-splitting and ensure italics always work correctly.
        """
        if not text.strip():
            return

        # Clean up escaped markdown characters (e.g., \* becomes *)
        text = text.replace("\\*", "*")

        # Save original margins
        prev_l_margin = self.l_margin
        prev_r_margin = self.r_margin

        new_l_margin = prev_l_margin + indent
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
                style, content = "B", part[2:-2]
            elif part.startswith("*") and part.endswith("*"):
                # Always non-bold italic for * markers
                style, content = "I", part[1:-1]
            else:
                style, content = base_style, part
            fragments.append({"text": content, "style": style})

        # Group fragments into Word objects (no spaces allowed inside a word)
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
        if bullet:
            self.set_font("CustomFont", "B", size)
            self.write(7, " • ")

        # 3. Assemble lines manually for justification
        lines = []
        current_line = []
        current_line_w = 0
        # Account for the bullet if it was drawn
        start_x_offset = (self.get_x() - self.l_margin) if bullet else 0
        available_w = self.epw - start_x_offset - 0.1

        for word in words:
            # Calculate word width
            word_w = 0
            for f in word["fragments"]:
                self.set_font("CustomFont", f["style"], size)
                word_w += self.get_string_width(f["text"])
            word["width"] = word_w

            # Check if word fits
            # We assume a space between words (approx width of a space in regular font)
            self.set_font("CustomFont", base_style, size)
            space_w = self.get_string_width(" ")

            if current_line and (current_line_w + space_w + word_w > available_w):
                # Line full, save it
                lines.append(
                    {
                        "words": current_line,
                        "width": current_line_w,
                        "available": available_w,
                    }
                )
                current_line = []
                current_line_w = 0
                available_w = self.epw - 0.1

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
        # Disable auto-wrap during manual rendering
        self.set_right_margin(0)
        for i, line in enumerate(lines):
            if i > 0:
                self.set_x(self.l_margin)

            is_last = line.get("last", False)
            num_words = len(line["words"])
            num_gaps = num_words - 1

            # Default space width
            self.set_font("CustomFont", base_style, size)
            base_space_w = self.get_string_width(" ")

            # Calculate extra space for justification
            extra_per_gap = 0
            if not is_last and num_gaps > 0:
                # available space / gaps
                extra_per_gap = (line["available"] - line["width"]) / num_gaps

            for j, word in enumerate(line["words"]):
                # Render fragments of the word
                for f in word["fragments"]:
                    self.set_font("CustomFont", f["style"], size)
                    self.write(7, f["text"])

                # Render gap
                if j < num_gaps:
                    gap_w = base_space_w + extra_per_gap
                    self.set_x(self.get_x() + gap_w)

            self.ln(7)

        # Restore margins
        self.set_right_margin(prev_r_margin)
        self.set_left_margin(prev_l_margin)
        self.ln(2)

    def draw_section_header(self, text):
        self.ln(6)
        if self.get_y() > 250:
            self.add_page()

        curr_y = self.get_y()
        self.set_fill_color(245, 245, 245)
        self.rect(self.l_margin, curr_y, self.epw, 8, style="F")
        self.set_fill_color(0, 0, 0)
        self.rect(self.l_margin, curr_y, 3, 8, style="F")

        self.set_x(self.l_margin + 7)
        self.set_font("CustomFont", "B", 13)
        self.cell(0, 8, text.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)

    def draw_subsection_header(self, text):
        self.ln(4)
        if self.get_y() > 260:
            self.add_page()

        self.set_font("CustomFont", "B", 12)
        self.cell(0, 8, text.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def write_inline_styled(self, text, size=11, default_style=""):
        """Helper to write a single line of text with **bold** and *italic* support using write()"""
        if not text:
            return

        # Clean up escaped markdown characters
        text = text.replace("\\*", "*")

        parts = re.split(r"(\*\*\*.*?\*\*\*|\*\*.*?\*\*|\*.*?\*)", text)
        for part in parts:
            if not part:
                continue
            if part.startswith("***") and part.endswith("***"):
                self.set_font("CustomFont", "BI", size)
                self.write(8, part[3:-3])
            elif part.startswith("**") and part.endswith("**"):
                self.set_font("CustomFont", "B", size)
                self.write(8, part[2:-2])
            elif part.startswith("*") and part.endswith("*"):
                # Always non-bold italic for * markers
                self.set_font("CustomFont", "I", size)
                self.write(8, part[1:-1])
            else:
                self.set_font("CustomFont", default_style, size)
                self.write(8, part)

    def get_styled_width(self, text, size=11, default_style=""):
        """Calculate the total width of a styled string without rendering it"""
        if not text:
            return 0
        total_w = 0
        parts = re.split(r"(\*\*\*.*?\*\*\*|\*\*.*?\*\*|\*.*?\*)", text)
        for part in parts:
            if not part:
                continue
            if part.startswith("***") and part.endswith("***"):
                self.set_font("CustomFont", "BI", size)
                total_w += self.get_string_width(part[3:-3])
            elif part.startswith("**") and part.endswith("**"):
                self.set_font("CustomFont", "B", size)
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
        name = name.replace("\\*", "*")
        quantity = quantity.replace("\\*", "*")

        # Robust footnote detection: starts with one or more asterisks
        stripped_name = name.strip()
        is_footnote = False
        if stripped_name.startswith("*"):
            if not quantity.strip():
                is_footnote = True
            elif re.match(r"^\*+\s+", stripped_name):
                # e.g. "* Option A" or "** Option B"
                is_footnote = True

        if is_footnote:
            self.set_x(self.l_margin)
            # Combine name and quantity for footnotes that were split by a colon
            full_text = (
                f"{name.strip()}: {quantity.strip()}"
                if quantity.strip()
                else name.strip()
            )
            # Render as light italic, justified, no bullet
            self.write_styled(
                full_text, size=10, bullet=False, indent=0, base_style="I"
            )
            return

        # Calculate widths for the dotted line
        clean_name = re.sub(r"\*\*\*|\*\*|\*", "", name).strip()
        name_width = self.get_string_width(clean_name) + 3

        # 1. Render the name (left side, bold by default)
        self.set_x(self.l_margin)
        self.write_inline_styled(name, size=11, default_style="B")

        # 2. Render the quantity (right side, bold by default)
        qty_width = self.get_styled_width(quantity, size=11, default_style="B")
        prev_r_margin = self.r_margin
        self.set_right_margin(0)
        self.set_x(self.w - prev_r_margin - qty_width)
        self.write_inline_styled(quantity, size=11, default_style="B")
        self.set_right_margin(prev_r_margin)

        # 3. Draw dotted line between name and quantity
        self.set_draw_color(200, 200, 200)
        self.set_line_width(0.1)
        line_y = curr_y + 5.5
        end_x = self.w - prev_r_margin - qty_width - 2

        if end_x > self.l_margin + name_width:
            self.set_dash_pattern(dash=0.5, gap=1.5)
            self.line(self.l_margin + name_width, line_y, end_x, line_y)
            self.set_dash_pattern()

        # Move to next line
        self.ln(7)

    def draw_boxed_section(self, title, content_lines):
        self.ln(5)
        clean_content = [line.strip() for line in content_lines if line.strip()]
        if not clean_content:
            return

        if self.get_y() > 250:
            self.add_page()

        self.set_font("CustomFont", "B", 11)
        self.cell(0, 6, title.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        for line in clean_content:
            text = line.lstrip("* ").lstrip("- ").lstrip("• ").strip()
            self.write_styled(text, size=10, bullet=True)

        self.ln(5)


def parse_recipe_title(content):
    lines = content.split("\n")
    if not lines:
        return "Untitled Recipe"
    title_match = re.search(r"^#\s*(.*)", lines[0])
    return title_match.group(1).strip() if title_match else "Untitled Recipe"


def draw_toc(pdf, recipe_titles):
    pdf.add_page()
    pdf.set_y(40)
    pdf.set_font("CustomFont", "B", 24)
    pdf.cell(0, 20, "TABLE OF CONTENTS", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(10)

    pdf.set_font("CustomFont", "", 14)
    for i, title in enumerate(recipe_titles, 1):
        recipe_page = i + 1
        curr_y = pdf.get_y()
        clean_title = title.replace("**", "").strip()
        pdf.cell(0, 10, f"{i}. {clean_title}")
        pdf.set_x(-pdf.r_margin - 15)
        pdf.cell(
            20, 10, str(recipe_page), align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT
        )

        pdf.set_draw_color(180, 180, 180)
        pdf.set_dash_pattern(dash=0.5, gap=1.5)
        line_y = curr_y + 7
        title_width = pdf.get_string_width(f"{i}. {clean_title}") + 10
        pdf.line(pdf.l_margin + title_width, line_y, pdf.w - pdf.r_margin - 25, line_y)
        pdf.set_dash_pattern()


def parse_and_draw_recipe(pdf, content, recipe_num):
    content = content.replace("\r\n", "\n")
    lines = content.split("\n")
    title = parse_recipe_title(content)

    subtitle = ""
    for line in lines[1:5]:
        sub_match = re.search(r"^\*\*(.*)\*\*", line)
        if sub_match:
            subtitle = sub_match.group(1)
            break

    pdf.add_page()
    pdf.set_y(15)
    pdf.set_font("CustomFont", "B", 22)
    pdf.set_text_color(0, 0, 0)
    # Support multi-line titles
    pdf.multi_cell(0, 10, title.upper(), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    if subtitle:
        pdf.ln(2)
        pdf.set_font("CustomFont", "", 10)
        # Support multi-line subtitles
        pdf.multi_cell(0, 5, subtitle, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(4)
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.3)
    pdf.line(pdf.l_margin + 30, pdf.get_y(), pdf.w - pdf.r_margin - 30, pdf.get_y())
    pdf.ln(8)

    sections = re.split(r"\n##\s+", "\n" + content)
    for section in sections:
        if not section.strip() or section.strip().startswith("# "):
            continue

        sec_lines = section.strip().split("\n")
        header_text = re.sub(r"^\d+\.\s*", "", sec_lines[0].strip())
        body = sec_lines[1:]

        if "ИНГРЕДИЕНТЫ" in header_text.upper():
            pdf.draw_section_header(header_text)
            for line in body:
                line = line.strip()
                if line.startswith("###"):
                    pdf.draw_subsection_header(line.lstrip("#").strip())
                    continue
                if line.startswith(("*", "-")):
                    # Simpler regex that preserves markers and splits at the first colon
                    m = re.search(r"^[\*\-]\s*(.*?):\s*(.*)", line)
                    if m:
                        pdf.draw_ingredient_line(m.group(1), m.group(2))
                    else:
                        # Handle footnotes/simple items: remove only the bullet, keep the rest
                        clean_line = re.sub(r"^[\*\-]\s*", "", line)
                        pdf.draw_ingredient_line(clean_line, "")
        else:
            pdf.draw_section_header(header_text)
            for line in body:
                if not line.strip():
                    continue

                # Handle manual page breaks (invisible in most renderers)
                if "<!-- PAGE_BREAK -->" in line:
                    pdf.add_page()
                    continue

                # Handle subsections
                if line.strip().startswith("###"):
                    pdf.draw_subsection_header(line.strip().lstrip("#").strip())
                    continue

                # Detect indentation
                stripped = line.lstrip()
                indent_size = len(line) - len(stripped)

                # Clean marker
                clean_line = re.sub(r"^[\*\-]?\s*\d*\.?\s*", "", stripped)

                # Apply indentation (approx 3mm per 2 spaces)
                pdf.write_styled(
                    clean_line, size=11, bullet=True, indent=(indent_size // 2) * 3
                )


def main():
    pdf = RecipePDF()
    md_files = sorted(
        [f for f in glob.glob("recipes/*.md") if os.path.basename(f)[0].isdigit()]
    )
    recipe_data = []
    for md_file in md_files:
        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()
            title = parse_recipe_title(content)
            recipe_data.append((title, content))

    if not recipe_data:
        print("No numbered markdown files found.")
        return

    draw_toc(pdf, [data[0] for data in recipe_data])
    for i, (title, content) in enumerate(recipe_data, 1):
        print(f"Processing {title}...")
        try:
            parse_and_draw_recipe(pdf, content, i)
        except Exception as e:
            print(f"Error processing {title}: {e}")

    pdf.output("Recipes.pdf")
    print("\nSuccess! Recipes.pdf generated.")


if __name__ == "__main__":
    main()
