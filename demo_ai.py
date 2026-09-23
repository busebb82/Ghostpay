"""
demo_ai.py
API anahtari olmadan calisan demo analiz motoru. ai_engine.py ile ayni
cikti bicimini, davranis profilindeki gercek sayilardan kural tabanli
olarak uretir. Boylece canli demo her zaman calisir ve maliyeti sifirdir.
ANTHROPIC_API_KEY tanimlandiginda uygulama otomatik olarak Claude'a gecer.
"""
import statistics


def tl(n: float) -> str:
    """289.99 -> '289,99 ₺', 1019.49 -> '1.019,49 ₺'"""
    s = f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} ₺"


def pct(n: float, digits: int = 1) -> str:
    return f"%{round(n, digits):g}"


def _rivals(f: dict) -> list[dict]:
    return f.get("ayni_kategorideki_diger_abonelikler", [])


def churn_score(f: dict) -> int:
    """Davranis sinyallerinden 0-100 arasi churn skoru."""
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
    return int(max(5, min(95, round(score))))


def analyze_subscription(f: dict) -> dict:
    """B2C: kullaniciya ozel tasarruf onerisi."""
    rivals = _rivals(f)
    count = len(rivals) + 1
    ratio = f["maasa_orani_yuzde"]
    cat = f["kategori"]
    frozen = f["sanal_kart_durumu"] == "Donduruldu"
    most_expensive = f["kategorinin_en_pahalisi_mi"] and rivals

    if frozen:
        ozet = (f"Kartın dondurulmuş durumda ve her ay {tl(f['aylik_ucret_tl'])} tasarruf ediyorsun; "
                "bu servisi artık kullanmıyorsan kartı kalıcı olarak silebilirsin.")
    elif rivals:
        ozet = (f"{'Maaşının çok küçük bir kısmını kaplıyor' if ratio < 1 else 'Bütçende hissedilir bir yer tutuyor'}"
                f" ama aynı kategoride {count} aboneliğin var"
                f"{' ve bu en pahalısı' if most_expensive else ''}, kullanım sıklığını gözden geçirmen iyi olur.")
    else:
        ozet = (f"{cat} kategorisindeki tek aboneliğin ve maaşının {pct(ratio, 2)}'ini oluşturuyor; "
                "düzenli kullanıyorsan devam etmen mantıklı.")

    maddeler = [
        f"Maaşının sadece {pct(ratio, 2)}'ini oluşturuyor, bütçene yük değil" if ratio < 1
        else f"Maaşının {pct(ratio, 2)}'ini oluşturuyor, abonelikler arasında yükü yüksek",
    ]
    if rivals:
        maddeler.append(f"{cat} kategorisinde {count} aboneliğin var"
                        f"{' ve bu en pahalısı' if most_expensive else ''}, hepsini aktif kullanmıyor olabilirsin")
        cheapest = min(r["aylik_ucret_tl"] for r in rivals)
        maddeler.append(f"Diğer {len(rivals)} {cat.lower()} aboneliğinle çakışma varsa, birini iptal edip "
                        f"aylık {tl(min(cheapest, f['aylik_ucret_tl']))} ile {tl(f['aylik_ucret_tl'])} "
                        "arası tasarruf edebilirsin")
    else:
        maddeler.append(f"{cat} kategorisinde alternatif bir aboneliğin yok, çakışan harcama görünmüyor")
        maddeler.append(f"Son {f['kesintisiz_odeme_ay_sayisi']} ayda kesintisiz ödeme yapılmış, "
                        "düzenli kullanılan bir servis gibi görünüyor")
    if f["limit_ucretin_altinda_mi"]:
        maddeler[-1] = (f"Kart limitin ({tl(f['sanal_kart_aylik_limiti_tl'])}) ücretin altında; "
                        "sonraki çekim reddedilecek")
    return {"ozet": ozet, "maddeler": maddeler[:3]}


def churn_analysis(f: dict) -> dict:
    """B2B: churn skoru, risk aciklamasi ve retention aksiyonlari."""
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

    cheapest = min(rivals, key=lambda r: r["aylik_ucret_tl"]) if rivals else None
    if frozen or score >= 70:
        disc = round(fee * 0.6, 2)
        first = {"baslik": "2 Ay %40 İndirim",
                 "aciklama": f"{tl(fee)} yerine {tl(disc)} ile"
                             + (f" rakip {cheapest['hizmet']}'in fiyatına yaklaşarak" if cheapest else "")
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
    """Islem gecmisi: son 6 ayin kisisel harcama ozeti."""
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
