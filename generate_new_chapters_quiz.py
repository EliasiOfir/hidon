#!/usr/bin/env python3
"""
Generate a PDF quiz for NEW chapters only.
  • בראשית  כ"ט–ל"א א'  (story files 16-20)
  • שופטים  י'–ט"ז      (story files 07-11)
  • cross_chapter ✨-marked questions from both books
  • text_questions ✨-marked story sections from both books

Same visual style as quiz_print.pdf / text_quiz_print.pdf.
Output: quiz_new_chapters.pdf
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

# ── paths ──────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
OUTPUT_FILE = BASE_DIR / "quiz_new_chapters.pdf"

FONT_PATH      = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_BOLD_PATH = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_NAME = "Arial"
FONT_BOLD = "ArialBold"

# ── new story files (Q&A) ──────────────────────────────────────────────────
NEW_STORY_FILES = [
    ("בראשית", BASE_DIR / "bereshit" / "16_yaakov_rachel_meeting.md"),
    ("בראשית", BASE_DIR / "bereshit" / "17_yaakov_marriages.md"),
    ("בראשית", BASE_DIR / "bereshit" / "18_birth_of_tribes.md"),
    ("בראשית", BASE_DIR / "bereshit" / "19_yaakov_lavan_flock.md"),
    ("בראשית", BASE_DIR / "bereshit" / "20_yaakov_flees_lavan.md"),
    ("שופטים", BASE_DIR / "shoftim" / "07_tolah_yair.md"),
    ("שופטים", BASE_DIR / "shoftim" / "08_yiftach.md"),
    ("שופטים", BASE_DIR / "shoftim" / "09_shibboleth_and_small_judges.md"),
    ("שופטים", BASE_DIR / "shoftim" / "10_birth_of_shimshon.md"),
    ("שופטים", BASE_DIR / "shoftim" / "11_shimshon.md"),
]

# cross_chapter: extract only ✨-tagged questions
CROSS_CHAPTER_FILES = [
    ("בראשית — חוצה פרקים", BASE_DIR / "bereshit" / "cross_chapter.md"),
    ("שופטים — חוצה פרקים", BASE_DIR / "shoftim" / "cross_chapter.md"),
]

# text_questions: story numbers that are new
NEW_TEXT_STORIES = {
    "bereshit": set(range(16, 21)),   # 16-20
    "shoftim":  set(range(7,  14)),   # 7-13
}
TEXT_BOOK_NAMES = {
    "bereshit": "בראשית",
    "shoftim":  "שופטים",
}
TEXT_QUESTION_DIR = BASE_DIR / "text_questions"

SECTION_TYPE_MAP = {
    "שאלות לתרגול":     "תרגול",
    "מי אמר למי":        "מי אמר למי",
    "זהה את הדמות":      "זהה דמות",
    "נכון או לא נכון":   "נכון/לא נכון",
    "השלם את הציטוט":    "השלם ציטוט",
    "מה לא שייך":        "מה לא שייך",
    "שאלות על ציטוטים":  "ציטוטים",
}


# ── font & bidi ─────────────────────────────────────────────────────────────
def register_fonts():
    pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, FONT_BOLD_PATH))


def reverse_hebrew(text):
    try:
        from bidi.algorithm import get_display
        return get_display(text)
    except ImportError:
        return text


# ── text layout ─────────────────────────────────────────────────────────────
def draw_rtl_text(c, text, x, y, font_name, font_size, max_width=None):
    """Draw RTL text; returns new y after all lines."""
    c.setFont(font_name, font_size)
    if max_width is None:
        c.drawRightString(x, y, reverse_hebrew(text))
        return y

    words = text.split()
    lines_out = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip() if current else word
        w = pdfmetrics.stringWidth(reverse_hebrew(candidate), font_name, font_size)
        if w > max_width and current:
            lines_out.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines_out.append(current)

    for ln in lines_out:
        c.drawRightString(x, y, reverse_hebrew(ln))
        y -= font_size + 4
    return y


# ── Q&A extraction ──────────────────────────────────────────────────────────
def extract_qa(filepath, book_name, only_new_marker=False):
    """
    Extract <details>/<summary> Q&A from a markdown file.
    If only_new_marker=True, only include questions whose raw text contains ✨.
    """
    questions = []
    content   = filepath.read_text(encoding="utf-8")

    story_match = re.search(r"#\s+(.+?)(?:\n|$)", content)
    story_name  = story_match.group(1).strip() if story_match else filepath.stem
    story_name  = re.sub(r"<[^>]+>", "", story_name).strip()
    story_name  = story_name.replace("✨", "").strip()

    current_section = "תרגול"
    lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        header_match = re.match(r"##\s+(.+)", line)
        if header_match:
            header_text = header_match.group(1).strip()
            for key, val in SECTION_TYPE_MAP.items():
                if key in header_text:
                    current_section = val
                    break

        if "<details>" in line:
            block_lines = []
            while i < len(lines):
                block_lines.append(lines[i])
                if "</details>" in lines[i]:
                    break
                i += 1
            block = "\n".join(block_lines)

            q_match = re.search(
                r"<summary>\s*<strong>\s*(.+?)\s*</strong>\s*</summary>",
                block, re.DOTALL,
            )
            if q_match:
                raw_question = q_match.group(1).strip()

                # For cross_chapter files: skip if not ✨-tagged
                if only_new_marker and "✨" not in raw_question:
                    i += 1
                    continue

                stars         = len(re.findall(r"⭐", raw_question))
                question_text = re.sub(r"^\d+\.\s*", "", raw_question)
                question_text = re.sub(r"[✨⭐]+\s*", "", question_text).strip()

                a_match = re.search(
                    r"</summary>\s*\n(.*?)\n\s*</details>", block, re.DOTALL
                )
                if a_match:
                    answer_text = a_match.group(1).strip()
                    answer_text = re.sub(r"<[^>]+>", "", answer_text)
                    answer_text = re.sub(r"\*\*([^*]+)\*\*", r"\1", answer_text)
                    answer_text = answer_text.strip()

                    if current_section == "מי אמר למי":
                        m1 = re.search(r"מי אמר:\s*(.+)", answer_text)
                        m2 = re.search(r"למי:\s*(.+)",    answer_text)
                        if m1 and m2:
                            answer_text = f"{m1.group(1).strip()} → {m2.group(1).strip()}"

                    if current_section == "נכון/לא נכון":
                        first = answer_text.split("\n")[0].strip()
                        if first:
                            answer_text = first

                    if len(answer_text) > 160:
                        answer_text = answer_text[:157] + "..."

                    questions.append({
                        "question": question_text,
                        "answer":   answer_text,
                        "book":     book_name,
                        "section":  current_section,
                        "story":    story_name,
                        "stars":    stars,
                        "kind":     "qa",
                    })
        i += 1
    return questions


# ── text-question extraction ────────────────────────────────────────────────
def extract_text_questions(filepath, book_key):
    """
    Extract text-based questions from text_questions/<book>.md,
    but only from story sections whose number is in NEW_TEXT_STORIES[book_key].
    """
    questions   = []
    book_name   = TEXT_BOOK_NAMES[book_key]
    new_stories = NEW_TEXT_STORIES[book_key]
    content     = filepath.read_text(encoding="utf-8")

    current_story     = ""
    current_story_num = 0

    lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        # Story section header: "## [✨ ]סיפור N: ..."
        story_match = re.match(r"##\s+(?:✨\s+)?סיפור\s+(\d+)\s*:\s*(.+)", line)
        if story_match:
            current_story_num = int(story_match.group(1))
            current_story     = story_match.group(2).strip()

        # Only process if this story is in the new set
        if current_story_num not in new_stories:
            i += 1
            continue

        # Look for **טקסט:** blocks
        if line.strip() == "**טקסט:**":
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

            question_text = ""
            answer_text   = ""
            search_limit  = min(j + 10, len(lines))
            while j < search_limit:
                if "<details>" in lines[j]:
                    block_lines = []
                    while j < len(lines):
                        block_lines.append(lines[j])
                        if "</details>" in lines[j]:
                            break
                        j += 1
                    block = "\n".join(block_lines)

                    q_match = re.search(
                        r"<summary>\s*<strong>\s*(?:שאלה:\s*)?(.+?)\s*</strong>\s*</summary>",
                        block, re.DOTALL,
                    )
                    if q_match:
                        question_text = re.sub(r"^שאלה:\s*", "", q_match.group(1).strip())

                    a_match = re.search(
                        r"</summary>\s*\n(.*?)\n\s*</details>", block, re.DOTALL
                    )
                    if a_match:
                        answer_text = a_match.group(1).strip()
                        answer_text = re.sub(r"<[^>]+>", "", answer_text)
                        answer_text = re.sub(r"\*\*([^*]+)\*\*", r"\1", answer_text)
                        answer_text = answer_text.strip()
                    break
                elif lines[j].strip().startswith("###"):
                    break
                else:
                    j += 1

            if text_excerpt and question_text and answer_text:
                if len(answer_text) > 200:
                    answer_text = answer_text[:197] + "..."
                questions.append({
                    "text_excerpt": text_excerpt,
                    "question":     question_text,
                    "answer":       answer_text,
                    "book":         book_name,
                    "story":        current_story,
                    "kind":         "text",
                })
        i += 1
    return questions


# ── collect everything ──────────────────────────────────────────────────────
def collect_qa_questions():
    all_q = []
    for book_name, path in NEW_STORY_FILES:
        if path.exists():
            all_q.extend(extract_qa(path, book_name, only_new_marker=False))
        else:
            print(f"  WARNING: {path} not found")

    for book_name, path in CROSS_CHAPTER_FILES:
        if path.exists():
            all_q.extend(extract_qa(path, book_name, only_new_marker=True))
        else:
            print(f"  WARNING: {path} not found")
    return all_q


def collect_text_questions():
    all_q = []
    for book_key in ("bereshit", "shoftim"):
        path = TEXT_QUESTION_DIR / f"{book_key}.md"
        if path.exists():
            all_q.extend(extract_text_questions(path, book_key))
        else:
            print(f"  WARNING: {path} not found")
    return all_q


# ── PDF creation ─────────────────────────────────────────────────────────────
def create_pdf(qa_questions, text_questions, output_path):
    register_fonts()

    page_width, page_height = A4
    margin_x      = 1.2 * cm
    margin_top    = 1.2 * cm
    margin_bottom = 1.5 * cm
    content_width = page_width - 2 * margin_x
    right_x       = page_width - margin_x

    c = canvas.Canvas(str(output_path), pagesize=A4)
    page_num = [0]

    def finish_page():
        page_num[0] += 1
        c.setFont(FONT_NAME, 8)
        c.setFillColor(HexColor("#888888"))
        c.drawCentredString(page_width / 2, 0.8 * cm, str(page_num[0]))
        c.setFillColor(HexColor("#000000"))
        c.showPage()

    # ── Title page ──────────────────────────────────────────────────────────
    c.setFont(FONT_BOLD, 34)
    c.drawCentredString(page_width / 2, page_height - 6.5 * cm,
                        reverse_hebrew('חידון תנ"ך'))

    c.setFont(FONT_BOLD, 22)
    c.drawCentredString(page_width / 2, page_height - 9 * cm,
                        reverse_hebrew("פרקים חדשים — דף תרגול"))

    c.setFont(FONT_NAME, 14)
    c.drawCentredString(page_width / 2, page_height - 11 * cm,
                        reverse_hebrew('בראשית כ"ט–ל"א א\'  |  שופטים י\'–ט"ז'))

    # Breakdown
    y = page_height - 13.5 * cm
    c.setFont(FONT_BOLD, 12)
    c.drawCentredString(page_width / 2, y,
                        reverse_hebrew(f"סה\"כ {len(qa_questions)} שאלות תרגול  +  {len(text_questions)} שאלות על טקסט"))
    y -= 0.8 * cm

    c.setFont(FONT_NAME, 11)
    # Q&A by book
    book_counts_qa: dict[str, int] = {}
    for q in qa_questions:
        book_counts_qa[q["book"]] = book_counts_qa.get(q["book"], 0) + 1
    for book, cnt in book_counts_qa.items():
        c.drawCentredString(page_width / 2, y,
                            reverse_hebrew(f"{book}: {cnt} שאלות תרגול"))
        y -= 22

    y -= 6
    # Text Qs by book
    book_counts_txt: dict[str, int] = {}
    for q in text_questions:
        book_counts_txt[q["book"]] = book_counts_txt.get(q["book"], 0) + 1
    for book, cnt in book_counts_txt.items():
        c.drawCentredString(page_width / 2, y,
                            reverse_hebrew(f"{book}: {cnt} שאלות על טקסט"))
        y -= 22

    finish_page()

    # ── Part 1: Q&A questions ──────────────────────────────────────────────
    y = page_height - margin_top

    # Section divider header
    c.setFont(FONT_BOLD, 13)
    c.setFillColor(HexColor("#154360"))
    c.drawRightString(right_x, y, reverse_hebrew("חלק א׳ — שאלות תרגול"))
    c.setFillColor(HexColor("#000000"))
    y -= 20
    c.setStrokeColor(HexColor("#154360"))
    c.setLineWidth(0.8)
    c.line(margin_x, y, right_x, y)
    c.setLineWidth(1)
    y -= 14

    for i, q in enumerate(qa_questions, 1):
        q_text = q["question"]
        answer = q["answer"]

        q_w       = pdfmetrics.stringWidth(reverse_hebrew(q_text), FONT_BOLD, 9)
        q_lines   = max(1, int(q_w / content_width) + 1)
        a_w       = pdfmetrics.stringWidth(reverse_hebrew(answer), FONT_NAME, 8)
        a_lines   = max(1, int(a_w / content_width) + 1)
        needed    = q_lines * 13 + a_lines * 12 + 14

        if y - needed < margin_bottom:
            finish_page()
            y = page_height - margin_top

        stars_str = "⭐" * q["stars"] if q["stars"] else ""
        q_line = f".{i}  {stars_str}  {q_text}" if stars_str else f".{i}  {q_text}"
        y = draw_rtl_text(c, q_line, right_x, y, FONT_BOLD, 9, content_width)

        c.setFillColor(HexColor("#1a5276"))
        y = draw_rtl_text(c, f"תשובה: {answer}", right_x - 15, y,
                          FONT_NAME, 8, content_width - 15)
        c.setFillColor(HexColor("#000000"))
        y -= 7

    finish_page()

    # ── Part 2: text questions ─────────────────────────────────────────────
    y = page_height - margin_top

    c.setFont(FONT_BOLD, 13)
    c.setFillColor(HexColor("#145a32"))
    c.drawRightString(right_x, y, reverse_hebrew("חלק ב׳ — שאלות על טקסט"))
    c.setFillColor(HexColor("#000000"))
    y -= 20
    c.setStrokeColor(HexColor("#145a32"))
    c.setLineWidth(0.8)
    c.line(margin_x, y, right_x, y)
    c.setLineWidth(1)
    y -= 14

    for i, q in enumerate(text_questions, 1):
        excerpt  = q["text_excerpt"]
        question = q["question"]
        answer   = q["answer"]

        combined = f'.{i}  "{excerpt}" — {question}'
        c_w      = pdfmetrics.stringWidth(reverse_hebrew(combined), FONT_BOLD, 9)
        c_lines  = max(1, int(c_w / content_width) + 1)
        a_w      = pdfmetrics.stringWidth(reverse_hebrew(answer), FONT_NAME, 8)
        a_lines  = max(1, int(a_w / content_width) + 1)
        needed   = c_lines * 13 + a_lines * 12 + 14

        if y - needed < margin_bottom:
            finish_page()
            y = page_height - margin_top

        y = draw_rtl_text(c, combined, right_x, y, FONT_BOLD, 9, content_width)

        c.setFillColor(HexColor("#145a32"))
        y = draw_rtl_text(c, f"תשובה: {answer}", right_x - 20, y,
                          FONT_NAME, 8, content_width - 20)
        c.setFillColor(HexColor("#000000"))
        y -= 8

    # number last page
    page_num[0] += 1
    c.setFont(FONT_NAME, 8)
    c.setFillColor(HexColor("#888888"))
    c.drawCentredString(page_width / 2, 0.8 * cm, str(page_num[0]))
    c.setFillColor(HexColor("#000000"))

    c.save()
    return str(output_path)


# ── main ────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed",   type=int, default=42)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    print("Collecting Q&A questions from new story files + cross_chapter ✨...")
    qa_qs = collect_qa_questions()
    print(f"  → {len(qa_qs)} Q&A questions")

    print("Collecting text questions from new story sections...")
    txt_qs = collect_text_questions()
    print(f"  → {len(txt_qs)} text questions")

    # Shuffle within each type
    random.seed(args.seed)
    random.shuffle(qa_qs)
    random.shuffle(txt_qs)

    output_path = Path(args.output) if args.output else OUTPUT_FILE
    print(f"\nGenerating PDF → {output_path} ...")
    result = create_pdf(qa_qs, txt_qs, output_path)
    print(f"Done: {result}")

    print(f"\nBreakdown — Q&A:")
    bc: dict[str, int] = {}
    for q in qa_qs:
        bc[q["book"]] = bc.get(q["book"], 0) + 1
    for b, n in sorted(bc.items()):
        print(f"  {b}: {n}")

    print(f"\nBreakdown — text:")
    bt: dict[str, int] = {}
    for q in txt_qs:
        bt[q["book"]] = bt.get(q["book"], 0) + 1
    for b, n in sorted(bt.items()):
        print(f"  {b}: {n}")


if __name__ == "__main__":
    main()
