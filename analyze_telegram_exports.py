"""
Analyze Telegram HTML exports and print reusable sales conversation patterns.

Run:
    python analyze_telegram_exports.py "C:\\Users\\user\\Downloads\\Telegram Desktop\\чаты архивы"
"""

from __future__ import annotations

import argparse
import html
import re
from collections import Counter
from pathlib import Path


MESSAGE_RE = re.compile(
    r'<div class="from_name">\s*(.*?)\s*</div>.*?<div class="text">\s*(.*?)\s*</div>',
    re.S,
)
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


def clean_text(raw: str) -> str:
    text = html.unescape(raw)
    text = text.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    text = TAG_RE.sub(" ", text)
    text = SPACE_RE.sub(" ", text).strip()
    return text


def iter_messages(root: Path):
    for html_file in root.rglob("messages*.html"):
        content = html_file.read_text(encoding="utf-8", errors="ignore")
        for author, body in MESSAGE_RE.findall(content):
            yield clean_text(author), clean_text(body), html_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze Telegram HTML exports")
    parser.add_argument("root", help="Path to the folder with ChatExport_* directories")
    parser.add_argument("--manager", default="Алексей", help="Manager name to treat as seller messages")
    args = parser.parse_args()

    root = Path(args.root)
    if not root.exists():
        raise SystemExit(f"Path not found: {root}")

    seller_messages = []
    customer_questions = []

    for author, body, _file in iter_messages(root):
        if not body:
            continue
        if args.manager.lower() in author.lower():
            seller_messages.append(body)
        else:
            if "?" in body or len(body.split()) <= 8:
                customer_questions.append(body)

    openings = Counter()
    closings = Counter()
    short_replies = Counter()

    for message in seller_messages:
        lowered = message.lower()
        if lowered.startswith(("добрый", "здравствуйте", "привет")):
            openings[message[:120]] += 1
        if any(word in lowered for word in ("звоните", "пишите", "обращайтесь", "на связи")):
            closings[message[:120]] += 1
        if len(message.split()) <= 8:
            short_replies[message[:120]] += 1

    print(f"Seller messages analyzed: {len(seller_messages)}")
    print(f"Customer short/questions analyzed: {len(customer_questions)}")

    print("\nTop seller openings:")
    for text, count in openings.most_common(10):
        print(f"{count:>3} | {text}")

    print("\nTop seller closings:")
    for text, count in closings.most_common(10):
        print(f"{count:>3} | {text}")

    print("\nTop short seller replies:")
    for text, count in short_replies.most_common(15):
        print(f"{count:>3} | {text}")

    print("\nSample customer prompts:")
    for prompt in customer_questions[:20]:
        print(f"- {prompt}")


if __name__ == "__main__":
    main()
