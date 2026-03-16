#!/usr/bin/env python3
import argparse
import csv
import os
import random
import re
import sys
import time
from typing import List, Tuple
import requests

DEFAULT_FROM = "whatsapp:+15555550123"

FALLBACK_SNIPPETS = [
    "A live agent will reach out during office hours. Chat is now frozen.",
    "A live agent will get back to you shortly",
    "Sorry, I couldn’t find that Dongle ID",
    "That Dongle ID looks invalid",
    "Hi ! i&apos;m Kai - Kommu Chatbot",
    "Hi ! i'm Kai - Kommu Chatbot",
    "Need a live agent ? Type LA",
    "If you need a live agent, type LA",
]

# --- Very light language checks (match your app’s heuristics) ---
def looks_english(s: str) -> bool:
    t = f" {(s or '').lower()} "
    en_hits = sum(w in t for w in [" the ", " and ", " to ", " is ", " are ", " you ", " we ", " will ", " please "])
    bm_hits = sum(w in t for w in [" dan ", " ialah ", " anda ", " kami ", " akan ", " sila ", " waktu ", " alamat "])
    return en_hits >= 2 and bm_hits == 0

def looks_malay(s: str) -> bool:
    t = f" {(s or '').lower()} "
    bm_hits = sum(w in t for w in [" dan ", " ialah ", " anda ", " kami ", " akan ", " sila ", " waktu ", " alamat "])
    en_hits = sum(w in t for w in [" the ", " and ", " to ", " is ", " are ", " you ", " we ", " will ", " please "])
    return bm_hits >= 1 and en_hits == 0

def classify_status(answer: str, requested: str) -> str:
    if not answer or not answer.strip():
        return "EMPTY"
    # language check
    if requested.upper() == "EN":
        if not looks_english(answer):
            return "WRONG_LANGUAGE"
    elif requested.upper() == "BM":
        if not looks_malay(answer):
            return "WRONG_LANGUAGE"
    # fallback patterns
    low = (answer or "").lower()
    for snip in FALLBACK_SNIPPETS:
        if snip.lower() in low:
            return "GAP"
    return "OK"

def post_whatsapp(endpoint: str, body: str, from_num: str = DEFAULT_FROM, timeout=15) -> Tuple[int, str]:
    try:
        resp = requests.post(
            endpoint,
            data={"Body": body, "From": from_num},
            timeout=timeout,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        # TwiML XML → extract <Message>...</Message> content if present
        text = resp.text or ""
        m = re.search(r"<Message>(.*?)</Message>", text, flags=re.S | re.I)
        if m:
            # unescape very basic entities
            msg = m.group(1)
            msg = msg.replace("&apos;", "'").replace("&quot;", '"').replace("&amp;", "&")
            return resp.status_code, msg.strip()
        return resp.status_code, text.strip()
    except Exception as e:
        return 0, f"[EXC] {e}"

def load_questions_from_csv(csv_path: str) -> List[str]:
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        # Auto-detect header vs plain list:
        # If the first row has more than 1 column and any column includes "question", we treat that column as source
        header = next(reader, None)
        if header is None:
            return rows
        header_l = [h.strip().lower() for h in header]
        q_idx = None
        for i, name in enumerate(header_l):
            if "question" in name:
                q_idx = i
                break
        if q_idx is not None:
            # treat remaining lines as rows with a Question column
            for r in reader:
                if not r or len(r) <= q_idx:
                    continue
                q = (r[q_idx] or "").strip()
                if q:
                    rows.append(q)
        else:
            # treat file as 1-column list (first cell was the first question)
            first = (header[0] or "").strip()
            if first:
                rows.append(first)
            for r in reader:
                if not r:
                    continue
                q = (r[0] or "").strip()
                if q:
                    rows.append(q)
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", default="http://127.0.0.1:8000/webhook", help="Bot webhook endpoint")
    ap.add_argument("--csv", help="CSV with questions (either one column, or has a 'Question' column). If omitted, uses a tiny built-in set.")
    ap.add_argument("--out", default="reports/bot_bilingual_results.csv", help="Where to save results CSV")
    ap.add_argument("--max", type=int, default=0, help="Max questions to test (0 = all)")
    ap.add_argument("--sleep", type=float, default=0.25, help="Sleep seconds between requests")
    ap.add_argument("--shuffle", action="store_true", help="Shuffle the questions before testing")
    ap.add_argument("--bilingual", action="store_true", help="Send each question twice: forced English and forced Malay")
    args = ap.parse_args()

    # Gather questions
    if args.csv and os.path.exists(args.csv):
        questions = load_questions_from_csv(args.csv)
    else:
        questions = [
            "What is KommuAssist?",
            "How does it work?",
            "Where is your office and working hours?",
            "How to claim warranty?",
            "Boleh pasang pada Perodua Myvi Gen 3?",
            "Peranti tiada LED berkelip",
            "Nak beli Kommu, bagaimana caranya?",
        ]

    if args.shuffle:
        random.shuffle(questions)
    if args.max and args.max > 0:
        questions = questions[: args.max]

    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    results = []
    total = len(questions)
    print(f"[+] Testing {total} base questions against {args.endpoint}")
    for idx, q in enumerate(questions, 1):
        # Variants:
        variants = [("original", "", "AUTO")]
        if args.bilingual:
            # Force-EN and Force-BM variants
            variants = [
                ("forced-EN", f"Please answer in English: {q}", "EN"),
                ("forced-BM", f"Sila jawab dalam Bahasa Melayu: {q}", "BM"),
            ]

        for variant_name, body, lang_req in variants:
            payload = body if body else q
            code, answer = post_whatsapp(args.endpoint, payload)
            if code != 200:
                status = "ERROR_HTTP"
            else:
                status = classify_status(answer, lang_req if lang_req in ("EN", "BM") else "EN")  # default to EN check for original
            results.append(
                {
                    "Question": q,
                    "Variant": variant_name,
                    "LanguageRequested": lang_req,
                    "Answer": answer,
                    "HTTP": code,
                    "Status": status,
                }
            )
            print(f"[{idx}/{total}] {variant_name} :: {status}")

            time.sleep(args.sleep)

    # Write CSV
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["Question", "Variant", "LanguageRequested", "Answer", "HTTP", "Status"])
        w.writeheader()
        for r in results:
            w.writerow(r)

    print(f"[+] Wrote {len(results)} rows → {args.out}")

if __name__ == "__main__":
    main()
