"""
app.py — GhostPay profesyonel arayuz v2
Calistir: python3 -m streamlit run app.py
"""
import hashlib

import pandas as pd
import plotly.express as px
import streamlit as st

from mock_data import generate_transactions
from detector import detect_subscriptions, build_features
from ai_engine import (AIError, get_client, analyze_subscription,
                       retention_insights)

# ---------------- Sayfa ayarlari ----------------
st.set_page_config(
    page_title="GhostPay — Abonelik Zekâsı",
    page_icon="👻",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------- Stil (CSS) ----------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="st-"], [class*="css"] {
    font-family: 'Inter', -apple-system, sans-serif;
}
#MainMenu, footer {visibility: hidden;}
.block-container {padding-top: 1.2rem; max-width: 1240px;}

h1, h2, h3, h4 {font-family:'Inter',sans-serif; letter-spacing:-.02em;}

/* ---- Hero ---- */
.gp-hero {
    background: linear-gradient(135deg, #6C5CE7 0%, #341f97 100%);
    padding: 32px 38px; border-radius: 20px; color: #fff; margin-bottom: 26px;
}
.gp-hero h1 {margin:0; font-size:2.15rem; font-weight:800; color:#fff;}
.gp-hero p  {margin:8px 0 0; opacity:.88; font-size:1rem; font-weight:400;}

/* ---- KPI kartlari ---- */
.gp-kpi {
    background:#fff; border:1px solid #ececf4; border-radius:14px;
    padding:18px 22px; box-shadow:0 2px 12px rgba(20,20,43,.05);
}
.gp-kpi .label {color:#8b8ba7; font-size:.72rem; letter-spacing:.6px;
                text-transform:uppercase; font-weight:600;}
.gp-kpi .value {font-size:1.5rem; font-weight:800; color:#14142b; margin-top:4px;}
.gp-kpi .sub   {font-size:.75rem; color:#0ca678; font-weight:600; margin-top:2px;}

/* ---- Sanal kart ---- */
.vcard {
    position:relative; border-radius:18px; padding:20px 24px; color:#fff;
    height:196px; box-shadow:0 10px 26px rgba(52,31,151,.22);
    display:flex; flex-direction:column; justify-content:space-between;
}
.vc-aktif      {background:linear-gradient(135deg,#6C5CE7 0%,#341f97 100%);}
.vc-donduruldu {background:linear-gradient(135deg,#74b9ff 0%,#0984e3 100%);}
.vc-iptal      {background:linear-gradient(135deg,#b2bec3 0%,#636e72 100%);}

.vcard .top {display:flex; justify-content:space-between; align-items:center;}
.vcard .brand {font-weight:800; font-size:.95rem; letter-spacing:1.2px;}
.vcard .stamp {
    font-size:.66rem; font-weight:800; letter-spacing:1px;
    border:1.6px solid rgba(255,255,255,.85); border-radius:6px;
    padding:3px 9px; text-transform:uppercase;
}
.vcard .chip {
    width:42px; height:30px; border-radius:6px;
    background:linear-gradient(135deg,#f5d76e,#d4af37);
    box-shadow:inset 0 0 4px rgba(0,0,0,.25);
}
.vcard .num {
    font-family:'Courier New',monospace; font-size:1.08rem;
    letter-spacing:2.6px; font-weight:600;
}
.vcard .meta {display:flex; justify-content:space-between; font-size:.68rem;
              opacity:.92; text-transform:uppercase; letter-spacing:.5px;}
.vcard .meta b {display:block; font-size:.82rem; letter-spacing:0;
                text-transform:none; margin-top:2px;}

/* ---- Abonelik detay ---- */
.sub-name {font-size:1.12rem; font-weight:700; color:#14142b; margin:0 0 2px;}
.sub-cat  {color:#8b8ba7; font-size:.82rem; margin:0 0 10px;}
.sub-line {font-size:.85rem; color:#4a4a68; margin:3px 0;}
.sub-line b {color:#14142b;}
.shield {color:#0ca678; font-weight:600; font-size:.8rem;}
</style>
""", unsafe_allow_html=True)


# ---------------- Yardimcilar ----------------
def kpi(col, label, value, sub=""):
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    col.markdown(
        f'<div class="gp-kpi"><div class="label">{label}</div>'
        f'<div class="value">{value}</div>{sub_html}</div>',
        unsafe_allow_html=True,
    )


def card_last4(merchant: str) -> str:
    """Her abonelige sabit, sahte bir kart-son-4-hane uretir."""
    return str(int(hashlib.md5(merchant.encode()).hexdigest(), 16) % 10000).zfill(4)


def next_payment(s: dict) -> str:
    return (pd.to_datetime(s["son_odeme"]) + pd.Timedelta(days=30)).strftime("%d.%m.%Y")


def vcard_html(s: dict, durum: str) -> str:
    cls = {"Aktif": "vc-aktif", "Donduruldu": "vc-donduruldu", "İptal": "vc-iptal"}[durum]
    stamp = {"Aktif": "AKTİF", "Donduruldu": "🧊 DONDURULDU", "İptal": "İPTAL EDİLDİ"}[durum]
    odeme = next_payment(s) if durum == "Aktif" else "—"
    return f"""
    <div class="vcard {cls}">
      <div class="top">
        <span class="brand">👻 GHOSTPAY <span style="opacity:.7">VIRTUAL</span></span>
        <span class="stamp">{stamp}</span>
      </div>
      <div class="chip"></div>
      <div class="num">••••&nbsp;••••&nbsp;••••&nbsp;{card_last4(s["merchant"])}</div>
      <div class="meta">
        <span>Bağlı Servis<b>{s["merchant"]}</b></span>
        <span>Aylık Limit<b>{s["aylik_tutar"]:.2f} ₺</b></span>
        <span>Sonraki Ödeme<b>{odeme}</b></span>
      </div>
    </div>"""


# ---------------- Veri hazirligi ----------------
if "subs" not in st.session_state:
    df = generate_transactions(months=6)
    subs = build_features(detect_subscriptions(df), df)
    st.session_state.df = df
    st.session_state.subs = subs
    st.session_state.cards = {s["merchant"]: "Aktif" for s in subs}
    st.session_state.analysis = {}
    st.session_state.retention = {}

subs = st.session_state.subs
cards = st.session_state.cards
client = get_client()

# ---------------- Kenar cubugu ----------------
with st.sidebar:
    st.markdown("## 👻 GhostPay")
    st.caption("Yapay zekâ destekli abonelik zekâ platformu")
    st.divider()
    if client:
        st.success("Claude bağlantısı hazır", icon="✅")
    else:
        st.error("API anahtarı bulunamadı. `.streamlit/secrets.toml` "
                 "dosyasını kontrol edin.", icon="🔑")
    st.divider()
    if st.button("🔄 Analizleri Sıfırla", use_container_width=True):
        st.session_state.analysis = {}
        st.session_state.retention = {}
        st.rerun()
    st.caption("GhostPay © 2026 — Demo sürümü")

# ---------------- Hero ----------------
st.markdown("""
<div class="gp-hero">
  <h1>👻 GhostPay</h1>
  <p>Her aboneliğe özel sanal kart, yapay zekâ destekli fayda ve churn analizi.
  Gereksiz harcamaları tek dokunuşla durdurun.</p>
</div>
""", unsafe_allow_html=True)

tab_user, tab_company, tab_raw = st.tabs(
    ["👤 Kullanıcı Paneli", "🏢 Şirket Paneli", "🧾 Ham Veri"]
)

# ==================== KULLANICI PANELI ====================
with tab_user:
    aktif_maliyet = sum(s["aylik_tutar"] for s in subs if cards[s["merchant"]] == "Aktif")
    tasarruf = sum(s["aylik_tutar"] for s in subs if cards[s["merchant"]] != "Aktif")

    k1, k2, k3, k4 = st.columns(4)
    kpi(k1, "Tespit Edilen Abonelik", len(subs))
    kpi(k2, "Aylık Aktif Maliyet", f"{aktif_maliyet:,.2f} ₺")
    kpi(k3, "Yıllık Tahmini Maliyet", f"{aktif_maliyet * 12:,.2f} ₺")
    kpi(k4, "Aylık Tasarruf", f"{tasarruf:,.2f} ₺",
        sub="dondurma ve iptallerden" if tasarruf else "")

    st.write("")
    g1, g2 = st.columns([1, 1.4])
    with g1:
        st.markdown("##### Kategoriye Göre Dağılım")
        cat = pd.DataFrame(subs).groupby("kategori")["aylik_tutar"].sum().reset_index()
        fig = px.pie(cat, names="kategori", values="aylik_tutar", hole=.58,
                     color_discrete_sequence=["#6C5CE7", "#a29bfe", "#341f97", "#b2bec3"])
        fig.update_traces(textinfo="label+percent")
        fig.update_layout(height=290, margin=dict(t=10, b=10, l=10, r=10),
                          showlegend=False, font_family="Inter")
        st.plotly_chart(fig, use_container_width=True)
    with g2:
        st.markdown("##### Abonelik Maliyetleri (₺/ay)")
        bar = pd.DataFrame(subs).sort_values("aylik_tutar")
        fig2 = px.bar(bar, x="aylik_tutar", y="merchant", orientation="h",
                      color_discrete_sequence=["#6C5CE7"])
        fig2.update_layout(height=290, margin=dict(t=10, b=10, l=10, r=10),
                           xaxis_title=None, yaxis_title=None, font_family="Inter")
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.markdown("### 💳 Sanal Kartlarınız")
    st.caption("Her abonelik, yalnızca o servise tanımlı ve aylık tutarla "
               "sınırlandırılmış bir sanal karta bağlıdır. Kart dondurulduğunda "
               "bir sonraki ödeme çekimi otomatik olarak engellenir.")

    for s in subs:
        m = s["merchant"]
        durum = cards[m]
        with st.container(border=True):
            col_card, col_info = st.columns([1.05, 1.5], gap="large")

            with col_card:
                st.markdown(vcard_html(s, durum), unsafe_allow_html=True)

            with col_info:
                st.markdown(
                    f'<p class="sub-name">{m}</p>'
                    f'<p class="sub-cat">{s["kategori"]} kategorisi</p>'
                    f'<p class="sub-line">Aylık ücret: <b>{s["aylik_tutar"]:.2f} ₺</b> '
                    f'&nbsp;•&nbsp; Bütçe payı: <b>%{s["butce_payi_yuzde"]}</b> '
                    f'&nbsp;•&nbsp; Toplam ödeme: <b>{s["odeme_sayisi"]}</b></p>'
                    f'<p class="sub-line">İlk ödeme: <b>{s["ilk_odeme"]}</b> '
                    f'&nbsp;•&nbsp; Son ödeme: <b>{s["son_odeme"]}</b></p>'
                    f'<p class="shield">🛡️ Limit koruması: bu karttan '
                    f'{s["aylik_tutar"]:.2f} ₺ üzeri çekim reddedilir</p>',
                    unsafe_allow_html=True)

                st.write("")
                b1, b2, b3 = st.columns([1, 1, 1.4])
                if durum == "Aktif":
                    if b1.button("🧊 Kartı Dondur", key=f"d_{m}", use_container_width=True):
                        cards[m] = "Donduruldu"
                        st.rerun()
                    if b2.button("❌ Aboneliği İptal Et", key=f"i_{m}", use_container_width=True):
                        cards[m] = "İptal"
                        st.rerun()
                elif durum == "Donduruldu":
                    if b1.button("▶️ Kartı Aktif Et", key=f"a_{m}", use_container_width=True):
                        cards[m] = "Aktif"
                        st.rerun()
                    if b2.button("❌ Aboneliği İptal Et", key=f"i_{m}", use_container_width=True):
                        cards[m] = "İptal"
                        st.rerun()
                else:  # Iptal
                    if b1.button("🔁 Yeniden Başlat", key=f"r_{m}", use_container_width=True):
                        cards[m] = "Aktif"
                        st.rerun()

                if b3.button("🤖 AI ile Analiz Et", key=f"ai_{m}", type="primary",
                             use_container_width=True, disabled=client is None):
                    with st.spinner("Claude davranış profilini analiz ediyor..."):
                        try:
                            st.session_state.analysis[m] = analyze_subscription(
                                client, {**s, "sanal_kart_durumu": durum})
                        except AIError as e:
                            st.session_state.analysis[m] = {"hata": str(e)}
                    st.rerun()

            r = st.session_state.analysis.get(m)
            if r:
                if "hata" in r:
                    st.error(f"Analiz başarısız: {r['hata']}", icon="⚠️")
                else:
                    a1, a2 = st.columns(2)
                    with a1:
                        st.markdown(f"**Utility Score:** {r['utility_score']}/100")
                        st.progress(r["utility_score"] / 100)
                    with a2:
                        st.markdown(f"**Churn Risk:** {r['churn_risk']}/100")
                        st.progress(r["churn_risk"] / 100)
                    st.markdown("**Skorların nedeni:**")
                    for madde in r["aciklamalar"]:
                        st.markdown(f"- {madde}")
                    st.info(f"💡 **Öneri:** {r['oneri']}")

# ==================== SIRKET PANELI ====================
with tab_company:
    st.markdown("### 🏢 Şirketler için Churn İstihbaratı")
    st.caption("Şirketlere yalnızca anonimleştirilmiş churn sinyalleri iletilir; "
               "kimlik bilgisi paylaşılmaz.")

    company = st.selectbox("Şirket seçin", [s["merchant"] for s in subs])
    s = next(x for x in subs if x["merchant"] == company)
    analiz = st.session_state.analysis.get(company, {})
    churn = analiz.get("churn_risk")

    k1, k2, k3 = st.columns(3)
    kpi(k1, "Sanal Kart Durumu", cards[company])
    kpi(k2, "Kategorideki Rakip Sayısı", s["ayni_kategori_abonelik_sayisi"] - 1)
    kpi(k3, "Hesaplanan Churn Risk", f"{churn}/100" if churn is not None else "—")

    st.write("")
    signals = {
        "anonim_kullanici_id": "user_7f3a9c",
        "hizmet": company,
        "aylik_ucret": s["aylik_tutar"],
        "ayni_kategorideki_rakip_abonelik_sayisi": s["ayni_kategori_abonelik_sayisi"] - 1,
        "kategorinin_en_pahalisi_mi": s["kategorideki_en_pahali_mi"],
        "sanal_kart_durumu": cards[company],
        "hesaplanan_churn_risk": churn if churn is not None else "henüz hesaplanmadı",
        "kullanicinin_genel_harcama_trendi": s["genel_harcama_trendi"],
    }
    with st.expander("Şirkete iletilen ham sinyaller (JSON)"):
        st.json(signals)

    if st.button("🤖 Retention Stratejisi Üret", type="primary",
                 disabled=client is None):
        with st.spinner("Claude retention önerileri üretiyor..."):
            try:
                st.session_state.retention[company] = retention_insights(client, signals)
            except AIError as e:
                st.session_state.retention[company] = {"hata": str(e)}
        st.rerun()

    r = st.session_state.retention.get(company)
    if r:
        if "hata" in r:
            st.error(f"Analiz başarısız: {r['hata']}", icon="⚠️")
        else:
            st.warning(f"**Risk Özeti:** {r['risk_ozeti']}")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Olası ayrılma nedenleri**")
                for n in r["ayrilma_nedenleri"]:
                    st.markdown(f"- {n}")
            with c2:
                st.markdown("**Önerilen retention aksiyonları**")
                for n in r["retention_onerileri"]:
                    st.markdown(f"- ✅ {n}")

# ==================== HAM VERI ====================
with tab_raw:
    st.markdown("### 🧾 Simüle Edilmiş Banka İşlem Dökümü (6 ay)")
    st.caption("Gerçek üründe bu veri Open Banking API'sinden gelir.")

    aylik = (st.session_state.df.set_index("tarih")
             .resample("ME")["tutar"].sum().reset_index())
    fig3 = px.area(aylik, x="tarih", y="tutar",
                   color_discrete_sequence=["#6C5CE7"])
    fig3.update_layout(height=250, margin=dict(t=10, b=10, l=10, r=10),
                       xaxis_title=None, yaxis_title="Aylık toplam (₺)",
                       font_family="Inter")
    st.plotly_chart(fig3, use_container_width=True)

    st.dataframe(st.session_state.df, use_container_width=True, hide_index=True)