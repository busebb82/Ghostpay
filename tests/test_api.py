import pytest

import app as ghost
from ai_engine import AIEngine


@pytest.fixture
def client():
    ghost.app.testing = True
    ghost.engine = AIEngine(None)
    ghost.sessions.clear()
    with ghost.app.test_client() as c:
        yield c


def state(c):
    return c.get("/api/state").get_json()


def test_index_and_health(client):
    assert client.get("/").status_code == 200
    assert client.get("/healthz").get_json()["durum"] == "ok"


def test_state_has_demo_numbers(client):
    s = state(client)
    assert s["ai_modu"] == "demo"
    assert len(s["abonelikler"]) == 11
    assert all(c["kaynak"] == "demo" and len(c["aksiyonlar"]) == 3 for c in s["churn"].values())


def test_freeze_activate_and_delete(client):
    s = client.post("/api/abonelik/netflix/durum", json={"durum": "Donduruldu"}).get_json()
    assert next(x for x in s["abonelikler"] if x["id"] == "netflix")["durum"] == "Donduruldu"
    s = client.post("/api/abonelik/netflix/durum", json={"durum": "Aktif"}).get_json()
    assert next(x for x in s["abonelikler"] if x["id"] == "netflix")["durum"] == "Aktif"
    s = client.delete("/api/abonelik/netflix").get_json()
    assert "netflix" not in {x["id"] for x in s["abonelikler"]}
    assert client.delete("/api/abonelik/netflix").status_code == 404


def test_limit_validation(client):
    s = client.post("/api/abonelik/netflix/limit", json={"limit": "289,00"}).get_json()
    assert next(x for x in s["abonelikler"] if x["id"] == "netflix")["limit"] == 289.0
    assert client.post("/api/abonelik/netflix/limit", json={"limit": "abc"}).status_code == 400
    assert client.post("/api/abonelik/netflix/limit", json={"limit": -5}).status_code == 400
    assert client.post("/api/abonelik/netflix/durum", json={"durum": "?"}).status_code == 400


def test_ai_endpoints_in_demo_mode(client):
    s = client.post("/api/ai/abonelik/netflix").get_json()
    assert len(s["kullanici_ai"]["netflix"]["maddeler"]) == 3
    s = client.post("/api/ai/ozet").get_json()
    assert s["ozet"]["ozet"]
    report = client.get("/api/b2b/disney-plus/rapor").get_json()
    assert report["anonim_kullanici_id"].startswith("usr_")


def test_visitors_do_not_share_state():
    ghost.app.testing = True
    ghost.engine = AIEngine(None)
    with ghost.app.test_client() as a, ghost.app.test_client() as b:
        a.delete("/api/abonelik/netflix")
        assert "netflix" not in {x["id"] for x in state(a)["abonelikler"]}
        assert "netflix" in {x["id"] for x in state(b)["abonelikler"]}


def test_deleted_card_can_be_restored_in_place(client):
    before = [x["id"] for x in state(client)["abonelikler"]]
    client.delete("/api/abonelik/disney-plus")
    s = client.post("/api/abonelik/disney-plus/geri-al").get_json()
    assert [x["id"] for x in s["abonelikler"]] == before
    assert "disney-plus" in s["churn"]
    assert client.post("/api/abonelik/disney-plus/geri-al").status_code == 404


def test_capping_limit_at_old_price_closes_the_hike(client):
    netflix = next(x for x in state(client)["abonelikler"] if x["id"] == "netflix")
    s = client.post("/api/abonelik/netflix/limit", json={"limit": netflix["zam"]["eski_fiyat"]}).get_json()
    netflix = next(x for x in s["abonelikler"] if x["id"] == "netflix")
    assert netflix["limit"] == 249.99 < netflix["fiyat"]
    analysis = client.post("/api/ai/abonelik/netflix").get_json()["kullanici_ai"]["netflix"]
    assert "reddedilecek" in analysis["ozet"]


def test_security_headers(client):
    headers = client.get("/").headers
    assert "script-src 'self'" in headers["Content-Security-Policy"]
    assert headers["X-Frame-Options"] == "DENY"


def test_reset_restores_demo(client):
    client.delete("/api/abonelik/netflix")
    s = client.post("/api/demo/sifirla").get_json()
    assert len(s["abonelikler"]) == 11


def test_claude_calls_are_rate_limited_and_fall_back_to_demo():
    calls = []

    class Fake:
        class beta:
            class messages:
                @staticmethod
                def create(**kw):
                    calls.append(kw)
                    raise AssertionError("limit asildiktan sonra Claude cagrilmamali")

    engine = AIEngine(Fake(), hourly_limit=0)
    assert engine.mode == "claude"
    out = engine.spending_summary({"aylik_net_maas_tl": 65000, "aylik_gider_toplamlari": [{"gider": 1}],
                                   "harcama_kalemleri_6_ay_tl": {"MIGROS": 1}, "abonelikler": []})
    assert out["ozet"] and not calls


def test_language_header_switches_generated_texts(client):
    assert state(client)["dil"] == "tr"
    s = client.get("/api/state", headers={"X-Lang": "en"}).get_json()
    assert s["dil"] == "en"
    netflix = s["churn"]["netflix"]
    assert netflix["aksiyonlar"][0]["baslik"] == "Pre-Hike Price Guarantee"
    assert "churn score" in " ".join(netflix["degerlendirme"])
    s = client.post("/api/ai/abonelik/netflix", headers={"X-Lang": "en"}).get_json()
    assert "price" in s["kullanici_ai"]["netflix"]["ozet"]
    # Dil değişince eski dildeki analizler silinir
    s = client.get("/api/state", headers={"X-Lang": "tr"}).get_json()
    assert s["kullanici_ai"] == {}
    assert s["churn"]["netflix"]["aksiyonlar"][0]["baslik"] == "Zam Öncesi Fiyat Garantisi"


def test_error_messages_follow_language(client):
    r = client.post("/api/abonelik/netflix/limit", json={"limit": "abc"}, headers={"X-Lang": "en"})
    assert r.status_code == 400 and r.get_json()["hata"] == "Enter a valid limit."
    r = client.post("/api/abonelik/yok/durum", json={"durum": "Aktif"}, headers={"X-Lang": "tr"})
    assert r.get_json()["hata"] == "Abonelik bulunamadı."


def test_unknown_language_is_ignored(client):
    assert client.get("/api/state", headers={"X-Lang": "de"}).get_json()["dil"] == "tr"
