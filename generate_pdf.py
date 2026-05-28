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

    def write_styled(self, text, size=11, bullet=True, indent=0):
        """
        High-precision justified text renderer with manual markdown support.
        This handles **bold**, *italic*, and ***bold-italic*** while ensuring
        perfect word-wrapping (words are NEVER split) and 'justified' alignment.
        """
        if not text.strip():
            return

        # Save original margins to restore later
        prev_l_margin = self.l_margin
        prev_r_margin = self.r_margin

        new_l_margin = prev_l_margin + indent
        self.set_left_margin(new_l_margin)
        self.set_x(new_l_margin)

        # 1. Parse text into fragments
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
                style, content = "I", part[1:-1]
            else:
                style, content = "", part
            fragments.append({"text": content, "style": style})

        # 2. Group fragments into "Items" (Words or Spaces)
        items = []
        current_word_fragments = []

        for frag in fragments:
            sub_parts = re.split(r"(\s+)", frag["text"])
            for sp in sub_parts:
                if not sp:
                    continue
                if sp.isspace():
                    if current_word_fragments:
                        items.append(
                            {"type": "word", "fragments": current_word_fragments}
                        )
                        current_word_fragments = []
                    items.append({"type": "space", "text": sp})
                else:
                    current_word_fragments.append({"text": sp, "style": frag["style"]})

        if current_word_fragments:
            items.append({"type": "word", "fragments": current_word_fragments})

        # 3. Handle bullet point
        if bullet:
            self.set_font("CustomFont", "B", size)
            bullet_str = " • "
            self.write(7, bullet_str)

        # 4. Build lines
        # We add a tiny buffer (0.1mm) to prevent floating point wrap triggers
        available_w = self.epw - (self.get_x() - self.l_margin) - 0.1
        current_line_items = []
        current_w = 0
        lines_to_render = []

        for item in items:
            item_w = 0
            if item["type"] == "word":
                for frag in item["fragments"]:
                    self.set_font("CustomFont", frag["style"], size)
                    item_w += self.get_string_width(frag["text"])
            else:
                self.set_font("CustomFont", "", size)
                item_w = self.get_string_width(item["text"])

            if (
                item["type"] == "word"
                and current_w + item_w > available_w
                and current_line_items
            ):
                lines_to_render.append(
                    {
                        "items": current_line_items,
                        "width": current_w,
                        "available": available_w,
                    }
                )
                current_line_items = []
                current_w = 0
                available_w = self.epw - 0.1

            if not current_line_items and item["type"] == "space":
                continue

            item["width"] = item_w
            current_line_items.append(item)
            current_w += item_w

        if current_line_items:
            lines_to_render.append(
                {
                    "items": current_line_items,
                    "width": current_w,
                    "available": available_w,
                    "last": True,
                }
            )

        # 5. Render the lines with justification
        # CRITICAL: Disable FPDF's internal wrap during manual rendering
        self.set_right_margin(0)

        for i, line in enumerate(lines_to_render):
            if i > 0:
                self.set_x(self.l_margin)

            is_last = line.get("last", False)
            words_in_line = [it for it in line["items"] if it["type"] == "word"]
            num_gaps = len(words_in_line) - 1

            extra_gap_space = 0
            if not is_last and num_gaps > 0:
                total_words_w = sum(it["width"] for it in words_in_line)
                extra_gap_space = (line["available"] - total_words_w) / num_gaps

            for item in line["items"]:
                if item["type"] == "word":
                    for frag in item["fragments"]:
                        self.set_font("CustomFont", frag["style"], size)
                        self.write(7, frag["text"])

                    if not is_last and num_gaps > 0:
                        word_idx = words_in_line.index(item)
                        if word_idx < num_gaps:
                            self.set_x(self.get_x() + extra_gap_space)
                else:
                    if is_last:
                        self.set_font("CustomFont", "", size)
                        self.write(7, item["text"])

            self.ln(7)

        # Restore original margins
        self.set_right_margin(prev_r_margin)
        self.set_left_margin(prev_l_margin)
        self.ln(2)  # Small gap between items

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
        # Capture ***bold-italic***, **bold**, and *italic*
        # Using a more robust regex that handles markers correctly
        parts = re.split(r"(\*\*\*.*?\*\*\*|\*\*.*?\*\*|\*.*?\*)", text)
        for part in parts:
            if not part:
                continue
            if part.startswith("***") and part.endswith("***"):
                self.set_font("CustomFont", "BI", size)
                self.write(8, part[3:-3])
            elif part.startswith("**") and part.endswith("**"):
                self.set_font("CustomFont", "B", size)
                self.write(7, part[2:-2])
            elif part.startswith("*") and part.endswith("*"):
                self.set_font("CustomFont", "I", size)
                self.write(7, part[1:-1])
            else:
                self.set_font("CustomFont", default_style, size)
                self.write(7, part)

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

        # Detect footnote: starts with * and has no quantity
        if not quantity.strip() and name.strip().startswith("*"):
            self.set_x(self.l_margin)
            # Render as italics, non-bold, slightly smaller
            self.write_inline_styled(name.strip(), size=10, default_style="I")
            self.ln(6)
            return

        # Calculate widths for the dotted line
        clean_name = re.sub(r"\*\*\*|\*\*|\*", "", name).strip()
        name_width = self.get_string_width(clean_name) + 3

        # 1. Render the name (left side, bold by default)
        self.set_x(self.l_margin)
        self.write_inline_styled(name, size=11, default_style="B")

        # 2. Render the quantity (right side, bold by default)
        # Calculate qty width carefully
        qty_width = self.get_styled_width(quantity, size=11, default_style="B")

        # Set cursor to the right, but ensure we don't wrap by temporarily
        # allowing text to overflow the right margin
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
    pdf.cell(0, 12, title.upper(), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    if subtitle:
        pdf.ln(2)
        pdf.set_font("CustomFont", "", 10)
        pdf.cell(0, 6, subtitle, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

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
                    pdf.set_y(10)
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
