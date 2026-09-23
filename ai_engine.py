"""Yapay zekâ katmanı: Claude varsa Claude, yoksa demo motoru.

Aynı girdiye verilen cevaplar önbellekte tutulur; Claude çağrıları saatlik
limitle sınırlanır, limit dolunca demo motoruna düşülür. Hatalar kullanıcıya
gösterilecek Türkçe mesajla AIError olarak iletilir.
"""
import hashlib
import json
import os
import threading
import time
from collections import deque

import anthropic

import demo_ai

MODEL = "claude-opus-5"


class AIError(Exception):
    pass


STYLE = """Türkçe yaz. Para tutarlarını Türk formatında yaz (örn. 289,99 ₺, 1.019,49 ₺),
yüzdeleri %0.45 biçiminde yaz. Kısa, somut ve veriye dayalı ol; verilen
sayıları kullan, veri dışında bilgi uydurma."""

SYSTEM_USER = f"""Sen GhostPay adlı abonelik yönetim platformunun kişisel analiz motorusun.
Sana kullanıcının bir aboneliğine ait davranışsal özellikler JSON olarak verilecek:
harcama alışkanlıkları, geçmiş ödemeler, aynı kategorideki rakip abonelikler,
fiyat seviyesi, varsa son zam ve ücretin maaşa oranı. Tüm sinyalleri birlikte
değerlendir.

- "ozet": kullanıcıya doğrudan hitap eden 1 cümlelik kişisel tasarruf önerisi
  (örn. "Maaşının çok küçük bir kısmını kaplıyor ama aynı kategoride 3 aboneliğin var,
  kullanım sıklığını gözden geçirmen iyi olur.")
- "maddeler": bu önerinin nedenlerini açıklayan tam 3 kısa madde.
{STYLE}"""

SYSTEM_COMPANY = f"""Sen GhostPay'in abonelik şirketlerine yönelik (B2B) churn analiz motorusun.
Sana bir abonelik şirketinin müşterisine ait ANONİMLEŞTİRİLMİŞ finansal davranış
sinyalleri verilecek: gelire göre abonelik maliyeti, aynı kategorideki rakip platformlar,
fiyat seviyesi, varsa son zam, ödeme alışkanlıkları ve sanal kartın aktif ya da
dondurulmuş olması.

- "churn_risk": müşterinin aboneliği iptal etme olasılığı, 0-100 arası tamsayı. Ölçek:
  0-39 düşük (düzenli ödeme, zam yok, kategoride en ucuz ya da tek seçenek),
  40-64 orta (son zam, pahalı fiyat, aktif rakip abonelik ya da limit ücretin altında),
  65-100 yüksek (sanal kart dondurulmuş). Kesintisiz ödeme geçmişi riski düşürür;
  dondurulmuş rakip abonelik rekabet sayılmaz. Her müşteriyi riskli gösterme.
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
        key = os.environ.get("ANTHROPIC_API_KEY")
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
        result = claude_call(payload) if self.client and self._allow_call() else demo_call(payload)
        with self._lock:
            self._cache[key] = result
            while len(self._cache) > 2000:
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
        # Anonim kimlik sonucu değiştirmez; önbellek anahtarına girerse her ziyaretçi ayrı çağrı yapar
        payload = {k: v for k, v in signals.items() if k != "anonim_kullanici_id"}
        return self._run("churn", payload, claude, demo_ai.churn_analysis)

    def spending_summary(self, payload: dict) -> dict:
        return self._run("summary", payload,
                         lambda p: _ask_claude(self.client, SYSTEM_SUMMARY, SCHEMA_SUMMARY, p),
                         demo_ai.spending_summary)
