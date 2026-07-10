"""
mock_data.py
Sahte banka islem verisi uretir. Gercek hayatta bu veri Open Banking
API'sinden gelirdi. Cikti: pandas DataFrame -> [tarih, aciklama, tutar]
"""
import random
from datetime import date, timedelta

import pandas as pd

random.seed(42)

SUBS = [
    {"merchant": "NETFLIX.COM",     "amount": 229.99, "day": 3},
    {"merchant": "DISNEY PLUS",     "amount": 134.99, "day": 7},
    {"merchant": "AMAZON PRIME",    "amount": 39.99,  "day": 12},
    {"merchant": "BLUTV",           "amount": 99.90,  "day": 18},
    {"merchant": "SPOTIFY",         "amount": 59.99,  "day": 5},
    {"merchant": "YOUTUBE PREMIUM", "amount": 57.99,  "day": 21},
    {"merchant": "ICLOUD",          "amount": 12.99,  "day": 9},
    {"merchant": "ADOBE CREATIVE",  "amount": 379.00, "day": 15},
]

NOISE_MERCHANTS = ["MIGROS", "GETIR", "SHELL", "TRENDYOL", "STARBUCKS", "YEMEKSEPETI"]


def generate_transactions(months: int = 6) -> pd.DataFrame:
    rows = []
    today = date.today()
    start = today - timedelta(days=30 * months)

    for sub in SUBS:
        d = date(start.year, start.month, 1)
        while d <= today:
            try:
                charge_date = d.replace(day=sub["day"])
            except ValueError:
                charge_date = d.replace(day=28)
            if start <= charge_date <= today:
                rows.append({
                    "tarih": charge_date,
                    "aciklama": sub["merchant"],
                    "tutar": sub["amount"],
                })
            d = (d.replace(day=28) + timedelta(days=4)).replace(day=1)

    for _ in range(80):
        rows.append({
            "tarih": start + timedelta(days=random.randint(0, 30 * months)),
            "aciklama": random.choice(NOISE_MERCHANTS),
            "tutar": round(random.uniform(50, 900), 2),
        })

    df = pd.DataFrame(rows)
    df["tarih"] = pd.to_datetime(df["tarih"])
    return df.sort_values("tarih").reset_index(drop=True)