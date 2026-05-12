#!/usr/bin/env python3
"""
Generate a printable Hebrew RTL PDF quiz from text-based questions.
Each question shows a short biblical text excerpt and asks a question about it.
Questions are shuffled and answers are shown inline (compact format).

Usage:
    python3 generate_text_quiz_pdf.py [--count N] [--seed S] [--output FILE]
"""

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
OUTPUT_FILE = BASE_DIR / "text_quiz_print.pdf"

TEXT_QUESTION_DIR = BASE_DIR / "text_questions"

BOOK_NAMES = {
    "bereshit": "בראשית",
    "shemot": "שמות",
    "bamidbar": "במדבר",
    "yehoshua": "יהושע",
    "shoftim": "שופטים",
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
    """Simple RTL reversal for reportlab."""
    try:
        from bidi.algorithm import get_display
        return get_display(text)
    except ImportError:
        return text


def extract_text_questions(filepath, book_name):
    """Extract text-based questions from a markdown file."""
    questions = []

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Find story sections
    current_story = ""

    # Split into lines for processing
    lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        # Track story headers (## סיפור N: ...)
        story_match = re.match(r"##\s+סיפור\s+\d+\s*:\s*(.+)", line)
        if story_match:
            current_story = story_match.group(1).strip()

        # Look for **טקסט:** followed by a blockquote
        if line.strip() == "**טקסט:**":
            # Next non-empty line should be the blockquote text
            text_excerpt = ""
            j = i + 1
            while j < len(lines):
                if lines[j].strip().startswith(">"):
                    text_excerpt = lines[j].strip().lstrip("> ").strip()
                    j += 1
                    break
                elif lines[j].strip() == "":
                    j += 1
                else:
                    break

            # Now look for the <details> block with question and answer
            question_text = ""
            answer_text = ""
            # Search forward up to 5 lines for the <details> block, skipping blanks
            search_limit = min(j + 10, len(lines))
            while j < search_limit:
                if "<details>" in lines[j]:
                    # Collect entire details block
                    block_lines = []
                    while j < len(lines):
                        block_lines.append(lines[j])
                        if "</details>" in lines[j]:
                            break
                        j += 1
                    block = "\n".join(block_lines)

                    # Extract question from summary
                    q_match = re.search(
                        r"<summary>\s*<strong>\s*(?:שאלה:\s*)?(.+?)\s*</strong>\s*</summary>",
                        block,
                        re.DOTALL,
                    )
                    if q_match:
                        question_text = q_match.group(1).strip()
                        # Clean up
                        question_text = re.sub(r"^שאלה:\s*", "", question_text)

                    # Extract answer
                    a_match = re.search(
                        r"</summary>\s*\n(.*?)\n\s*</details>",
                        block,
                        re.DOTALL,
                    )
                    if a_match:
                        answer_text = a_match.group(1).strip()
                        # Clean markdown/HTML
                        answer_text = re.sub(r"<[^>]+>", "", answer_text)
                        answer_text = re.sub(r"\*\*([^*]+)\*\*", r"\1", answer_text)
                        answer_text = answer_text.strip()
                    break
                elif lines[j].strip().startswith("###"):
                    break  # Hit next question, stop
                else:
                    j += 1  # Skip blank lines and other content

            if text_excerpt and question_text and answer_text:
                # Truncate long answers
                if len(answer_text) > 200:
                    answer_text = answer_text[:197] + "..."

                questions.append({
                    "text_excerpt": text_excerpt,
                    "question": question_text,
                    "answer": answer_text,
                    "book": book_name,
                    "story": current_story,
                })

        i += 1

    return questions


def collect_all_text_questions():
    """Collect text questions from all book files."""
    all_questions = []

    for filename, book_name in BOOK_NAMES.items():
        filepath = TEXT_QUESTION_DIR / f"{filename}.md"
        if filepath.exists():
            questions = extract_text_questions(filepath, book_name)
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
    lines_out = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip() if current_line else word
        test_display = reverse_hebrew(test_line)
        width = pdfmetrics.stringWidth(test_display, font_name, font_size)
        if width > max_width and current_line:
            lines_out.append(current_line)
            current_line = word
        else:
            current_line = test_line
    if current_line:
        lines_out.append(current_line)

    for line in lines_out:
        display_line = reverse_hebrew(line)
        c.drawRightString(x, y, display_line)
        y -= font_size + 4

    return y


def create_pdf(questions, output_path, count=None):
    """Create the PDF with text-based questions."""
    register_fonts()

    if count and count < len(questions):
        questions = questions[:count]

    page_width, page_height = A4
    margin_x = 1.2 * cm
    margin_top = 1.2 * cm
    margin_bottom = 1.5 * cm
    content_width = page_width - 2 * margin_x
    right_x = page_width - margin_x

    c = canvas.Canvas(str(output_path), pagesize=A4)
    page_num = [0]  # mutable counter

    def finish_page():
        """Draw page number at bottom center and advance page."""
        page_num[0] += 1
        c.setFont(FONT_NAME, 8)
        c.setFillColor(HexColor("#888888"))
        c.drawCentredString(page_width / 2, 0.8 * cm, str(page_num[0]))
        c.setFillColor(HexColor("#000000"))
        c.showPage()

    # --- Title Page ---
    c.setFont(FONT_BOLD, 36)
    title = reverse_hebrew("חידון תנ\"ך")
    c.drawCentredString(page_width / 2, page_height - 8 * cm, title)

    c.setFont(FONT_BOLD, 28)
    subtitle = reverse_hebrew("שאלות על טקסט")
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

    finish_page()

    # --- Questions ---
    y = page_height - margin_top

    for i, q in enumerate(questions, 1):
        text_excerpt = q["text_excerpt"]
        question = q["question"]
        answer = q["answer"]

        # Combined quote + question on same line
        combined = f'.{i}  "{text_excerpt}" - {question}'
        combined_width = pdfmetrics.stringWidth(reverse_hebrew(combined), FONT_BOLD, 9)
        combined_lines = max(1, int(combined_width / content_width) + 1)
        a_width = pdfmetrics.stringWidth(reverse_hebrew(answer), FONT_NAME, 8)
        a_lines = max(1, int(a_width / content_width) + 1)
        space_needed = (combined_lines * 13) + (a_lines * 12) + 14

        if y - space_needed < margin_bottom:
            finish_page()
            y = page_height - margin_top

        # Quote + question together, same style
        y = draw_rtl_text(c, combined, right_x, y, FONT_BOLD, 9, content_width)

        # Answer in dark blue
        c.setFillColor(HexColor("#1a5276"))
        answer_line = f"תשובה: {answer}"
        y = draw_rtl_text(c, answer_line, right_x - 20, y, FONT_NAME, 8, content_width - 20)
        c.setFillColor(HexColor("#000000"))

        y -= 8

    # Number the final page
    page_num[0] += 1
    c.setFont(FONT_NAME, 8)
    c.setFillColor(HexColor("#888888"))
    c.drawCentredString(page_width / 2, 0.8 * cm, str(page_num[0]))
    c.setFillColor(HexColor("#000000"))

    c.save()
    return str(output_path)


def main():
    parser = argparse.ArgumentParser(description="Generate Text-Based Bible Quiz PDF")
    parser.add_argument("--count", type=int, default=None, help="Number of questions")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument("--output", type=str, default=None, help="Output file path")
    args = parser.parse_args()

    print("Collecting text-based questions...")
    all_questions = collect_all_text_questions()
    print(f"Found {len(all_questions)} text questions total")

    # Print breakdown
    book_counts = {}
    for q in all_questions:
        book_counts[q["book"]] = book_counts.get(q["book"], 0) + 1

    print("\nBy book:")
    for book, cnt in sorted(book_counts.items(), key=lambda x: -x[1]):
        print(f"  {book}: {cnt}")

    # Shuffle
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
