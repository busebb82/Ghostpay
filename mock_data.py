"""
mock_data.py
6 aylik sentetik Open Banking islem gecmisi uretir. Gercek hayatta bu veri
Open Banking API'sinden gelirdi. Veri seti maas, market, ulasim, restoran,
fatura ve dijital abonelik odemelerini icerir.

Cikti: [{tarih, aciklama, tip, tutar}] listesi (tutar: gelir +, gider -)
"""
import calendar
import random
from datetime import date

AYLIK_NET_MAAS = 65000.00

# Banka dokumunde gorunen abonelik odemeleri. Gercek fiyat ayliga gore kur ve
# vergi farki nedeniyle biraz oynar; "fiyat" platformun liste fiyatidir.
SUBSCRIPTION_CHARGES = {
    "NETFLIX":         {"fiyat": 289.99,  "gun": 3},
    "DISNEY+":         {"fiyat": 249.90,  "gun": 7},
    "YOUTUBE PREMIUM": {"fiyat": 119.99,  "gun": 21},
    "SPOTIFY":         {"fiyat": 99.00,   "gun": 5},
    "YOUTUBE MUSIC":   {"fiyat": 89.99,   "gun": 11},
    "APPLE MUSIC":     {"fiyat": 59.99,   "gun": 14},
    "CANVA PRO":       {"fiyat": 757.50,  "gun": 19},
    "ADOBE CREATIVE":  {"fiyat": 379.00,  "gun": 23},
    "CHATGPT PLUS":    {"fiyat": 1019.49, "gun": 16},
    "CLAUDE PRO":      {"fiyat": 1010.00, "gun": 15},
    "GEMINI":          {"fiyat": 1000.00, "gun": 25},
}

# Abonelik disi harcamalar: (aciklama, min tutar, max tutar, aylik ortalama adet)
DAILY_SPENDING = [
    ("MIGROS",       100, 900, 2),
    ("BIM",          150, 800, 2),
    ("CARREFOURSA",  200, 700, 1),
    ("GETIR",        150, 700, 1),
    ("YEMEKSEPETI",  300, 900, 2),
    ("STARBUCKS",     80, 480, 2),
    ("TRENDYOL",     250, 900, 1),
    ("SHELL",        300, 900, 1),
    ("PEGASUS",      400, 1200, 1),
    ("TÜRK TELEKOM", 120, 750, 1),
]


def window_months(today: date, months: int = 6) -> list[tuple[int, int]]:
    """Bugunden onceki son `months` tam ayi (yil, ay) olarak dondurur."""
    y, m = today.year, today.month
    out = []
    for _ in range(months):
        m -= 1
        if m == 0:
            y, m = y - 1, 12
        out.append((y, m))
    return list(reversed(out))


def generate_transactions(today: date | None = None, months: int = 6) -> list[dict]:
    """Son `months` tam ay ile icinde bulunulan ayin bugune kadarki islemleri."""
    today = today or date.today()
    rng = random.Random(42)
    rows = []

    for y, m in window_months(today, months) + [(today.year, today.month)]:
        last_day = calendar.monthrange(y, m)[1]
        if (y, m) == (today.year, today.month):
            last_day = today.day

        rows.append({"tarih": date(y, m, 1), "aciklama": "MAAS ODEMESI",
                     "tip": "Gelir", "tutar": AYLIK_NET_MAAS})

        for merchant, sub in SUBSCRIPTION_CHARGES.items():
            tutar = sub["fiyat"] * rng.uniform(0.92, 1.08)
            if sub["gun"] > last_day and (y, m) == (today.year, today.month):
                continue
            rows.append({"tarih": date(y, m, min(sub["gun"], last_day)),
                         "aciklama": merchant, "tip": "Gider",
                         "tutar": -round(tutar, 2)})

        for merchant, lo, hi, avg_count in DAILY_SPENDING:
            count = rng.choice([avg_count - 1, avg_count, avg_count + 1])
            if (y, m) == (today.year, today.month):
                count = round(count * today.day / calendar.monthrange(y, m)[1])
            for _ in range(count):
                rows.append({"tarih": date(y, m, rng.randint(1, last_day)),
                             "aciklama": merchant, "tip": "Gider",
                             "tutar": -round(rng.uniform(lo, hi), 2)})

    rows.sort(key=lambda r: r["tarih"], reverse=True)
    return rows
