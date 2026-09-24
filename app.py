"""GhostPay sunucusu.

Yerel: python3 app.py → http://localhost:8501
Canlı: gunicorn app:app (render.yaml)

Her ziyaretçi çerezle kendi demo verisini alır; biri kart silince diğerleri
etkilenmez. Oturumlar bellekte tutulduğu için gunicorn tek işçiyle çalışır.
"""
import hashlib
import os
import secrets
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime

from flask import Flask, g, jsonify, request, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix

import demo_ai
from ai_engine import AIEngine, AIError
from catalog import CATEGORIES
from detector import build_features, detect_subscriptions, monthly_totals, next_due
from mock_data import AYLIK_NET_MAAS, TIMEZONE, generate_transactions, local_today, window_months

SESSION_COOKIE = "gp_sid"
SESSION_TTL = 2 * 3600
MAX_SESSIONS = 300
MAX_LIMIT = 100_000
LANGS = ("tr", "en")

MESSAGES = {
    "bad_status": {"tr": "Geçersiz kart durumu.", "en": "Invalid card status."},
    "not_found": {"tr": "Abonelik bulunamadı.", "en": "Subscription not found."},
    "bad_limit": {"tr": "Geçerli bir limit girin.", "en": "Enter a valid limit."},
    "limit_range": {"tr": "Limit 0 ile 100.000 ₺ arasında olmalı.", "en": "The limit must be between ₺0 and ₺100,000."},
    "nothing_to_restore": {"tr": "Geri alınacak kart bulunamadı.", "en": "There is no card to restore."},
}

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

engine = AIEngine.from_environment()
executor = ThreadPoolExecutor(max_workers=6)


def now_iso() -> str:
    return datetime.now(TIMEZONE).isoformat(timespec="seconds")


class DemoSession:
    def __init__(self, sid: str):
        self.sid = sid
        self.lock = threading.RLock()
        self.last_seen = time.time()
        self.today = local_today()
        self.months = window_months(self.today)
        self.transactions = generate_transactions(self.today)
        self.subs: list[dict] = detect_subscriptions(self.transactions, self.today)
        self.anon_id = "usr_" + hashlib.sha1(sid.encode()).hexdigest()[:8]
        self.churn: dict[str, dict] = {}
        self.user_ai: dict[str, dict] = {}
        self.summary: dict = {}
        self.deleted: dict[str, tuple[int, dict]] = {}
        self.pending: set[str] = set()
        self.lang = "tr"
        # Aynı abonelik için eski bir Claude cevabı yenisinin üstüne yazılmasın
        self.generation = 0
        for s in self.subs:
            self.reset_churn(s)

    def find(self, sub_id: str) -> dict | None:
        return next((s for s in self.subs if s["id"] == sub_id), None)

    def features(self, sub: dict) -> dict:
        return build_features(sub, self.subs, self.transactions, AYLIK_NET_MAAS)

    def company_signals(self, sub: dict) -> dict:
        return {"anonim_kullanici_id": self.anon_id, **self.features(sub)}

    def set_lang(self, lang: str) -> None:
        """Dil değişince üretilmiş metinler yeni dilde baştan üretilir."""
        self.lang = lang
        self.user_ai.clear()
        self.summary = {}
        for s in self.subs:
            self.reset_churn(s)

    def reset_churn(self, sub: dict) -> None:
        """Tahmini skoru hemen yazar; Claude cevabı arka planda gelince üstüne yazılır."""
        self.generation += 1
        signals = self.company_signals(sub)
        self.churn[sub["id"]] = {"churn_risk": demo_ai.churn_score(signals), "kaynak": "tahmini",
                                 "degerlendirme": [], "aksiyonlar": [], "zaman": None,
                                 "nesil": self.generation}
        if engine.mode == "claude":
            self.pending.add(sub["id"])
            executor.submit(self._run_churn, sub["id"], signals, self.generation, self.lang)
        else:
            self._run_churn(sub["id"], signals, self.generation, self.lang)

    def _run_churn(self, sub_id: str, signals: dict, gen: int, lang: str) -> None:
        try:
            result = {**engine.churn_analysis(signals, lang), "kaynak": engine.mode, "zaman": now_iso()}
        except AIError as e:
            result = {"hata": str(e)}
        with self.lock:
            current = self.churn.get(sub_id)
            if not current or current["nesil"] != gen:
                return
            self.pending.discard(sub_id)
            self.churn[sub_id] = {**current, **result}

    def payload(self) -> dict:
        with self.lock:
            return {
                "bugun": self.today.isoformat(),
                "dil": self.lang,
                "maas": AYLIK_NET_MAAS,
                "kategoriler": CATEGORIES,
                "ai_modu": engine.mode,
                "aylar": [{"yil": y, "ay": m} for y, m in self.months],
                "aylik_toplamlar": monthly_totals(self.transactions, self.months),
                "islemler": [{**t, "tarih": t["tarih"].isoformat()} for t in self.transactions],
                "abonelikler": self.subs,
                "churn": self.churn,
                "kullanici_ai": self.user_ai,
                "ozet": self.summary,
                "bekleyen": sorted(self.pending),
            }


sessions: dict[str, DemoSession] = {}
sessions_lock = threading.Lock()


def _cleanup_sessions() -> None:
    now = time.time()
    for sid in [k for k, s in sessions.items() if now - s.last_seen > SESSION_TTL]:
        del sessions[sid]
    while len(sessions) >= MAX_SESSIONS:
        oldest = min(sessions.values(), key=lambda s: s.last_seen)
        del sessions[oldest.sid]


def current_session() -> DemoSession:
    sid = request.cookies.get(SESSION_COOKIE, "")
    with sessions_lock:
        sess = sessions.get(sid)
        if sess is None:
            _cleanup_sessions()
            sid = secrets.token_urlsafe(18)
            sess = sessions[sid] = DemoSession(sid)
            g.new_sid = sid
        sess.last_seen = time.time()
    lang = request.headers.get("X-Lang")
    if lang in LANGS and lang != sess.lang:
        with sess.lock:
            sess.set_lang(lang)
    return sess


@app.after_request
def finalize(response):
    if getattr(g, "new_sid", None):
        response.set_cookie(SESSION_COOKIE, g.new_sid, max_age=SESSION_TTL, httponly=True,
                            samesite="Lax", secure=request.is_secure)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "font-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'")
    return response


def error(key: str, status: int, sess: DemoSession):
    return jsonify({"hata": MESSAGES[key][sess.lang]}), status


def body() -> dict:
    return request.get_json(silent=True) or {}


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/healthz")
def healthz():
    return {"durum": "ok", "ai_modu": engine.mode}


@app.get("/api/state")
def get_state():
    return jsonify(current_session().payload())


@app.post("/api/demo/sifirla")
def reset_demo():
    sess = current_session()
    with sessions_lock:
        fresh = sessions[sess.sid] = DemoSession(sess.sid)
    if sess.lang != fresh.lang:
        fresh.set_lang(sess.lang)
    return jsonify(fresh.payload())


@app.post("/api/abonelik/<sub_id>/durum")
def set_status(sub_id):
    sess = current_session()
    status = body().get("durum")
    if status not in ("Aktif", "Donduruldu"):
        return error("bad_status", 400, sess)
    with sess.lock:
        sub = sess.find(sub_id)
        if not sub:
            return error("not_found", 404, sess)
        sub["durum"] = status
        sub["dondurma_tarihi"] = sess.today.isoformat() if status == "Donduruldu" else None
        sub["sonraki_odeme"] = next_due(date.fromisoformat(sub["son_odeme"]), sess.today).isoformat()
        sess.user_ai.pop(sub_id, None)
        sess.reset_churn(sub)
    return jsonify(sess.payload())


@app.post("/api/abonelik/<sub_id>/limit")
def set_limit(sub_id):
    sess = current_session()
    try:
        limit = round(float(str(body().get("limit")).replace(",", ".")), 2)
    except (TypeError, ValueError):
        return error("bad_limit", 400, sess)
    if not 0 <= limit <= MAX_LIMIT:
        return error("limit_range", 400, sess)
    with sess.lock:
        sub = sess.find(sub_id)
        if not sub:
            return error("not_found", 404, sess)
        sub["limit"] = limit
        sess.user_ai.pop(sub_id, None)
        sess.reset_churn(sub)
    return jsonify(sess.payload())


@app.delete("/api/abonelik/<sub_id>")
def delete_card(sub_id):
    sess = current_session()
    with sess.lock:
        sub = sess.find(sub_id)
        if not sub:
            return error("not_found", 404, sess)
        sess.deleted[sub_id] = (sess.subs.index(sub), sub)
        sess.subs.remove(sub)
        for store in (sess.churn, sess.user_ai):
            store.pop(sub_id, None)
        sess.pending.discard(sub_id)
    return jsonify(sess.payload())


@app.post("/api/abonelik/<sub_id>/geri-al")
def restore_card(sub_id):
    sess = current_session()
    with sess.lock:
        if sub_id not in sess.deleted:
            return error("nothing_to_restore", 404, sess)
        position, sub = sess.deleted.pop(sub_id)
        sess.subs.insert(min(position, len(sess.subs)), sub)
        sess.reset_churn(sub)
    return jsonify(sess.payload())


@app.post("/api/ai/abonelik/<sub_id>")
def ai_user(sub_id):
    sess = current_session()
    with sess.lock:
        sub = sess.find(sub_id)
        if not sub:
            return error("not_found", 404, sess)
        features = sess.features(sub)
    try:
        result = {**engine.analyze_subscription(features, sess.lang), "zaman": now_iso()}
    except AIError as e:
        return jsonify({"hata": str(e)}), 502
    with sess.lock:
        sess.user_ai[sub_id] = result
    return jsonify(sess.payload())


@app.get("/api/b2b/<sub_id>/rapor")
def b2b_report(sub_id):
    sess = current_session()
    with sess.lock:
        sub = sess.find(sub_id)
        if not sub:
            return error("not_found", 404, sess)
        return jsonify(sess.company_signals(sub))


@app.post("/api/ai/ozet")
def ai_summary():
    sess = current_session()
    with sess.lock:
        by_merchant: dict[str, float] = {}
        for t in sess.transactions:
            if t["tip"] == "Gider":
                by_merchant[t["aciklama"]] = by_merchant.get(t["aciklama"], 0) - t["tutar"]
        payload = {
            "aylik_net_maas_tl": AYLIK_NET_MAAS,
            "aylik_gider_toplamlari": monthly_totals(sess.transactions, sess.months),
            "harcama_kalemleri_6_ay_tl": {k: round(v, 2) for k, v in
                                          sorted(by_merchant.items(), key=lambda x: -x[1])},
            "abonelikler": [{"hizmet": s["ad"], "kategori": s["kategori"],
                             "aylik_ucret_tl": s["fiyat"], "sanal_kart": s["durum"]}
                            for s in sess.subs],
        }
    try:
        result = {**engine.spending_summary(payload, sess.lang), "zaman": now_iso()}
    except AIError as e:
        return jsonify({"hata": str(e)}), 502
    with sess.lock:
        sess.summary = result
    return jsonify(sess.payload())


@app.post("/api/ai/yenile")
def refresh_all():
    sess = current_session()
    with sess.lock:
        sess.user_ai.clear()
        sess.summary = {}
        for s in sess.subs:
            sess.reset_churn(s)
    return jsonify(sess.payload())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8501"))
    print(f"GhostPay çalışıyor: http://localhost:{port}  (yapay zekâ modu: {engine.mode})")
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=port, threaded=True)
