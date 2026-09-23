"""
detector.py
Islem gecmisinden duzenli (aylik) odemeleri tespit eder, abonelik olup
olmadiklarini belirler ve kategorilere ayirir. Ayrica her abonelik icin
yapay zekaya gonderilecek davranissal ozellikleri (feature) cikarir.
"""
import calendar
import statistics
import zlib
from collections import defaultdict
from datetime import date, timedelta

CATEGORIES = ["Video", "Müzik", "Üretkenlik", "Yapay Zekâ"]

# Bilinen servisler: banka dokumundeki aciklama -> gorunen ad ve kategori
SERVICE_CATALOG = {
    "NETFLIX":         {"ad": "Netflix",         "kategori": "Video",      "fiyat": 289.99},
    "DISNEY+":         {"ad": "Disney+",         "kategori": "Video",      "fiyat": 249.90},
    "YOUTUBE PREMIUM": {"ad": "Youtube Premium", "kategori": "Video",      "fiyat": 119.99},
    "SPOTIFY":         {"ad": "Spotify",         "kategori": "Müzik",      "fiyat": 99.00},
    "YOUTUBE MUSIC":   {"ad": "Youtube Music",   "kategori": "Müzik",      "fiyat": 89.99},
    "APPLE MUSIC":     {"ad": "Apple Music",     "kategori": "Müzik",      "fiyat": 59.99},
    "CANVA PRO":       {"ad": "Canva Pro",       "kategori": "Üretkenlik", "fiyat": 757.50},
    "ADOBE CREATIVE":  {"ad": "Adobe Creative",  "kategori": "Üretkenlik", "fiyat": 379.00},
    "CHATGPT PLUS":    {"ad": "ChatGPT Plus",    "kategori": "Yapay Zekâ", "fiyat": 1019.49},
    "CLAUDE PRO":      {"ad": "Claude Pro",      "kategori": "Yapay Zekâ", "fiyat": 1010.00},
    "GEMINI":          {"ad": "Gemini",          "kategori": "Yapay Zekâ", "fiyat": 1000.00},
}

# Demo baslangic durumu: kullanicinin daha once dondurdugu kartlar ve
# ucretin altina cektigi limitler
INITIAL_CARD_STATE = {
    "DISNEY+":       {"durum": "Donduruldu"},
    "YOUTUBE MUSIC": {"durum": "Donduruldu"},
    "CLAUDE PRO":    {"durum": "Donduruldu"},
    "CANVA PRO":     {"limit": 704.70},
    "CHATGPT PLUS":  {"limit": 808.33},
}

CARD_NUMBERS = {
    "NETFLIX": "4821", "DISNEY+": "3390", "YOUTUBE PREMIUM": "9931",
    "SPOTIFY": "2205", "YOUTUBE MUSIC": "6614", "APPLE MUSIC": "5017",
    "CANVA PRO": "1140", "ADOBE CREATIVE": "7788", "CHATGPT PLUS": "3072",
    "CLAUDE PRO": "8456", "GEMINI": "6203",
}


def add_months(d: date, n: int = 1) -> date:
    """Ayin gununu korur; kisa aylarda ayin son gunune yuvarlar (31 Oca -> 28 Sub)."""
    y, m = divmod(d.month - 1 + n, 12)
    year, month = d.year + y, m + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def next_due(last_payment: date, today: date) -> date:
    """Son odemeden sonra bugunden ileri dusen ilk odeme tarihi."""
    n = 1
    while add_months(last_payment, n) <= today:
        n += 1
    return add_months(last_payment, n)


def slug(merchant: str) -> str:
    return merchant.lower().replace("+", "-plus").replace(" ", "-")


def detect_subscriptions(transactions: list[dict], today: date) -> list[dict]:
    """En az 3 kez, ~30 gun arayla ve benzer tutarla tekrarlanan giderleri
    abonelik olarak isaretler."""
    groups = defaultdict(list)
    for t in transactions:
        if t["tip"] == "Gider":
            groups[t["aciklama"]].append(t)

    subs = []
    for merchant, txs in groups.items():
        txs = sorted(txs, key=lambda t: t["tarih"])
        amounts = [-t["tutar"] for t in txs]
        if len(txs) < 3:
            continue
        if statistics.pstdev(amounts) > statistics.mean(amounts) * 0.15:
            continue
        gaps = [(b["tarih"] - a["tarih"]).days for a, b in zip(txs, txs[1:])]
        if not all(25 <= g <= 35 for g in gaps):
            continue

        info = SERVICE_CATALOG.get(merchant, {
            "ad": merchant.title(), "kategori": "Diğer",
            "fiyat": round(amounts[-1], 2)})
        state = INITIAL_CARD_STATE.get(merchant, {})
        son_odeme = txs[-1]["tarih"]
        durum = state.get("durum", "Aktif")

        subs.append({
            "id": slug(merchant),
            "merchant": merchant,
            "ad": info["ad"],
            "kategori": info["kategori"],
            "fiyat": info["fiyat"],
            "limit": state.get("limit", info["fiyat"]),
            "durum": durum,
            "kart_no": CARD_NUMBERS.get(merchant, str(zlib.crc32(merchant.encode()) % 10000).zfill(4)),
            "son_odeme": son_odeme.isoformat(),
            "sonraki_odeme": next_due(son_odeme, today).isoformat(),
            # Demo: kullanici bu kartlari son odemenin ertesi gunu dondurdu
            "dondurma_tarihi": (son_odeme + timedelta(days=1)).isoformat() if durum == "Donduruldu" else None,
            "odemeler": [{"tarih": t["tarih"].isoformat(), "tutar": -t["tutar"]} for t in txs],
        })

    cat_order = {c: i for i, c in enumerate(CATEGORIES)}
    catalog_order = {m: i for i, m in enumerate(SERVICE_CATALOG)}
    subs.sort(key=lambda s: (cat_order.get(s["kategori"], len(cat_order)),
                             catalog_order.get(s["merchant"], len(catalog_order))))
    return subs


def _spending_trend(transactions: list[dict]) -> str:
    monthly = defaultdict(float)
    for t in transactions:
        if t["tip"] == "Gider":
            monthly[t["tarih"].strftime("%Y-%m")] -= t["tutar"]
    values = [monthly[k] for k in sorted(monthly)]
    if len(values) < 2:
        return "stabil"
    last, avg = values[-1], statistics.mean(values[:-1])
    if last > avg * 1.1:
        return "yükselişte"
    if last < avg * 0.9:
        return "düşüşte"
    return "stabil"


def build_features(sub: dict, subs: list[dict], transactions: list[dict],
                   salary: float) -> dict:
    """Yapay zekaya gonderilecek davranis profili. Kisisel veri icermez."""
    same_cat = [s for s in subs if s["kategori"] == sub["kategori"] and s["id"] != sub["id"]]
    rival_avg = statistics.mean(s["fiyat"] for s in same_cat) if same_cat else None
    total_active = sum(s["fiyat"] for s in subs if s["durum"] == "Aktif")

    return {
        "hizmet": sub["ad"],
        "kategori": sub["kategori"],
        "aylik_ucret_tl": sub["fiyat"],
        "maasa_orani_yuzde": round(100 * sub["fiyat"] / salary, 2),
        "sanal_kart_durumu": sub["durum"],
        "dondurma_tarihi": sub["dondurma_tarihi"],
        "sanal_kart_aylik_limiti_tl": sub["limit"],
        "limit_ucretin_altinda_mi": sub["limit"] < sub["fiyat"],
        "ayni_kategorideki_diger_abonelikler": [
            {"hizmet": s["ad"], "aylik_ucret_tl": s["fiyat"], "durum": s["durum"]}
            for s in same_cat],
        "kategorideki_rakip_sayisi": len(same_cat),
        "rakip_ortalama_ucret_tl": round(rival_avg, 2) if rival_avg else None,
        "kategorinin_en_pahalisi_mi": all(sub["fiyat"] >= s["fiyat"] for s in same_cat),
        "odeme_gecmisi": sub["odemeler"],
        "kesintisiz_odeme_ay_sayisi": len(sub["odemeler"]),
        "toplam_aktif_abonelik_yuku_tl": round(total_active, 2),
        "toplam_abonelik_yukunun_maasa_orani_yuzde": round(100 * total_active / salary, 2),
        "genel_harcama_trendi": _spending_trend(transactions),
    }


def monthly_totals(transactions: list[dict], months: list[tuple[int, int]]) -> list[dict]:
    out = []
    for y, m in months:
        gider = -sum(t["tutar"] for t in transactions
                     if t["tip"] == "Gider" and (t["tarih"].year, t["tarih"].month) == (y, m))
        gelir = sum(t["tutar"] for t in transactions
                    if t["tip"] == "Gelir" and (t["tarih"].year, t["tarih"].month) == (y, m))
        out.append({"yil": y, "ay": m, "gider": round(gider, 2), "gelir": round(gelir, 2)})
    return out

