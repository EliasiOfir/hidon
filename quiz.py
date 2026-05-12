#!/usr/bin/env python3
"""Interactive Bible Quiz - חידון התנ"ך שלב ב'"""

import os
import re
import random
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BOOKS = {
    "1": ("בראשית", ["bereshit"], "text_questions/bereshit.md"),
    "2": ("שמות", ["shemot"], "text_questions/shemot.md"),
    "3": ("במדבר", ["bamidbar"], "text_questions/bamidbar.md"),
    "4": ("יהושע", ["yehoshua"], "text_questions/yehoshua.md"),
    "5": ("שופטים", ["shoftim"], "text_questions/shoftim.md"),
    "6": ("כל הספרים", ["bereshit", "shemot", "bamidbar", "yehoshua", "shoftim"], None),
}

QUESTION_TYPES = {
    "1": "שאלות סיפור (knowledge questions)",
    "2": "שאלות טקסט (text identification)",
    "3": "מעורב",
}


def parse_story_questions(book_dirs):
    """Parse <details> questions from story markdown files."""
    questions = []
    for book_dir in book_dirs:
        dir_path = os.path.join(BASE_DIR, book_dir)
        if not os.path.isdir(dir_path):
            continue
        for fname in sorted(os.listdir(dir_path)):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(dir_path, fname)
            with open(fpath, encoding="utf-8") as f:
                content = f.read()
            # Extract story title from filename
            story = fname.replace(".md", "").replace("_", " ")
            # Find all <details> blocks
            pattern = re.compile(
                r"<details>\s*<summary><strong>(.*?)</strong></summary>\s*(.*?)\s*</details>",
                re.DOTALL,
            )
            for m in pattern.finditer(content):
                q = m.group(1).strip()
                a = m.group(2).strip()
                if q and a:
                    questions.append({"q": q, "a": a, "source": story, "type": "story"})
    return questions


def parse_text_questions(text_files):
    """Parse text-identification questions from text_questions/*.md files."""
    questions = []
    for tf in text_files:
        if tf is None:
            continue
        fpath = os.path.join(BASE_DIR, tf)
        if not os.path.isfile(fpath):
            continue
        with open(fpath, encoding="utf-8") as f:
            content = f.read()
        # Find blocks: quote + details question
        pattern = re.compile(
            r"> (.*?)\n+<details>\s*<summary><strong>(.*?)</strong></summary>\s*(.*?)\s*</details>",
            re.DOTALL,
        )
        for m in pattern.finditer(content):
            quote = m.group(1).strip()
            q = m.group(2).strip()
            a = m.group(3).strip()
            if quote and q and a:
                questions.append({
                    "q": f'טקסט: "{quote}"\n{q}',
                    "a": a,
                    "source": tf,
                    "type": "text",
                })
    return questions


def clear():
    os.system("clear" if os.name == "posix" else "cls")


def print_header():
    print("=" * 60)
    print("       חידון התנ\"ך - שלב ב'       ".center(60))
    print("=" * 60)


def choose_menu(title, options):
    print(f"\n{title}")
    for k, v in options.items():
        print(f"  {k}. {v}")
    while True:
        choice = input("\nבחר מספר: ").strip()
        if choice in options:
            return choice
        print("בחירה לא תקינה, נסה שוב.")


def run_quiz(questions, total):
    if not questions:
        print("\nלא נמצאו שאלות. בדוק שהקבצים קיימים.")
        return

    random.shuffle(questions)
    questions = questions[:total]

    score = 0
    for i, q_item in enumerate(questions, 1):
        clear()
        print_header()
        print(f"\nשאלה {i}/{len(questions)}")
        if q_item.get("source"):
            print(f"נושא: {q_item['source']}")
        print("-" * 60)
        print(f"\n{q_item['q']}\n")

        input("הקש Enter לצפייה בתשובה...")
        print("\n--- תשובה ---")
        print(q_item["a"])
        print()

        while True:
            ans = input("האם ידעת? (כ/ל): ").strip().lower()
            if ans in ("כ", "ל", "k", "y", "n"):
                break
        if ans in ("כ", "k", "y"):
            score += 1

        print(f"\nציון עד כה: {score}/{i}")
        if i < len(questions):
            input("\nהקש Enter לשאלה הבאה...")

    clear()
    print_header()
    print(f"\n*** סיום החידון ***\n")
    print(f"ציון סופי: {score}/{len(questions)}")
    pct = int(score / len(questions) * 100)
    print(f"אחוז הצלחה: {pct}%")
    if pct == 100:
        print("מושלם! 🌟")
    elif pct >= 80:
        print("כל הכבוד!")
    elif pct >= 60:
        print("טוב, יש מה לשפר.")
    else:
        print("כדאי לחזור על החומר.")
    print()


def main():
    while True:
        clear()
        print_header()

        book_choice = choose_menu("בחר ספר:", {k: v[0] for k, v in BOOKS.items()})
        book_name, book_dirs, text_file = BOOKS[book_choice]

        if book_choice == "6":
            text_files = [v[2] for v in BOOKS.values() if v[2]]
        else:
            text_files = [text_file] if text_file else []

        q_type = choose_menu("בחר סוג שאלות:", QUESTION_TYPES)

        story_qs = []
        text_qs = []
        if q_type in ("1", "3"):
            story_qs = parse_story_questions(book_dirs)
        if q_type in ("2", "3"):
            text_qs = parse_text_questions(text_files)

        all_qs = story_qs + text_qs
        if not all_qs:
            print("\nלא נמצאו שאלות לבחירה זו.")
            input("הקש Enter להמשך...")
            continue

        print(f"\nנמצאו {len(all_qs)} שאלות.")
        while True:
            n_input = input("כמה שאלות לשאול? (Enter = 10): ").strip()
            if n_input == "":
                n = 10
                break
            try:
                n = int(n_input)
                if 1 <= n <= len(all_qs):
                    break
                print(f"הכנס מספר בין 1 ל-{len(all_qs)}.")
            except ValueError:
                print("הכנס מספר.")

        run_quiz(all_qs, n)

        again = input("חידון נוסף? (כ/ל): ").strip().lower()
        if again not in ("כ", "k", "y"):
            print("\nשלום! 👋")
            break


if __name__ == "__main__":
    main()
