"""API anahtarı yokken kullanılan kural tabanlı analiz motoru.

Claude ile aynı çıktı biçimini, davranış profilindeki sayılardan üretir.
Metinler Türkçe ve İngilizce yazılabilir; skor dilden bağımsızdır.
"""
import statistics
from datetime import date

MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
          "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July",
             "August", "September", "October", "November", "December"]
CATEGORY_EN = {"Video": "video", "Müzik": "music", "Üretkenlik": "productivity", "Yapay Zekâ": "AI"}
TREND_EN = {"stabil": "stable", "yükselişte": "rising", "düşüşte": "falling"}


def tl(n: float) -> str:
    s = f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} ₺"


def pct(n: float, digits: int = 1) -> str:
    return f"%{round(n, digits):g}".replace(".", ",")


def _month(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{MONTHS[d.month - 1]} {d.year}"


def money_en(n: float) -> str:
    return f"₺{n:,.2f}"


def pct_en(n: float, digits: int = 1) -> str:
    return f"{round(n, digits):g}%"


def _month_en(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{MONTHS_EN[d.month - 1]} {d.year}"


def _rivals(f: dict) -> list[dict]:
    return f.get("ayni_kategorideki_diger_abonelikler", [])


RISK_HIGH = 65
RISK_MEDIUM = 40


def _active_rivals(f: dict) -> list[dict]:
    return [r for r in _rivals(f) if r["durum"] == "Aktif"]


def churn_score(f: dict) -> int:
    """Kartı dondurmak en güçlü iptal sinyali; kesintisiz ödeme geçmişi riski düşürür."""
    fee = f["aylik_ucret_tl"]
    active = _active_rivals(f)
    score = 20.0
    if f["sanal_kart_durumu"] == "Donduruldu":
        score += 50
    # Dondurulmuş rakip, kullanıcının o servisi bıraktığını gösterir; rekabet sayılmaz
    score += min(14, 7 * len(active))
    if active:
        avg = statistics.mean(r["aylik_ucret_tl"] for r in active)
        if fee > avg:
            score += min(10, 10 * (fee / avg - 1))
        elif f["sanal_kart_durumu"] == "Aktif" and fee <= min(r["aylik_ucret_tl"] for r in active):
            score -= 4
    score += min(6, 4 * f["maasa_orani_yuzde"])
    if f["limit_ucretin_altinda_mi"]:
        score += 18
    if f.get("fiyat_artisi"):
        score += min(20, 1.25 * f["fiyat_artisi"]["oran_yuzde"])
    score -= min(8, f["kesintisiz_odeme_ay_sayisi"])
    return int(max(5, min(95, round(score))))


def analyze_subscription(f: dict, lang: str = "tr") -> dict:
    return _analyze_en(f) if lang == "en" else _analyze_tr(f)


def _analyze_tr(f: dict) -> dict:
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


def churn_analysis(f: dict, lang: str = "tr") -> dict:
    return _churn_en(f) if lang == "en" else _churn_tr(f)


def _churn_tr(f: dict) -> dict:
    rivals = _rivals(f)
    fee = f["aylik_ucret_tl"]
    score = churn_score(f)
    frozen = f["sanal_kart_durumu"] == "Donduruldu"

    months = f["kesintisiz_odeme_ay_sayisi"]
    degerlendirme = []
    if frozen:
        tarih = f.get("dondurma_tarihi") or ""
        tarih = ".".join(reversed(tarih.split("-"))) if tarih else "yakın zamanda"
        degerlendirme.append(f"Kullanıcı sanal kartı dondurdu ve %{score} churn skoru ile kaybedilme "
                             f"eşiğinde, {tarih} tarihinden bu yana ödeme yapılmıyor")
    elif f["limit_ucretin_altinda_mi"]:
        degerlendirme.append(f"Kullanıcı kart limitini {tl(f['sanal_kart_aylik_limiti_tl'])} ile ücretin altına "
                             "çekti; sonraki çekim reddedilecek ve bu güçlü bir iptal sinyali")
    elif score < RISK_MEDIUM:
        degerlendirme.append(f"Son {months} ayda kesintisiz ödeme yapılıyor; %{score} churn skoru "
                             "sadık bir kullanıcıya işaret ediyor")
    else:
        degerlendirme.append(f"Son {months} ayda kesintisiz ödeme yapılmasına rağmen "
                             f"%{score} churn skoru, fiyat hassasiyeti sinyali veriyor")
    if rivals:
        avg = statistics.mean(r["aylik_ucret_tl"] for r in rivals)
        diff = 100 * (fee / avg - 1)
        if len(rivals) == 1:
            other = f"diğer aboneliği {rivals[0]['hizmet']} ({tl(avg)})"
        else:
            other = f"diğer aboneliklerinin ortalaması ({tl(avg)})"
        compare = ("ile hemen hemen aynı" if abs(diff) < 2
                   else f"ile karşılaştırıldığında {pct(abs(diff))} {'daha pahalı' if diff > 0 else 'daha ucuz'}")
        degerlendirme.append(f"{tl(fee)} aylık ücret, kullanıcının {f['kategori'].lower()} kategorisindeki {other} {compare}")
        active = _active_rivals(f)
        paused = [r["hizmet"] for r in rivals if r["durum"] != "Aktif"]
        if active:
            names = ", ".join(r["hizmet"] for r in active)
            line = f"Aynı kategoride {len(active)} rakip servise ({names}) hâlâ ödeme yapılıyor"
            line += f"; {', '.join(paused)} kartı dondurulmuş" if paused else ", bu da alternatif kullanım gösteriyor"
        else:
            line = f"Kategorideki diğer abonelikler ({', '.join(paused)}) dondurulmuş; bu servis kategoride tek aktif seçenek"
        degerlendirme.append(line)
    else:
        degerlendirme.append(f"Kategoride rakip abonelik yok; ücretin maaşa oranı {pct(f['maasa_orani_yuzde'], 2)}")
        degerlendirme.append(f"Toplam abonelik yükünün maaşa oranı {pct(f['toplam_abonelik_yukunun_maasa_orani_yuzde'])}, "
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
    elif frozen or score >= RISK_HIGH:
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


def spending_summary(payload: dict, lang: str = "tr") -> dict:
    return _summary_en(payload) if lang == "en" else _summary_tr(payload)


def _summary_tr(payload: dict) -> dict:
    months = payload["aylik_gider_toplamlari"]
    avg = statistics.mean(m["gider"] for m in months)
    items = list(payload["harcama_kalemleri_6_ay_tl"].items())
    sub_names = {s["hizmet"].upper() for s in payload["abonelikler"]}
    top = [k for k, _ in items if k not in sub_names][:2]
    subs_total = sum(s["aylik_ucret_tl"] for s in payload["abonelikler"] if s["sanal_kart"] == "Aktif")
    first, last = months[0]["gider"], months[-1]["gider"]
    trend = "arttı" if last > first * 1.05 else "azaldı" if last < first * 0.95 else "dengede kaldı"
    return {"ozet": (
        f"Son 6 ayda aylık ortalama {tl(avg)} harcadın, maaşa oranı {pct(100 * avg / payload['aylik_net_maas_tl'])}. "
        f"En çok harcama yaptığın yerler {' ve '.join(t.title() for t in top)}; aylık giderin dönem başına göre {trend}. "
        f"Aktif aboneliklerin ayda {tl(subs_total)} tutuyor, kullanmadıklarını dondurarak bu yükü azaltabilirsin.")}


def _analyze_en(f: dict) -> dict:
    rivals = _rivals(f)
    count = len(rivals) + 1
    ratio = f["maasa_orani_yuzde"]
    cat = CATEGORY_EN.get(f["kategori"], f["kategori"])
    frozen = f["sanal_kart_durumu"] == "Donduruldu"
    most_expensive = f["kategorinin_en_pahalisi_mi"] and rivals
    hike = f.get("fiyat_artisi")
    capped = hike and f["sanal_kart_aylik_limiti_tl"] <= hike["eski_fiyat"]
    money = money_en

    if frozen:
        ozet = (f"Your card is frozen, which saves you {money(f['aylik_ucret_tl'])} a month; "
                "if you no longer use this service you can delete the card for good.")
    elif hike and not capped:
        ozet = (f"The price went up {pct_en(hike['oran_yuzde'])} in {_month_en(hike['tarih'])}; if you do not "
                f"want to pay the new price, lock the card limit at the old price of {money(hike['eski_fiyat'])}.")
    elif hike:
        ozet = (f"You kept the card limit at the old price of {money(hike['eski_fiyat'])} after the price hike, "
                f"so the next {money(hike['yeni_fiyat'])} charge will be declined. Raise the limit if you want to "
                "keep using it.")
    elif rivals:
        ozet = (f"{'It takes up a tiny share of your salary' if ratio < 1 else 'It takes up a noticeable part of your budget'}"
                f", but you have {count} {cat} subscriptions"
                f"{' and this is the most expensive one' if most_expensive else ''}, so it is worth checking how often "
                "you use each.")
    else:
        ozet = (f"This is your only {cat} subscription and costs {pct_en(ratio, 2)} of your salary; "
                "if you use it regularly, keeping it makes sense.")

    maddeler = [
        f"It costs {pct_en(ratio, 2)} of your salary, a light load on your budget" if ratio < 1
        else f"It costs {pct_en(ratio, 2)} of your salary, one of your heavier subscriptions",
    ]
    if rivals:
        maddeler.append(f"You have {count} {cat} subscriptions"
                        f"{' and this is the most expensive one' if most_expensive else ''}; you may not be using all of them")
        fees = [r["aylik_ucret_tl"] for r in rivals] + [f["aylik_ucret_tl"]]
        saving = money(min(fees)) if min(fees) == max(fees) else f"{money(min(fees))} to {money(max(fees))}"
        others = f"your other {len(rivals)} {cat} subscriptions" if len(rivals) > 1 else f"your other {cat} subscription"
        maddeler.append(f"If it overlaps with {others}, cancelling one saves {saving} a month")
    else:
        maddeler.append(f"You have no other {cat} subscription, so there is no overlapping spend")
        maddeler.append(f"It was paid every month for the last {f['kesintisiz_odeme_ay_sayisi']} months, "
                        "so it looks like a service you use regularly")
    if hike:
        maddeler.insert(1, f"The price rose from {money(hike['eski_fiyat'])} to {money(hike['yeni_fiyat'])} "
                           f"in {_month_en(hike['tarih'])} (a {pct_en(hike['oran_yuzde'])} increase)")
    if f["limit_ucretin_altinda_mi"]:
        maddeler[2] = (f"Your card limit ({money(f['sanal_kart_aylik_limiti_tl'])}) is below the price, "
                       "so the next charge will be declined")
    return {"ozet": ozet, "maddeler": maddeler[:3]}


def _churn_en(f: dict) -> dict:
    rivals = _rivals(f)
    fee = f["aylik_ucret_tl"]
    score = churn_score(f)
    frozen = f["sanal_kart_durumu"] == "Donduruldu"
    cat = CATEGORY_EN.get(f["kategori"], f["kategori"])
    months = f["kesintisiz_odeme_ay_sayisi"]
    money = money_en

    degerlendirme = []
    if frozen:
        when = f.get("dondurma_tarihi")
        if when:
            d = date.fromisoformat(when)
            when = f"{MONTHS_EN[d.month - 1]} {d.day}, {d.year}"
        degerlendirme.append(f"The customer froze the virtual card and is close to leaving, with a churn score of "
                             f"{score}%; no payment has gone through since {when or 'recently'}")
    elif f["limit_ucretin_altinda_mi"]:
        degerlendirme.append(f"The customer lowered the card limit to {money(f['sanal_kart_aylik_limiti_tl'])}, below "
                             "the price; the next charge will be declined, a strong cancellation signal")
    elif score < RISK_MEDIUM:
        degerlendirme.append(f"Payments went through every month for {months} months; a churn score of {score}% "
                             "points to a loyal customer")
    else:
        degerlendirme.append(f"Despite {months} months of uninterrupted payments, a churn score of {score}% "
                             "signals price sensitivity")
    if rivals:
        avg = statistics.mean(r["aylik_ucret_tl"] for r in rivals)
        diff = 100 * (fee / avg - 1)
        other = (f"the customer's other {cat} subscription, {rivals[0]['hizmet']} ({money(avg)})" if len(rivals) == 1
                 else f"the average of the customer's other {cat} subscriptions ({money(avg)})")
        if abs(diff) < 2:
            degerlendirme.append(f"The {money(fee)} monthly price is about the same as {other}")
        else:
            degerlendirme.append(f"The {money(fee)} monthly price is {pct_en(abs(diff))} "
                                 f"{'more expensive' if diff > 0 else 'cheaper'} than {other}")
        active = _active_rivals(f)
        paused = [r["hizmet"] for r in rivals if r["durum"] != "Aktif"]
        if active:
            names = ", ".join(r["hizmet"] for r in active)
            line = f"The customer still pays for {len(active)} competing service{'s' if len(active) > 1 else ''} ({names})"
            line += f"; the {', '.join(paused)} card is frozen" if paused else ", which shows alternative usage"
        else:
            line = (f"The other subscriptions in this category ({', '.join(paused)}) are frozen; this is the only "
                    "active option")
        degerlendirme.append(line)
    else:
        degerlendirme.append(f"No competing subscription in the category; the price is {pct_en(f['maasa_orani_yuzde'], 2)} "
                             "of the salary")
        degerlendirme.append(f"All subscriptions together cost {pct_en(f['toplam_abonelik_yukunun_maasa_orani_yuzde'])} "
                             f"of the salary and overall spending is {TREND_EN.get(f['genel_harcama_trendi'], 'stable')}")

    hike = f.get("fiyat_artisi")
    if hike:
        degerlendirme.insert(1, f"After the {_month_en(hike['tarih'])} price hike the fee rose from "
                                f"{money(hike['eski_fiyat'])} to {money(fee)} ({pct_en(hike['oran_yuzde'])}); "
                                "the customer is price sensitive")
        degerlendirme = degerlendirme[:3]

    cheapest = min(rivals, key=lambda r: r["aylik_ucret_tl"]) if rivals else None
    if hike:
        first = {"baslik": "Pre-Hike Price Guarantee",
                 "aciklama": f"Offer the old price of {money(hike['eski_fiyat'])} for 3 months to reduce "
                             "hike-driven cancellations"}
    elif frozen or score >= RISK_HIGH:
        first = {"baslik": "40% Off for 2 Months",
                 "aciklama": f"Charge {money(round(fee * 0.6, 2))} instead of {money(fee)}"
                             + (f", close to the competing {cheapest['hizmet']} price," if cheapest else "")
                             + " to win 2 months of loyalty"}
    else:
        first = {"baslik": "20% Off for 3 Months",
                 "aciklama": f"Charge {money(round(fee * 0.8, 2))} instead of {money(fee)} for 3 months"
                             + (f" to compete with {cheapest['hizmet']}" if cheapest else "")}
    second = {"baslik": "Annual Plan Bonus",
              "aciklama": f"Give 2 months free on a 12-month plan, bringing the monthly cost down to "
                          f"{money(round(fee * 10 / 12, 2))}"}
    if f["kategori"] in ("Video", "Müzik"):
        third = {"baslik": "Family Plan Upgrade",
                 "aciklama": f"Offer 4 profiles for {money(round(fee * 1.2, 2))} instead of {money(fee)} so the "
                             "customer can share the cost and stay"}
    else:
        third = {"baslik": "Usage-Based Lite Plan",
                 "aciklama": f"Offer a lite plan with the core features for {money(round(fee * 0.5, 2))} so the "
                             "customer downgrades instead of cancelling"}
    return {"churn_risk": score, "degerlendirme": degerlendirme, "aksiyonlar": [first, second, third]}


def _summary_en(payload: dict) -> dict:
    months = payload["aylik_gider_toplamlari"]
    avg = statistics.mean(m["gider"] for m in months)
    items = list(payload["harcama_kalemleri_6_ay_tl"].items())
    sub_names = {s["hizmet"].upper() for s in payload["abonelikler"]}
    top = [k for k, _ in items if k not in sub_names][:2]
    subs_total = sum(s["aylik_ucret_tl"] for s in payload["abonelikler"] if s["sanal_kart"] == "Aktif")
    first, last = months[0]["gider"], months[-1]["gider"]
    trend = "went up" if last > first * 1.05 else "went down" if last < first * 0.95 else "stayed flat"
    return {"ozet": (
        f"Over the last 6 months you spent {money_en(avg)} a month on average, "
        f"{pct_en(100 * avg / payload['aylik_net_maas_tl'])} of your salary. You spent the most at "
        f"{' and '.join(t.title() for t in top)}, and your monthly spending {trend} since the start of the period. "
        f"Your active subscriptions cost {money_en(subs_total)} a month; freezing the ones you do not use "
        "would lower that.")}
