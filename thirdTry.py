import pymupdf # PyMuPDF
import pandas as pd
import requests
import base64
import os
from PIL import Image
import io
import re

# ---------------------
APP_ID = "oba"
APP_KEY = "apsipisk"
PDF_FILE = "VBE_Fizika_2024_Pagrindine.pdf"
OUTPUT_EXCEL = "Parsed_Questions.xlsx"
ANSWER_FILE = "2024_FIZ_VBE_PG.pdf"
# ---------------------

# Fix OCR misrecognized characters
char_fixes = {
    'è': 'ė', 'ė̀': 'ė', 'ė́': 'ė', 'ė̃': 'ė', 'ě':'ė' ,
    'õ': 'o', 'ì': 'i', 'ị': 'į', 'í': 'i', 'í̇': 'i',
    'į̇': 'į', 'İ': 'į', 'ù': 'u', 'ū̀': 'ū', 'û': 'u',
    'ñ': 'n', 'č́': 'č', 'š́': 'š', 'ž́': 'ž', 'à': 'a',
    'é': 'ė', 'ẻ': 'ė',
    'ivair': 'įvair'
}

skip_keywords = [
    "žr. pav", "pav.", "paveiksl", "Paveiksl", "lentelė", "1 pav", "2 pav", "3 pav", "pavaizduot", " eiga", "sujungt", "Sinusai"
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

    for page_num in range(1, 7):  # Customize page range
        page = doc.load_page(page_num)
        mat = pymupdf.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        width, height = img.size
        cropped_img = img.crop((0, 165, width, height - 180))  # crop top/bottom
        image_path = os.path.join(output_folder, f"page_{page_num+1}.png")
        cropped_img.save(image_path)
        image_paths.append(image_path)

    return image_paths

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

pattern = re.compile(r"(?P<num>\d{2})\.\s(?P<question>.+?)(?=\nA\s)", flags=re.DOTALL)
question_dict = {match[0]: match[1] for match in pattern.findall(all_text)}

options_pattern = re.compile(
    r"(?P<num>\d{2})\.\s.*?A\s(?P<A>.+?)\sB\s(?P<B>.+?)\sC\s(?P<C>.+?)\sD\s(?P<D>.+?)(?=(\n\d{2}\.|$))",
    flags=re.DOTALL
)

answer_key = get_mcq_answers(ANSWER_FILE)


data = []
for match in options_pattern.finditer(all_text):
    q = match.groupdict()
    question_number = q["num"]
    raw_question_text = question_dict.get(question_number)

    if not raw_question_text:
        print(f"⚠️  Skipping question {question_number} — no matching question text found")
        continue

    cleaned_question_text = clean_text(re.sub(r"\s+", " ", raw_question_text.strip()))

    if any(keyword in cleaned_question_text.lower() for keyword in skip_keywords):
        print(f"⏭ Skipping question {q['num']} due to image/table reference")
        continue

    correct_letter = answer_key.get(q["num"], "")

    options = {
        "A": clean_text(q["A"].strip()),
        "B": clean_text(q["B"].strip()),
        "C": clean_text(q["C"].strip()),
        "D": clean_text(q["D"].strip()),
    }
    correct_answer = options.get(correct_letter, "")
    wrong_answers = [ans for key, ans in options.items() if key != correct_letter]
    while len(wrong_answers) < 3:
        wrong_answers.append("")

    data.append({
        "Question No.": q["num"],
        "Question": cleaned_question_text,
        "Correct Answer": correct_answer,
        "Wrong Option 1": wrong_answers[0],
        "Wrong Option 2": wrong_answers[1],
        "Wrong Option 3": wrong_answers[2],
    })

# === Save to Excel ===
df = pd.DataFrame(data)
df.to_excel(OUTPUT_EXCEL, index=False)

print(f"✅ {len(data)} questions saved to: {OUTPUT_EXCEL}")
