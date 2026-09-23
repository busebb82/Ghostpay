"""
ai_engine.py
Claude API katmani. Uc yerde kullanilir:
  1. B2C: aboneligin kullaniciya ozel analizi (kartin yanindaki AI simgesi)
  2. B2B: anonim sinyallerden churn skoru, risk aciklamasi ve retention aksiyonlari
  3. Islem gecmisi: son 6 ayin kisisel harcama ozeti
Tum hatalar AIError olarak Turkce mesajla yukari iletilir.
"""
import json
import os
import tomllib
from pathlib import Path

import anthropic

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


def get_client() -> anthropic.Anthropic | None:
    key = _api_key()
    return anthropic.Anthropic(api_key=key) if key else None


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


def analyze_subscription(client, features: dict) -> dict:
    return _ask_claude(client, SYSTEM_USER, SCHEMA_USER, features)


def churn_analysis(client, signals: dict) -> dict:
    result = _ask_claude(client, SYSTEM_COMPANY, SCHEMA_COMPANY, signals)
    result["churn_risk"] = max(0, min(100, int(result["churn_risk"])))
    return result


def spending_summary(client, payload: dict) -> dict:
    return _ask_claude(client, SYSTEM_SUMMARY, SCHEMA_SUMMARY, payload)
