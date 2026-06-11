#!/usr/bin/env python3
"""
=============================================================
  HOSE Stock Scraper Bot
  Nguồn dữ liệu: Yahoo Finance (yfinance) — hoạt động ổn định

  Tính năng:
    ✅ Giá realtime / snapshot tất cả mã HOSE
    ✅ Lịch sử OHLCV theo ngày
    ✅ Thông tin cơ bản doanh nghiệp (P/E, vốn hóa, ngành...)
    ✅ Gửi báo cáo tóm tắt qua Telegram
    ✅ Lưu CSV

  Cách dùng:
    python3 main.py                  # Chạy tất cả
    python3 main.py --realtime       # Chỉ giá snapshot
    python3 main.py --history        # Chỉ lịch sử OHLCV
    python3 main.py --overview       # Thông tin doanh nghiệp
    python3 main.py --schedule 60    # Lặp mỗi 60 phút
    python3 main.py --ticker VNM     # Chỉ 1 mã cụ thể
=============================================================
"""

import os
import sys
import re
import time
import argparse
import warnings
from datetime import datetime, date

import pandas as pd
import requests
import yfinance as yf

warnings.filterwarnings("ignore")

# ── Import config ──────────────────────────────────────────────
try:
    from config import (
        TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
        WATCHLIST, HISTORY_START, HISTORY_END, OUTPUT_DIR
    )
except ImportError:
    print("❌ Không tìm thấy config.py!")
    sys.exit(1)


# ==============================================================
#  Yahoo Finance suffix helper
# ==============================================================
def to_yf_symbol(ticker: str) -> str:
    """VNM  →  VNM.VN  (HOSE suffix cho Yahoo Finance)"""
    ticker = ticker.upper().strip()
    if not ticker.endswith(".VN"):
        return ticker + ".VN"
    return ticker


def from_yf_symbol(sym: str) -> str:
    """VNM.VN  →  VNM"""
    return sym.replace(".VN", "").replace(".HN", "").upper()


# ==============================================================
#  Telegram
# ==============================================================
def tg_send(text: str, parse_mode: str = "HTML") -> bool:
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("\n[Telegram — chưa cấu hình, in ra terminal]")
        print("─" * 55)
        plain = re.sub(r"<[^>]+>", "", text)
        print(plain)
        print("─" * 55)
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id"                : TELEGRAM_CHAT_ID,
        "text"                   : text,
        "parse_mode"             : parse_mode,
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            print("✅ Đã gửi Telegram")
            return True
        print(f"❌ Telegram lỗi {r.status_code}: {r.text[:200]}")
        return False
    except Exception as e:
        print(f"❌ Gửi Telegram thất bại: {e}")
        return False


def tg_send_document(filepath: str, caption: str = "") -> bool:
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print(f"[Telegram] sẽ gửi file: {filepath}")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    try:
        with open(filepath, "rb") as f:
            r = requests.post(
                url,
                data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption},
                files={"document": f},
                timeout=30,
            )
        if r.status_code == 200:
            print(f"✅ Gửi file: {os.path.basename(filepath)}")
            return True
        print(f"❌ Gửi file lỗi: {r.text[:200]}")
        return False
    except Exception as e:
        print(f"❌ Gửi file thất bại: {e}")
        return False


# ==============================================================
#  Helpers
# ==============================================================
def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def save_csv(df: pd.DataFrame, filename: str) -> str:
    ensure_dir(OUTPUT_DIR)
    filepath = os.path.join(OUTPUT_DIR, filename)
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    print(f"💾 Đã lưu: {filepath}  ({len(df)} dòng)")
    return filepath


def fmt_number(n) -> str:
    try:
        n = float(n)
        if abs(n) >= 1_000_000_000_000:
            return f"{n/1_000_000_000_000:.2f}T"
        if abs(n) >= 1_000_000_000:
            return f"{n/1_000_000_000:.2f}B"
        if abs(n) >= 1_000_000:
            return f"{n/1_000_000:.2f}M"
        if abs(n) >= 1_000:
            return f"{n/1_000:.1f}K"
        return f"{n:,.0f}"
    except Exception:
        return str(n)


# ==============================================================
#  Data Fetchers
# ==============================================================
def get_realtime_price(symbols: list) -> pd.DataFrame:
    """
    Lấy giá snapshot gần nhất của danh sách mã HOSE.
    Trả về DataFrame: ticker, price, open, high, low, volume,
                      change, pct_change, market_cap, currency
    """
    yf_syms = [to_yf_symbol(s) for s in symbols]
    print(f"  📡 Đang lấy {len(yf_syms)} mã từ Yahoo Finance...")

    records = []
    # download tất cả 1 lần cho nhanh (period=1d)
    data = yf.download(
        yf_syms,
        period="2d",
        interval="1d",
        group_by="ticker",
        progress=False,
        threads=True,
    )

    for sym in yf_syms:
        ticker_code = from_yf_symbol(sym)
        try:
            if len(yf_syms) == 1:
                df_t = data
            else:
                df_t = data[sym] if sym in data else pd.DataFrame()

            if df_t is None or df_t.empty:
                continue

            last = df_t.dropna(subset=["Close"]).iloc[-1]
            prev = df_t.dropna(subset=["Close"]).iloc[-2] if len(df_t.dropna(subset=["Close"])) >= 2 else last

            price     = float(last["Close"])
            open_p    = float(last["Open"])
            high      = float(last["High"])
            low       = float(last["Low"])
            vol       = float(last["Volume"])
            prev_close = float(prev["Close"])
            change    = price - prev_close
            pct       = (change / prev_close * 100) if prev_close else 0.0

            records.append({
                "ticker"    : ticker_code,
                "price"     : price,
                "open"      : open_p,
                "high"      : high,
                "low"       : low,
                "volume"    : int(vol),
                "change"    : round(change, 0),
                "pct_change": round(pct, 2),
                "date"      : str(last.name.date()) if hasattr(last.name, "date") else str(last.name)[:10],
            })
        except Exception as e:
            print(f"  ⚠️  {ticker_code}: {e}")

    # Thêm fast_info (market cap) nếu cần
    return pd.DataFrame(records)


def get_price_history(ticker: str, start: str, end: str = "") -> pd.DataFrame:
    """Lấy lịch sử OHLCV theo ngày."""
    if not end:
        end = date.today().strftime("%Y-%m-%d")
    print(f"  📈 Lịch sử {ticker}: {start} → {end}")
    try:
        t = yf.Ticker(to_yf_symbol(ticker))
        df = t.history(start=start, end=end, interval="1d")
        if df.empty:
            return pd.DataFrame()
        df = df.reset_index()
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]
        df["ticker"] = ticker
        df["date"] = df["date"].astype(str).str[:10]
        keep = [c for c in ["date", "ticker", "open", "high", "low", "close", "volume"]
                if c in df.columns]
        return df[keep].dropna(subset=["close"])
    except Exception as e:
        print(f"  ⚠️  Lịch sử {ticker}: {e}")
        return pd.DataFrame()


def get_company_overview(ticker: str) -> dict:
    """Lấy thông tin cơ bản doanh nghiệp từ Yahoo Finance."""
    try:
        t = yf.Ticker(to_yf_symbol(ticker))
        info = t.info or {}
        return {
            "ticker"          : ticker,
            "company_name"    : info.get("longName") or info.get("shortName", ticker),
            "sector"          : info.get("sector", "N/A"),
            "industry"        : info.get("industry", "N/A"),
            "market_cap"      : info.get("marketCap", "N/A"),
            "pe_ratio"        : info.get("trailingPE", "N/A"),
            "eps"             : info.get("trailingEps", "N/A"),
            "dividend_yield"  : info.get("dividendYield", "N/A"),
            "52w_high"        : info.get("fiftyTwoWeekHigh", "N/A"),
            "52w_low"         : info.get("fiftyTwoWeekLow", "N/A"),
            "avg_volume"      : info.get("averageVolume", "N/A"),
            "currency"        : info.get("currency", "VND"),
            "exchange"        : info.get("exchange", "HOSE"),
            "employees"       : info.get("fullTimeEmployees", "N/A"),
            "website"         : info.get("website", "N/A"),
            "description"     : (info.get("longBusinessSummary", "") or "")[:200],
        }
    except Exception as e:
        print(f"  ⚠️  Overview {ticker}: {e}")
        return {"ticker": ticker}


# ==============================================================
#  Report Builders
# ==============================================================
def build_realtime_report(df: pd.DataFrame, top_n: int = 10) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    total = len(df)
    up    = len(df[df["pct_change"] > 0]) if "pct_change" in df.columns else 0
    dn    = len(df[df["pct_change"] < 0]) if "pct_change" in df.columns else 0
    flat  = total - up - dn

    lines = [
        f"📊 <b>Báo cáo HOSE — {now}</b>",
        f"Tổng: <b>{total}</b> mã  |  🟢{up}  🔴{dn}  ⬜{flat}\n",
    ]

    if "pct_change" in df.columns:
        df = df.copy()
        df["pct_change"] = pd.to_numeric(df["pct_change"], errors="coerce")

        top_up = df.nlargest(top_n, "pct_change")
        lines.append("🟢 <b>Top tăng:</b>")
        for _, row in top_up.iterrows():
            pct = float(row.get("pct_change", 0) or 0)
            lines.append(
                f"  <code>{str(row.get('ticker','')).ljust(6)}</code>"
                f" <b>{fmt_number(row.get('price', 0))}</b> đ"
                f" (+{pct:.2f}%)"
                f" Vol:{fmt_number(row.get('volume', 0))}"
            )

        top_dn = df.nsmallest(top_n, "pct_change")
        lines.append("\n🔴 <b>Top giảm:</b>")
        for _, row in top_dn.iterrows():
            pct = float(row.get("pct_change", 0) or 0)
            lines.append(
                f"  <code>{str(row.get('ticker','')).ljust(6)}</code>"
                f" <b>{fmt_number(row.get('price', 0))}</b> đ"
                f" ({pct:.2f}%)"
                f" Vol:{fmt_number(row.get('volume', 0))}"
            )

    # Watchlist
    if WATCHLIST and "ticker" in df.columns:
        wl = df[df["ticker"].isin(WATCHLIST)]
        if not wl.empty:
            lines.append("\n⭐ <b>Watchlist của bạn:</b>")
            for _, row in wl.iterrows():
                pct  = float(row.get("pct_change", 0) or 0)
                sign = "🟢" if pct >= 0 else "🔴"
                lines.append(
                    f"  {sign} <code>{str(row.get('ticker','')).ljust(6)}</code>"
                    f" <b>{fmt_number(row.get('price', 0))}</b> đ"
                    f" ({pct:+.2f}%)"
                    f" | H:{fmt_number(row.get('high',0))}"
                    f" L:{fmt_number(row.get('low',0))}"
                )

    return "\n".join(lines)


# ==============================================================
#  Jobs
# ==============================================================
def job_realtime(symbols: list = None):
    print("\n" + "═"*55)
    print("🚀 JOB: Giá Snapshot")
    print("═"*55)

    if symbols is None:
        symbols = WATCHLIST or [
            "VIC","VHM","VNM","HPG","MWG","TCB","VCB","BID","CTG","FPT",
            "SSI","VND","HDB","ACB","STB","MBB","VPB","NVL","GVR","PLX",
        ]

    df = get_realtime_price(symbols)
    if df.empty:
        print("❌ Không lấy được dữ liệu")
        return

    fname = f"realtime_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    fpath = save_csv(df, fname)

    report = build_realtime_report(df)
    tg_send(report)
    tg_send_document(fpath, caption=f"📎 Dữ liệu đầy đủ: {fname}")

    print("\n" + df.to_string(index=False))


def job_history(symbols: list = None):
    print("\n" + "═"*55)
    print("🚀 JOB: Lịch sử giá OHLCV")
    print("═"*55)

    if symbols is None:
        symbols = WATCHLIST or ["VNM","VCB","HPG","TCB","FPT"]

    all_frames = []
    for sym in symbols:
        df = get_price_history(sym, HISTORY_START, HISTORY_END)
        if not df.empty:
            all_frames.append(df)
            save_csv(df, f"history_{sym}.csv")

    if all_frames:
        combined = pd.concat(all_frames, ignore_index=True)
        fpath = save_csv(combined, f"history_all_{datetime.now().strftime('%Y%m%d')}.csv")
        msg = (
            f"📈 <b>Lịch sử giá HOSE</b>\n"
            f"Mã: <code>{', '.join(symbols)}</code>\n"
            f"Từ: <b>{HISTORY_START}</b> → <b>{HISTORY_END or date.today()}</b>\n"
            f"Tổng: <b>{len(combined)}</b> bản ghi"
        )
        tg_send(msg)
        tg_send_document(fpath, caption="📎 Lịch sử giá tổng hợp")
        print(f"\n✅ Tổng {len(combined)} dòng lịch sử")


def job_overview(symbols: list = None):
    print("\n" + "═"*55)
    print("🚀 JOB: Thông tin doanh nghiệp")
    print("═"*55)

    if symbols is None:
        symbols = WATCHLIST or ["VNM","VCB","HPG","TCB","FPT"]

    records = []
    for sym in symbols:
        info = get_company_overview(sym)
        records.append(info)
        print(f"  ✅ {sym}: {info.get('company_name','')}")

    df = pd.DataFrame(records)
    fpath = save_csv(df, f"overview_{datetime.now().strftime('%Y%m%d')}.csv")

    lines = ["🏢 <b>Thông tin doanh nghiệp HOSE</b>\n"]
    for rec in records:
        pe   = rec.get("pe_ratio", "N/A")
        mcap = rec.get("market_cap", "N/A")
        div  = rec.get("dividend_yield", "N/A")
        name = rec.get("company_name", rec["ticker"])
        try:
            div_pct = f"{float(div)*100:.2f}%" if div != "N/A" else "N/A"
        except Exception:
            div_pct = str(div)
        lines.append(
            f"<code>{str(rec['ticker']).ljust(6)}</code> {name}\n"
            f"   P/E: {pe} | Vốn hóa: {fmt_number(mcap) if mcap != 'N/A' else 'N/A'}"
            f" | Div: {div_pct}\n"
            f"   Ngành: {rec.get('sector','N/A')}\n"
        )
    tg_send("\n".join(lines))
    tg_send_document(fpath, caption="📎 Thông tin doanh nghiệp")


# ==============================================================
#  Entry point
# ==============================================================
def main():
    parser = argparse.ArgumentParser(description="HOSE Scraper Bot — Yahoo Finance")
    parser.add_argument("--realtime", action="store_true", help="Lấy giá snapshot")
    parser.add_argument("--history",  action="store_true", help="Lấy lịch sử OHLCV")
    parser.add_argument("--overview", action="store_true", help="Thông tin doanh nghiệp")
    parser.add_argument("--all",      action="store_true", help="Chạy tất cả jobs")
    parser.add_argument("--schedule", type=int, default=0,
                        metavar="PHUT", help="Lặp lại mỗi N phút (0 = 1 lần)")
    parser.add_argument("--ticker",   type=str, default="",
                        help="Chỉ lấy 1 mã (vd: VNM)")
    args = parser.parse_args()

    symbols = None
    if args.ticker:
        symbols = [args.ticker.upper()]

    run_all = args.all or not (args.realtime or args.history or args.overview)

    print("═" * 55)
    print("🇻🇳  HOSE SCRAPER BOT  —  Yahoo Finance  🇻🇳")
    print("═" * 55)

    def run_jobs():
        if run_all or args.realtime:
            job_realtime(symbols)
        if run_all or args.history:
            job_history(symbols)
        if run_all or args.overview:
            job_overview(symbols)
        print(f"\n✅ Hoàn thành: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    if args.schedule > 0:
        print(f"⏰ Chế độ tự động: mỗi {args.schedule} phút\n")
        while True:
            run_jobs()
            print(f"\n💤 Chờ {args.schedule} phút... (Ctrl+C để dừng)")
            time.sleep(args.schedule * 60)
    else:
        run_jobs()


if __name__ == "__main__":
    main()
