import pymupdf
import pandas as pd
import re

def convert_to_latex(text):
    # m/s²
    text = re.sub(r"(\d+)\s*m/s2", r"$$\1\\ \\mathrm{m/s^{2}}$$", text)
    text = re.sub(r"(\d+)\s*m/s\^2", r"$$\1\\ \\mathrm{m/s^{2}}$$", text)

    # m³
    text = re.sub(r"(\d+(?:[.,]\d+)?)\s*m3", r"$$\1\\ \\mathrm{m^{3}}$$", text)
    text = re.sub(r"(\d+(?:[.,]\d+)?)\s*m\^3", r"$$\1\\ \\mathrm{m^{3}}$$", text)

    # Celsius
    text = re.sub(r"(\d+)\s*°C", r"$$\1\\,^{\\circ}\\mathrm{C}$$", text)

    # Fractions like 1/2
    text = re.sub(r"\b(\d+)\s+(\d+)\b", r"\1/\2", text)

    # Replace fancy Unicode math letters with standard LaTeX equivalents
    unicode_map = {
        "𝑃": "P", "𝑡": "t", "𝑐": "c", "ℎ": "h", "λ": "\\lambda",
        "𝑄": "Q", "𝑣": "v", "𝑚": "m", "𝑉": "V",
    }
    for k, v in unicode_map.items():
        text = text.replace(k, v)

    # Now catch expressions like "Ptc/hλ" and turn them into LaTeX
    text = re.sub(r"\b([A-Za-z]+)\s*/\s*([A-Za-z\\]+)\b", r"$$\\frac{\1}{\2}$$", text)
    
    text = re.sub(r"\b(\d+)\s*/\s*(\d+)\b", r"$$\\frac{\1}{\2}$$", text)

    # Greek letters
    text = re.sub(r"\balfa\b", r"$$\\alpha$$", text, flags=re.IGNORECASE)
    text = re.sub(r"\bbeta\b", r"$$\\beta$$", text, flags=re.IGNORECASE)
    text = text.replace("α", "$$\\alpha$$")
    text = text.replace("β", "$$\\beta$$")

    # Lambda
    text = re.sub(r"\blambda\b", r"$$\\lambda$$", text, flags=re.IGNORECASE)
    text = text.replace("λ", "$$\\lambda$$")

    # Degrees and Ohms
    text = text.replace("°", "$$^{\\circ}$$")
    text = text.replace("Ω", "$$\\Omega$$")
    return text

doc = pymupdf.open("VBE_Fizika_2024_Pagrindine.pdf")
texts = [doc[i].get_text() for i in range(1, len(doc))]
full_text = "\n".join(texts)

# Remove known noise patterns
noise_keywords = [
    "NEPAMIRŠKITE ATSAKYMŲ PERKELTI",
    "RIBOTO NAUDOJIMO",
    "Valstybinio brandos egzamino užduotis",
    "Juodraštis",
    "Linkime sėkmės!",
    "Neatsakę į kurį nors klausimą, nenusiminkite ir stenkitės atsakyti į kitus.",
    "Atsakymų lape neturi būti užrašų ar kitokių ženklų, kurie leistų identifikuoti darbo autorių.",
    "Pasibaigus egzaminui, užduoties sąsiuvinį galite pasiimti.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\nFIZIKA",

]
for noise in noise_keywords:
    full_text = full_text.replace(noise, "")

full_text = re.sub(r"\n\d+\s+[\w\s]+\s+–.*?(?=\n|$)", "", full_text)
full_text = re.sub(r"_+", "", full_text)
# Extract questions starting from "01." to "30."
matches = re.findall(
    r"(\d{2})\.\s(.+?)(?=(?:\n\d{2}\.\s)|(?:\n{2,}))", full_text, flags=re.DOTALL
)

questions = []

skip_table_keywords = ["q, kj", "t, k", "sinusai", "laipsniai", "kampas", "kampų", "kampu", "lentelė"]


for qnum, block in matches:
    lower_block = block.lower()

    # Skip invalid: not enough answer options (e.g., missing A–D)
    options_match = re.findall(r"([A-D])\s+(.*?)(?=\n[A-D]\s+|\n?$)", block.strip(), re.DOTALL)
    if len(options_match) < 3:  # less than A, B, C — definitely not a full MCQ
        continue

    # Skip image/table references
    if any(x in lower_block for x in ["žr. pav", "paveiksl", "pav.", "1 pav", "2 pav", "3 pav", "pavaizduot"]):
        continue

    # Skip extra-long blocks or blocks with too many numbers per line


    # Clean question text and options
    question_text = re.split(r"\nA\s+", block)[0].replace('\n', ' ').strip()
    question_text = convert_to_latex(question_text)

    opts = {k: convert_to_latex(v.replace('\n', ' ').strip()) for k, v in options_match}

    questions.append({
        "Question No.": qnum,
        "Question": question_text,
        "Option A": opts.get("A", ""),
        "Option B": opts.get("B", ""),
        "Option C": opts.get("C", ""),
        "Option D": opts.get("D", ""),
    })


# Save to Excel
df = pd.DataFrame(questions)
df.to_excel("Fizika_Part1_Clean.xlsx", index=False)



