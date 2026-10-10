# -*- coding: utf-8 -*-
"""
Module trích xuất đặc trưng văn bản, hai hướng để so sánh trong bài NCKH:

  A. FEATURE HASHING (Hashing Trick) -- dựa trên HashTable tự cài đặt (src/hashtable.py)
     -> vector đặc trưng có kích thước CỐ ĐỊNH (n_buckets), bất kể vocab lớn/nhỏ.

  B. TF-IDF truyền thống (dùng sklearn.TfidfVectorizer làm baseline đối chiếu)
     -> vector đặc trưng có kích thước = |vocabulary|, tăng theo dữ liệu.

So sánh (A) và (B) là nội dung thực nghiệm cốt lõi của đề tài.
"""

from typing import List
# pyrefly: ignore [missing-import]
import numpy as np
# pyrefly: ignore [missing-import]
from scipy.sparse import lil_matrix, csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer

from hashtable import HashTable
from preprocess import preprocess


class HashingFeatureExtractor:
    """
    Trích xuất đặc trưng kiểu 'hashing trick':
    mỗi văn bản -> vector đếm tần suất từ, nhưng chỉ số cột được xác định
    bằng hàm băm (qua HashTable tự cài đặt) thay vì tra từ điển vocab.
    """

    def __init__(self, n_buckets: int = 2 ** 14, hash_func: str = "polynomial",
                 drop_stopwords: bool = True):
        self.n_buckets = n_buckets
        self.hash_func = hash_func
        self.drop_stopwords = drop_stopwords
        # Bảng băm dùng để tra "từ" -> "chỉ số cột" (không lưu tần suất ở đây)
        self._index_table = HashTable(n_buckets=n_buckets, hash_func=hash_func)

    def _token_to_col(self, token: str) -> int:
        """Ánh xạ 1 token sang 1 chỉ số cột trong [0, n_buckets)."""
        return self._index_table._hash(token)  # tái sử dụng hàm băm nội bộ

    def fit_transform(self, texts: List[str]) -> csr_matrix:
        return self.transform(texts)  # hashing trick không cần "fit" vocab

    def transform(self, texts: List[str]) -> csr_matrix:
        n_docs = len(texts)
        mat = lil_matrix((n_docs, self.n_buckets), dtype=np.float32)
        for i, text in enumerate(texts):
            tokens = preprocess(text, drop_stopwords=self.drop_stopwords)
            for tok in tokens:
                col = self._token_to_col(tok)
                mat[i, col] += 1.0
        return mat.tocsr()

    def collision_stats(self, texts: List[str]) -> dict:
        """
        Đo mức độ va chạm hash THỰC SỰ xảy ra trên tập văn bản đưa vào:
        với n_buckets đã chọn, có bao nhiêu từ khác nhau bị ánh xạ trùng cột?
        """
        col_to_words = {}
        for text in texts:
            for tok in preprocess(text, drop_stopwords=self.drop_stopwords):
                col = self._token_to_col(tok)
                col_to_words.setdefault(col, set()).add(tok)

        collided_cols = {c: w for c, w in col_to_words.items() if len(w) > 1}
        distinct_words = set()
        for w in col_to_words.values():
            distinct_words |= w

        return {
            "n_buckets": self.n_buckets,
            "distinct_tokens": len(distinct_words),
            "used_columns": len(col_to_words),
            "collided_columns": len(collided_cols),
            "collision_rate_over_used_columns": round(
                len(collided_cols) / len(col_to_words), 4) if col_to_words else 0,
            "example_collisions": list(collided_cols.items())[:5],
        }


def build_tfidf_features(train_texts: List[str], test_texts: List[str],
                          max_features: int = None):
    """Baseline TF-IDF truyền thống để đối chiếu với Feature Hashing."""
    def joined_tokens(t):
        return " ".join(preprocess(t, drop_stopwords=True))

    train_joined = [joined_tokens(t) for t in train_texts]
    test_joined = [joined_tokens(t) for t in test_texts]

    vectorizer = TfidfVectorizer(max_features=max_features)
    X_train = vectorizer.fit_transform(train_joined)
    X_test = vectorizer.transform(test_joined)
    return X_train, X_test, vectorizer


if __name__ == "__main__":
    sample_texts = [
        "Thầy dạy rất nhiệt tình và dễ hiểu",
        "Cơ sở vật chất phòng học quá cũ, cần cải thiện",
        "Giảng viên nhiệt tình, giải thích dễ hiểu",
    ]
    extractor = HashingFeatureExtractor(n_buckets=32)
    X = extractor.transform(sample_texts)
    print("Ma trận đặc trưng (Feature Hashing), shape:", X.shape)
    print("Thống kê va chạm hash:", extractor.collision_stats(sample_texts))
