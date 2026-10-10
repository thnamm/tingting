# -*- coding: utf-8 -*-
"""
Cài đặt Hashtable thủ công (từ đầu, không dùng dict có sẵn của Python)
để phục vụ mục đích NGHIÊN CỨU: đo đếm số lượng va chạm (collision),
hệ số tải (load factor), và ảnh hưởng của kích thước bảng băm (n_buckets)
đến hiệu năng trích xuất đặc trưng văn bản.

Kỹ thuật xử lý va chạm: Separate Chaining (mỗi bucket là một list).
Hàm băm: có thể chọn giữa 'builtin' (hash() của Python + salt cố định)
hoặc 'polynomial' (hàm băm đa thức tự cài đặt kiểu Java String.hashCode).
"""

from typing import Any, List, Tuple


class HashTable:
    def __init__(self, n_buckets: int = 2 ** 18, hash_func: str = "polynomial"):
        self.n_buckets = n_buckets
        self.buckets: List[List[Tuple[str, Any]]] = [[] for _ in range(n_buckets)]
        self.hash_func_name = hash_func
        self.size = 0            # số cặp (key, value) đang lưu
        self.collision_count = 0  # số lần một bucket đã có phần tử trước khi insert

    # ---------- Hàm băm ----------
    def _hash(self, key: str) -> int:
        if self.hash_func_name == "polynomial":
            return self._polynomial_hash(key) % self.n_buckets
        else:
            # Dùng hash() built-in của Python (kèm salt cố định để tái lập kết quả)
            return (hash(key) ^ 0x9E3779B9) % self.n_buckets

    @staticmethod
    def _polynomial_hash(key: str, base: int = 131, mod: int = 2 ** 61 - 1) -> int:
        """Hàm băm đa thức: h = sum(c_i * base^i) mod M -- tương tự String.hashCode()."""
        h = 0
        for ch in key:
            h = (h * base + ord(ch)) % mod
        return h

    # ---------- Thao tác cơ bản ----------
    def put(self, key: str, value: Any = None) -> None:
        idx = self._hash(key)
        bucket = self.buckets[idx]
        if bucket:  # bucket đã có ít nhất 1 phần tử -> có khả năng va chạm
            for i, (k, _) in enumerate(bucket):
                if k == key:
                    bucket[i] = (key, value)
                    return
            self.collision_count += 1
        bucket.append((key, value))
        self.size += 1

    def get(self, key: str, default=None):
        idx = self._hash(key)
        for k, v in self.buckets[idx]:
            if k == key:
                return v
        return default

    def contains(self, key: str) -> bool:
        idx = self._hash(key)
        return any(k == key for k, _ in self.buckets[idx])

    def increment(self, key: str, amount: int = 1) -> int:
        """Tăng giá trị đếm cho key (dùng cho đếm tần suất từ)."""
        cur = self.get(key, 0)
        new_val = cur + amount
        self.put(key, new_val)
        return new_val

    # ---------- Thống kê phục vụ phân tích khoa học ----------
    def load_factor(self) -> float:
        return self.size / self.n_buckets

    def bucket_lengths(self) -> List[int]:
        return [len(b) for b in self.buckets]

    def max_bucket_length(self) -> int:
        lengths = self.bucket_lengths()
        return max(lengths) if lengths else 0

    def stats(self) -> dict:
        lengths = self.bucket_lengths()
        non_empty = [l for l in lengths if l > 0]
        return {
            "n_buckets": self.n_buckets,
            "n_keys": self.size,
            "load_factor": round(self.load_factor(), 4),
            "collision_count": self.collision_count,
            "max_bucket_length": max(lengths) if lengths else 0,
            "avg_bucket_length_nonempty": round(sum(non_empty) / len(non_empty), 3) if non_empty else 0,
            "empty_buckets_ratio": round(1 - len(non_empty) / self.n_buckets, 4),
        }

    def items(self):
        for bucket in self.buckets:
            for k, v in bucket:
                yield k, v


if __name__ == "__main__":
    # Demo nhanh: đếm tần suất từ bằng hashtable tự cài đặt
    ht = HashTable(n_buckets=16, hash_func="polynomial")
    words = "con mèo ngồi trên thảm con mèo ngủ".split()
    for w in words:
        ht.increment(w)
    for k, v in ht.items():
        print(f"{k}: {v}")
    print("Thống kê:", ht.stats())
