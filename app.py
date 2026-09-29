import hashlib
import os
import re

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

VALID = re.compile(r"^[A-Za-z][A-Za-z0-9_]{4,31}$")
VOWELS = set("aeiouy")

KEYWORDS = {
    "king": 8, "queen": 8, "boss": 7, "legend": 8, "alpha": 6, "lord": 6,
    "pro": 6, "official": 6, "real": 4, "best": 5, "top": 5, "star": 5,
    "cool": 5, "ninja": 6, "wolf": 6, "tiger": 6, "sher": 6, "mafia": 6,
    "dev": 5, "shah": 4, "bek": 4, "uz": 5, "uzb": 5, "admin": 3,
}

TIERS = [
    (90, "Afsona 👑", [
        "Bunday username bilan Telegramning eng yuqori qavatiga chiqasan.",
        "Ismingni ko'rgan odam profilingga kirmasdan turolmaydi.",
    ]),
    (75, "Zo'r username 🔥", [
        "Qisqa, chiroyli va esda qoladigan. Tanishlar bir zumda topadi.",
        "Sifatli tanlov! Faqat parolni ham shunday o'ylab qo'y 😄",
    ]),
    (55, "Yaxshi, lekin yaxshiroq bo'lishi mumkin 😎", [
        "Yomon emas, ammo bir oz sayqal bersang yulduzga aylanadi.",
        "O'rtacha kuchli. Bitta chiroyli so'z qo'shsang, boshqa gap bo'ladi.",
    ]),
    (35, "Sal charchagan 😅", [
        "Username o'zi ham dam olishni xohlayotganga o'xshaydi.",
        "Raqamlar ko'payib ketibdi, ehtimol ro'yxatdan o'tishda shoshgansan.",
    ]),
    (0, "Yangi username kerak! 🚨", [
        "Bu username ustida jiddiy ish qilish kerak. Yangi variant o'ylab ko'r.",
        "Do'stlaring buni yozib olishga ulguradimi, bilmadim 😂",
    ]),
]


def pick(seed: str, options: list) -> str:
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    return options[h % len(options)]


def analyze(name: str) -> dict:
    low = name.lower()
    length = len(name)
    score = 50
    details = []

    def add(label: str, delta: int):
        nonlocal score
        if delta:
            score += delta
            details.append({"label": label, "delta": delta})

    # Uzunlik
    if length <= 4:
        add("Juda qisqa", -5)
    elif length <= 8:
        add("Ideal uzunlik", 20)
    elif length <= 12:
        add("Yaxshi uzunlik", 14)
    elif length <= 16:
        add("Sal uzun", 4)
    else:
        add("Juda uzun", -8)

    # Raqamlar
    digits = sum(c.isdigit() for c in name)
    if digits:
        add(f"Raqamlar ({digits} ta)", -min(digits * 3, 18))

    # Pastki chiziq
    underscores = name.count("_")
    if underscores:
        add(f"Pastki chiziq ({underscores} ta)", -min(underscores * 4, 12))
    if "__" in name:
        add("Qo'sh pastki chiziq", -6)

    # Takrorlanuvchi harflar
    if re.search(r"(.)\1{2,}", low):
        add("Harf ko'p takrorlangan", -8)

    # Maxsus so'zlar
    found = [w for w in KEYWORDS if w in low]
    if found:
        bonus = min(sum(KEYWORDS[w] for w in found), 20)
        add("Zo'r so'z: " + ", ".join(found[:3]), bonus)

    # O'qilishi oson-qiyinligi
    letters = [c for c in low if c.isalpha()]
    if letters:
        ratio = sum(c in VOWELS for c in letters) / len(letters)
        if 0.25 <= ratio <= 0.6:
            add("Talaffuzi oson", 8)
        elif ratio == 0:
            add("Unli harf yo'q", -8)

    # Toza ko'rinish
    if low.isalpha():
        add("Faqat harflar", 6)

    # Har bir username uchun doimiy mayda farq
    jitter = int(hashlib.md5(low.encode()).hexdigest(), 16) % 7 - 3
    score += jitter

    score = max(0, min(100, score))

    for limit, title, jokes in TIERS:
        if score >= limit:
            break

    return {
        "username": name,
        "score": score,
        "title": title,
        "joke": pick(low, jokes),
        "details": details,
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze_route():
    data = request.get_json(silent=True) or {}
    raw = str(data.get("username", "")).strip()
    raw = re.sub(r"^(https?://)?(t\.me/)?", "", raw, flags=re.I).lstrip("@").strip()

    if not raw:
        return jsonify(error="Username kiriting, masalan: @ism"), 400
    if not VALID.match(raw):
        return jsonify(
            error="Username 5-32 belgidan iborat bo'lsin, harf bilan boshlansin "
                  "va faqat lotin harflari, raqam va _ bo'lsin."
        ), 400

    return jsonify(analyze(raw))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
