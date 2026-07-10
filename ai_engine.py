"""
ai_engine.py
Claude API katmani. Davranis profilini alir, skor + aciklama + oneri doner.
Tum hatalar AIError olarak Turkce mesajla yukari iletilir.
"""
import json

import anthropic
import streamlit as st

MODEL = "claude-sonnet-4-6"


class AIError(Exception):
    """Arayuzde kullaniciya gosterilecek Turkce hata mesaji tasir."""
    pass


SYSTEM_USER = """Sen GhostPay adlı abonelik zekâ platformunun analiz motorusun.
Sana bir aboneliğin davranışsal özellikleri JSON olarak verilecek.
Kurallara göre değil, TÜM sinyalleri birlikte değerlendirerek karar ver:
aynı kategorideki abonelik sayısı, fiyat, bütçe payı, harcama trendi,
sanal kart durumu vb.

Şu JSON'u üret:
{
  "utility_score": 0-100 arası tamsayı (aboneliğin kullanıcıya tahmini faydası),
  "churn_risk": 0-100 arası tamsayı (yakında iptal etme olasılığı),
  "aciklamalar": [skorların NEDENİNİ anlatan 3-4 kısa Türkçe madde],
  "oneri": "kullanıcıya tek cümlelik somut aksiyon (iptal et / dondur / devam et gibi)"
}
SADECE geçerli JSON döndür, başka hiçbir metin yazma."""

SYSTEM_COMPANY = """Sen GhostPay'in şirketlere yönelik (B2B) churn analiz motorusun.
Sana bir abonelik şirketinin müşterisine ait ANONİMLEŞTİRİLMİŞ churn
sinyalleri verilecek. Şu JSON'u üret:
{
  "risk_ozeti": "1-2 cümlelik Türkçe risk değerlendirmesi",
  "ayrilma_nedenleri": [2-3 olası ayrılma nedeni],
  "retention_onerileri": [3 somut kampanya önerisi, örn: öğrenci paketi,
                          3 aylık indirim, reklamlı ucuz plan]
}
SADECE geçerli JSON döndür, başka hiçbir metin yazma."""


def get_client() -> anthropic.Anthropic | None:
    """API anahtarini .streamlit/secrets.toml dosyasindan okur."""
    try:
        return anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    except (KeyError, FileNotFoundError):
        return None


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        text = text.removeprefix("json").strip()
    return json.loads(text)


def _call(client: anthropic.Anthropic, system: str, payload: dict):
    return client.messages.create(
        model=MODEL,
        max_tokens=800,
        system=system,
        messages=[{
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False, indent=2),
        }],
    )


def _ask_claude(client: anthropic.Anthropic, system: str, payload: dict) -> dict:
    try:
        response = _call(client, system, payload)
    except anthropic.AuthenticationError:
        raise AIError("API anahtarı geçersiz veya iptal edilmiş. "
                      "console.anthropic.com üzerinden yeni bir anahtar oluşturup "
                      ".streamlit/secrets.toml dosyasına yapıştırın.")
    except anthropic.PermissionDeniedError:
        raise AIError("API anahtarının bu modele erişim izni yok. "
                      "Konsoldan anahtar yetkilerini kontrol edin.")
    except anthropic.RateLimitError:
        raise AIError("İstek limiti aşıldı. Birkaç saniye bekleyip tekrar deneyin.")
    except anthropic.APIConnectionError:
        raise AIError("Claude API'ye bağlanılamadı. İnternet bağlantınızı kontrol edin.")
    except anthropic.APIStatusError as e:
        raise AIError(f"Claude API hatası (kod {e.status_code}). "
                      "Hesabınızda kredi olduğundan emin olun ve tekrar deneyin.")

    text = response.content[0].text
    try:
        return _parse_json(text)
    except (json.JSONDecodeError, IndexError):
        # Bozuk cikti geldiyse bir kez daha dene
        try:
            response = _call(client, system, payload)
            return _parse_json(response.content[0].text)
        except Exception:
            raise AIError("Yapay zekâ çıktısı çözümlenemedi. "
                          "Lütfen butona tekrar basın.")


def analyze_subscription(client, features: dict) -> dict:
    return _ask_claude(client, SYSTEM_USER, features)


def retention_insights(client, signals: dict) -> dict:
    return _ask_claude(client, SYSTEM_COMPANY, signals)