import pymupdf  # PyMuPDF
import pandas as pd
import re

# ---------------------
PDF_FILE = "egzai/2024.pdf"
ANSWER_FILE = "egzai/2024_ats.pdf"
OUTPUT_EXCEL = "surinkti/2024.xlsx"
# ---------------------

skip_keywords = [
    "žr. pav", "pav.", "paveiksl", "Paveiksl", "lentel", "pavaizduot", "eiga",
    "Grafik", "grafik", "tašką", "šaltinis", "schema", "nuotraukoje", "lentelėje"
]





def extract_open_questions_from_part_ii(text):
    open_questions = []

    # Locate start of Part II
    match = re.search(r"II dalis.*?tašku\.", text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        print("⚠️ Could not locate Part II")
        return open_questions

    part2_text_local = text[match.end():]

    # Remove extra blank lines
    part2_text_local = re.sub(r'\n\s*\n+', '\n\n', part2_text_local)

    # Split on open-ended question numbers like "1." or "10."
    blocks = re.split(r"\n?(?=\d{1,2}\.\s)", part2_text_local)

    for block_open in blocks:
        block_open = block_open.strip()
        if not block_open:
            continue

        # Match number and content
        match_local = re.match(r"(?P<num>\d{1,2})\.\s*(?P<question>.+)", block_open, flags=re.DOTALL)
        if not match_local:
            continue

        num = match_local.group("num")
        qtext = re.sub(r'\s+', ' ', match_local.group("question")).strip()

        # Skip if it contains image/table indicators
        if any(kw in qtext.lower() for kw in skip_keywords):
            print(f"⏭ Skipping Part II Q{num} — image or diagram referenced")
            continue

        open_questions.append({
            "Question No.": num,
            "Question": qtext,
            "fa_check": "TRUE"
        })

    return open_questions







def extract_clean_text_from_pdf(pdf_path, start_page=1, end_page=8):
    doc = pymupdf.open(pdf_path)
    text = "\n".join(doc[i].get_text() for i in range(start_page - 1, end_page))
    # Remove common headers/footers
    text = re.sub(
        r"RIBOTO NAUDOJIMO.*?\)\s*|BIOLOGIJA\s+●.*?sesija|NEPAMIRŠKITE.*?LAPĄ",
        "", text, flags=re.IGNORECASE | re.DOTALL
    )
    # Normalize multiple blank lines
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    return text


# === Main workflow ===
print("📄 Reading exam content from PDF...")
raw_text = extract_clean_text_from_pdf(PDF_FILE)

print("🔍 Parsing questions...")
part1_text, part2_text = raw_text, ""
split_match = re.search(r"\bII dalis\b", raw_text, flags=re.IGNORECASE)
if split_match:
    part1_text = raw_text[:split_match.start()]
    part2_text = raw_text[split_match.start():]
else:
    print("⚠️ Could not find 'II dalis'. Using full text as Part I.")

question_blocks = re.split(r"(?=\d{2}\.\s)", part1_text)

data = []

for block in question_blocks:
    block = block.strip()
    print('\n')
    print(block)
    print('\n')
    if not block:
        continue

    match = re.match(r"(?P<num>\d{2})\.\s(?P<question>.+?)(?=(\nA\s|$))", block, flags=re.DOTALL)
    if not match:
        continue

    q = match.groupdict()
    qnum = q["num"]
    question_text = re.sub(r"\s+", " ", q["question"].strip())

    if any(kw in question_text.lower() for kw in skip_keywords):
        print(f"⏭ Skipping {qnum} (image-based)")
        continue


    options = re.findall(r"(?:^|\n)([A-D])\s+(.*?)(?=(?:\n[A-D]\s|$))", block, flags=re.DOTALL)

    if len(options) < 4:
        print(f"⚠️ Skipping question {qnum} — not enough options found ({len(options)}).")
        continue

    options_dict = {letter: text.strip() for letter, text in options}

    # Extract options
    data.append({
        "Question No.": qnum,
        "Question": question_text,
        "Correct Answer": options_dict['A'],
        "Wrong Option 1": options_dict['B'],
        "Wrong Option 2": options_dict['C'],
        "Wrong Option 3": options_dict['D'],
        "fa_check": "FALSE"
    })


print("📘 Extracting open-ended questions from Part II...")
open_questions = extract_open_questions_from_part_ii(raw_text)

# === Combine with MCQs
mcq_df = pd.DataFrame(data)
open_df = pd.DataFrame(open_questions)

if not open_df.empty:
    open_df["Correct Answer"] = ""
    open_df["Wrong Option 1"] = ""
    open_df["Wrong Option 2"] = ""
    open_df["Wrong Option 3"] = ""
    combined_df = pd.concat([mcq_df, open_df], ignore_index=True)
else:
    combined_df = mcq_df

# === Export to Excel ===
print(f"💾 Saving {len(combined_df)} questions to Excel...")
df = pd.DataFrame(combined_df)
df.to_excel(OUTPUT_EXCEL, index=False)
print(f"✅ Done! File saved to: {OUTPUT_EXCEL}")
