"""
ai_engine.py
Yapay zeka katmani. Uc yerde kullanilir:
  1. B2C: aboneligin kullaniciya ozel analizi (kartin yanindaki AI simgesi)
  2. B2B: anonim sinyallerden churn skoru, risk aciklamasi ve retention aksiyonlari
  3. Islem gecmisi: son 6 ayin kisisel harcama ozeti

ANTHROPIC_API_KEY varsa Claude kullanilir; yoksa demo_ai.py'deki kural tabanli
motor ayni bicimde cevap uretir. Ayni girdiye verilen cevaplar onbellekte
tutulur ve Claude cagrilari saatlik limitle korunur (herkese acik demo icin).
Tum hatalar AIError olarak Turkce mesajla yukari iletilir.
"""
import hashlib
import json
import os
import threading
import time
import tomllib
from collections import deque
from pathlib import Path

import anthropic

import demo_ai

MODEL = "claude-opus-5"
SECRETS_FILE = Path(__file__).parent / ".streamlit" / "secrets.toml"


class AIError(Exception):
    """Arayuzde kullaniciya gosterilecek Turkce hata mesaji tasir."""


STYLE = """Türkçe yaz. Para tutarlarını Türk formatında yaz (örn. 289,99 ₺, 1.019,49 ₺),
yüzdeleri %0.45 biçiminde yaz. Kısa, somut ve veriye dayalı ol; verilen
sayıları kullan, veri dışında bilgi uydurma."""

SYSTEM_USER = f"""Sen GhostPay adlı abonelik yönetim platformunun kişisel analiz motorusun.
Sana kullanıcının bir aboneliğine ait davranışsal özellikler JSON olarak verilecek:
harcama alışkanlıkları, geçmiş ödemeler, aynı kategorideki rakip abonelikler,
fiyat seviyesi ve ücretin maaşa oranı. Tüm sinyalleri birlikte değerlendir.

- "ozet": kullanıcıya doğrudan hitap eden 1 cümlelik kişisel tasarruf önerisi
  (örn. "Maaşının çok küçük bir kısmını kaplıyor ama aynı kategoride 3 aboneliğin var,
  kullanım sıklığını gözden geçirmen iyi olur.")
- "maddeler": bu önerinin nedenlerini açıklayan tam 3 kısa madde.
{STYLE}"""

SYSTEM_COMPANY = f"""Sen GhostPay'in abonelik şirketlerine yönelik (B2B) churn analiz motorusun.
Sana bir abonelik şirketinin müşterisine ait ANONİMLEŞTİRİLMİŞ finansal davranış
sinyalleri verilecek: gelire göre abonelik maliyeti, aynı kategorideki rakip platformlar,
fiyat seviyesi, ödeme alışkanlıkları ve sanal kartın aktif ya da dondurulmuş olması.

- "churn_risk": müşterinin aboneliği iptal etme olasılığı, 0-100 arası tamsayı.
- "degerlendirme": skorun temel nedenlerini şirkete açıklayan tam 3 madde.
- "aksiyonlar": müşteriyi tutmak için tam 3 kişiselleştirilmiş retention aksiyonu.
  Her biri kısa bir "baslik" (örn. "2 Ay %40 İndirim", "Yıllık Pakete Geçiş Bonusu",
  "Aile Paketi Upgrade") ve somut fiyatlar içeren tek cümlelik "aciklama".
{STYLE}"""

SYSTEM_SUMMARY = f"""Sen GhostPay'in kişisel finans asistanısın. Sana kullanıcının son 6 aylık
Open Banking işlem özetleri verilecek. "ozet" alanına kullanıcıya doğrudan hitap eden,
2-3 cümlelik kişisel bir harcama davranışı özeti yaz: en çok nereye harcadığı,
aylık eğilim ve abonelik yükü hakkında somut bir tespit ve tek bir öneri.
{STYLE}"""

SCHEMA_USER = {
    "type": "object",
    "properties": {
        "ozet": {"type": "string"},
        "maddeler": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["ozet", "maddeler"],
    "additionalProperties": False,
}

SCHEMA_COMPANY = {
    "type": "object",
    "properties": {
        "churn_risk": {"type": "integer"},
        "degerlendirme": {"type": "array", "items": {"type": "string"}},
        "aksiyonlar": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"baslik": {"type": "string"}, "aciklama": {"type": "string"}},
                "required": ["baslik", "aciklama"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["churn_risk", "degerlendirme", "aksiyonlar"],
    "additionalProperties": False,
}

SCHEMA_SUMMARY = {
    "type": "object",
    "properties": {"ozet": {"type": "string"}},
    "required": ["ozet"],
    "additionalProperties": False,
}


def _api_key() -> str | None:
    """Anahtari ANTHROPIC_API_KEY ortam degiskeninden, yoksa
    .streamlit/secrets.toml dosyasindan okur."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"]
    try:
        with open(SECRETS_FILE, "rb") as f:
            return tomllib.load(f).get("ANTHROPIC_API_KEY")
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        return None


def _ask_claude(client: anthropic.Anthropic, system: str, schema: dict, payload: dict) -> dict:
    try:
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=4000,
            system=system,
            messages=[{
                "role": "user",
                "content": json.dumps(payload, ensure_ascii=False, indent=2),
            }],
            output_config={"effort": "low",
                           "format": {"type": "json_schema", "schema": schema}},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.AuthenticationError:
        raise AIError("API anahtarı geçersiz veya iptal edilmiş. console.anthropic.com "
                      "üzerinden yeni bir anahtar oluşturun.")
    except anthropic.PermissionDeniedError:
        raise AIError("API anahtarının bu modele erişim izni yok.")
    except anthropic.RateLimitError:
        raise AIError("İstek limiti aşıldı. Birkaç saniye bekleyip tekrar deneyin.")
    except anthropic.APIConnectionError:
        raise AIError("Claude API'ye bağlanılamadı. İnternet bağlantınızı kontrol edin.")
    except anthropic.APIStatusError as e:
        raise AIError(f"Claude API hatası (kod {e.status_code}). "
                      "Hesabınızda kredi olduğundan emin olun ve tekrar deneyin.")

    if response.stop_reason == "refusal":
        raise AIError("Yapay zekâ bu isteği yanıtlamadı. Lütfen tekrar deneyin.")
    if response.stop_reason == "max_tokens":
        raise AIError("Yapay zekâ yanıtı yarıda kesildi. Lütfen tekrar deneyin.")
    try:
        text = next(b.text for b in response.content if b.type == "text")
        return json.loads(text)
    except (StopIteration, json.JSONDecodeError):
        raise AIError("Yapay zekâ çıktısı çözümlenemedi. Lütfen tekrar deneyin.")


class AIEngine:
    """Claude ya da demo motorunu ayni arayuzle sunar."""

    def __init__(self, client: anthropic.Anthropic | None = None,
                 hourly_limit: int | None = None):
        self.client = client
        self.mode = "claude" if client else "demo"
        self.hourly_limit = hourly_limit if hourly_limit is not None else \
            int(os.environ.get("AI_HOURLY_LIMIT", "200"))
        self._cache: dict[str, dict] = {}
        self._calls: deque[float] = deque()
        self._lock = threading.Lock()

    @classmethod
    def from_environment(cls) -> "AIEngine":
        key = _api_key()
        return cls(anthropic.Anthropic(api_key=key) if key else None)

    def _allow_call(self) -> bool:
        with self._lock:
            now = time.time()
            while self._calls and now - self._calls[0] > 3600:
                self._calls.popleft()
            if len(self._calls) >= self.hourly_limit:
                return False
            self._calls.append(now)
            return True

    def _run(self, kind: str, payload: dict, claude_call, demo_call) -> dict:
        key = kind + ":" + hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        with self._lock:
            if key in self._cache:
                return dict(self._cache[key])
        if self.client and self._allow_call():
            result = claude_call(payload)
        else:
            # Demo modu ya da saatlik Claude limiti doldu: kural tabanli motor
            result = demo_call(payload)
        with self._lock:
            self._cache[key] = result
            while len(self._cache) > 2000:        # en eski kaydi at
                self._cache.pop(next(iter(self._cache)))
        return dict(result)

    def analyze_subscription(self, features: dict) -> dict:
        return self._run("user", features,
                         lambda p: _ask_claude(self.client, SYSTEM_USER, SCHEMA_USER, p),
                         demo_ai.analyze_subscription)

    def churn_analysis(self, signals: dict) -> dict:
        def claude(p):
            result = _ask_claude(self.client, SYSTEM_COMPANY, SCHEMA_COMPANY, p)
            result["churn_risk"] = max(0, min(100, int(result["churn_risk"])))
            return result
        # Anonim kullanici kimligi analiz sonucunu degistirmez; onbellek anahtarina girmesin
        payload = {k: v for k, v in signals.items() if k != "anonim_kullanici_id"}
        return self._run("churn", payload, claude, demo_ai.churn_analysis)

    def spending_summary(self, payload: dict) -> dict:
        return self._run("summary", payload,
                         lambda p: _ask_claude(self.client, SYSTEM_SUMMARY, SCHEMA_SUMMARY, p),
                         demo_ai.spending_summary)
