#!/usr/bin/env python3
"""
=============================================================
  HOSE Scraper Bot — Web Dashboard Backend (Flask)
  Run: python3 app.py
  Open: http://localhost:5050
=============================================================
"""

import os
import sys
import json
import threading
import time
from datetime import datetime, date

from flask import Flask, jsonify, render_template, request, send_from_directory
import pandas as pd

# ── Import scraper functions ──────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from main import (
    get_realtime_price, get_price_history, get_company_overview,
    tg_send, tg_send_document, save_csv, build_realtime_report,
    job_realtime, job_history, job_overview,
    WATCHLIST, HISTORY_START, HISTORY_END, OUTPUT_DIR,
)
try:
    from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
except ImportError:
    TELEGRAM_BOT_TOKEN = ""
    TELEGRAM_CHAT_ID = ""

app = Flask(__name__, static_folder="static", template_folder="templates")

# ── In-memory state ──────────────────────────────────────────
_state = {
    "realtime_data": [],
    "last_updated": None,
    "loading": False,
    "logs": [],
    "scheduler_running": False,
    "scheduler_interval": 0,
}
_scheduler_thread = None


def _log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] {msg}"
    _state["logs"].append(entry)
    if len(_state["logs"]) > 200:
        _state["logs"] = _state["logs"][-200:]
    print(entry)


# ── Routes ────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    return jsonify({
        "loading": _state["loading"],
        "last_updated": _state["last_updated"],
        "scheduler_running": _state["scheduler_running"],
        "scheduler_interval": _state["scheduler_interval"],
        "log_count": len(_state["logs"]),
    })


@app.route("/api/realtime")
def api_realtime():
    """Trả về cached data hoặc fetch mới nếu chưa có."""
    if not _state["realtime_data"] and not _state["loading"]:
        _fetch_realtime_bg()
    return jsonify({
        "data": _state["realtime_data"],
        "last_updated": _state["last_updated"],
        "loading": _state["loading"],
    })


@app.route("/api/fetch", methods=["POST"])
def api_fetch():
    """Kích hoạt fetch mới."""
    body = request.get_json(force=True, silent=True) or {}
    symbols = body.get("symbols") or WATCHLIST
    if _state["loading"]:
        return jsonify({"ok": False, "msg": "Đang tải, vui lòng chờ..."})
    _fetch_realtime_bg(symbols)
    return jsonify({"ok": True, "msg": "Đang lấy dữ liệu..."})


@app.route("/api/history/<ticker>")
def api_history(ticker):
    start = request.args.get("start", HISTORY_START)
    end = request.args.get("end", "")
    _log(f"Lấy lịch sử {ticker} từ {start}")
    df = get_price_history(ticker.upper(), start, end)
    if df.empty:
        return jsonify({"ticker": ticker, "rows": []})
    return jsonify({"ticker": ticker, "rows": df.to_dict(orient="records")})


@app.route("/api/overview/<ticker>")
def api_overview(ticker):
    _log(f"Lấy thông tin {ticker}")
    info = get_company_overview(ticker.upper())
    return jsonify(info)


@app.route("/api/telegram/send", methods=["POST"])
def api_tg_send():
    """Gửi báo cáo realtime qua Telegram."""
    if not _state["realtime_data"]:
        return jsonify({"ok": False, "msg": "Chưa có dữ liệu. Hãy fetch trước."})
    df = pd.DataFrame(_state["realtime_data"])
    report = build_realtime_report(df)
    ok = tg_send(report)
    msg = "✅ Đã gửi Telegram!" if ok else "❌ Gửi Telegram thất bại (kiểm tra config.py)"
    _log(msg)
    return jsonify({"ok": ok, "msg": msg})


@app.route("/api/scheduler/start", methods=["POST"])
def api_scheduler_start():
    global _scheduler_thread
    body = request.get_json(force=True, silent=True) or {}
    minutes = int(body.get("minutes", 30))
    if _state["scheduler_running"]:
        return jsonify({"ok": False, "msg": "Scheduler đang chạy rồi."})
    _state["scheduler_interval"] = minutes
    _state["scheduler_running"] = True

    def _loop():
        _log(f"⏰ Scheduler bắt đầu — mỗi {minutes} phút")
        while _state["scheduler_running"]:
            _fetch_realtime_bg()
            for _ in range(minutes * 60):
                if not _state["scheduler_running"]:
                    break
                time.sleep(1)
        _log("⏹ Scheduler đã dừng")

    _scheduler_thread = threading.Thread(target=_loop, daemon=True)
    _scheduler_thread.start()
    return jsonify({"ok": True, "msg": f"Scheduler bắt đầu — mỗi {minutes} phút"})


@app.route("/api/scheduler/stop", methods=["POST"])
def api_scheduler_stop():
    _state["scheduler_running"] = False
    _state["scheduler_interval"] = 0
    _log("⏹ Dừng scheduler")
    return jsonify({"ok": True, "msg": "Đã dừng scheduler"})


@app.route("/api/logs")
def api_logs():
    n = int(request.args.get("n", 50))
    return jsonify({"logs": _state["logs"][-n:]})


@app.route("/api/config", methods=["GET"])
def api_config():
    return jsonify({
        "watchlist": WATCHLIST,
        "history_start": HISTORY_START,
        "history_end": HISTORY_END or str(date.today()),
        "output_dir": OUTPUT_DIR,
        "telegram_configured": bool(TELEGRAM_BOT_TOKEN and TELEGRAM_BOT_TOKEN != "YOUR_BOT_TOKEN_HERE"),
    })


@app.route("/data/<path:filename>")
def serve_data(filename):
    data_dir = os.path.join(os.path.dirname(__file__), OUTPUT_DIR)
    return send_from_directory(data_dir, filename)


# ── Background fetch ──────────────────────────────────────────
def _fetch_realtime_bg(symbols=None):
    if symbols is None:
        symbols = WATCHLIST
    _state["loading"] = True
    _log(f"📡 Đang lấy {len(symbols)} mã...")

    def _work():
        try:
            df = get_realtime_price(symbols)
            if not df.empty:
                _state["realtime_data"] = df.to_dict(orient="records")
                _state["last_updated"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                _log(f"✅ Cập nhật {len(df)} mã thành công")
                # Auto-save CSV
                fname = f"realtime_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
                save_csv(df, fname)
            else:
                _log("⚠️ Không lấy được dữ liệu")
        except Exception as e:
            _log(f"❌ Lỗi: {e}")
        finally:
            _state["loading"] = False

    t = threading.Thread(target=_work, daemon=True)
    t.start()


# ── Main ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print("═" * 55)
    print("🇻🇳  HOSE SCRAPER DASHBOARD")
    print("   http://localhost:5050")
    print("═" * 55)
    # Pre-fetch on startup
    _fetch_realtime_bg()
    app.run(host="0.0.0.0", port=5050, debug=False)
