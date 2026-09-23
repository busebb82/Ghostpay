# 👻 GhostPay — Moka United

Dijital abonelikleri kullanıcılar ve şirketler için daha şeffaf, yönetilebilir ve
akıllı hale getiren, yapay zekâ destekli abonelik yönetim platformu (demo).

Demo, gerçek banka verisi yerine **6 aylık sentetik Open Banking işlem geçmişi**
kullanır. Sistem bu geçmişteki düzenli ödemeleri tespit eder, abonelikleri
kategorilere ayırır ve her aboneliğe ayrı bir **Moka United sanal kartı** bağlar.

## Kurulum ve çalıştırma

```bash
python3 -m pip install -r requirements.txt
python3 app.py
```

Tarayıcıda **http://localhost:8501** adresini açın.

### Claude API anahtarı

Yapay zekâ özellikleri için anahtarı iki yoldan biriyle verin:

- Ortam değişkeni: `export ANTHROPIC_API_KEY="sk-ant-..."`
- ya da `.streamlit/secrets.toml` dosyası (git'e eklenmez):

  ```toml
  ANTHROPIC_API_KEY = "sk-ant-..."
  ```

Anahtar yoksa uygulama yine açılır. Churn skorları kural tabanlı tahminle
gösterilir, yapay zekâ butonları anlaşılır bir hata mesajı verir.

## Ekranlar

### B2C — Müşteri Paneli
- Aylık net maaş, bu ayki abonelik tutarı, maaşa oranı ve dondurulan kartlardan gelen aylık tasarruf
- Kategori bazında aylık maliyet dağılımı (halka grafik) ve tüm sanal kartların limit kullanımı
- Kategori kartları (Video, Müzik, Üretkenlik, Yapay Zekâ) ve son 6 ayın toplam harcaması
- Her abonelik için sanal kart işlemleri:
  - **Kartı Dondur / Kartı Aktif Et**: dondurulan kartta sonraki çekim engellenir
  - **Kartı Sil**
  - **Aylık harcama limiti**: fiyat zammında limit ücretin altına çekilirse
    "Limit Ücretin Altında: Sonraki çekim reddedilecek." uyarısı çıkar
  - **✨ AI analizi**: harcama alışkanlıkları, geçmiş ödemeler, aynı kategorideki rakip
    abonelikler, fiyat seviyesi ve maaşa oranı değerlendirilerek kişisel tasarruf önerisi

### B2B — Şirket Paneli
- Abonelik sağlayıcısı kişisel veriye erişmeden, anonimleştirilmiş sinyallerle çalışır
- Churn riski, aylık ücret, kategorideki rakip sayısı, hesap (kart) durumu, aylık/yıllık gelir kaybı riski
- Churn skorunun nasıl hesaplandığını anlatan bilgi kutusu ve son 6 ay ödeme geçmişi
- **AI Açıklamasını Gör**: riskin nedenlerini doğal dilde açıklar
- **Önerilen Aksiyonlar**: müşteriyi tutmak için yapay zekânın ürettiği 3 kişisel kampanya
- **Anonimleştirilmiş Hesap Raporu**: şirkete iletilen sinyallerin tam listesi

### İşlem Geçmişi
- Aylık gider grafiği, açıklamada arama, Tümü / Gelir / Gider filtresi
- **✨ Son 6 ay özeti**: harcama davranışının yapay zekâ ile kişisel özeti

Kenar çubuğundaki **Analizi Yenile**, tüm abonelikler için churn analizlerini yeniden çalıştırır.

## Dosyalar

| Dosya | Görev |
|---|---|
| `app.py` | Flask sunucusu: sayfa, sanal kart işlemleri ve yapay zekâ için JSON API |
| `mock_data.py` | 6 aylık sentetik Open Banking işlem geçmişi |
| `detector.py` | Düzenli ödeme / abonelik tespiti, kategoriler, AI'a giden davranış profili |
| `ai_engine.py` | Claude API katmanı (kişisel analiz, churn analizi, harcama özeti) |
| `static/` | Arayüz (HTML, CSS, JavaScript) |

Demo verisi bellekte tutulur; sunucu yeniden başlatılınca başlangıç durumuna döner.
