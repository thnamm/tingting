/* ═══════════════════════════════════════════════
   HOSE Dashboard — Frontend JavaScript
   ═══════════════════════════════════════════════ */

let allData = [];
let sortKey = "pct_change";
let sortAsc = false;
let priceChart = null;
let watchlist = [];
let pollingTimer = null;
let isLoading = false;

// ══════════════════════════════════════════
//  Init
// ══════════════════════════════════════════
document.addEventListener("DOMContentLoaded", () => {
  setupNav();
  loadConfig();
  startPolling();

  // Sidebar toggle
  document.getElementById("sidebar-toggle").addEventListener("click", () => {
    document.getElementById("sidebar").classList.toggle("collapsed");
    document.querySelector(".main").classList.toggle("expanded");
  });
});

function setupNav() {
  document.querySelectorAll(".nav-item").forEach(el => {
    el.addEventListener("click", e => {
      e.preventDefault();
      const page = el.dataset.page;
      navigate(page);
    });
  });
}

function navigate(page) {
  document.querySelectorAll(".nav-item").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".page").forEach(el => el.classList.remove("active"));

  document.getElementById("nav-" + page)?.classList.add("active");
  document.getElementById("page-" + page)?.classList.add("active");

  const titles = {
    dashboard: "Tổng quan",
    stocks: "Bảng giá",
    chart: "Biểu đồ",
    telegram: "Telegram",
    logs: "Log hệ thống",
  };
  document.getElementById("page-title").textContent = titles[page] || page;

  if (page === "logs") refreshLogs();
  if (page === "stocks" && allData.length) renderTable(allData);
}

// ══════════════════════════════════════════
//  Config
// ══════════════════════════════════════════
async function loadConfig() {
  try {
    const cfg = await fetchJSON("/api/config");
    watchlist = cfg.watchlist || [];

    // Populate chart ticker select
    const sel = document.getElementById("chart-ticker");
    watchlist.forEach(t => {
      const opt = document.createElement("option");
      opt.value = t;
      opt.textContent = t;
      sel.appendChild(opt);
    });

    // Telegram config status
    const el = document.getElementById("tg-config-status");
    if (cfg.telegram_configured) {
      el.textContent = "✅ Telegram đã cấu hình";
      el.className = "tg-config-status ok";
    } else {
      el.textContent = "⚠️ Chưa cấu hình Telegram (xem config.py)";
      el.className = "tg-config-status notok";
    }
  } catch (e) {
    console.error("loadConfig:", e);
  }
}

// ══════════════════════════════════════════
//  Polling
// ══════════════════════════════════════════
function startPolling() {
  checkStatus();
  pollingTimer = setInterval(checkStatus, 3000);
}

async function checkStatus() {
  try {
    const s = await fetchJSON("/api/status");
    updateStatusBar(s);
    if (!s.loading && !isLoading) {
      // load data if empty
      const d = await fetchJSON("/api/realtime");
      if (d.data && d.data.length) {
        allData = d.data;
        updateAll(d);
      }
    }
  } catch (_) {}
}

// ══════════════════════════════════════════
//  Fetch / Refresh
// ══════════════════════════════════════════
async function fetchData() {
  if (isLoading) return;
  isLoading = true;
  showLoading(true);
  setRefreshSpin(true);

  try {
    await postJSON("/api/fetch", { symbols: watchlist });
    // poll until done
    await waitUntilNotLoading();
    const d = await fetchJSON("/api/realtime");
    allData = d.data || [];
    updateAll(d);
    toast("✅ Dữ liệu đã cập nhật!");
  } catch (e) {
    toast("❌ Lỗi: " + e.message, "error");
  } finally {
    isLoading = false;
    showLoading(false);
    setRefreshSpin(false);
  }
}

async function waitUntilNotLoading(maxWait = 60000) {
  const start = Date.now();
  while (Date.now() - start < maxWait) {
    const s = await fetchJSON("/api/status");
    if (!s.loading) return;
    await sleep(1000);
  }
}

// ══════════════════════════════════════════
//  Render All
// ══════════════════════════════════════════
function updateAll(d) {
  const data = d.data || [];
  if (!data.length) return;

  const lu = d.last_updated;
  if (lu) document.getElementById("last-updated").textContent = "⏱ " + lu;

  renderStats(data);
  renderMovers(data);
  renderWatchlist(data);
  renderTable(data);

  // glow effect on cards
  document.querySelectorAll(".stat-card").forEach(el => {
    el.classList.remove("glow");
    void el.offsetWidth;
    el.classList.add("glow");
  });
}

// ── Stats ──
function renderStats(data) {
  const up   = data.filter(r => (r.pct_change || 0) > 0).length;
  const down = data.filter(r => (r.pct_change || 0) < 0).length;
  const flat = data.length - up - down;

  document.getElementById("stat-total").textContent = data.length;
  document.getElementById("stat-up").textContent    = up;
  document.getElementById("stat-down").textContent  = down;
  document.getElementById("stat-flat").textContent  = flat;
}

// ── Movers ──
function renderMovers(data) {
  const sorted = [...data].sort((a, b) => (b.pct_change || 0) - (a.pct_change || 0));
  const topUp   = sorted.slice(0, 7);
  const topDown = sorted.slice(-7).reverse();

  document.getElementById("top-up-list").innerHTML   = topUp.map(moverHTML).join("") || '<div class="placeholder">Không có dữ liệu</div>';
  document.getElementById("top-down-list").innerHTML = topDown.map(moverHTML).join("") || '<div class="placeholder">Không có dữ liệu</div>';
}

function moverHTML(r) {
  const pct  = parseFloat(r.pct_change || 0);
  const cls  = pct > 0 ? "up" : pct < 0 ? "down" : "flat";
  const sign = pct > 0 ? "+" : "";
  return `
    <div class="mover-item">
      <span class="mover-ticker">${r.ticker}</span>
      <span class="mover-price">${fmtPrice(r.price)}</span>
      <span class="badge badge-${cls}">${sign}${pct.toFixed(2)}%</span>
    </div>`;
}

// ── Watchlist cards ──
function renderWatchlist(data) {
  const map = {};
  data.forEach(r => map[r.ticker] = r);

  const items = watchlist.map(t => map[t]).filter(Boolean);
  if (!items.length) return;

  document.getElementById("watchlist-cards").innerHTML = items.map(r => {
    const pct = parseFloat(r.pct_change || 0);
    const cls = pct > 0 ? "up" : pct < 0 ? "down" : "flat";
    const sign = pct > 0 ? "+" : "";
    return `
      <div class="wl-card ${cls}" onclick="goChart('${r.ticker}')">
        <div class="wl-ticker">${r.ticker}</div>
        <div class="wl-price">${fmtPrice(r.price)} đ</div>
        <div class="wl-pct ${cls}">${sign}${pct.toFixed(2)}%</div>
      </div>`;
  }).join("");
}

function goChart(ticker) {
  navigate("chart");
  document.getElementById("chart-ticker").value = ticker;
  loadChart();
}

// ══════════════════════════════════════════
//  Table
// ══════════════════════════════════════════
function renderTable(data) {
  const sorted = sortData([...data], sortKey, sortAsc);
  const tbody = document.getElementById("stock-tbody");
  tbody.innerHTML = sorted.map(r => {
    const pct  = parseFloat(r.pct_change || 0);
    const chg  = parseFloat(r.change || 0);
    const cls  = pct > 0 ? "td-up" : pct < 0 ? "td-down" : "td-flat";
    const sign = pct > 0 ? "+" : "";
    const arrow = pct > 0 ? "▲" : pct < 0 ? "▼" : "─";
    return `
      <tr>
        <td class="td-ticker">${r.ticker}</td>
        <td>${fmtPrice(r.price)}</td>
        <td class="${cls}">${arrow} ${fmtPrice(Math.abs(chg))}</td>
        <td class="${cls}"><b>${sign}${pct.toFixed(2)}%</b></td>
        <td>${fmtPrice(r.open)}</td>
        <td class="td-up">${fmtPrice(r.high)}</td>
        <td class="td-down">${fmtPrice(r.low)}</td>
        <td>${fmtVol(r.volume)}</td>
        <td style="color:var(--text-muted)">${r.date || "—"}</td>
        <td><button class="mini-btn" onclick="goChart('${r.ticker}')">📉</button></td>
      </tr>`;
  }).join("");
}

function sortTable(key) {
  if (sortKey === key) sortAsc = !sortAsc;
  else { sortKey = key; sortAsc = false; }
  renderTable(allData);
}

function sortData(arr, key, asc) {
  return arr.sort((a, b) => {
    const va = parseFloat(a[key]) || 0;
    const vb = parseFloat(b[key]) || 0;
    const s  = typeof a[key] === "string" ? a[key].localeCompare(b[key]) : va - vb;
    return asc ? s : -s;
  });
}

function filterTable(q) {
  const query = q.trim().toUpperCase();
  document.querySelectorAll("#stock-tbody tr").forEach(tr => {
    const ticker = tr.querySelector(".td-ticker")?.textContent || "";
    tr.classList.toggle("hidden", query && !ticker.includes(query));
  });
}

// ══════════════════════════════════════════
//  Chart
// ══════════════════════════════════════════
async function loadChart() {
  const ticker = document.getElementById("chart-ticker").value;
  const days   = parseInt(document.getElementById("chart-range").value) || 90;
  if (!ticker) return;

  document.getElementById("chart-empty").style.display = "none";
  document.getElementById("overview-card").style.display = "none";

  // Compute start date
  const startDate = new Date();
  startDate.setDate(startDate.getDate() - days);
  const start = startDate.toISOString().slice(0, 10);

  try {
    const [hist, ov] = await Promise.all([
      fetchJSON(`/api/history/${ticker}?start=${start}`),
      fetchJSON(`/api/overview/${ticker}`),
    ]);

    drawChart(ticker, hist.rows || []);
    renderOverview(ov);
  } catch (e) {
    toast("❌ Lỗi lấy dữ liệu biểu đồ", "error");
  }
}

function drawChart(ticker, rows) {
  const ctx = document.getElementById("price-chart");
  if (priceChart) { priceChart.destroy(); priceChart = null; }
  if (!rows.length) {
    document.getElementById("chart-empty").style.display = "block";
    document.getElementById("chart-empty").textContent = "Không có dữ liệu lịch sử";
    return;
  }

  const labels = rows.map(r => r.date);
  const closes = rows.map(r => parseFloat(r.close));
  const opens  = rows.map(r => parseFloat(r.open));
  const highs  = rows.map(r => parseFloat(r.high));
  const lows   = rows.map(r => parseFloat(r.low));

  const gradient = ctx.getContext("2d").createLinearGradient(0, 0, 0, 380);
  gradient.addColorStop(0, "rgba(59,130,246,0.35)");
  gradient.addColorStop(1, "rgba(59,130,246,0.0)");

  priceChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: `${ticker} — Đóng cửa`,
          data: closes,
          borderColor: "#3b82f6",
          backgroundColor: gradient,
          borderWidth: 2,
          fill: true,
          tension: 0.35,
          pointRadius: 0,
          pointHoverRadius: 5,
          pointHoverBackgroundColor: "#3b82f6",
        },
        {
          label: "Cao nhất",
          data: highs,
          borderColor: "rgba(16,185,129,0.5)",
          borderWidth: 1,
          fill: false,
          tension: 0.35,
          pointRadius: 0,
          borderDash: [4, 4],
        },
        {
          label: "Thấp nhất",
          data: lows,
          borderColor: "rgba(239,68,68,0.4)",
          borderWidth: 1,
          fill: false,
          tension: 0.35,
          pointRadius: 0,
          borderDash: [4, 4],
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          labels: { color: "#64748b", font: { family: "Inter", size: 12 } },
        },
        tooltip: {
          backgroundColor: "#111827",
          borderColor: "rgba(255,255,255,0.1)",
          borderWidth: 1,
          titleColor: "#f1f5f9",
          bodyColor: "#94a3b8",
          callbacks: {
            label: ctx => ` ${ctx.dataset.label}: ${fmtPrice(ctx.parsed.y)}`,
          },
        },
      },
      scales: {
        x: {
          grid: { color: "rgba(255,255,255,0.04)" },
          ticks: { color: "#475569", maxTicksLimit: 10, font: { family: "JetBrains Mono", size: 11 } },
        },
        y: {
          grid: { color: "rgba(255,255,255,0.04)" },
          ticks: {
            color: "#475569",
            font: { family: "JetBrains Mono", size: 11 },
            callback: v => fmtPrice(v),
          },
        },
      },
    },
  });
}

function renderOverview(ov) {
  if (!ov || !ov.ticker) return;
  const fmtMcap = v => (isNaN(v) || v === "N/A") ? "N/A" : fmtBig(parseFloat(v));
  const fmtDivY = v => (isNaN(v) || v === "N/A") ? "N/A" : (parseFloat(v) * 100).toFixed(2) + "%";

  const fields = [
    ["Mã", ov.ticker],
    ["Tên công ty", ov.company_name],
    ["Ngành", ov.sector],
    ["Lĩnh vực", ov.industry],
    ["Vốn hóa", fmtMcap(ov.market_cap)],
    ["P/E", ov.pe_ratio === "N/A" ? "N/A" : parseFloat(ov.pe_ratio).toFixed(2)],
    ["EPS", ov.eps === "N/A" ? "N/A" : parseFloat(ov.eps).toFixed(2)],
    ["Cổ tức", fmtDivY(ov.dividend_yield)],
    ["52W Cao", fmtPrice(ov["52w_high"])],
    ["52W Thấp", fmtPrice(ov["52w_low"])],
    ["KL TB", ov.avg_volume === "N/A" ? "N/A" : fmtVol(ov.avg_volume)],
    ["Website", ov.website !== "N/A" ? `<a href="${ov.website}" target="_blank" style="color:var(--accent)">${ov.website}</a>` : "N/A"],
  ];

  const html = `<div class="overview-grid">${fields.map(([k, v]) =>
    `<div class="ov-item"><span class="ov-label">${k}</span><span class="ov-value">${v || "N/A"}</span></div>`
  ).join("")}</div>`;

  document.getElementById("overview-body").innerHTML = html;
  document.getElementById("overview-card").style.display = "block";
}

// ══════════════════════════════════════════
//  Telegram
// ══════════════════════════════════════════
async function sendTelegram() {
  const btn = document.getElementById("btn-tg-send");
  const res = document.getElementById("tg-result");
  btn.disabled = true;
  btn.textContent = "✈️ Đang gửi...";
  res.className = "tg-result";
  res.style.display = "none";

  try {
    const r = await postJSON("/api/telegram/send", {});
    res.textContent = r.msg;
    res.className = "tg-result show " + (r.ok ? "ok" : "fail");
  } catch (e) {
    res.textContent = "❌ Lỗi kết nối";
    res.className = "tg-result show fail";
  } finally {
    btn.disabled = false;
    btn.textContent = "✈️ Gửi báo cáo ngay";
  }
}

async function startScheduler() {
  const mins = parseInt(document.getElementById("scheduler-minutes").value) || 30;
  const r = await postJSON("/api/scheduler/start", { minutes: mins });
  toast(r.msg);
  document.getElementById("scheduler-status").textContent = `⏰ Đang chạy — mỗi ${mins} phút`;
  document.getElementById("scheduler-status").className = "scheduler-status running";
}

async function stopScheduler() {
  const r = await postJSON("/api/scheduler/stop", {});
  toast(r.msg);
  document.getElementById("scheduler-status").textContent = "Scheduler đã dừng";
  document.getElementById("scheduler-status").className = "scheduler-status";
}

// ══════════════════════════════════════════
//  Logs
// ══════════════════════════════════════════
async function refreshLogs() {
  try {
    const r = await fetchJSON("/api/logs?n=100");
    const el = document.getElementById("log-console");
    el.textContent = (r.logs || []).join("\n") || "(Chưa có log)";
    el.scrollTop = el.scrollHeight;
  } catch (_) {}
}

// ══════════════════════════════════════════
//  Status bar
// ══════════════════════════════════════════
function updateStatusBar(s) {
  const dot  = document.getElementById("status-dot");
  const text = document.getElementById("status-text");
  if (s.loading) {
    dot.className  = "status-dot loading";
    text.textContent = "Đang tải dữ liệu...";
  } else {
    dot.className  = "status-dot online";
    text.textContent = s.scheduler_running
      ? `⏰ Tự động — ${s.scheduler_interval}p`
      : "Kết nối ✓";
  }
}

// ══════════════════════════════════════════
//  UI helpers
// ══════════════════════════════════════════
function showLoading(on) {
  document.getElementById("loading-overlay").classList.toggle("active", on);
}

function setRefreshSpin(on) {
  const icon = document.getElementById("refresh-icon");
  icon.className = on ? "spinning" : "";
  icon.textContent = "🔄";
}

let toastTimer;
function toast(msg, type = "info") {
  clearTimeout(toastTimer);
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.style.borderColor = type === "error" ? "var(--red)" : "var(--border)";
  el.classList.add("show");
  toastTimer = setTimeout(() => el.classList.remove("show"), 3500);
}

// ══════════════════════════════════════════
//  Formatters
// ══════════════════════════════════════════
function fmtPrice(v) {
  const n = parseFloat(v);
  if (isNaN(n)) return "—";
  if (n >= 1000) return n.toLocaleString("vi-VN");
  return n.toFixed(2);
}

function fmtVol(v) {
  const n = parseFloat(v);
  if (isNaN(n)) return "—";
  if (n >= 1e9) return (n / 1e9).toFixed(2) + "B";
  if (n >= 1e6) return (n / 1e6).toFixed(2) + "M";
  if (n >= 1e3) return (n / 1e3).toFixed(1) + "K";
  return n.toLocaleString("vi-VN");
}

function fmtBig(v) {
  if (v >= 1e12) return (v / 1e12).toFixed(2) + " Nghìn tỷ";
  if (v >= 1e9)  return (v / 1e9).toFixed(2)  + " Tỷ";
  if (v >= 1e6)  return (v / 1e6).toFixed(2)  + " Triệu";
  return v.toLocaleString("vi-VN");
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ══════════════════════════════════════════
//  HTTP helpers
// ══════════════════════════════════════════
async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}
