import pymupdf  # PyMuPDF
import pandas as pd
import re

# ---------------------
PDF_FILE = "egzai/2019.pdf"
ANSWER_FILE = "egzai/2019_ats.pdf"
OUTPUT_EXCEL = "surinkti/2019.xlsx"
REMOVE = "101BIVU0"
LASTPAGE = 8
# ---------------------

skip_keywords = [
    "žr. pav", "pav.", "paveiksl", "Paveiksl", "lentel", "pavaizduot", "eiga",
    "Grafik", "grafik", "tašką", "šaltinis", "schema", "nuotraukoje", "lentelėje", "Schemoje", "schemoje", "diagrama", "pažymėta"
]

# Category mapping based on keyword fragments
category_keywords = {
    25: ["ląstel", "bakter"],
    26: ["ląstelės prisitaikiusios", "įgyjamas", "refleks", "genas", "DNR"],
    27: ["cheminis elementas", "angliavanden", "radioaktyv", "maisto pried", "maisto papild", "baltym", "cheminėms reakcij", "duj"],
    28: ["plauč", "kraujagysl", "galvos smegen", "virkštel", "pacient", "kepenys", "krauj", "adrenalin", "smegen", "kvėpavimo tak", "paauglyst", "kasa", "inkstai", "kiaušialąsči", "cholesterol",
         "plonosios žarn"],
    29: ["gyvūn"],
    30: ["augal", "fotosintez", "papar"],
    31: ["karalyst", "bendrij", "teorij", "gryb", "klasifikacij", "rūšy", "lygmeniui"],
    32: ["aplinkosaug", "apsaugoti", "ekosistem", "ekologin", "populiacij", ],
}

def assign_category(text):
    text_lower = text.lower()
    for category, keywords in category_keywords.items():
        if any(kw in text_lower for kw in keywords):
            return category
    return "null"  # No category matched


def clean_answer(text):
    return re.sub(r'[.;]', '', text)

def remove_header_footer_noise(text):
    # Remove blocks starting with a line like: 1 word – word – word
    text = re.sub(
        r"""
        ^\d+\s+[^\n–]+(?:\s+–\s+[^\n–]+)+   # first line like "1 stiebagumbis – bulwocebula – ..."
        (?:\n[^\n]*){1,5}                   # up to 5 lines that follow (junk)
        """,
        "",
        text,
        flags=re.MULTILINE | re.VERBOSE
    )

    # Remove uppercase titles
    text = re.sub(r"^[A-ZĄČĘĖĮŠŲŪŽ\s]{10,}$", "", text, flags=re.MULTILINE)

    # Remove codes or short standalone numbers (e.g., "231BIVU0", "3")
    text = re.sub(r"^[A-Z0-9]{6,}$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\d{1,3}$", "", text, flags=re.MULTILINE)

    text = re.sub(r'^\s*\d{1,3}\s*$', '', text, flags=re.MULTILINE)

    text = text.replace(REMOVE, '')
    text = text.replace("Juodraštis", '')
    text = text.replace("2010 M. BIOLOGIJOS VALSTYBINIO BRANDOS EGZAMINO UŽDUOTIS ", '')
    text = text.replace("B",'')
    text = text.replace("*", '')
    # Remove excess blank lines
    text = re.sub(r'\n\s*\n+', '\n\n', text)

    # Remove reference marks
    # Step 1: remove digits after letters but not if followed by dot
    text = re.sub(r'(?<=[a-zA-Z])(\d+)(?!\.)', '', text)


    return text.strip()





def get_mcq_answers(pdf_path):
    doc = pymupdf.open(pdf_path)
    first_page_text = doc[0].get_text()

    part1_answer, part2_answer = first_page_text, ""
    split_match_answer = re.search(r"\bII DALIS\b", first_page_text, flags=re.IGNORECASE)
    if split_match_answer:
        part1_answer = first_page_text[:split_match_answer.start()]
        part2_answer = first_page_text[split_match_answer.start():]
    else:
        print("⚠️ Could not find 'II dalis'. Using full text as Part I.")


    with open("outputAnswer.txt", "w", encoding="utf-8") as f:
        f.write(first_page_text)

    # Find all standalone capital letters A–D (answer choices)
    answers = re.findall(r"\b([ABCD])\b", part1_answer)
    mcq_answers = {str(i + 1).zfill(2): answers[i] for i in range(min(30, len(answers)))}

    part2_blocks = re.split(r"\n(?=\d{1,2}\s)", part2_answer)
    part2_answers = {}
    for block in part2_blocks:
        match = re.match(r"(?P<num>\d{1,2})\s+(?P<answer>.+)", block.strip(), flags=re.DOTALL)
        if match:
            num = match.group("num").zfill(2)
            answer = re.sub(r'\s+', ' ', match.group("answer").strip())
            part2_answers[num] = answer

    print(f" Found {len(mcq_answers)} MCQ answers and {len(part2_answers)} open-ended answers.")
    return mcq_answers, part2_answers



def extract_open_questions_from_part_ii(text):
    open_questions = []

    # Locate start of Part II
    match = re.search(r"II dalis.*?tašku\.", text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        print("️ Could not locate Part II")
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
        if num == "0":
            print(" Detected question number 0 — correcting to 10")
            num = "10"
        qtext = re.sub(r'\s+', ' ', match_local.group("question")).strip()

        # Skip if it contains image/table indicators
        if any(kw in qtext.lower() for kw in skip_keywords):
            print(f" Skipping Part II Q{num} — image or diagram referenced")
            continue

        open_questions.append({
            "Question No.": num,
            "Category": assign_category(qtext),
            "Question": qtext,
            "fa_check": "TRUE"
        })

    return open_questions







def extract_clean_text_from_pdf(pdf_path, start_page=2, end_page=LASTPAGE):
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
print(" Reading exam content from PDF...")
raw_text = extract_clean_text_from_pdf(PDF_FILE)
raw_text = remove_header_footer_noise(raw_text)
with open("output.txt", "w", encoding="utf-8") as f:
    f.write(raw_text)

print("getting answers...")
mcq_answers, open_answers = get_mcq_answers(ANSWER_FILE)

print(" Parsing questions...")
part1_text, part2_text = raw_text, ""
split_match = re.search(r"\bII dalis\b", raw_text, flags=re.IGNORECASE)
if split_match:
    part1_text = raw_text[:split_match.start()]
    part2_text = raw_text[split_match.start():]
else:
    print(" Could not find 'II dalis'. Using full text as Part I.")

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
        print(f" Skipping {qnum} (image-based)")
        continue


    options = re.findall(r"(?:^|\n)([A-D])\s+(.*?)(?=(?:\n[A-D]\s|$))", block, flags=re.DOTALL)

    if len(options) < 4:
        print(f" Skipping question {qnum} — not enough options found ({len(options)}).")
        continue

    options_dict = {letter: text.strip() for letter, text in options}
    correct_letter = mcq_answers.get(qnum, "")
    correct_answer = options_dict.get(correct_letter, "")
    wrong_answers = [ans for key, ans in options_dict.items() if key != correct_letter]
    correct_answer = correct_answer.replace(';', '')
    correct_answer = clean_answer(correct_answer)
    wrong_answers = [clean_answer(ans) for ans in wrong_answers]
    question_text = re.sub(r'\s+', ' ', question_text).strip()
    correct_answer = re.sub(r'\s+', ' ', correct_answer).strip()
    wrong_answers = [re.sub(r'\s+', ' ', ans).strip() for ans in wrong_answers]
    # Extract options
    data.append({
        "Question No.": qnum,
        "Category": assign_category(question_text),
        "Question": question_text,
        "Correct Answer": correct_answer,
        "Wrong Option 1": wrong_answers[0],
        "Wrong Option 2": wrong_answers[1],
        "Wrong Option 3": wrong_answers[2],
        "fa_check": "FALSE"
    })


print(" Extracting open-ended questions from Part II...")
open_questions = extract_open_questions_from_part_ii(raw_text)





for q in open_questions:
    qnum = q["Question No."].zfill(2)
    q["Correct Answer"] = open_answers.get(qnum, "")
    q["Wrong Option 1"] = ""
    q["Wrong Option 2"] = ""
    q["Wrong Option 3"] = ""

# === Combine with MCQs
mcq_df = pd.DataFrame(data)
open_df = pd.DataFrame(open_questions)
combined_df = pd.concat([mcq_df, open_df], ignore_index=True)
combined_df["Question No."] = combined_df["Question No."].astype(str).str.zfill(2)

# === Export to Excel ===
print(f" Saving {len(combined_df)} questions to Excel...")
df = pd.DataFrame(combined_df)
df.to_excel(OUTPUT_EXCEL, index=False)
print(f" Done! File saved to: {OUTPUT_EXCEL}")
