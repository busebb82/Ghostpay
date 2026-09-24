// Arayüz metinleri. Veri anahtarları (kategori, kart durumu, işlem tipi) sunucuda Türkçe kalır,
// burada yalnızca gösterim için çevrilir.
const I18N = {
  tr: {
    locale: "tr-TR",
    months: ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"],
    monthsShort: ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"],
    views: { b2c: "Müşteri Paneli", b2b: "Şirket Paneli", islemler: "İşlem Geçmişi" },
    categories: {},
    status: { Aktif: "Aktif", Donduruldu: "Donduruldu" },
    types: { "Tümü": "Tümü", Gelir: "Gelir", Gider: "Gider" },
    merchants: {},
    trend: {},
    s: {
      skip: "İçeriğe geç",
      navLabel: "Paneller",
      navB2c: "Müşteri Paneli", navB2cShort: "Müşteri",
      navB2b: "Şirket Paneli", navB2bShort: "Şirket",
      navTx: "İşlem Geçmişi", navTxShort: "İşlemler",
      aiBadge: "Yapay Zekâ Destekli Analiz",
      demoMode: "Demo modu",
      demoModeTip: "API anahtarı tanımlı değil: yapay zekâ yanıtları davranış verisinden kural tabanlı üretiliyor.",
      refresh: "Analizi Yenile",
      langSwitch: "Switch to English",
      loading: "Yükleniyor",
      serverError: "Sunucu hatası.",
      connectError: "Sunucuya bağlanılamadı: {msg}",
      retry: "Tekrar dene",
      close: "Kapat",

      introTitle: "GhostPay demosuna hoş geldin",
      introText: "Veriler sentetik ve yalnızca sana özel; yaptığın değişiklikler başkalarını etkilemez. Bir kartı dondurmayı, limitini değiştirmeyi ya da ✦ simgesiyle kişisel analiz almayı dene. Aynı verinin abonelik şirketine nasıl göründüğünü Şirket Paneli'nde görebilirsin.",
      introB2b: "Şirket Paneline Geç",
      introOk: "Anladım",
      introReset: "Demoyu sıfırla",

      welcome: "Tekrar Hoş Geldin!",
      kpiSalary: "Aylık Net Maaş", kpiSalarySub: "Her ayın 1'inde yatıyor",
      kpiSubs: "Bu Ay Abonelik", kpiSubsSub: "{n} aktif sanal kart",
      kpiRatio: "Maaşa Oranı", kpiRatioSub: "Abonelik giderinin gelire oranı",
      kpiSavings: "Aylık Tasarruf", kpiSavingsSub: "{n} dondurulmuş kart",
      hikeAlert: "{n} abonelikte zam tespit edildi.",
      review: "İncele",
      costSplit: "Aylık Maliyet Dağılımı",
      donutLabel: "Kategorilere göre aylık maliyet",
      monthlyLimit: "Aylık Abonelik Limiti",
      limitUsedAria: "Limitin {p} kısmı kullanıldı",
      used: "Kullanılan", remaining: "Kalan",
      categoriesLabel: "Kategoriler",
      cards: "{n} kart",
      totalSpend: "TOPLAM HARCAMA", last6: "son 6 ay",
      subsTitle: "{cat} Abonelikleri",
      noSubs: "Tespit edilen abonelik kalmadı.",
      resetDemo: "Demoyu Sıfırla",

      hike: "{p} zam",
      hikeSince: "{month} itibarıyla {old} → {new}",
      limitAtOld: "Limit eski fiyatta",
      capLimit: "Limiti {amount}'ye sabitle",
      cardFrozen: "Kart dondurulmuş",
      analyzing: "Analiz ediliyor",
      aiAnalysis: "AI Analizi",
      limitLabel: "Aylık harcama limiti (₺)",
      stepUp: "Limiti 1 ₺ artır", stepDown: "Limiti 1 ₺ azalt",
      saveLimit: "Limiti kaydet",
      monthlyFee: "Aylık ücret", salaryRatio: "Maaşa oranı", lastPayment: "Son ödeme",
      activate: "Kartı Aktif Et", freeze: "Kartı Dondur", delete: "Kartı Sil",
      aiFor: "{name} için AI analizi", aiTitle: "AI ile analiz et",
      cardBank: "SANAL KART", cardActive: "AKTİF", cardFrozenPill: "DONDURULDU",
      cardService: "SERVİS", cardLimit: "LİMİT", cardNext: "SONRAKİ",
      usage: "Kullanım",
      limitWarn: "Limit ücretin altında. Sonraki çekim reddedilecek.",
      limitUpdated: "Kart limiti güncellendi.",
      invalidLimit: "Geçerli bir limit girin.",
      capped: "{name} limiti {amount}'ye sabitlendi. Zamlı çekim reddedilecek.",
      reactivated: "{name} kartı yeniden aktif.",
      frozenToast: "{name} kartı donduruldu. Sonraki çekim reddedilecek.",
      deleted: "{name} sanal kartı silindi.",
      undo: "Geri al",
      restored: "{name} kartı geri yüklendi.",
      demoReset: "Demo başlangıç durumuna döndü.",
      refreshed: "Yapay zekâ analizleri yenilendi.",

      riskHigh: "Yüksek risk", riskMid: "Orta risk", riskLow: "Düşük risk",
      profileTitle: "Müşteri Profil Analizi",
      noCompany: "Analiz edilecek abonelik yok.",
      aiNotRun: "AI analizi henüz çalışmadı. 'Analizi Yenile' butonunu kullanın.",
      pickSub: "Abonelik seçin",
      report: "Anonimleştirilmiş Hesap Raporu",
      lastUpdate: "Son güncelleme: {when}", analyzingDots: "analiz ediliyor…",
      churn: "Churn Riski", estimated: "tahmini",
      fee: "Aylık Ücret", feeSub: "Maaşa oranı {p}", hiked: "{p} zamlı",
      rivals: "Rakip Abonelik", rivalsSub: "{cat} kategorisinde",
      account: "Hesap Durumu", cardLimitSub: "Kart limiti {amount}",
      revenueRisk: "Gelir Kaybı Riski", perMonth: "/ ay", perYear: "{amount} / yıl",
      churnTipTitle: "Churn Skoru Nasıl Hesaplanıyor?",
      churnTip: "AI modeli; işlem geçmişi, ödeme düzeni, aynı kategorideki diğer abonelikler, abonelik maliyeti, son zamlar, toplam abonelik yükü ve harcama alışkanlıklarını birlikte analiz ederek her kullanıcı için bir davranış profili oluşturur. Bu profil üzerinden ilgili aboneliğin iptal edilme (churn) olasılığı yüzdesel olarak hesaplanır. 0–39 düşük, 40–64 orta, 65 ve üzeri yüksek risk sayılır; en güçlü sinyal kartın dondurulması, kesintisiz ödeme geçmişi ise riski düşürür.",
      explain: "AI Açıklamasını Gör",
      payHistory: "Son 6 Ay Ödeme Geçmişi", payHistoryAria: "{name} son 6 ay ödemeleri",
      actions: "Önerilen Aksiyonlar",
      explainTitle: "AI Risk Açıklaması",
      explainNotReady: "AI açıklaması henüz hazır değil.",
      aiVerdict: "AI'ın Değerlendirmesi",
      reportNote: "Şirketlere kimlik bilgisi paylaşılmaz; yalnızca aşağıdaki anonim finansal davranış sinyalleri iletilir.",
      yes: "Evet", no: "Hayır",

      txTitle: "İşlem Geçmişi",
      aiMade: "Yapay Zekâ Üretimi", txSub: "6 aylık sentetik Open Banking simülasyonu",
      summaryTitle: "Son 6 Ay Özeti",
      summaryHint: "Son 6 aylık harcama davranışının kişisel özetini görmek için sağ üstteki ışıltı simgesine dokun.",
      summaryBtn: "AI harcama özeti oluştur", summaryBtnTitle: "AI özeti oluştur",
      search: "Açıklamada ara...", txType: "İşlem türü",
      monthlySpend: "Aylık Gider (₺) — Son 6 Ay", monthlySpendAria: "Son 6 ay aylık gider",
      transactions: "İşlemler", txCount: "{n} işlem",
      colDate: "TARİH", colDesc: "AÇIKLAMA", colType: "TİP", colAmount: "TUTAR",
      noTx: "Eşleşen işlem bulunamadı.",

      agoNow: "az önce", agoMin: "{n} dk önce", agoHour: "{n} sa önce", agoDay: "{n} gün önce",
    },
    report: {
      anonim_kullanici_id: "Anonim kullanıcı kimliği", hizmet: "Hizmet", kategori: "Kategori",
      aylik_ucret_tl: "Aylık ücret", maasa_orani_yuzde: "Ücretin maaşa oranı", fiyat_artisi: "Son zam",
      sanal_kart_durumu: "Sanal kart durumu", dondurma_tarihi: "Dondurma tarihi",
      sanal_kart_aylik_limiti_tl: "Kart limiti", limit_ucretin_altinda_mi: "Limit ücretin altında mı",
      kesintisiz_odeme_ay_sayisi: "Kesintisiz ödenen ay", odeme_gecmisi: "Ödeme geçmişi",
      kategorideki_rakip_sayisi: "Rakip abonelik sayısı", ayni_kategorideki_diger_abonelikler: "Aynı kategorideki abonelikler",
      rakip_ortalama_ucret_tl: "Rakiplerin ortalama ücreti", kategorinin_en_pahalisi_mi: "Kategorinin en pahalısı mı",
      toplam_aktif_abonelik_yuku_tl: "Toplam aktif abonelik yükü",
      toplam_abonelik_yukunun_maasa_orani_yuzde: "Abonelik yükünün maaşa oranı", genel_harcama_trendi: "Genel harcama eğilimi",
    },
  },

  en: {
    locale: "en-US",
    months: ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
    monthsShort: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    views: { b2c: "Customer Dashboard", b2b: "Company Dashboard", islemler: "Transactions" },
    categories: { "Video": "Video", "Müzik": "Music", "Üretkenlik": "Productivity", "Yapay Zekâ": "AI" },
    status: { Aktif: "Active", Donduruldu: "Frozen" },
    types: { "Tümü": "All", Gelir: "Income", Gider: "Expense" },
    merchants: { "MAAS ODEMESI": "SALARY PAYMENT" },
    trend: { stabil: "stable", "yükselişte": "rising", "düşüşte": "falling" },
    s: {
      skip: "Skip to content",
      navLabel: "Dashboards",
      navB2c: "Customer", navB2cShort: "Customer",
      navB2b: "Company", navB2bShort: "Company",
      navTx: "Transactions", navTxShort: "Transactions",
      aiBadge: "AI-Powered Analysis",
      demoMode: "Demo mode",
      demoModeTip: "No API key set: AI answers are generated by rules from the behaviour data.",
      refresh: "Refresh Analysis",
      langSwitch: "Türkçeye geç",
      loading: "Loading",
      serverError: "Server error.",
      connectError: "Could not reach the server: {msg}",
      retry: "Try again",
      close: "Close",

      introTitle: "Welcome to the GhostPay demo",
      introText: "The data is synthetic and private to you; your changes do not affect anyone else. Try freezing a card, changing its limit or getting a personal analysis with the ✦ button. The Company Dashboard shows how the same data looks to the subscription provider.",
      introB2b: "Open Company Dashboard",
      introOk: "Got it",
      introReset: "Reset demo",

      welcome: "Welcome back!",
      kpiSalary: "Monthly Net Salary", kpiSalarySub: "Paid on the 1st of every month",
      kpiSubs: "Subscriptions This Month", kpiSubsSub: "{n} active virtual cards", kpiSubsSub_one: "1 active virtual card",
      kpiRatio: "Share of Salary", kpiRatioSub: "Subscription spend as a share of income",
      kpiSavings: "Monthly Savings", kpiSavingsSub: "{n} frozen cards", kpiSavingsSub_one: "1 frozen card",
      hikeAlert: "Price hikes found on {n} subscriptions.", hikeAlert_one: "Price hike found on 1 subscription.",
      review: "Review",
      costSplit: "Monthly Cost Breakdown",
      donutLabel: "Monthly cost by category",
      monthlyLimit: "Monthly Subscription Limit",
      limitUsedAria: "{p} of the limit is used",
      used: "Used", remaining: "Remaining",
      categoriesLabel: "Categories",
      cards: "{n} cards", cards_one: "1 card",
      totalSpend: "TOTAL SPEND", last6: "last 6 months",
      subsTitle: "{cat} Subscriptions",
      noSubs: "No subscriptions left.",
      resetDemo: "Reset Demo",

      hike: "{p} price hike",
      hikeSince: "Since {month}: {old} → {new}",
      limitAtOld: "Limit kept at old price",
      capLimit: "Lock limit at {amount}",
      cardFrozen: "Card frozen",
      analyzing: "Analyzing",
      aiAnalysis: "AI Analysis",
      limitLabel: "Monthly spending limit (₺)",
      stepUp: "Raise limit by ₺1", stepDown: "Lower limit by ₺1",
      saveLimit: "Save limit",
      monthlyFee: "Monthly fee", salaryRatio: "Share of salary", lastPayment: "Last payment",
      activate: "Activate Card", freeze: "Freeze Card", delete: "Delete Card",
      aiFor: "AI analysis for {name}", aiTitle: "Analyze with AI",
      cardBank: "VIRTUAL CARD", cardActive: "ACTIVE", cardFrozenPill: "FROZEN",
      cardService: "SERVICE", cardLimit: "LIMIT", cardNext: "NEXT",
      usage: "Usage",
      limitWarn: "Limit is below the price. The next charge will be declined.",
      limitUpdated: "Card limit updated.",
      invalidLimit: "Enter a valid limit.",
      capped: "{name} limit locked at {amount}. The higher charge will be declined.",
      reactivated: "{name} card is active again.",
      frozenToast: "{name} card frozen. The next charge will be declined.",
      deleted: "{name} virtual card deleted.",
      undo: "Undo",
      restored: "{name} card restored.",
      demoReset: "Demo reset to the starting state.",
      refreshed: "AI analyses refreshed.",

      riskHigh: "High risk", riskMid: "Medium risk", riskLow: "Low risk",
      profileTitle: "Customer Profile Analysis",
      noCompany: "No subscription to analyze.",
      aiNotRun: "The AI analysis has not run yet. Use the 'Refresh Analysis' button.",
      pickSub: "Choose a subscription",
      report: "Anonymized Account Report",
      lastUpdate: "Last update: {when}", analyzingDots: "analyzing…",
      churn: "Churn Risk", estimated: "estimated",
      fee: "Monthly Fee", feeSub: "{p} of salary", hiked: "{p} hike",
      rivals: "Competing Subscriptions", rivalsSub: "in {cat}",
      account: "Account Status", cardLimitSub: "Card limit {amount}",
      revenueRisk: "Revenue at Risk", perMonth: "/ mo", perYear: "{amount} / year",
      churnTipTitle: "How is the churn score calculated?",
      churnTip: "The AI model combines transaction history, payment regularity, other subscriptions in the same category, price, recent price hikes, total subscription load and spending habits into a behaviour profile for each user, and estimates the chance that the subscription will be cancelled (churn). 0–39 is low, 40–64 medium and 65 or more high risk; a frozen card is the strongest signal and an unbroken payment history lowers the risk.",
      explain: "View AI Explanation",
      payHistory: "Payment History, Last 6 Months", payHistoryAria: "{name} payments in the last 6 months",
      actions: "Recommended Actions",
      explainTitle: "AI Risk Explanation",
      explainNotReady: "The AI explanation is not ready yet.",
      aiVerdict: "AI Assessment",
      reportNote: "No identity data is shared with companies; only the anonymous financial behaviour signals below are sent.",
      yes: "Yes", no: "No",

      txTitle: "Transactions",
      aiMade: "AI Generated", txSub: "6 months of synthetic Open Banking data",
      summaryTitle: "Last 6 Months Summary",
      summaryHint: "Tap the sparkle icon in the top right corner to get a personal summary of your last 6 months of spending.",
      summaryBtn: "Create AI spending summary", summaryBtnTitle: "Create AI summary",
      search: "Search descriptions...", txType: "Transaction type",
      monthlySpend: "Monthly Spending (₺), Last 6 Months", monthlySpendAria: "Monthly spending in the last 6 months",
      transactions: "Transactions", txCount: "{n} transactions", txCount_one: "1 transaction",
      colDate: "DATE", colDesc: "DESCRIPTION", colType: "TYPE", colAmount: "AMOUNT",
      noTx: "No matching transactions.",

      agoNow: "just now", agoMin: "{n} min ago", agoHour: "{n} h ago", agoDay: "{n} days ago", agoDay_one: "1 day ago",
    },
    report: {
      anonim_kullanici_id: "Anonymous user ID", hizmet: "Service", kategori: "Category",
      aylik_ucret_tl: "Monthly fee", maasa_orani_yuzde: "Share of salary", fiyat_artisi: "Latest price hike",
      sanal_kart_durumu: "Virtual card status", dondurma_tarihi: "Frozen on",
      sanal_kart_aylik_limiti_tl: "Card limit", limit_ucretin_altinda_mi: "Limit below price",
      kesintisiz_odeme_ay_sayisi: "Months paid in a row", odeme_gecmisi: "Payment history",
      kategorideki_rakip_sayisi: "Competing subscriptions", ayni_kategorideki_diger_abonelikler: "Other subscriptions in category",
      rakip_ortalama_ucret_tl: "Competitors' average fee", kategorinin_en_pahalisi_mi: "Most expensive in category",
      toplam_aktif_abonelik_yuku_tl: "Total active subscription cost",
      toplam_abonelik_yukunun_maasa_orani_yuzde: "Subscription cost as share of salary", genel_harcama_trendi: "Overall spending trend",
    },
  },
};

function detectLang() {
  const fromUrl = new URLSearchParams(location.search).get("lang");
  if (fromUrl in I18N) return fromUrl;
  try {
    const saved = localStorage.getItem("gp_lang");
    if (saved in I18N) return saved;
  } catch { /* gizli pencerede depolama kapalı olabilir */ }
  return (navigator.language || "tr").toLowerCase().startsWith("tr") ? "tr" : "en";
}

let LANG = detectLang();
let L = I18N[LANG];

function setLang(lang) {
  LANG = lang;
  L = I18N[lang];
  try { localStorage.setItem("gp_lang", lang); } catch { /* yoksay */ }
  const url = new URL(location.href);
  url.searchParams.delete("lang");
  history.replaceState(null, "", url);
}

function t(key, vars = {}) {
  // İngilizcede tekil hâl ayrı anahtarla yazılır: "1 card" / "2 cards"
  const one = vars.n === 1 ? L.s[`${key}_one`] : undefined;
  const s = one ?? L.s[key] ?? I18N.tr.s[key] ?? key;
  return s.replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? "");
}
const catName = (c) => L.categories[c] || c;
const statusName = (s) => L.status[s] || s;
const typeName = (s) => L.types[s] || s;
const merchantName = (m) => L.merchants[m] || m;

// Statik HTML'deki data-i18n öğelerini seçili dile çevirir
function applyStaticText() {
  document.documentElement.lang = LANG;
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll("[data-i18n-title]").forEach((el) => { el.title = t(el.dataset.i18nTitle); });
  document.querySelectorAll("[data-i18n-aria]").forEach((el) => { el.setAttribute("aria-label", t(el.dataset.i18nAria)); });
}
