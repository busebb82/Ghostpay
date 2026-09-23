"""
app.py — GhostPay sunucusu
Calistir: python3 app.py   ->   http://localhost:8501

Arayuz static/ klasorundeki tek sayfalik uygulamadir; bu dosya veri,
sanal kart islemleri ve yapay zeka cagrilari icin JSON API sunar.
Demo verisi bellekte tutulur, sunucu yeniden baslatilinca sifirlanir.
"""
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime

from flask import Flask, jsonify, request, send_from_directory

from ai_engine import (AIError, analyze_subscription, churn_analysis, get_client,
                       spending_summary)
from detector import (CATEGORIES, build_features, detect_subscriptions,
                      heuristic_churn, monthly_totals, next_due)
from mock_data import AYLIK_NET_MAAS, generate_transactions, window_months

app = Flask(__name__, static_folder="static", static_url_path="/static")
client = get_client()
executor = ThreadPoolExecutor(max_workers=6)
lock = threading.RLock()

TODAY = date.today()
MONTHS = window_months(TODAY)
TRANSACTIONS = generate_transactions(TODAY)
ANON_ID = "usr_" + hashlib.sha1(b"ghostpay-demo-user").hexdigest()[:8]

subs: list[dict] = detect_subscriptions(TRANSACTIONS, TODAY)
churn: dict[str, dict] = {}      # B2B churn analizi (abonelik id -> sonuc)
user_ai: dict[str, dict] = {}    # B2C kisisel analiz (abonelik id -> sonuc)
summary: dict = {}               # Islem gecmisi AI ozeti
pending: set[str] = set()        # AI churn analizi suren abonelikler
generation = 0                   # eski AI yanitlarinin yenisini ezmemesi icin


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def find_sub(sub_id: str) -> dict | None:
    return next((s for s in subs if s["id"] == sub_id), None)


def company_signals(sub: dict) -> dict:
    """Sirkete iletilen anonimlestirilmis finansal davranis sinyalleri."""
    return {"anonim_kullanici_id": ANON_ID,
            **build_features(sub, subs, TRANSACTIONS, AYLIK_NET_MAAS)}


def reset_churn(sub: dict) -> None:
    """Kural tabanli skoru hemen yazar; API anahtari varsa AI analizini baslatir."""
    global generation
    generation += 1
    churn[sub["id"]] = {"churn_risk": heuristic_churn(sub, subs, AYLIK_NET_MAAS),
                        "kaynak": "tahmini", "degerlendirme": [], "aksiyonlar": [],
                        "zaman": None, "nesil": generation}
    if client:
        pending.add(sub["id"])
        executor.submit(run_churn, sub["id"], company_signals(sub), generation)


def run_churn(sub_id: str, signals: dict, gen: int) -> None:
    try:
        result = {**churn_analysis(client, signals), "kaynak": "ai", "zaman": now_iso()}
    except AIError as e:
        result = {"hata": str(e)}
    with lock:
        current = churn.get(sub_id)
        if not current or current["nesil"] != gen:
            return
        pending.discard(sub_id)
        churn[sub_id] = {**current, **result}


def state_payload() -> dict:
    with lock:
        return {
            "bugun": TODAY.isoformat(),
            "maas": AYLIK_NET_MAAS,
            "kategoriler": CATEGORIES,
            "ai_hazir": client is not None,
            "aylar": [{"yil": y, "ay": m} for y, m in MONTHS],
            "aylik_toplamlar": monthly_totals(TRANSACTIONS, MONTHS),
            "islemler": [{**t, "tarih": t["tarih"].isoformat()} for t in TRANSACTIONS],
            "abonelikler": subs,
            "churn": churn,
            "kullanici_ai": user_ai,
            "ozet": summary,
            "bekleyen": sorted(pending),
        }


# ---------------- Sayfa ----------------
@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/state")
def get_state():
    return jsonify(state_payload())


# ---------------- Sanal kart islemleri ----------------
@app.post("/api/abonelik/<sub_id>/durum")
def set_status(sub_id):
    durum = request.json.get("durum")
    if durum not in ("Aktif", "Donduruldu"):
        return jsonify({"hata": "Geçersiz kart durumu."}), 400
    with lock:
        sub = find_sub(sub_id)
        if not sub:
            return jsonify({"hata": "Abonelik bulunamadı."}), 404
        sub["durum"] = durum
        sub["dondurma_tarihi"] = TODAY.isoformat() if durum == "Donduruldu" else None
        sub["sonraki_odeme"] = next_due(date.fromisoformat(sub["son_odeme"]), TODAY).isoformat()
        user_ai.pop(sub_id, None)
        reset_churn(sub)
    return jsonify(state_payload())


@app.post("/api/abonelik/<sub_id>/limit")
def set_limit(sub_id):
    try:
        limit = round(float(str(request.json.get("limit")).replace(",", ".")), 2)
    except (TypeError, ValueError):
        return jsonify({"hata": "Geçerli bir limit girin."}), 400
    if limit < 0:
        return jsonify({"hata": "Limit negatif olamaz."}), 400
    with lock:
        sub = find_sub(sub_id)
        if not sub:
            return jsonify({"hata": "Abonelik bulunamadı."}), 404
        sub["limit"] = limit
        user_ai.pop(sub_id, None)
        reset_churn(sub)
    return jsonify(state_payload())


@app.delete("/api/abonelik/<sub_id>")
def delete_card(sub_id):
    with lock:
        sub = find_sub(sub_id)
        if not sub:
            return jsonify({"hata": "Abonelik bulunamadı."}), 404
        subs.remove(sub)
        for store in (churn, user_ai):
            store.pop(sub_id, None)
        pending.discard(sub_id)
    return jsonify(state_payload())


# ---------------- Yapay zeka ----------------
def ai_unavailable():
    return jsonify({"hata": "API anahtarı bulunamadı. ANTHROPIC_API_KEY ortam değişkenini "
                            "ya da .streamlit/secrets.toml dosyasını kontrol edin."}), 503


@app.post("/api/ai/abonelik/<sub_id>")
def ai_user(sub_id):
    if not client:
        return ai_unavailable()
    with lock:
        sub = find_sub(sub_id)
        if not sub:
            return jsonify({"hata": "Abonelik bulunamadı."}), 404
        features = build_features(sub, subs, TRANSACTIONS, AYLIK_NET_MAAS)
    try:
        result = {**analyze_subscription(client, features), "zaman": now_iso()}
    except AIError as e:
        return jsonify({"hata": str(e)}), 502
    with lock:
        user_ai[sub_id] = result
    return jsonify(state_payload())


@app.get("/api/b2b/<sub_id>/rapor")
def b2b_report(sub_id):
    with lock:
        sub = find_sub(sub_id)
        if not sub:
            return jsonify({"hata": "Abonelik bulunamadı."}), 404
        return jsonify(company_signals(sub))


@app.post("/api/ai/ozet")
def ai_summary():
    if not client:
        return ai_unavailable()
    with lock:
        by_merchant: dict[str, float] = {}
        for t in TRANSACTIONS:
            if t["tip"] == "Gider":
                by_merchant[t["aciklama"]] = by_merchant.get(t["aciklama"], 0) - t["tutar"]
        payload = {
            "aylik_net_maas_tl": AYLIK_NET_MAAS,
            "aylik_gider_toplamlari": monthly_totals(TRANSACTIONS, MONTHS),
            "harcama_kalemleri_6_ay_tl": {k: round(v, 2) for k, v in
                                          sorted(by_merchant.items(), key=lambda x: -x[1])},
            "abonelikler": [{"hizmet": s["ad"], "kategori": s["kategori"],
                             "aylik_ucret_tl": s["fiyat"], "sanal_kart": s["durum"]}
                            for s in subs],
        }
    try:
        result = {**spending_summary(client, payload), "zaman": now_iso()}
    except AIError as e:
        return jsonify({"hata": str(e)}), 502
    with lock:
        summary.clear()
        summary.update(result)
    return jsonify(state_payload())


@app.post("/api/ai/yenile")
def refresh_all():
    with lock:
        user_ai.clear()
        summary.clear()
        for s in subs:
            reset_churn(s)
    return jsonify(state_payload())


with lock:
    for s in subs:
        reset_churn(s)

if __name__ == "__main__":
    print("GhostPay çalışıyor: http://localhost:8501")
    app.run(host="127.0.0.1", port=8501, debug=False, threaded=True)
