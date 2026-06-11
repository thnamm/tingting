# ============================================================
#  HOSE Scraper — Cấu hình
#  Điền thông tin Telegram Bot của bạn vào đây
# ============================================================

# --- Telegram ---
# Lấy token từ @BotFather trên Telegram
TELEGRAM_BOT_TOKEN = "8958355678:AAFW2CMJtR4f__Ik5BO0Xxb70uAXcIuNAdM"

# Chat ID nhận báo cáo (dùng @userinfobot để lấy ID của bạn)
TELEGRAM_CHAT_ID   = "8549950982"

# --- Danh sách mã cổ phiếu muốn theo dõi (HOSE) ---
# Để trống [] để lấy toàn bộ top cổ phiếu
WATCHLIST = ["VIC", "VHM", "VNM", "HPG", "MWG", "TCB", "VCB", "BID", "CTG", "FPT"]

# --- Lịch sử giá ---
HISTORY_START = "2026-01-01"   # Ngày bắt đầu lấy lịch sử
HISTORY_END   = ""              # Để trống = đến hôm nay

# --- Output ---
OUTPUT_DIR = "data"             # Thư mục lưu CSV
