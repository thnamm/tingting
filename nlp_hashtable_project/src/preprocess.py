# -*- coding: utf-8 -*-
"""
Module tiền xử lý văn bản tiếng Việt cho pipeline NLP + Hashtable.

Các bước:
  1. Làm sạch văn bản (lowercase, loại bỏ ký tự đặc biệt, số, khoảng trắng thừa)
  2. Tách từ tiếng Việt (word segmentation) bằng pyvi (ViTokenizer)
  3. Loại bỏ stopwords tiếng Việt (dùng set/hashtable để tra cứu O(1))
"""

import re
import unicodedata

try:
    # pyrefly: ignore [missing-import]
    from pyvi import ViTokenizer
    _HAS_PYVI = True
except ImportError:
    _HAS_PYVI = False

# Danh sách stopword tiếng Việt cơ bản (có thể mở rộng thêm từ file ngoài).
# Dùng set() -- vốn được cài đặt nội bộ bằng hashtable trong Python -- để
# tra cứu "từ này có phải stopword không" với độ phức tạp trung bình O(1).
VIETNAMESE_STOPWORDS = {
    "và", "là", "của", "có", "trong", "một", "những", "các", "này", "đó",
    "cho", "được", "với", "để", "khi", "đã", "rất", "cũng", "thì", "mà",
    "nên", "vì", "nếu", "nhưng", "hay", "hoặc", "từ", "đến", "về", "ra",
    "vào", "lên", "xuống", "trên", "dưới", "sau", "trước", "giữa", "còn",
    "sẽ", "đang", "bị", "bởi", "do", "tại", "theo", "như", "nào", "gì",
    "ai", "sao", "vậy", "thế", "quá", "lắm", "chỉ", "chưa", "không", "ừ",
    "à", "ạ", "ơi", "nhé", "nha", "thôi", "luôn", "rồi", "mình", "tôi",
    "em", "thầy", "cô", "bạn", "họ", "nó", "ta", "chúng"
}


def clean_text(text: str) -> str:
    """Chuẩn hóa & làm sạch văn bản thô."""
    if not isinstance(text, str):
        return ""
    text = text.strip().lower()
    text = unicodedata.normalize("NFC", text)  # chuẩn hóa Unicode tiếng Việt
    text = re.sub(r"http\S+|www\.\S+", " ", text)          # loại URL
    text = re.sub(r"[0-9]+", " ", text)                     # loại số
    text = re.sub(r"[^\w\sÀ-ỹà-ỹ]", " ", text, flags=re.UNICODE)  # ký tự đặc biệt
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str) -> list:
    """Tách từ tiếng Việt. Dùng pyvi nếu có, ngược lại tách theo khoảng trắng."""
    text = clean_text(text)
    if not text:
        return []
    if _HAS_PYVI:
        segmented = ViTokenizer.tokenize(text)   # ghép từ ghép bằng dấu "_"
        tokens = segmented.split()
    else:
        tokens = text.split()
    return tokens


def remove_stopwords(tokens: list) -> list:
    """Loại bỏ stopword. Tra cứu qua set (hashtable) -> O(1) mỗi từ."""
    return [t for t in tokens if t.replace("_", " ") not in VIETNAMESE_STOPWORDS]


def preprocess(text: str, drop_stopwords: bool = True) -> list:
    """Pipeline tiền xử lý đầy đủ: clean -> tokenize -> (loại stopword)."""
    tokens = tokenize(text)
    if drop_stopwords:
        tokens = remove_stopwords(tokens)
    return tokens


if __name__ == "__main__":
    sample = "Thầy dạy rất nhiệt tình và dễ hiểu, em cảm ơn thầy nhiều ạ!!!"
    print("Gốc      :", sample)
    print("Sau xử lý:", preprocess(sample))
