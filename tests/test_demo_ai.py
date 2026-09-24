from datetime import date

import demo_ai
from detector import build_features, detect_subscriptions
from mock_data import AYLIK_NET_MAAS, generate_transactions

TODAY = date(2026, 7, 11)
TX = generate_transactions(TODAY)
SUBS = detect_subscriptions(TX, TODAY)


def features(name):
    sub = next(s for s in SUBS if s["ad"] == name)
    return build_features(sub, SUBS, TX, AYLIK_NET_MAAS)


def test_turkish_money_format():
    assert demo_ai.tl(289.99) == "289,99 ₺"
    assert demo_ai.tl(1019.49) == "1.019,49 ₺"


def test_user_analysis_shape():
    out = demo_ai.analyze_subscription(features("Netflix"))
    assert out["ozet"] and len(out["maddeler"]) == 3
    assert "%0,45" in out["maddeler"][0]


def test_churn_scores_spread_across_levels():
    scores = {s["ad"]: demo_ai.churn_score(features(s["ad"])) for s in SUBS}
    frozen = [scores[s["ad"]] for s in SUBS if s["durum"] == "Donduruldu"]
    assert min(frozen) >= demo_ai.RISK_HIGH
    assert scores["Apple Music"] < demo_ai.RISK_MEDIUM
    assert scores["Adobe Creative"] < demo_ai.RISK_MEDIUM
    assert demo_ai.RISK_MEDIUM <= scores["Netflix"] < demo_ai.RISK_HIGH


def test_churn_is_higher_when_card_is_frozen():
    active = demo_ai.churn_analysis(features("Netflix"))
    frozen = demo_ai.churn_analysis(features("Disney+"))
    assert 0 <= active["churn_risk"] < frozen["churn_risk"] <= 100
    assert len(frozen["degerlendirme"]) == 3 and len(frozen["aksiyonlar"]) == 3
    assert all(a["baslik"] and a["aciklama"] for a in frozen["aksiyonlar"])


def test_spending_summary_mentions_average():
    payload = {"aylik_net_maas_tl": AYLIK_NET_MAAS,
               "aylik_gider_toplamlari": [{"gider": 10000}, {"gider": 12000}],
               "harcama_kalemleri_6_ay_tl": {"MIGROS": 5000, "NETFLIX": 1700, "BIM": 4000},
               "abonelikler": [{"hizmet": "Netflix", "aylik_ucret_tl": 289.99, "sanal_kart": "Aktif"}]}
    text = demo_ai.spending_summary(payload)["ozet"]
    assert "11.000,00 ₺" in text and "Migros" in text and "Netflix" not in text


def test_price_hike_shows_up_in_advice():
    user = demo_ai.analyze_subscription(features("Netflix"))
    assert "249,99 ₺" in user["ozet"] and "%16" in user["ozet"]
    churn = demo_ai.churn_analysis(features("Netflix"))
    assert churn["aksiyonlar"][0]["baslik"] == "Zam Öncesi Fiyat Garantisi"


def test_texts_avoid_broken_turkish_suffixes():
    for sub in SUBS:
        f = build_features(sub, SUBS, TX, AYLIK_NET_MAAS)
        text = " ".join(demo_ai.analyze_subscription(f)["maddeler"]
                        + demo_ai.churn_analysis(f)["degerlendirme"])
        assert "'ini" not in text and "'in fiyat" not in text
        assert "ile 1.000,00 ₺ arası" not in text or "1.019,49" in text
