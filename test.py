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

    # Replace fancy Unicode math letters with standard LaTeX equivalents
    unicode_map = {
        "𝑃": "P", "𝑡": "t", "𝑐": "c", "ℎ": "h", "λ": "\\lambda",
        "𝑄": "Q", "𝑣": "v", "𝑚": "m", "𝑉": "V",
    }
    for k, v in unicode_map.items():
        text = text.replace(k, v)

    # Greek letters by name
    text = re.sub(r"\balfa\b", r"$$\\alpha$$", text, flags=re.IGNORECASE)
    text = re.sub(r"\bbeta\b", r"$$\\beta$$", text, flags=re.IGNORECASE)
    text = re.sub(r"\blambda\b", r"$$\\lambda$$", text, flags=re.IGNORECASE)

    # Greek letters by symbol
    text = text.replace("α", "$$\\alpha$$")
    text = text.replace("β", "$$\\beta$$")
    text = text.replace("λ", "$$\\lambda$$")
    text = text.replace("", "$$\\lambda$$")
    


    # Degrees and Ohms
    text = text.replace("°", "$$^{\\circ}$$")
    text = text.replace("\uf0b0", "$$^{\\circ}$$")
    text = text.replace("Ω", "$$\\Omega$$")

    # ----------------------------------------------------------------
    # 1) Handle isotope notation FIRST (in various formats):
    # ----------------------------------------------------------------

    # Format A: "239 Pu 94" => $$^{239}_{94}\mathrm{Pu}$$
    isotope_pattern_1 = re.compile(r"(\d{2,3})\s*([A-Z][a-z]?)\s*(\d{1,3})")
    text = isotope_pattern_1.sub(r"$$^{\1}_{\3}\\mathrm{\2}$$", text)

    # Format B: "Pu 239/94" => $$^{239}_{94}\mathrm{Pu}$$
    isotope_pattern_2 = re.compile(r"([A-Z][a-z]?)\s*(\d{2,3})\s*/\s*(\d{1,3})")
    text = isotope_pattern_2.sub(r"$$^{\2}_{\3}\\mathrm{\1}$$", text)

    # Format C: "[Element] [Number] [Number]", e.g. "Pu 94 239"
    # We'll assume the smaller is the atomic number (94) and the larger is the mass (239).
    isotope_pattern_3 = re.compile(r"\b([A-Z][a-z]?)\s+(\d{1,3})\s+(\d{1,3})\b")
    def repl_isotope(m):
        symbol, val1, val2 = m.group(1), int(m.group(2)), int(m.group(3))
        if val1 < val2:
            return f"$$^{{{val2}}}_{{{val1}}}\\mathrm{{{symbol}}}$$"
        else:
            return f"$$^{{{val1}}}_{{{val2}}}\\mathrm{{{symbol}}}$$"
    text = isotope_pattern_3.sub(repl_isotope, text)

    # ----------------------------------------------------------------
    # 2) THEN handle fraction-like patterns (to avoid messing isotopes).
    # ----------------------------------------------------------------

    # Fractions: e.g. "1 2" -> "1/2"
    text = re.sub(r"\b(\d+)\s+(\d+)\b", r"\1/\2", text)

    # Fractions: e.g. "1/2" -> $$\\frac{1}{2}$$
    text = re.sub(r"\b(\d+)\s*/\s*(\d+)\b", r"$$\\frac{\1}{\2}$$", text)

    return text

    return text

doc = pymupdf.open("FIZ_pagr_2023-1.pdf")
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



