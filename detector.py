"""
detector.py
Islem listesinden abonelikleri tespit eder ve her abonelik icin
Claude'a gonderilecek davranissal ozellikleri (feature) cikarir.
"""
import pandas as pd

CATEGORY_MAP = {
    "NETFLIX.COM": "Video",
    "DISNEY PLUS": "Video",
    "AMAZON PRIME": "Video",
    "BLUTV": "Video",
    "YOUTUBE PREMIUM": "Video",
    "SPOTIFY": "Müzik",
    "ICLOUD": "Bulut Depolama",
    "ADOBE CREATIVE": "Üretkenlik",
}


def detect_subscriptions(df: pd.DataFrame) -> list[dict]:
    subs = []
    for merchant, g in df.groupby("aciklama"):
        g = g.sort_values("tarih")

        if len(g) < 3:
            continue
        if g["tutar"].std() > g["tutar"].mean() * 0.05:
            continue
        gaps = g["tarih"].diff().dropna().dt.days
        if not gaps.between(25, 35).all():
            continue

        subs.append({
            "merchant": merchant,
            "kategori": CATEGORY_MAP.get(merchant, "Diğer"),
            "aylik_tutar": round(g["tutar"].mean(), 2),
            "odeme_sayisi": len(g),
            "ilk_odeme": g["tarih"].min().strftime("%Y-%m-%d"),
            "son_odeme": g["tarih"].max().strftime("%Y-%m-%d"),
        })
    return subs


def build_features(subs: list[dict], df: pd.DataFrame, months: int = 6) -> list[dict]:
    if not subs:
        return subs

    toplam = sum(s["aylik_tutar"] for s in subs)

    sub_names = [s["merchant"] for s in subs]
    noise = df[~df["aciklama"].isin(sub_names)]
    son_30_gun = noise[noise["tarih"] >= df["tarih"].max() - pd.Timedelta(days=30)]["tutar"].sum()
    aylik_ortalama = noise["tutar"].sum() / months

    if son_30_gun < aylik_ortalama * 0.85:
        trend = "düşüşte"
    elif son_30_gun > aylik_ortalama * 1.15:
        trend = "yükselişte"
    else:
        trend = "stabil"

    for s in subs:
        ayni_kategori = [x for x in subs if x["kategori"] == s["kategori"]]
        s["ayni_kategori_abonelik_sayisi"] = len(ayni_kategori)
        s["kategorideki_en_pahali_mi"] = s["aylik_tutar"] >= max(x["aylik_tutar"] for x in ayni_kategori)
        s["toplam_abonelik_maliyeti"] = round(toplam, 2)
        s["butce_payi_yuzde"] = round(100 * s["aylik_tutar"] / toplam, 1)
        s["genel_harcama_trendi"] = trend
    return subs