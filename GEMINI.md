# 📖 Recipe PDF Generator

A custom Python-based tool designed to convert Markdown recipes into a professional, high-fidelity PDF cookbook.

## 🚀 What it does

- **Professional Layout:** Replicates a premium cookbook design with centered titles, horizontal separators, and structured sections.
- **High-Fidelity Styling:** Each section (Ingredients, Technology, Reheating) features a light grey background bar and a black vertical accent bar.
- **Smart Formatting:**
  - Automatically connects ingredients and quantities with dotted lines.
  - Handles inline **bold text** (`**bold**`) correctly within instructions.
  - Automatically generates a **Table of Contents (TOC)** as the first page.
- **Russian Language Support:** Uses Cyrillic-compatible fonts (Arial/Arial Bold) for perfect rendering of Russian recipes.
- **Organized Ordering:** Sorts recipes based on numerical filename prefixes (e.g., `01_Recipe.md`, `02_Recipe.md`).

## 🛠 How it's made

- **Language:** Python 3
- **Core Library:** `fpdf2` (chosen for precise control over drawing primitives and font embedding).
- **Custom Parsing:** Uses a specialized Markdown-to-PDF engine built with Python's `re` (regex) module. It avoids heavy HTML/CSS conversion to ensure pixel-perfect alignment and faster execution.
- **Font System:** Dynamically searches for system fonts (`Arial.ttf` and `Arial Bold.ttf`) on macOS to support rich typography and Cyrillic glyphs.

## 🏃‍♂️ How to run it

### 1. Prerequisites

Ensure you have Python 3 installed. The project uses a virtual environment for dependency management.

### 2. Setup (First time only)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Generate PDF

Simply place your numbered `.md` files in the root folder and run:

```bash
./venv/bin/python3 generate_pdf.py
```

The output will be saved as `Recipes.pdf`.

## 📝 Recipe Format Guidelines

To ensure the best output, your Markdown files should follow this structure:

1. **Title:** Starts with `# Recipe Name`
2. **Subtitle:** (Optional) Wrap in double asterisks: `**Subtitle Info**`
3. **Sections:** Use `## Number. SECTION NAME` (e.g., `## 1. ИНГРЕДИЕНТЫ`)
4. **Ingredients:** Use bullet points with bold keys: `* **Item:** Quantity`
5. **Instructions:** Use standard Markdown bullets or numbers.
