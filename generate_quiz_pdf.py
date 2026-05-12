#!/usr/bin/env python3
"""
Generate a printable Hebrew RTL PDF quiz from the Bible Quiz study guide.
Extracts questions from all story files, shuffles them, and creates a PDF
with questions on the first pages and answers at the end.

Usage:
    python3 generate_quiz_pdf.py [--count N] [--seed S]

    --count N   Number of questions to include (default: all)
    --seed S    Random seed for reproducible shuffles
"""

import os
import re
import random
import argparse
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor

# --- Configuration ---
BASE_DIR = Path(__file__).parent
OUTPUT_FILE = BASE_DIR / "quiz_print.pdf"

BOOK_DIRS = {
    "בראשית": BASE_DIR / "bereshit",
    "שמות": BASE_DIR / "shemot",
    "במדבר": BASE_DIR / "bamidbar",
    "יהושע": BASE_DIR / "yehoshua",
    "שופטים": BASE_DIR / "shoftim",
}

SECTION_TYPE_MAP = {
    "שאלות לתרגול": "תרגול",
    "מי אמר למי": "מי אמר למי",
    "זהה את הדמות": "זהה דמות",
    "נכון או לא נכון": "נכון/לא נכון",
    "השלם את הציטוט": "השלם ציטוט",
    "מה לא שייך": "מה לא שייך",
    "שאלות על ציטוטים": "ציטוטים",
}

# Hebrew font
FONT_PATH = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_BOLD_PATH = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_NAME = "Arial"
FONT_BOLD = "ArialBold"


def register_fonts():
    pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, FONT_BOLD_PATH))


def reverse_hebrew(text):
    """Simple RTL reversal for reportlab - reverse the logical order for display."""
    try:
        from bidi.algorithm import get_display
        return get_display(text)
    except ImportError:
        return text


def extract_questions_from_file(filepath, book_name):
    """Extract all questions from a markdown file with <details>/<summary> blocks."""
    questions = []

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Find the story name from the first heading
    story_match = re.search(r"#\s+(.+?)(?:\n|$)", content)
    story_name = story_match.group(1).strip() if story_match else filepath.stem
    # Clean story name from HTML
    story_name = re.sub(r"<[^>]+>", "", story_name).strip()

    # Determine current section type
    current_section = "תרגול"

    # Split by lines and track sections
    lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        # Check for section headers
        header_match = re.match(r"##\s+(.+)", line)
        if header_match:
            header_text = header_match.group(1).strip()
            for key, value in SECTION_TYPE_MAP.items():
                if key in header_text:
                    current_section = value
                    break

        # Check for <details> block
        if "<details>" in line:
            # Collect the entire details block
            block_lines = []
            while i < len(lines):
                block_lines.append(lines[i])
                if "</details>" in lines[i]:
                    break
                i += 1

            block = "\n".join(block_lines)

            # Extract question from <summary>
            q_match = re.search(
                r"<summary>\s*<strong>\s*(.+?)\s*</strong>\s*</summary>",
                block,
                re.DOTALL,
            )
            if q_match:
                raw_question = q_match.group(1).strip()
                # Count stars for difficulty
                stars = len(re.findall(r"⭐", raw_question))
                # Remove leading number and stars
                question_text = re.sub(r"^\d+\.\s*", "", raw_question)
                question_text = re.sub(r"⭐+\s*", "", question_text)
                question_text = question_text.strip()

                # Extract answer (everything between </summary> and </details>)
                answer_match = re.search(
                    r"</summary>\s*\n(.*?)\n\s*</details>",
                    block,
                    re.DOTALL,
                )
                if answer_match:
                    answer_text = answer_match.group(1).strip()
                    # Clean HTML and markdown from answer
                    answer_text = re.sub(r"<[^>]+>", "", answer_text)
                    answer_text = re.sub(r"\*\*([^*]+)\*\*", r"\1", answer_text)
                    answer_text = answer_text.strip()

                    # For "mi amar lemi" - create compact answer
                    if current_section == "מי אמר למי":
                        mi_amar = re.search(r"מי אמר:\s*(.+)", answer_text)
                        lemi = re.search(r"למי:\s*(.+)", answer_text)
                        if mi_amar and lemi:
                            answer_text = f"{mi_amar.group(1).strip()} → {lemi.group(1).strip()}"

                    # For "identify character" - extract the character name
                    if current_section == "זהה דמות":
                        char_match = re.search(r"(?:התשובה|הדמות)[:\s]+(.+?)(?:\n|$)", answer_text)
                        if not char_match:
                            # First line is often the answer
                            first_line = answer_text.split("\n")[0].strip()
                            if len(first_line) < 50:
                                answer_text = first_line

                    # For true/false - get first line
                    if current_section == "נכון/לא נכון":
                        first_line = answer_text.split("\n")[0].strip()
                        if first_line:
                            answer_text = first_line

                    # Truncate long answers
                    if len(answer_text) > 150:
                        answer_text = answer_text[:147] + "..."

                    questions.append({
                        "question": question_text,
                        "answer": answer_text,
                        "book": book_name,
                        "section": current_section,
                        "story": story_name,
                        "stars": stars,
                    })
        i += 1

    return questions


def collect_all_questions():
    """Collect questions from all story files."""
    all_questions = []

    for book_name, book_dir in BOOK_DIRS.items():
        if not book_dir.exists():
            continue
        for md_file in sorted(book_dir.glob("*.md")):
            if md_file.name.startswith("00_"):
                continue  # Skip comparison tables
            questions = extract_questions_from_file(md_file, book_name)
            all_questions.extend(questions)

    # Cross-book questions
    cross_book = BASE_DIR / "questions" / "cross_book_questions.md"
    if cross_book.exists():
        questions = extract_questions_from_file(cross_book, "חוצה ספרים")
        all_questions.extend(questions)

    return all_questions


def draw_rtl_text(c, text, x, y, font_name, font_size, max_width=None):
    """Draw RTL Hebrew text on the canvas. Returns the y position after drawing."""
    c.setFont(font_name, font_size)
    display_text = reverse_hebrew(text)

    if max_width is None:
        c.drawRightString(x, y, display_text)
        return y

    # Word wrap for long text
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip() if current_line else word
        test_display = reverse_hebrew(test_line)
        width = pdfmetrics.stringWidth(test_display, font_name, font_size)
        if width > max_width and current_line:
            lines.append(current_line)
            current_line = word
        else:
            current_line = test_line
    if current_line:
        lines.append(current_line)

    for line in lines:
        display_line = reverse_hebrew(line)
        c.drawRightString(x, y, display_line)
        y -= font_size + 4

    return y


def create_pdf(questions, output_path, count=None):
    """Create the PDF with questions and answers."""
    register_fonts()

    if count and count < len(questions):
        questions = questions[:count]

    page_width, page_height = A4
    margin_x = 1.2 * cm
    margin_top = 1.2 * cm
    margin_bottom = 1.2 * cm
    content_width = page_width - 2 * margin_x
    right_x = page_width - margin_x

    c = canvas.Canvas(str(output_path), pagesize=A4)

    # --- Title Page ---
    c.setFont(FONT_BOLD, 36)
    title = reverse_hebrew("חידון תנ\"ך")
    c.drawCentredString(page_width / 2, page_height - 8 * cm, title)

    c.setFont(FONT_BOLD, 28)
    subtitle = reverse_hebrew("שלב שני - דף תרגול")
    c.drawCentredString(page_width / 2, page_height - 10 * cm, subtitle)

    c.setFont(FONT_NAME, 16)
    info = reverse_hebrew(f"{len(questions)} שאלות מעורבבות מכל הספרים")
    c.drawCentredString(page_width / 2, page_height - 13 * cm, info)

    # Book breakdown
    book_counts = {}
    for q in questions:
        book_counts[q["book"]] = book_counts.get(q["book"], 0) + 1

    y = page_height - 15 * cm
    c.setFont(FONT_NAME, 13)
    for book, cnt in book_counts.items():
        line = reverse_hebrew(f"{book}: {cnt} שאלות")
        c.drawCentredString(page_width / 2, y, line)
        y -= 25

    # Section breakdown
    y -= 20
    section_counts = {}
    for q in questions:
        section_counts[q["section"]] = section_counts.get(q["section"], 0) + 1

    c.setFont(FONT_NAME, 11)
    for section, cnt in section_counts.items():
        line = reverse_hebrew(f"{section}: {cnt}")
        c.drawCentredString(page_width / 2, y, line)
        y -= 20

    c.showPage()

    # --- Questions + Answers (interleaved) ---
    y = page_height - margin_top

    for i, q in enumerate(questions, 1):
        q_text = q["question"]
        answer = q["answer"]

        # Estimate space needed for question + answer together
        q_width = pdfmetrics.stringWidth(reverse_hebrew(q_text), FONT_BOLD, 9)
        q_lines = max(1, int(q_width / content_width) + 1)
        a_width = pdfmetrics.stringWidth(reverse_hebrew(answer), FONT_NAME, 8)
        a_lines = max(1, int(a_width / content_width) + 1)
        space_needed = (q_lines * 13) + (a_lines * 12) + 15

        if y - space_needed < margin_bottom:
            c.showPage()
            y = page_height - margin_top

        # Question number and text (bold)
        q_line = f".{i}  {q_text}"
        c.setFont(FONT_BOLD, 9)
        y = draw_rtl_text(c, q_line, right_x, y, FONT_BOLD, 9, content_width)

        # Answer in dark blue, compact
        c.setFillColor(HexColor("#1a5276"))
        answer_line = f"תשובה: {answer}"
        y = draw_rtl_text(c, answer_line, right_x - 15, y, FONT_NAME, 8, content_width - 15)
        c.setFillColor(HexColor("#000000"))

        y -= 7

    c.save()
    return str(output_path)


def main():
    parser = argparse.ArgumentParser(description="Generate Bible Quiz PDF")
    parser.add_argument("--count", type=int, default=None, help="Number of questions")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--min-stars", type=int, default=0, help="Minimum difficulty (1-3)")
    parser.add_argument("--output", type=str, default=None, help="Output file path")
    args = parser.parse_args()

    print("Collecting questions from all story files...")
    all_questions = collect_all_questions()
    print(f"Found {len(all_questions)} questions total")

    # Print breakdown
    book_counts = {}
    section_counts = {}
    for q in all_questions:
        book_counts[q["book"]] = book_counts.get(q["book"], 0) + 1
        section_counts[q["section"]] = section_counts.get(q["section"], 0) + 1

    print("\nBy book:")
    for book, cnt in sorted(book_counts.items(), key=lambda x: -x[1]):
        print(f"  {book}: {cnt}")

    print("\nBy type:")
    for section, cnt in sorted(section_counts.items(), key=lambda x: -x[1]):
        print(f"  {section}: {cnt}")

    # Filter by difficulty
    if args.min_stars > 0:
        all_questions = [q for q in all_questions if q["stars"] >= args.min_stars]
        print(f"\nAfter filtering (min {args.min_stars} stars): {len(all_questions)} questions")

    # Shuffle
    if args.seed is not None:
        random.seed(args.seed)
    random.shuffle(all_questions)

    # Limit count
    if args.count and args.count < len(all_questions):
        all_questions = all_questions[:args.count]
        print(f"Using {args.count} questions")

    output_path = Path(args.output) if args.output else OUTPUT_FILE
    print(f"\nGenerating PDF with {len(all_questions)} questions...")
    output = create_pdf(all_questions, output_path)
    print(f"PDF saved to: {output}")


if __name__ == "__main__":
    main()
