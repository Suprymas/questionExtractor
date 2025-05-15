import pymupdf # PyMuPDF
import pandas as pd
import requests
import base64
import os
from PIL import Image
import io
import re

# ---------------------
APP_ID = "oops"
APP_KEY = "oops"
PDF_FILE = "egzai/2009.pdf"
OUTPUT_EXCEL = "surinkti/2009.xlsx"
ANSWER_FILE = "egzai/2009_ats.pdf"
# ---------------------

# Fix OCR misrecognized characters
char_fixes = {
    'è': 'ė', 'ė̀': 'ė', 'ė́': 'ė', 'ė̃': 'ė', 'ě':'ė' ,
    'õ': 'o', 'ì': 'i', 'ị': 'į', 'í': 'i', 'í̇': 'i', 'ı':'i',
    'į̇': 'į', 'İ': 'į', 'ù': 'u', 'ū̀': 'ū', 'û': 'u',
    'ñ': 'n', 'č́': 'č', 'š́': 'š', 'ž́': 'ž', 'à': 'a', 'a̧': 'ą',
    'é': 'ė', 'ẻ': 'ė', 'ư': 'ų', 'Icentr':'Įcentr', 'ụ':'ų', 'ittempis' : 'įtempis',
    'ivair': 'įvair', '$${ }^{1}$$': '', '$${ }^{2}$$': '', '$${ }^{3}$$': '',
    'ijungiami': 'įjungiami', "It ": "Į", 'ú': 'ų', 'ş':'š', 'igyja':'įgyja', 'ittempimo':'įtempimo'
}
category_map = {
    "Mechanika": 18,
    "Molekulinė fizika": 19,
    "Elektrodinamika": 20,
    "Svyravimai ir bangos": 21,
    "Modernioji fizika": 22,
    "Astronomija": 23,
}

skip_keywords = [
    "žr. pav", "pav.", "paveiksl", "Paveiksl", "lentel", "1 pav", "2 pav", "3 pav", "pavaizduot", " eiga", "Sinusai",
    "Grafik", "grafik", "tašką O", "Taške", "taške",
]

def get_mcq_answers(pdf_path):
    doc = pymupdf.open(pdf_path)
    first_page_text = doc[0].get_text()

    # Find all standalone capital letters A–D (answer choices)
    answers = re.findall(r"\b([ABCD])\b", first_page_text)

    if len(answers) < 30:
        print(f"⚠️ Warning: Only found {len(answers)} answers (expected 30).")
    else:
        print("✅ Found 30 MCQ answers.")

    # Return a dictionary like {'01': 'C', '02': 'D', ...}
    return {str(i + 1).zfill(2): answers[i] for i in range(min(30, len(answers)))}




def clean_text(text):
    for wrong, correct in char_fixes.items():
        text = text.replace(wrong, correct)
    return text

def image_to_latex(image_path, app_id, app_key):
    with open(image_path, "rb") as image_file:
        img_base64 = base64.b64encode(image_file.read()).decode()

    headers = {
        "app_id": app_id,
        "app_key": app_key,
        "Content-type": "application/json",
    }

    data = {
        "src": f"data:image/png;base64,{img_base64}",
        "formats": ["text", "data"],
        "math_inline_delimiters": ["$$", "$$"],
        "math_display_delimiters": ["$$", "$$"],
    }

    response = requests.post("https://api.mathpix.com/v3/text", headers=headers, json=data)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Mathpix API error: {response.status_code} - {response.text}")
        return {"text": ""}

def save_pdf_pages_as_images(pdf_path, output_folder="ocr_pages", zoom=2.0):
    os.makedirs(output_folder, exist_ok=True)
    doc = pymupdf.open(pdf_path)
    image_paths = []

    for page_num in range(2, 9):  # Customize page range
        page = doc.load_page(page_num)
        mat = pymupdf.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        width, height = img.size
        cropped_img = img.crop((100, 165, width, height - 180))  # crop top/bottom
        image_path = os.path.join(output_folder, f"page_{page_num+1}.png")
        cropped_img.save(image_path)
        image_paths.append(image_path)

    return image_paths
def assign_categories(text):
    current_category = 18  # Assume "Judėjimas ir jėgos" at the start
    q_to_category = {}

    lines = text.splitlines()

    for line in lines:
        line = line.strip()
        cleaned_line = clean_text(line)

        if cleaned_line in category_map:
            current_category = category_map[cleaned_line]

        match = re.match(r"^(\d{2})\.", line)
        if match and current_category is not None:
            question_num = match.group(1)
            q_to_category[question_num] = current_category

    return q_to_category



# === OCR all pages ===
print("🔄 Converting PDF to images...")
image_paths = save_pdf_pages_as_images(PDF_FILE)


print("📤 Sending images to Mathpix...")
all_text = ""
for idx, img_path in enumerate(image_paths):
    print(f"  → Processing page {idx + 2}...")
    ocr_result = image_to_latex(img_path, APP_ID, APP_KEY)
    text_block = ocr_result.get("text", "")
    all_text += "\n" + ocr_result.get("text", "")

all_text = re.sub(r"\\begin{tabular}.*?\\end{tabular}", "", all_text, flags=re.DOTALL)
all_text = re.sub(r'[ \t]+', ' ', all_text)
all_text = re.sub(r'\n+', '\n', all_text)
with open("output.txt", "w", encoding="utf-8") as f:
    f.write(all_text.strip())
# === Extract questions ===
print("🧠 Parsing questions...")



answer_key = get_mcq_answers(ANSWER_FILE)
category_per_question = assign_categories(all_text)
# After assigning categories
for category in category_map:
    all_text = all_text.replace(clean_text(category), "")



question_blocks = re.split(r"(?=\d{2}\.\s)", all_text)

data = []

for block in question_blocks:
    block = block.strip()
    if not block:
        continue

    match = re.match(r"(?P<num>\d{2})\.\s(?P<question>.+?)(?=(\nA\s|$))", block, flags=re.DOTALL)
    if not match:
        continue

    q = match.groupdict()
    question_number = q["num"]
    raw_question_text = clean_text(re.sub(r"\s+", " ", q["question"].strip()))

    if any(keyword in raw_question_text.lower() for keyword in skip_keywords):
        print(f"⏭ Skipping question {question_number} due to image/table reference")
        continue

    # 🧠 Now extract options manually
    options = re.findall(r"(?:^|\n)([A-D])\s+(.*?)(?=(?:\n[A-D]\s|$))", block, flags=re.DOTALL)

    if len(options) < 4:
        print(f"⚠️ Skipping question {question_number} — not enough options found ({len(options)}).")
        continue

    options_dict = {letter: clean_text(text.strip()) for letter, text in options}

    correct_letter = answer_key.get(question_number, "")
    correct_answer = options_dict.get(correct_letter, "")
    wrong_answers = [ans for key, ans in options_dict.items() if key != correct_letter]

    while len(wrong_answers) < 3:
        wrong_answers.append("")

    data.append({
        "Question No.": question_number,
        "Category No.": category_per_question.get(question_number, ""),
        "Question": raw_question_text,
        "Correct Answer": correct_answer,
        "Wrong Option 1": wrong_answers[0],
        "Wrong Option 2": wrong_answers[1],
        "Wrong Option 3": wrong_answers[2],
    })


# === Save to Excel ===
df = pd.DataFrame(data)
df.to_excel(OUTPUT_EXCEL, index=False)

print(f"✅ {len(data)} questions saved to: {OUTPUT_EXCEL}")
