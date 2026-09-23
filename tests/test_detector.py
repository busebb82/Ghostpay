from datetime import date

from detector import CATEGORIES, build_features, detect_subscriptions, next_due
from mock_data import AYLIK_NET_MAAS, generate_transactions

TODAY = date(2026, 7, 11)   # demo videosundaki tarih


def _subs():
    return detect_subscriptions(generate_transactions(TODAY), TODAY)


def test_detects_all_subscriptions_in_category_order():
    names = [s["ad"] for s in _subs()]
    assert names == ["Netflix", "Disney+", "Youtube Premium", "Spotify", "Youtube Music",
                     "Apple Music", "Canva Pro", "Adobe Creative", "ChatGPT Plus",
                     "Claude Pro", "Gemini"]
    assert {s["kategori"] for s in _subs()} == set(CATEGORIES)


def test_everyday_spending_is_not_a_subscription():
    merchants = {s["merchant"] for s in _subs()}
    for noise in ("MIGROS", "BIM", "STARBUCKS", "TÜRK TELEKOM", "MAAS ODEMESI"):
        assert noise not in merchants


def test_payment_dates_match_demo_video():
    subs = {s["ad"]: s for s in _subs()}
    assert subs["Netflix"]["son_odeme"] == "2026-07-03"
    assert subs["Youtube Premium"]["son_odeme"] == "2026-06-21"
    assert subs["Youtube Premium"]["sonraki_odeme"] == "2026-07-21"


def test_initial_card_state():
    subs = {s["ad"]: s for s in _subs()}
    assert {n for n, s in subs.items() if s["durum"] == "Donduruldu"} == \
        {"Disney+", "Youtube Music", "Claude Pro"}
    assert subs["Canva Pro"]["limit"] == 704.70


def test_next_due_is_always_in_the_future():
    assert next_due(date(2026, 1, 31), date(2026, 2, 5)) == date(2026, 2, 28)
    assert next_due(date(2026, 1, 31), date(2026, 3, 5)) == date(2026, 3, 31)
    assert next_due(date(2026, 6, 3), date(2026, 7, 11)) == date(2026, 8, 3)


def test_features_are_json_serializable():
    import json
    subs = _subs()
    tx = generate_transactions(TODAY)
    f = build_features(subs[0], subs, tx, AYLIK_NET_MAAS)
    json.dumps(f)
    assert f["kategorideki_rakip_sayisi"] == 2
    assert f["kategorinin_en_pahalisi_mi"] is True
