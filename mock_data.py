"""Sentetik Open Banking işlem geçmişi.

Gerçek üründe bu veri Open Banking API'sinden gelir. Maaş, market, ulaşım,
restoran, fatura ve dijital abonelik ödemelerini içerir; tutarlar gelirde
pozitif, giderde negatiftir.
"""
import calendar
import random
from datetime import date, datetime
from zoneinfo import ZoneInfo

from catalog import SERVICES

AYLIK_NET_MAAS = 65000.00

# Render gibi sunucular UTC'de çalışır; "bugün" Türkiye saatine göre hesaplanmalı
TIMEZONE = ZoneInfo("Europe/Istanbul")

# (açıklama, en düşük tutar, en yüksek tutar, aylık ortalama işlem sayısı)
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


def local_today() -> date:
    return datetime.now(TIMEZONE).date()


def window_months(today: date, months: int = 6) -> list[tuple[int, int]]:
    """İçinde bulunulan aydan önceki son `months` tam ay, eskiden yeniye."""
    y, m = today.year, today.month
    out = []
    for _ in range(months):
        m -= 1
        if m == 0:
            y, m = y - 1, 12
        out.append((y, m))
    return list(reversed(out))


def _charge(service: dict, months_ago: int, rng: random.Random) -> float:
    price = service["fiyat"]
    if "zam" in service:
        old_price, hike_months_ago = service["zam"]
        if months_ago > hike_months_ago:
            price = old_price
    if service.get("doviz"):
        price *= rng.uniform(0.97, 1.03)
    return round(price, 2)


def generate_transactions(today: date | None = None, months: int = 6) -> list[dict]:
    """Son `months` tam ay ile bu ayın bugüne kadarki işlemleri, yeniden eskiye."""
    today = today or local_today()
    rng = random.Random(42)
    rows = []

    for y, m in window_months(today, months) + [(today.year, today.month)]:
        is_current = (y, m) == (today.year, today.month)
        days_in_month = calendar.monthrange(y, m)[1]
        last_day = today.day if is_current else days_in_month
        months_ago = (today.year - y) * 12 + today.month - m

        rows.append({"tarih": date(y, m, 1), "aciklama": "MAAS ODEMESI",
                     "tip": "Gelir", "tutar": AYLIK_NET_MAAS})

        for merchant, service in SERVICES.items():
            amount = _charge(service, months_ago, rng)
            if service["gun"] > last_day and is_current:
                continue
            rows.append({"tarih": date(y, m, min(service["gun"], last_day)),
                         "aciklama": merchant, "tip": "Gider", "tutar": -amount})

        for merchant, lo, hi, avg_count in DAILY_SPENDING:
            count = rng.choice([avg_count - 1, avg_count, avg_count + 1])
            if is_current:
                count = round(count * today.day / days_in_month)
            for _ in range(count):
                rows.append({"tarih": date(y, m, rng.randint(1, last_day)),
                             "aciklama": merchant, "tip": "Gider",
                             "tutar": -round(rng.uniform(lo, hi), 2)})

    rows.sort(key=lambda r: r["tarih"], reverse=True)
    return rows
