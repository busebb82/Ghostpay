const CAT_COLORS = {
  "Video": "var(--c-video)",
  "Müzik": "var(--c-muzik)",
  "Üretkenlik": "var(--c-uretkenlik)",
  "Yapay Zekâ": "var(--c-ai)",
};
const MONTHS_LONG = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
  "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];
const MONTHS_SHORT = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"];
const VIEW_TITLES = { b2c: "Müşteri Paneli", b2b: "Şirket Paneli", islemler: "İşlem Geçmişi" };

const ICON = {
  snow: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2v20M4.9 6l14.2 12M19.1 6L4.9 18M9 3.5l3 2.5 3-2.5M9 20.5l3-2.5 3 2.5"/></svg>',
  play: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 5l11 7-11 7z"/></svg>',
  trash: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/></svg>',
  spark: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 3l1.8 5.2L17 10l-5.2 1.8L10 17l-1.8-5.2L3 10l5.2-1.8zM18 14l.9 2.1L21 17l-2.1.9L18 20l-.9-2.1L15 17l2.1-.9z"/></svg>',
  check: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>',
  info: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/></svg>',
  shield: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3l7 3v5c0 4.5-3 8.3-7 10-4-1.7-7-5.5-7-10V6z"/></svg>',
  search: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>',
  list: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01"/></svg>',
  down: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M17 7L7 17M7 9v8h8"/></svg>',
  up: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 17L17 7M9 7h8v8"/></svg>',
  trend: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 17l6-6 4 4 8-8M15 7h6v6"/></svg>',
  lock: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>',
};

const ui = {
  state: null,
  view: "b2c",
  category: null,
  company: null,
  aiBusy: new Set(),
  aiErrors: {},
  summaryBusy: false,
  txFilter: "Tümü",
  txQuery: "",
  pollTimer: null,
};

const $main = document.getElementById("main");

const esc = (s) => String(s ?? "").replace(/[&<>"']/g,
  (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const tl = (n) => Number(n).toLocaleString("tr-TR",
  { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " ₺";
const tlInt = (n) => Math.round(n).toLocaleString("tr-TR") + " ₺";
const pct = (n, d = 1) => Number(Number(n).toFixed(d)).toString();
const money = (n) => `<span class="money">${tl(n)}</span>`;

function parseDate(iso) {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d);
}
const dmy = (iso) => {
  const d = parseDate(iso);
  return `${String(d.getDate()).padStart(2, "0")}.${String(d.getMonth() + 1).padStart(2, "0")}.${d.getFullYear()}`;
};
const longDate = (iso) => {
  const d = parseDate(iso);
  return `${d.getDate()} ${MONTHS_LONG[d.getMonth()]} ${d.getFullYear()}`;
};
const monthYear = (iso) => {
  const d = parseDate(iso);
  return `${MONTHS_LONG[d.getMonth()]} ${d.getFullYear()}`;
};
function longDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return `${d.getDate()} ${MONTHS_LONG[d.getMonth()]} ${d.getFullYear()}, `
    + `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}
function ago(iso) {
  if (!iso) return "";
  const min = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (min < 1) return "az önce";
  if (min < 60) return `${min} dk önce`;
  const h = Math.floor(min / 60);
  return h < 24 ? `${h} sa önce` : `${Math.floor(h / 24)} gün önce`;
}
const limitText = (n) => String(n).replace(".", ",");
function parseAmount(text) {
  let t = String(text).trim();
  if (t.includes(",")) t = t.replace(/\./g, "").replace(",", ".");
  return /^\d+(\.\d+)?$/.test(t) ? parseFloat(t) : NaN;
}

function toast(message, { error = false, action = null, duration = 3800 } = {}) {
  const el = document.getElementById("toast");
  el.innerHTML = `<span>${esc(message)}</span>`
    + (action ? `<button class="toast-action" type="button">${esc(action.label)}</button>` : "");
  el.className = "toast show" + (error ? " err" : "");
  if (action) {
    el.querySelector(".toast-action").onclick = () => {
      el.className = "toast";
      action.run();
    };
  }
  clearTimeout(el._timer);
  el._timer = setTimeout(() => (el.className = "toast"), duration);
}
const toastError = (message) => toast(message, { error: true });

async function api(method, url, body) {
  const res = await fetch(url, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.hata || "Sunucu hatası.");
  return data;
}

const subs = () => ui.state.abonelikler;
const salary = () => ui.state.maas;
const isFrozen = (s) => s.durum === "Donduruldu";
// Kartın bu ay izin vereceği en yüksek çekim
const effective = (s) => Math.min(s.fiyat, s.limit);
const churnOf = (s) => ui.state.churn[s.id] || { churn_risk: 0 };
const hikeOpen = (s) => s.zam && !isFrozen(s) && s.limit > s.zam.eski_fiyat;

function riskLevel(score) {
  if (score >= 70) return { cls: "yuksek", text: "Yüksek risk" };
  if (score >= 45) return { cls: "orta", text: "Orta risk" };
  return { cls: "dusuk", text: "Düşük risk" };
}

function categoryStats() {
  return ui.state.kategoriler.map((name) => {
    const items = subs().filter((s) => s.kategori === name);
    return {
      name, items,
      total: items.reduce((a, s) => a + effective(s), 0),
      limit: items.reduce((a, s) => a + s.limit, 0),
      used: items.filter((s) => !isFrozen(s)).reduce((a, s) => a + s.fiyat, 0),
    };
  }).filter((c) => c.items.length);
}

function donutSvg(cats) {
  const total = cats.reduce((a, c) => a + c.total, 0) || 1;
  const r = 60, C = 2 * Math.PI * r, gap = cats.length > 1 ? 3 : 0;
  let offset = 0;
  const segs = cats.map((c) => {
    const len = (c.total / total) * C;
    const seg = `<circle cx="80" cy="80" r="${r}" fill="none" stroke="${CAT_COLORS[c.name] || "#888"}"
      stroke-width="26" stroke-dasharray="${Math.max(0, len - gap)} ${C}" stroke-dashoffset="${-offset}"
      transform="rotate(-90 80 80)"><title>${esc(c.name)}: ${tl(c.total)}</title></circle>`;
    offset += len;
    return seg;
  }).join("");
  return `<svg class="donut" viewBox="0 0 160 160" role="img" aria-label="Kategorilere göre aylık maliyet">
    <circle cx="80" cy="80" r="${r}" fill="none" stroke="#23232f" stroke-width="26"/>${segs}
    <circle cx="80" cy="80" r="44" fill="#14141c"/></svg>`;
}

function ringSvg(score) {
  const r = 58, C = 2 * Math.PI * r, len = (score / 100) * C;
  return `<svg viewBox="0 0 150 150" width="150" height="150" aria-hidden="true">
    <circle cx="75" cy="75" r="${r}" fill="none" stroke="#2c2c38" stroke-width="18"/>
    <circle cx="75" cy="75" r="${r}" fill="none" stroke="#9d8cf2" stroke-width="18" stroke-linecap="round"
      stroke-dasharray="${len} ${C}" transform="rotate(-90 75 75)"/>
    <circle cx="75" cy="75" r="44" fill="#15151d"/></svg>`;
}

function areaSvg(points, { width = 900, height = 190, yTicks = false, label = "" } = {}) {
  const W = width, H = height, padL = yTicks ? 58 : 8, padR = 8, padT = 12, padB = 24;
  const max = Math.max(...points.map((p) => p.value), 1);
  const yMax = yTicks ? max * 4 / 3 : max * 1.35;
  const x = (i) => padL + (i * (W - padL - padR)) / Math.max(1, points.length - 1);
  const y = (v) => padT + (1 - v / yMax) * (H - padT - padB);
  const line = points.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.value).toFixed(1)}`).join(" ");
  const area = `${line} L${x(points.length - 1)},${H - padB} L${x(0)},${H - padB} Z`;

  let grid = "";
  if (yTicks) {
    for (let k = 0; k <= 4; k++) {
      const v = (yMax * k) / 4, yy = y(v);
      grid += `<line x1="${padL}" x2="${W - padR}" y1="${yy}" y2="${yy}" stroke="#262634" stroke-dasharray="3 4"/>
        <text class="axis-text" x="${padL - 8}" y="${yy + 3}" text-anchor="end">${tlInt(v)}</text>`;
    }
  }
  const labels = points.map((p, i) => `<text class="axis-text" x="${x(i)}" y="${H - 6}"
    text-anchor="${i === 0 ? "start" : i === points.length - 1 ? "end" : "middle"}">${p.label}</text>`).join("");
  const dots = points.map((p, i) => `<circle class="dot" cx="${x(i)}" cy="${y(p.value)}" r="4">
    <title>${p.label}: ${tl(p.value)}</title></circle>`).join("");

  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(label)}">
    <defs><linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#7c6be0" stop-opacity=".75"/>
      <stop offset="1" stop-color="#4b3f9a" stop-opacity=".12"/></linearGradient></defs>
    ${grid}<path d="${area}" fill="url(#areaGrad)"/>
    <path d="${line}" fill="none" stroke="#a594f9" stroke-width="2" vector-effect="non-scaling-stroke"/>
    ${labels}${dots}</svg>`;
}

const resetButton = () => `<button class="btn activate" data-action="reset-demo">Demoyu Sıfırla</button>`;
const pageHead = (title) => `<div class="page-head"><h1>${title}</h1><div class="today">${longDate(ui.state.bugun)}</div></div>`;

function renderB2C() {
  const cats = categoryStats();
  if (!cats.find((c) => c.name === ui.category)) ui.category = cats[0]?.name ?? null;

  const active = subs().filter((s) => !isFrozen(s));
  const frozen = subs().filter(isFrozen);
  const used = cats.reduce((a, c) => a + c.used, 0);
  const limitTotal = cats.reduce((a, c) => a + c.limit, 0);
  const savings = frozen.reduce((a, s) => a + s.fiyat, 0);
  const monthlyTotal = cats.reduce((a, c) => a + c.total, 0);
  const donutTotal = monthlyTotal || 1;
  const filled = limitTotal ? Math.round(Math.min(1, used / limitTotal) * 60) : 0;
  const hikes = subs().filter(hikeOpen);

  const legend = (c) => c ? `<div class="legend-item">
      <div class="name"><i class="dot" style="background:${CAT_COLORS[c.name]}"></i>${esc(c.name)}</div>
      <div class="amount">${money(c.total)} <span>· ${pct((100 * c.total) / donutTotal)}%</span></div>
    </div>` : "";

  const selected = cats.find((c) => c.name === ui.category);
  const kpi = (label, value, sub) => `<div class="panel kpi"><div class="label">${label}</div>
    <div class="value">${value}</div><div class="sub">${sub}</div></div>`;

  $main.innerHTML = `
    ${pageHead("Tekrar Hoş Geldin!")}

    <div class="kpis">
      ${kpi("Aylık Net Maaş", money(salary()), "Her ayın 1'inde yatıyor")}
      ${kpi("Bu Ay Abonelik", money(used), `${active.length} aktif sanal kart`)}
      ${kpi("Maaşa Oranı", `%${pct((100 * used) / salary())}`, "Abonelik giderinin gelire oranı")}
      ${kpi("Aylık Tasarruf", money(savings), `${frozen.length} dondurulmuş kart`)}
    </div>

    ${hikes.length ? `<div class="alert" role="note">
      <span class="alert-icon">${ICON.trend}</span>
      <div class="alert-text"><b>${hikes.length} abonelikte zam tespit edildi.</b>
        ${hikes.map((s) => `${esc(s.ad)} %${pct(s.zam.oran_yuzde)}`).join(" · ")}</div>
      <button class="btn small" data-action="go-hike" data-id="${hikes[0].id}">İncele</button>
    </div>` : ""}

    <div class="grid-2">
      <div class="panel donut-panel">
        <div class="label plain">Aylık Maliyet Dağılımı</div>
        <div class="legend-col">${legend(cats[0])}${legend(cats[1])}</div>
        ${donutSvg(cats)}
        <div class="legend-col right">${legend(cats[2])}${legend(cats[3])}</div>
      </div>
      <div class="panel">
        <div class="label plain">Aylık Abonelik Limiti</div>
        <div class="limit-total">${money(limitTotal)}</div>
        <div class="ticks" role="img" aria-label="Limitin %${pct(limitTotal ? (100 * used) / limitTotal : 0, 0)} kısmı kullanıldı">
          ${Array.from({ length: 60 }, (_, i) => `<i class="${i < filled ? "on" : ""}"></i>`).join("")}</div>
        <div class="limit-meta"><span>Kullanılan: <b>${money(used)}</b></span><span>Kalan: <b>${money(Math.max(0, limitTotal - used))}</b></span></div>
        ${cats.map((c) => `<div class="cat-row">
          <div class="top"><span class="n"><i style="background:${CAT_COLORS[c.name]}"></i>${esc(c.name)}</span>
            <span class="v">${money(c.used)} / ${money(c.limit)}</span></div>
          <div class="bar"><div style="width:${c.limit ? Math.min(100, (100 * c.used) / c.limit) : 0}%;background:${CAT_COLORS[c.name]}"></div></div>
        </div>`).join("")}
      </div>
    </div>

    <div class="subs-layout">
      <div class="stack-col">
        <div class="stack" role="tablist" aria-label="Kategoriler">
          ${cats.map((c) => `<button class="stack-item ${c.name === ui.category ? "selected" : ""}" role="tab"
              aria-selected="${c.name === ui.category}" data-action="category" data-cat="${esc(c.name)}">
            <span class="nm">${esc(c.name)}</span><span class="am">${money(c.total)}</span><span class="ct">${c.items.length} kart</span>
          </button>`).join("")}
        </div>
        <div class="total-card">
          <div><div class="t">TOPLAM HARCAMA</div><div class="s">son 6 ay</div></div>
          <div class="v">${tl(6 * monthlyTotal)}</div>
        </div>
      </div>
      <div>
        ${selected ? `<h2 class="subs-title">${esc(selected.name)} Abonelikleri</h2>
          ${selected.items.map(subPanel).join("")}`
          : `<div class="panel empty">Tespit edilen abonelik kalmadı.<br>${resetButton()}</div>`}
      </div>
    </div>`;
}

function hikeHtml(s) {
  if (!s.zam) return "";
  const z = s.zam;
  const capped = s.limit <= z.eski_fiyat;
  return `<div class="hike ${capped ? "capped" : ""}">
    <div class="hike-text">
      <b>${ICON.trend} %${pct(z.oran_yuzde)} zam</b>
      <span>${monthYear(z.tarih)} itibarıyla ${money(z.eski_fiyat)} → ${money(z.yeni_fiyat)}</span>
    </div>
    ${capped
      ? `<span class="hike-state">${ICON.lock}Limit eski fiyatta</span>`
      : isFrozen(s) ? ""
      : `<button class="btn small" data-action="cap-limit">${ICON.lock}Limiti ${tl(z.eski_fiyat)}'ye sabitle</button>`}
  </div>`;
}

function subPanel(s) {
  const frozen = isFrozen(s);
  const churn = churnOf(s);
  const risk = frozen ? { cls: "yuksek", text: "Kart dondurulmuş" } : riskLevel(churn.churn_risk);
  const ai = ui.state.kullanici_ai[s.id];
  const busy = ui.aiBusy.has(s.id);
  const err = ui.aiErrors[s.id];

  let aiHtml = "";
  if (busy) {
    aiHtml = `<div class="skeleton" aria-label="Analiz ediliyor"><i class="big"></i><i style="width:60%"></i><i style="width:92%"></i><i style="width:78%"></i></div>`;
  } else if (err) {
    aiHtml = `<div class="ai-error">${esc(err)}</div>`;
  } else if (ai) {
    aiHtml = `<div class="ai-out">
      <div class="ai-lead">${esc(ai.ozet)}</div>
      <div class="ai-box"><div class="head"><span class="label">AI Analizi</span><span class="when" data-ago="${esc(ai.zaman)}">${ago(ai.zaman)}</span></div>
        <ul>${ai.maddeler.map((m) => `<li>${esc(m)}</li>`).join("")}</ul></div>
    </div>`;
  }

  return `<article class="sub-panel" data-sub="${s.id}" aria-label="${esc(s.ad)}">
    <span class="status-badge ${frozen ? "frozen" : ""}">${frozen ? "Donduruldu" : "Aktif"}</span>
    <div class="sub-card-col">
      ${cardHtml(s, s.limit)}
      ${usageHtml(s, s.limit)}
      <label class="limit-label" for="limit-${s.id}">Aylık harcama limiti (₺)</label>
      <div class="limit-row">
        <div class="num-input">
          <input id="limit-${s.id}" type="text" inputmode="decimal" autocomplete="off" value="${limitText(s.limit)}" data-limit-input="${s.id}">
          <div class="spin-btns"><button data-action="step" data-step="1" tabindex="-1" aria-label="Limiti 1 ₺ artır">▲</button><button data-action="step" data-step="-1" tabindex="-1" aria-label="Limiti 1 ₺ azalt">▼</button></div>
        </div>
        <button class="save-btn" data-action="save-limit" disabled aria-label="Limiti kaydet" title="Limiti kaydet">${ICON.check}</button>
      </div>
      <div class="warn-slot">${warnHtml(s, s.limit)}</div>
    </div>
    <div class="sub-info-col">
      <h3 class="sub-name"><i class="risk-dot ${risk.cls}" title="${risk.text}"></i>${esc(s.ad)}</h3>
      <div class="sub-cat">${esc(s.kategori)}</div>
      <div class="sub-line">
        <span>Aylık ücret: <b>${money(s.fiyat)}</b></span><span class="sep">·</span>
        <span>Maaşa oranı: <b>%${pct((100 * s.fiyat) / salary(), 2)}</b></span><span class="sep">·</span>
        <span>Son ödeme: <b>${dmy(s.son_odeme)}</b></span>
      </div>
      ${hikeHtml(s)}
      <div class="actions">
        ${frozen
          ? `<button class="btn activate" data-action="status" data-status="Aktif">${ICON.play}Kartı Aktif Et</button>`
          : `<button class="btn" data-action="status" data-status="Donduruldu">${ICON.snow}Kartı Dondur</button>`}
        <button class="btn" data-action="delete">${ICON.trash}Kartı Sil</button>
        <button class="btn icon ${busy ? "busy" : ""}" data-action="ai" aria-label="${esc(s.ad)} için AI analizi" title="AI ile analiz et" ${busy ? "disabled" : ""}>${ICON.spark}</button>
      </div>
      ${aiHtml}
    </div>
  </article>`;
}

function cardHtml(s, limit) {
  const frozen = isFrozen(s);
  return `<div class="vcard ${frozen ? "is-frozen" : ""}" aria-hidden="true">
    <div class="row"><span class="bank"><b>MOKA</b> SANAL KART</span><span class="pill">${frozen ? "DONDURULDU" : "AKTİF"}</span></div>
    <div class="chip-img"></div>
    <div class="num">••••&nbsp; ••••&nbsp; ••••&nbsp; ${s.kart_no}</div>
    <div class="meta">
      <span>SERVİS<b>${esc(s.ad)}</b></span>
      <span>LİMİT<b class="card-limit">${tl(limit)}</b></span>
      <span>SONRAKİ<b>${frozen ? "—" : dmy(s.sonraki_odeme)}</b></span>
    </div>
  </div>`;
}

function usageHtml(s, limit) {
  const usedNow = isFrozen(s) ? 0 : s.fiyat;
  const over = usedNow > limit;
  const w = limit > 0 ? Math.min(100, (100 * usedNow) / limit) : (usedNow ? 100 : 0);
  return `<div class="usage ${over ? "over" : ""}"><div class="top"><span>Kullanım</span><span><b>${tl(usedNow)}</b> / ${tl(limit)}</span></div>
    <div class="bar"><div style="width:${w}%"></div></div></div>`;
}

function warnHtml(s, limit) {
  return limit < s.fiyat
    ? `<div class="limit-warn" role="status">Limit Ücretin Altında: Sonraki çekim reddedilecek.</div>` : "";
}

function onLimitInput(input) {
  const panel = input.closest(".sub-panel");
  const s = subs().find((x) => x.id === panel.dataset.sub);
  const v = parseAmount(input.value);
  const valid = Number.isFinite(v) && v >= 0;
  const shown = valid ? v : s.limit;
  panel.querySelector(".card-limit").textContent = tl(shown);
  panel.querySelector(".usage").outerHTML = usageHtml(s, shown);
  panel.querySelector(".warn-slot").innerHTML = warnHtml(s, shown);
  input.closest(".num-input").classList.toggle("invalid", !valid && input.value.trim() !== "");
  const btn = panel.querySelector(".save-btn");
  const dirty = valid && Math.round(v * 100) !== Math.round(s.limit * 100);
  btn.disabled = !dirty;
  btn.classList.toggle("dirty", dirty);
}

async function saveLimit(subId, value, message = "Kart limiti güncellendi.") {
  try {
    setState(await api("POST", `/api/abonelik/${subId}/limit`, { limit: value }));
    toast(message);
  } catch (e) { toastError(e.message); }
}

function renderB2B() {
  const list = subs();
  if (!list.length) {
    $main.innerHTML = `${pageHead("Müşteri Profil Analizi")}<div class="panel empty">Analiz edilecek abonelik yok.<br>${resetButton()}</div>`;
    return;
  }
  if (!list.find((s) => s.id === ui.company)) ui.company = list[0].id;
  const s = list.find((x) => x.id === ui.company);
  const c = churnOf(s);
  const level = riskLevel(c.churn_risk);
  const rivals = list.filter((x) => x.kategori === s.kategori && x.id !== s.id).length;
  const pendingAi = ui.state.bekleyen.includes(s.id);
  const hasAi = c.kaynak !== "tahmini";

  const months = ui.state.aylar.map(({ yil, ay }) => ({
    label: MONTHS_SHORT[ay - 1],
    value: s.odemeler.filter((o) => {
      const d = parseDate(o.tarih);
      return d.getFullYear() === yil && d.getMonth() + 1 === ay;
    }).reduce((a, o) => a + o.tutar, 0),
  }));

  let actions;
  if (hasAi) {
    actions = c.aksiyonlar.map((a, i) => `<li class="item"><div class="no">${String(i + 1).padStart(2, "0")}</div>
      <div><div class="t">${esc(a.baslik)}</div><div class="d">${esc(a.aciklama)}</div></div></li>`).join("");
    actions = `<ol class="plain-list">${actions}</ol>`;
  } else if (pendingAi) {
    actions = `<div class="skeleton" style="margin-top:14px"><i style="width:30%"></i><i style="width:85%"></i><i style="width:26%;margin-top:18px"></i><i style="width:78%"></i><i style="width:32%;margin-top:18px"></i><i style="width:70%"></i></div>`;
  } else {
    actions = `<div class="ai-error">${esc(c.hata || "AI analizi henüz çalışmadı. 'Analizi Yenile' butonunu kullanın.")}</div>`;
  }

  $main.innerHTML = `
    ${pageHead("Müşteri Profil Analizi")}
    <div class="b2b-bar">
      <select class="select" data-action="company" aria-label="Abonelik seçin">
        ${list.map((x) => `<option value="${x.id}" ${x.id === s.id ? "selected" : ""}>${esc(x.ad)}</option>`).join("")}
      </select>
      <div class="b2b-right">
        <button class="btn outline-accent" data-action="report">${ICON.shield}Anonimleştirilmiş Hesap Raporu</button>
        <span class="updated">Son güncelleme: ${hasAi ? longDateTime(c.zaman) : pendingAi ? "analiz ediliyor…" : "—"}</span>
      </div>
    </div>

    <div class="kpis five">
      <div class="panel kpi"><div class="label">Churn Riski</div><div class="value">%${c.churn_risk}</div><div class="sub">${level.text}${hasAi ? "" : " · tahmini"}</div></div>
      <div class="panel kpi"><div class="label">Aylık Ücret</div><div class="value">${money(s.fiyat)}</div><div class="sub">Maaşa oranı %${pct((100 * s.fiyat) / salary(), 2)}${s.zam ? ` · %${pct(s.zam.oran_yuzde)} zamlı` : ""}</div></div>
      <div class="panel kpi"><div class="label">Kategorideki Rakip Sayısı</div><div class="value">${rivals}</div><div class="sub">${esc(s.kategori)}</div></div>
      <div class="panel kpi"><div class="label">Hesap Durumu</div><div class="chip ${isFrozen(s) ? "" : "aktif"}">${s.durum}</div></div>
      <div class="panel kpi danger"><div class="label">Gelir Kaybı Riski</div><div class="value">${money(s.fiyat)} / ay</div><div class="sub">${tl(12 * s.fiyat)} / yıl</div></div>
    </div>

    <div class="b2b-grid">
      <div class="panel churn-panel">
        <div class="label plain">Churn Riski
          <span class="info" tabindex="0" aria-describedby="churn-tip">${ICON.info}<span class="tooltip" id="churn-tip" role="tooltip"><b>Churn Skoru Nasıl Hesaplanıyor?</b>
            AI modeli; işlem geçmişi, ödeme düzeni, aynı kategorideki diğer abonelikler, abonelik maliyeti,
            son zamlar, toplam abonelik yükü ve harcama alışkanlıklarını birlikte analiz ederek her kullanıcı için bir
            davranış profili oluşturur. Bu profil üzerinden ilgili aboneliğin iptal edilme (churn) olasılığı
            yüzdesel olarak hesaplanır.</span></span>
        </div>
        <div class="ring">${ringSvg(c.churn_risk)}<div class="val">%${c.churn_risk}</div></div>
        <button class="btn small" data-action="explain">${ICON.spark}AI Açıklamasını Gör</button>
      </div>
      <div class="panel chart-panel">
        <div class="label plain">Son 6 Ay Ödeme Geçmişi</div>
        ${areaSvg(months, { width: 760, height: 200, label: `${s.ad} son 6 ay ödemeleri` })}
      </div>
    </div>

    <div class="panel actions-list">
      <div class="label plain">Önerilen Aksiyonlar</div>
      ${actions}
    </div>`;
}

let lastFocus = null;
function openModal(title, bodyHtml, wide = false) {
  lastFocus = document.activeElement;
  document.getElementById("modal-root").innerHTML = `<div class="overlay" data-action="close-modal">
    <div class="modal ${wide ? "wide" : ""}" role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <div class="modal-head"><h3 id="modal-title">${title}</h3><button class="modal-close" data-action="close-modal" aria-label="Kapat">×</button></div>
      ${bodyHtml}
    </div></div>`;
  document.querySelector(".modal-close").focus();
}
function closeModal() {
  const root = document.getElementById("modal-root");
  if (!root.innerHTML) return;
  root.innerHTML = "";
  lastFocus?.focus?.();
}

function openExplain() {
  const s = subs().find((x) => x.id === ui.company);
  const c = churnOf(s);
  let body;
  if (c.kaynak !== "tahmini") {
    body = `<ul>${c.degerlendirme.map((d) => `<li>${esc(d)}</li>`).join("")}</ul>`;
  } else if (ui.state.bekleyen.includes(s.id)) {
    body = `<div class="skeleton"><i></i><i style="width:85%"></i><i style="width:92%"></i><i style="width:70%"></i></div>`;
  } else {
    body = `<div class="ai-error">${esc(c.hata || "AI açıklaması henüz hazır değil.")}</div>`;
  }
  openModal("AI Risk Açıklaması", `
    <div class="risk-box"><div><div class="label">Churn Riski</div><div class="n">${esc(s.ad.toLocaleUpperCase("tr-TR"))}</div></div><div class="v">%${c.churn_risk}</div></div>
    <div class="ai-box flat">
      <div class="head"><span class="label">AI'ın Değerlendirmesi</span><span class="when">${c.kaynak !== "tahmini" ? ago(c.zaman) : ""}</span></div>
      ${body}
    </div>`);
}

async function openReport() {
  try {
    const r = await api("GET", `/api/b2b/${ui.company}/rapor`);
    const fmt = (v) => {
      if (v === null) return "—";
      if (typeof v === "boolean") return v ? "evet" : "hayır";
      if (Array.isArray(v)) return v.map((x) => esc(typeof x === "object" ? Object.values(x).join(" · ") : x)).join("<br>");
      if (typeof v === "object") return Object.entries(v).map(([k, x]) => `${esc(k)}: ${esc(x)}`).join("<br>");
      return esc(v);
    };
    openModal("Anonimleştirilmiş Hesap Raporu", `
      <p class="modal-note">Şirketlere kimlik bilgisi paylaşılmaz; yalnızca aşağıdaki anonim finansal davranış sinyalleri iletilir.</p>
      <div class="kv">${Object.entries(r).map(([k, v]) => `<div class="k">${esc(k)}</div><div class="v">${fmt(v)}</div>`).join("")}</div>`, true);
  } catch (e) { toastError(e.message); }
}

function renderTransactions() {
  const q = ui.txQuery.trim().toLocaleUpperCase("tr-TR");
  const rows = ui.state.islemler.filter((t) =>
    (ui.txFilter === "Tümü" || t.tip === ui.txFilter) &&
    (!q || t.aciklama.toLocaleUpperCase("tr-TR").includes(q)));
  const points = ui.state.aylik_toplamlar.map((m) => ({ label: MONTHS_SHORT[m.ay - 1], value: m.gider }));
  const oz = ui.state.ozet;

  let summary;
  if (ui.summaryBusy) summary = `<div class="skeleton"><i style="width:92%"></i><i style="width:70%"></i></div>`;
  else if (oz && oz.ozet) summary = `<p>${esc(oz.ozet)}</p>`;
  else summary = `<p class="muted">Son 6 aylık harcama davranışının kişisel özetini görmek için sağ üstteki ışıltı simgesine dokun.</p>`;

  const seg = (name, icon) => `<button class="${ui.txFilter === name ? "on" : ""}" data-action="tx-filter" data-filter="${name}" aria-pressed="${ui.txFilter === name}">${icon}${name}</button>`;

  $main.innerHTML = `
    ${pageHead("İşlem Geçmişi")}
    <div class="tx-sub"><span class="ai-badge">${ICON.spark}Yapay Zekâ Üretimi</span>6 aylık sentetik Open Banking simülasyonu</div>

    <div class="panel summary-panel">
      <div class="label plain">Son 6 Ay Özeti</div>
      ${summary}
      <button class="btn icon ${ui.summaryBusy ? "busy" : ""}" data-action="summary" aria-label="AI harcama özeti oluştur" title="AI özeti oluştur" ${ui.summaryBusy ? "disabled" : ""}>${ICON.spark}</button>
    </div>

    <div class="tx-tools">
      <label class="search">${ICON.search}<input type="search" placeholder="Açıklamada ara..." value="${esc(ui.txQuery)}" data-tx-search aria-label="Açıklamada ara"></label>
      <div class="seg" role="group" aria-label="İşlem türü">${seg("Tümü", ICON.list)}${seg("Gelir", ICON.down)}${seg("Gider", ICON.up)}</div>
    </div>

    <div class="panel tx-chart">
      <div class="label plain">Aylık Gider (₺) — Son 6 Ay</div>
      ${areaSvg(points, { width: 1200, height: 230, yTicks: true, label: "Son 6 ay aylık gider" })}
    </div>

    <div class="panel table-wrap">
      <div class="table-head"><span class="label plain">İşlemler</span><span class="count">${rows.length} işlem</span></div>
      <div class="table-scroll">
      <table><thead><tr><th>TARİH</th><th>AÇIKLAMA</th><th class="col-type">TİP</th><th class="amt">TUTAR</th></tr></thead>
      <tbody>${rows.map((t) => `<tr><td>${dmy(t.tarih)}</td><td>${esc(t.aciklama)}</td><td class="col-type">${t.tip}</td>
        <td class="amt ${t.tutar > 0 ? "in" : ""}">${t.tutar > 0 ? "+" : "−"}${tl(Math.abs(t.tutar))}</td></tr>`).join("")
        || `<tr><td colspan="4" class="empty">Eşleşen işlem bulunamadı.</td></tr>`}</tbody></table>
    </div></div>`;
}

function render() {
  document.querySelectorAll(".nav a").forEach((a) => {
    const on = a.dataset.view === ui.view;
    a.classList.toggle("active", on);
    if (on) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });
  document.title = `${VIEW_TITLES[ui.view]} · GhostPay`;
  if (!ui.state) return;
  document.getElementById("mode-badge").hidden = ui.state.ai_modu !== "demo";
  if (ui.view === "b2b") renderB2B();
  else if (ui.view === "islemler") renderTransactions();
  else renderB2C();
}

function setState(state) {
  ui.state = state;
  render();
  schedulePoll();
}

// Claude modunda churn analizleri arka planda sürer; bitene kadar durumu tazele
function schedulePoll() {
  clearTimeout(ui.pollTimer);
  if (!ui.state.bekleyen.length) return;
  ui.pollTimer = setTimeout(async () => {
    try {
      ui.state = await api("GET", "/api/state");
      const editing = document.activeElement?.matches("input, select");
      if (ui.view !== "islemler" && !editing) {
        const y = window.scrollY;
        render();
        window.scrollTo(0, y);
      }
    } catch { /* bir sonraki turda tekrar denenir */ }
    schedulePoll();
  }, 2500);
}

function routeFromHash() {
  const v = location.hash.replace("#", "");
  ui.view = ["b2c", "b2b", "islemler"].includes(v) ? v : "b2c";
  render();
  window.scrollTo(0, 0);
}

async function runAction(el, e) {
  const action = el.dataset.action;
  const panel = el.closest(".sub-panel");
  const id = panel?.dataset.sub;
  const sub = id && subs().find((s) => s.id === id);

  switch (action) {
    case "close-modal":
      if (e.target === el) closeModal();
      return;
    case "category":
      ui.category = el.dataset.cat;
      return render();
    case "go-hike": {
      const target = subs().find((s) => s.id === el.dataset.id);
      ui.category = target.kategori;
      render();
      document.querySelector(`[data-sub="${target.id}"]`)?.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
    case "step": {
      const input = panel.querySelector("[data-limit-input]");
      const v = parseAmount(input.value);
      const next = Math.max(0, Math.round(((Number.isFinite(v) ? v : 0) + Number(el.dataset.step)) * 100) / 100);
      input.value = limitText(next);
      return onLimitInput(input);
    }
    case "save-limit": {
      const v = parseAmount(panel.querySelector("[data-limit-input]").value);
      if (!Number.isFinite(v) || v < 0) return toastError("Geçerli bir limit girin.");
      return saveLimit(id, v);
    }
    case "cap-limit":
      return saveLimit(id, sub.zam.eski_fiyat,
        `${sub.ad} limiti ${tl(sub.zam.eski_fiyat)}'ye sabitlendi. Zamlı çekim reddedilecek.`);
    case "status":
      try {
        setState(await api("POST", `/api/abonelik/${id}/durum`, { durum: el.dataset.status }));
        toast(el.dataset.status === "Aktif" ? `${sub.ad} kartı yeniden aktif.` : `${sub.ad} kartı donduruldu. Sonraki çekim reddedilecek.`);
      } catch (err) { toastError(err.message); }
      return;
    case "delete":
      try {
        setState(await api("DELETE", `/api/abonelik/${id}`));
        toast(`${sub.ad} sanal kartı silindi.`, {
          duration: 6000,
          action: {
            label: "Geri al",
            run: async () => {
              try {
                setState(await api("POST", `/api/abonelik/${id}/geri-al`));
                toast(`${sub.ad} kartı geri yüklendi.`);
              } catch (err) { toastError(err.message); }
            },
          },
        });
      } catch (err) { toastError(err.message); }
      return;
    case "ai":
      ui.aiBusy.add(id);
      delete ui.aiErrors[id];
      render();
      try {
        const fresh = await api("POST", `/api/ai/abonelik/${id}`);
        ui.aiBusy.delete(id);
        setState(fresh);
      } catch (err) {
        ui.aiBusy.delete(id);
        ui.aiErrors[id] = err.message;
        render();
      }
      return;
    case "explain":
      return openExplain();
    case "report":
      return openReport();
    case "tx-filter":
      ui.txFilter = el.dataset.filter;
      return render();
    case "summary":
      ui.summaryBusy = true;
      render();
      try {
        const fresh = await api("POST", "/api/ai/ozet");
        ui.summaryBusy = false;
        setState(fresh);
      } catch (err) {
        ui.summaryBusy = false;
        render();
        toastError(err.message);
      }
      return;
    case "reset-demo":
      try {
        ui.aiErrors = {};
        setState(await api("POST", "/api/demo/sifirla"));
        toast("Demo başlangıç durumuna döndü.");
      } catch (err) { toastError(err.message); }
      return;
    case "reload":
      return location.reload();
    case "refresh":
      el.classList.add("spin");
      ui.aiErrors = {};
      try {
        setState(await api("POST", "/api/ai/yenile"));
        toast("Yapay zekâ analizleri yenilendi.");
      } catch (err) { toastError(err.message); }
      setTimeout(() => el.classList.remove("spin"), 800);
  }
}

document.addEventListener("click", (e) => {
  const el = e.target.closest("[data-action]");
  if (el && el.tagName !== "SELECT") runAction(el, e);
});

document.addEventListener("input", (e) => {
  if (e.target.matches("[data-limit-input]")) onLimitInput(e.target);
  if (e.target.matches("[data-tx-search]")) {
    ui.txQuery = e.target.value;
    const pos = e.target.selectionStart;
    render();
    const input = document.querySelector("[data-tx-search]");
    input.focus();
    input.setSelectionRange(pos, pos);
  }
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeModal();
  if (e.key === "Enter" && e.target.matches("[data-limit-input]")) {
    const btn = e.target.closest(".sub-panel").querySelector(".save-btn");
    if (!btn.disabled) btn.click();
  }
});

document.addEventListener("change", (e) => {
  if (e.target.matches('[data-action="company"]')) {
    ui.company = e.target.value;
    render();
  }
});

setInterval(() => {
  document.querySelectorAll("[data-ago]").forEach((el) => (el.textContent = ago(el.dataset.ago)));
}, 30000);

window.addEventListener("hashchange", routeFromHash);

(async function init() {
  routeFromHash();
  try {
    setState(await api("GET", "/api/state"));
  } catch (e) {
    $main.innerHTML = `<div class="panel empty">Sunucuya bağlanılamadı: ${esc(e.message)}<br>
      <button class="btn activate" data-action="reload">Tekrar dene</button></div>`;
  }
})();
