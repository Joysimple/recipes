#!/usr/bin/env python3
import argparse
import logging
from pathlib import Path
from typing import List, Optional, Tuple

from fpdf.enums import XPos, YPos

from src.models import Recipe
from src.parser import RecipeParser
from src.renderer import RecipePDF

# Configure logging
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def draw_toc(pdf: RecipePDF, toc_data: List[Tuple[str, int]]):
    """
    Render the Table of Contents.
    toc_data is a list of (recipe_title, start_page_number)
    """
    pdf.add_page()
    pdf.set_y(40)
    pdf.set_font("CustomFont", "B", 24)
    pdf.cell(0, 20, "ОГЛАВЛЕНИЕ", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(10)

    pdf.set_font("CustomFont", "", 14)
    for i, (title, page_num) in enumerate(toc_data, 1):
        curr_y = pdf.get_y()
        clean_title = (
            title.replace("**", "").replace("\\*", "*").replace("\\", "").strip()
        )
        display_text = f"{i}. {clean_title}"

        # Create internal link to the recipe page
        link_id = pdf.add_link()
        pdf.set_link(link_id, page=page_num)

        # Make both the title and the number clickable
        pdf.cell(0, 10, display_text, link=link_id)
        pdf.set_x(-pdf.r_margin - 15)
        pdf.cell(
            15,
            10,
            str(page_num),
            align="R",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            link=link_id,
        )

        pdf.set_draw_color(*pdf.config.COLOR_TOC_LINE)
        pdf.set_dash_pattern(dash=0.5, gap=1.5)
        line_y = curr_y + 7
        title_width = pdf.get_string_width(display_text) + 10
        pdf.line(pdf.l_margin + title_width, line_y, pdf.w - pdf.r_margin - 20, line_y)
        pdf.set_dash_pattern()


def render_recipe_structured(pdf: RecipePDF, recipe: Recipe):
    pdf.add_page()
    recipe.start_page = pdf.page_no()

    pdf.set_y(15)
    pdf.set_font("CustomFont", "B", pdf.config.TITLE_FONT_SIZE)
    pdf.set_text_color(*pdf.config.COLOR_BLACK)
    # Support multi-line titles
    pdf.multi_cell(
        0, 10, recipe.title.upper(), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT
    )

    if recipe.subtitle:
        pdf.ln(2)
        pdf.set_font("CustomFont", "", pdf.config.SUBTITLE_FONT_SIZE)
        # Support multi-line subtitles
        pdf.multi_cell(
            0, 5, recipe.subtitle, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT
        )

    pdf.ln(4)
    pdf.set_draw_color(*pdf.config.COLOR_BLACK)
    pdf.set_line_width(0.3)
    pdf.line(pdf.l_margin + 30, pdf.get_y(), pdf.w - pdf.r_margin - 30, pdf.get_y())
    pdf.ln(8)

    for section in recipe.sections:
        if section.is_ingredients:
            pdf.draw_section_header(section.title)
            for line in section.body:
                import re

                line = line.strip()
                if line.startswith("###"):
                    pdf.draw_subsection_header(line.lstrip("#").strip())
                    continue
                if line.startswith(("*", "-")):
                    m = re.search(r"^[\*\-]\s*(.*?):\s*(.*)", line)
                    if m:
                        pdf.draw_ingredient_line(m.group(1), m.group(2))
                    else:
                        clean_line = re.sub(r"^[\*\-]\s*", "", line)
                        pdf.draw_ingredient_line(clean_line, "")
        else:
            pdf.draw_section_header(section.title)
            for line in section.body:
                if not line.strip():
                    continue
                if "<!-- PAGE_BREAK -->" in line:
                    pdf.add_page()
                    continue
                if line.strip().startswith("###"):
                    pdf.draw_subsection_header(line.strip().lstrip("#").strip())
                    continue
                stripped = line.lstrip()
                indent_size = len(line) - len(stripped)
                import re

                clean_line = re.sub(r"^[\*\-]?\s*\d*\.?\s*", "", stripped)
                pdf.write_styled(
                    clean_line,
                    size=pdf.config.BODY_FONT_SIZE,
                    bullet=True,
                    indent=(indent_size // 2) * 3,
                )
    return recipe.start_page


def generate_book(folder_path: Path, output_filename: Optional[str] = None):
    book_name = folder_path.name
    md_files = sorted([f for f in folder_path.glob("*.md") if f.name[0].isdigit()])

    if not md_files:
        logger.warning(f"No recipes found in {folder_path}")
        return

    recipes = []
    for md_file in md_files:
        try:
            recipes.append(RecipeParser.parse_file(md_file))
        except Exception as e:
            logger.error(f"Error parsing {md_file}: {e}")

    # --- Phase 1: Determine page counts ---
    recipe_page_counts = []
    for recipe in recipes:
        temp_pdf = RecipePDF()
        render_recipe_structured(temp_pdf, recipe)
        recipe_page_counts.append(temp_pdf.page_no())

    # --- Phase 2: Determine TOC count ---
    dummy_toc_info = [(r.title, 999) for r in recipes]
    temp_pdf_toc = RecipePDF()
    draw_toc(temp_pdf_toc, dummy_toc_info)
    toc_pages_count = temp_pdf_toc.page_no()

    # --- Phase 3: Calculate TOC offsets ---
    toc_info = []
    current_page = 1 + toc_pages_count
    for recipe, count in zip(recipes, recipe_page_counts):
        toc_info.append((recipe.title, current_page))
        current_page += count

    # --- Phase 4: Render final PDF ---
    pdf = RecipePDF()
    draw_toc(pdf, toc_info)
    for recipe in recipes:
        logger.info(f"[{book_name}] Processing {recipe.title}...")
        try:
            render_recipe_structured(pdf, recipe)
        except Exception as e:
            logger.error(f"Error processing {recipe.title}: {e}")

    output_path = output_filename or f"{book_name}.pdf"
    pdf.output(output_path)
    logger.info(f"Success! {output_path} generated.\n")


def main():
    parser = argparse.ArgumentParser(
        description="Generate professional recipe PDFs from Markdown files."
    )
    parser.add_argument("folders", nargs="*", help="Cookbook folders to process.")
    parser.add_argument("-o", "--output", help="Output filename.")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging."
    )
    args = parser.parse_args()
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    base_dir = Path(".")
    if args.folders:
        folders = [Path(f) for f in args.folders if Path(f).is_dir()]
    else:
        folders = [
            d
            for d in base_dir.iterdir()
            if d.is_dir()
            and not d.name.startswith(".")
            and d.name != "venv"
            and d.name != "src"
        ]
    if not folders:
        logger.error("No cookbook folders found.")
        return
    if args.output and len(folders) > 1:
        logger.error(
            "Output filename can only be specified when processing a single folder."
        )
        return
    for folder in sorted(folders):
        generate_book(folder, output_filename=args.output)


if __name__ == "__main__":
    main()
