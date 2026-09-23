"""API anahtarı yokken kullanılan kural tabanlı analiz motoru.

Claude ile aynı çıktı biçimini, davranış profilindeki sayılardan üretir.
"""
import statistics
from datetime import date

MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
          "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def tl(n: float) -> str:
    s = f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} ₺"


def pct(n: float, digits: int = 1) -> str:
    return f"%{round(n, digits):g}"


def _month(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{MONTHS[d.month - 1]} {d.year}"


def _rivals(f: dict) -> list[dict]:
    return f.get("ayni_kategorideki_diger_abonelikler", [])


def churn_score(f: dict) -> int:
    rivals = _rivals(f)
    score = 20.0
    if f["sanal_kart_durumu"] == "Donduruldu":
        score += 30
    score += min(20, 8 * len(rivals))
    if rivals:
        avg = statistics.mean(r["aylik_ucret_tl"] for r in rivals)
        if f["aylik_ucret_tl"] > avg:
            score += min(15, 15 * (f["aylik_ucret_tl"] / avg - 1))
    score += min(10, 10 * f["maasa_orani_yuzde"])
    if f["limit_ucretin_altinda_mi"]:
        score += 10
    if f.get("fiyat_artisi"):
        score += min(12, f["fiyat_artisi"]["oran_yuzde"] / 2)
    return int(max(5, min(95, round(score))))


def analyze_subscription(f: dict) -> dict:
    rivals = _rivals(f)
    count = len(rivals) + 1
    ratio = f["maasa_orani_yuzde"]
    cat = f["kategori"]
    frozen = f["sanal_kart_durumu"] == "Donduruldu"
    most_expensive = f["kategorinin_en_pahalisi_mi"] and rivals
    hike = f.get("fiyat_artisi")
    capped = hike and f["sanal_kart_aylik_limiti_tl"] <= hike["eski_fiyat"]

    if frozen:
        ozet = (f"Kartın dondurulmuş durumda ve her ay {tl(f['aylik_ucret_tl'])} tasarruf ediyorsun; "
                "bu servisi artık kullanmıyorsan kartı kalıcı olarak silebilirsin.")
    elif hike and not capped:
        ozet = (f"Ücret {_month(hike['tarih'])} zammıyla {pct(hike['oran_yuzde'])} arttı; yeni fiyatı "
                f"ödemek istemiyorsan kart limitini eski fiyat olan {tl(hike['eski_fiyat'])}'ye sabitleyebilirsin.")
    elif hike:
        ozet = (f"Zamdan sonra kart limitini eski fiyat olan {tl(hike['eski_fiyat'])}'de tuttun; "
                f"{tl(hike['yeni_fiyat'])} tutarındaki sonraki çekim reddedilecek. Kullanmaya devam "
                "edeceksen limiti yeni fiyata çekmen gerekir.")
    elif rivals:
        ozet = (f"{'Maaşının çok küçük bir kısmını kaplıyor' if ratio < 1 else 'Bütçende hissedilir bir yer tutuyor'}"
                f" ama aynı kategoride {count} aboneliğin var"
                f"{' ve bu en pahalısı' if most_expensive else ''}, kullanım sıklığını gözden geçirmen iyi olur.")
    else:
        ozet = (f"{cat} kategorisindeki tek aboneliğin ve maaşa oranı {pct(ratio, 2)}; "
                "düzenli kullanıyorsan devam etmen mantıklı.")

    maddeler = [
        f"Maaşa oranı {pct(ratio, 2)}, bütçene yük değil" if ratio < 1
        else f"Maaşa oranı {pct(ratio, 2)}, abonelikler arasında yükü yüksek",
    ]
    if rivals:
        maddeler.append(f"{cat} kategorisinde {count} aboneliğin var"
                        f"{' ve bu en pahalısı' if most_expensive else ''}, hepsini aktif kullanmıyor olabilirsin")
        fees = [r["aylik_ucret_tl"] for r in rivals] + [f["aylik_ucret_tl"]]
        saving = tl(min(fees)) if min(fees) == max(fees) else f"{tl(min(fees))} ile {tl(max(fees))} arası"
        maddeler.append(f"Diğer {len(rivals)} {cat.lower()} aboneliğinle çakışma varsa, birini iptal edip "
                        f"aylık {saving} tasarruf edebilirsin")
    else:
        maddeler.append(f"{cat} kategorisinde alternatif bir aboneliğin yok, çakışan harcama görünmüyor")
        maddeler.append(f"Son {f['kesintisiz_odeme_ay_sayisi']} ayda kesintisiz ödeme yapılmış, "
                        "düzenli kullanılan bir servis gibi görünüyor")
    if hike:
        maddeler.insert(1, f"{_month(hike['tarih'])} itibarıyla fiyat {tl(hike['eski_fiyat'])}'den "
                           f"{tl(hike['yeni_fiyat'])}'ye çıktı ({pct(hike['oran_yuzde'])} zam)")
    if f["limit_ucretin_altinda_mi"]:
        maddeler[2] = (f"Kart limitin ({tl(f['sanal_kart_aylik_limiti_tl'])}) ücretin altında; "
                       "sonraki çekim reddedilecek")
    return {"ozet": ozet, "maddeler": maddeler[:3]}


def churn_analysis(f: dict) -> dict:
    rivals = _rivals(f)
    fee = f["aylik_ucret_tl"]
    score = churn_score(f)
    frozen = f["sanal_kart_durumu"] == "Donduruldu"

    degerlendirme = []
    if frozen:
        tarih = f.get("dondurma_tarihi") or ""
        tarih = ".".join(reversed(tarih.split("-"))) if tarih else "yakın zamanda"
        degerlendirme.append(f"Kullanıcı sanal kartı dondurdu ve %{score} churn skoru ile kaybedilme "
                             f"eşiğinde, {tarih} tarihinden bu yana ödeme yapılmıyor")
    else:
        degerlendirme.append(f"Son {f['kesintisiz_odeme_ay_sayisi']} ayda kesintisiz ödeme yapılmasına rağmen "
                             f"%{score} churn skoru, fiyat hassasiyeti sinyali veriyor")
    if rivals:
        avg = statistics.mean(r["aylik_ucret_tl"] for r in rivals)
        diff = 100 * (fee / avg - 1)
        degerlendirme.append(
            f"{tl(fee)} aylık ücret, kullanıcının {f['kategori'].lower()} kategorisindeki diğer aboneliklerinin "
            f"ortalaması olan {tl(avg)}'den {pct(abs(diff))} {'daha pahalı' if diff >= 0 else 'daha ucuz'}")
        names = ", ".join(r["hizmet"] for r in rivals)
        degerlendirme.append(f"Aynı kategoride {len(rivals)} rakip servise ({names}) ödeme yapılıyor, "
                             "bu da alternatif kullanım gösteriyor")
    else:
        degerlendirme.append(f"Kategoride rakip abonelik yok; ücret maaşın {pct(f['maasa_orani_yuzde'], 2)}'i")
        degerlendirme.append(f"Toplam abonelik yükü maaşın {pct(f['toplam_abonelik_yukunun_maasa_orani_yuzde'])}'i, "
                             "genel harcama trendi " + f["genel_harcama_trendi"])

    hike = f.get("fiyat_artisi")
    if hike:
        degerlendirme.insert(1, f"{_month(hike['tarih'])} zammından sonra ücret {tl(hike['eski_fiyat'])}'den "
                                f"{tl(fee)}'ye çıktı ({pct(hike['oran_yuzde'])}); kullanıcı fiyata duyarlı")
        degerlendirme = degerlendirme[:3]

    cheapest = min(rivals, key=lambda r: r["aylik_ucret_tl"]) if rivals else None
    if hike:
        first = {"baslik": "Zam Öncesi Fiyat Garantisi",
                 "aciklama": f"3 ay boyunca eski fiyat olan {tl(hike['eski_fiyat'])} ile devam etme "
                             "teklifiyle zam kaynaklı iptal riskini azaltın"}
    elif frozen or score >= 70:
        disc = round(fee * 0.6, 2)
        first = {"baslik": "2 Ay %40 İndirim",
                 "aciklama": f"{tl(fee)} yerine {tl(disc)} ile"
                             + (f" rakip {cheapest['hizmet']} fiyatına yaklaşarak" if cheapest else "")
                             + " 2 aylık sadakat kazanın"}
    else:
        disc = round(fee * 0.8, 2)
        first = {"baslik": "3 Aylık %20 İndirim",
                 "aciklama": f"{tl(fee)} yerine {tl(disc)} ödeyerek 3 ay boyunca"
                             + (f" {cheapest['hizmet']} ile rekabet edebilecek" if cheapest else " daha uygun")
                             + " fiyata devam edin"}
    yearly = round(fee * 10 / 12, 2)
    second = {"baslik": "Yıllık Pakete Geçiş Bonusu",
              "aciklama": f"12 aylık pakette 2 ay hediye sunarak aylık maliyeti {tl(yearly)}'ye düşürün"}
    if f["kategori"] in ("Video", "Müzik"):
        third = {"baslik": "Aile Paketi Upgrade",
                 "aciklama": f"{tl(fee)} yerine {tl(round(fee * 1.2, 2))} ile 4 profil sunarak kullanıcının "
                             "maliyet paylaşımıyla aboneliği sürdürmesini sağlayın"}
    else:
        third = {"baslik": "Kullanım Bazlı Hafif Plan",
                 "aciklama": f"Temel özellikleri {tl(round(fee * 0.5, 2))} ile sunan hafif bir planla "
                             "kullanıcıyı iptal yerine plan değiştirmeye yönlendirin"}
    return {"churn_risk": score, "degerlendirme": degerlendirme, "aksiyonlar": [first, second, third]}


def spending_summary(payload: dict) -> dict:
    months = payload["aylik_gider_toplamlari"]
    avg = statistics.mean(m["gider"] for m in months)
    items = list(payload["harcama_kalemleri_6_ay_tl"].items())
    sub_names = {s["hizmet"].upper() for s in payload["abonelikler"]}
    top = [k for k, _ in items if k not in sub_names][:2]
    subs_total = sum(s["aylik_ucret_tl"] for s in payload["abonelikler"] if s["sanal_kart"] == "Aktif")
    first, last = months[0]["gider"], months[-1]["gider"]
    trend = "arttı" if last > first * 1.05 else "azaldı" if last < first * 0.95 else "dengede kaldı"
    return {"ozet": (
        f"Son 6 ayda aylık ortalama {tl(avg)} harcadın; bu, maaşının {pct(100 * avg / payload['aylik_net_maas_tl'])}'i. "
        f"En çok harcama yaptığın yerler {' ve '.join(t.title() for t in top)}; aylık giderin dönem başına göre {trend}. "
        f"Aktif aboneliklerin ayda {tl(subs_total)} tutuyor, kullanmadıklarını dondurarak bu yükü azaltabilirsin.")}
