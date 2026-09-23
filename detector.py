"""İşlem geçmişinden abonelik tespiti ve yapay zekâya giden davranış profili."""
import calendar
import statistics
import zlib
from collections import defaultdict
from datetime import date, timedelta
from itertools import pairwise

from catalog import CARD_NUMBERS, CATEGORIES, INITIAL_CARD_STATE, SERVICES

# Kur oynaması (±%3) zam sayılmasın diye eşik bunun üstünde tutuldu
PRICE_HIKE_MIN_RATIO = 1.06


def add_months(d: date, n: int = 1) -> date:
    """Ayın gününü korur, kısa aylarda son güne yuvarlar (31 Oca → 28 Şub → 31 Mar)."""
    y, m = divmod(d.month - 1 + n, 12)
    year, month = d.year + y, m + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def next_due(last_payment: date, today: date) -> date:
    n = 1
    while add_months(last_payment, n) <= today:
        n += 1
    return add_months(last_payment, n)


def slug(merchant: str) -> str:
    return merchant.lower().replace("+", "-plus").replace(" ", "-")


def detect_price_hike(charges: list[dict]) -> dict | None:
    """Tutarın kalıcı olarak yükseldiği son noktayı bulur.

    Yükselişten sonraki her çekim, önceki en yüksek çekimin belirgin şekilde
    üstünde olmalı; tek seferlik bir sapma zam sayılmaz.
    """
    amounts = [c["tutar"] for c in charges]
    for k in range(len(amounts) - 1, 0, -1):
        before, after = amounts[:k], amounts[k:]
        old, new = statistics.median(before), statistics.median(after)
        if min(after) >= max(before) * 1.02 and new / old >= PRICE_HIKE_MIN_RATIO:
            return {"eski_fiyat": round(old, 2), "yeni_fiyat": round(new, 2),
                    "oran_yuzde": round(100 * (new / old - 1), 1),
                    "tarih": charges[k]["tarih"]}
    return None


def detect_subscriptions(transactions: list[dict], today: date) -> list[dict]:
    """En az 3 kez, ~30 gün arayla ve benzer tutarla tekrarlanan giderler abonelik sayılır."""
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
        if not all(25 <= (b["tarih"] - a["tarih"]).days <= 35 for a, b in pairwise(txs)):
            continue

        info = SERVICES.get(merchant, {"ad": merchant.title(), "kategori": "Diğer",
                                       "fiyat": round(amounts[-1], 2)})
        state = INITIAL_CARD_STATE.get(merchant, {})
        last_payment = txs[-1]["tarih"]
        status = state.get("durum", "Aktif")
        charges = [{"tarih": t["tarih"].isoformat(), "tutar": -t["tutar"]} for t in txs]

        subs.append({
            "id": slug(merchant),
            "merchant": merchant,
            "ad": info["ad"],
            "kategori": info["kategori"],
            "fiyat": info["fiyat"],
            "limit": state.get("limit", info["fiyat"]),
            "durum": status,
            "kart_no": CARD_NUMBERS.get(merchant, str(zlib.crc32(merchant.encode()) % 10000).zfill(4)),
            "son_odeme": last_payment.isoformat(),
            "sonraki_odeme": next_due(last_payment, today).isoformat(),
            # Demo kullanıcısı bu kartları son ödemenin ertesi günü dondurdu
            "dondurma_tarihi": (last_payment + timedelta(days=1)).isoformat()
                               if status == "Donduruldu" else None,
            "zam": detect_price_hike(charges),
            "odemeler": charges,
        })

    cat_order = {c: i for i, c in enumerate(CATEGORIES)}
    known_order = {m: i for i, m in enumerate(SERVICES)}
    subs.sort(key=lambda s: (cat_order.get(s["kategori"], len(cat_order)),
                             known_order.get(s["merchant"], len(known_order))))
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


def build_features(sub: dict, subs: list[dict], transactions: list[dict], salary: float) -> dict:
    """Yapay zekâya ve şirkete giden profil; kullanıcıyı tanıtan bilgi içermez."""
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
        "fiyat_artisi": sub["zam"],
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
        in_month = [t for t in transactions if (t["tarih"].year, t["tarih"].month) == (y, m)]
        out.append({
            "yil": y, "ay": m,
            "gider": round(-sum(t["tutar"] for t in in_month if t["tip"] == "Gider"), 2),
            "gelir": round(sum(t["tutar"] for t in in_month if t["tip"] == "Gelir"), 2),
        })
    return out
