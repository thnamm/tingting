# -*- coding: utf-8 -*-
"""
Module tải bộ dữ liệu UIT-VSFC (Vietnamese Students' Feedback Corpus).

ĐỊNH DẠNG GỐC của UIT-VSFC (tải từ http://nlp.uit.edu.vn/datasets/ hoặc
https://github.com/kietnv/uit-vsfc) gồm 3 thư mục train/dev/test, mỗi
thư mục có 3 file văn bản, MỖI DÒNG tương ứng 1 mẫu, các dòng cùng chỉ
số (index) khớp nhau giữa 3 file:

    sents.txt        - câu phản hồi (mỗi dòng 1 câu)
    sentiments.txt   - nhãn cảm xúc: 0=Negative, 1=Neutral, 2=Positive
    topics.txt       - nhãn chủ đề : 0..3

Cách dùng với dữ liệu THẬT:
    1. Tải dataset từ nguồn chính thức, giải nén.
    2. Đặt các file vào  data/train/{sents,sentiments,topics}.txt
                          data/dev/...
                          data/test/...
    3. Gọi load_uit_vsfc("data") như bên dưới.

Nếu chưa có dữ liệu thật, module sẽ tự sinh một bộ DEMO nhỏ (synthetic)
để toàn bộ pipeline vẫn chạy được từ đầu đến cuối, PHỤC VỤ KIỂM THỬ CODE.
Khi có dữ liệu thật, pipeline sẽ tự động dùng dữ liệu thật.
"""

import os
from typing import List, Tuple, Dict

SENTIMENT_LABELS = {0: "Negative", 1: "Neutral", 2: "Positive"}
TOPIC_LABELS = {0: "Giảng viên", 1: "Chương trình đào tạo", 2: "Cơ sở vật chất", 3: "Khác"}


def _read_lines(path: str) -> List[str]:
    with open(path, encoding="utf-8") as f:
        return [line.strip() for line in f.readlines()]


def _load_split(split_dir: str) -> Tuple[List[str], List[int], List[int]]:
    sents = _read_lines(os.path.join(split_dir, "sents.txt"))
    sentiments = [int(x) for x in _read_lines(os.path.join(split_dir, "sentiments.txt"))]
    topics_path = os.path.join(split_dir, "topics.txt")
    if os.path.exists(topics_path):
        topics = [int(x) for x in _read_lines(topics_path)]
    else:
        topics = [-1] * len(sents)
    assert len(sents) == len(sentiments), f"Số dòng không khớp trong {split_dir}"
    return sents, sentiments, topics


def _demo_dataset() -> Dict[str, Tuple[List[str], List[int], List[int]]]:
    """Bộ dữ liệu DEMO nhỏ (synthetic) để test pipeline khi chưa có UIT-VSFC thật."""
    pos = [
        "Thầy dạy rất nhiệt tình và dễ hiểu",
        "Giảng viên nhiệt tình, giải thích dễ hiểu",
        "Môn học rất thú vị và bổ ích",
        "Cô giáo rất tận tâm với sinh viên",
        "Chương trình đào tạo rất tốt và cập nhật",
        "Em rất hài lòng với cách giảng dạy của thầy",
        "Phòng lab hiện đại, thiết bị đầy đủ",
        "Giáo trình rõ ràng dễ theo dõi",
    ]
    neg = [
        "Cơ sở vật chất phòng học quá cũ, cần cải thiện",
        "Giảng viên dạy quá nhanh, khó theo kịp",
        "Chương trình học nặng và không thực tế",
        "Phòng học chật chội và nóng bức",
        "Wifi trường quá yếu, không thể học online",
        "Thầy giảng bài khó hiểu, không rõ ràng",
        "Giáo trình lỗi thời, cần cập nhật gấp",
        "Lịch học sắp xếp không hợp lý",
    ]
    neu = [
        "Buổi học diễn ra vào sáng thứ hai",
        "Môn học có ba tín chỉ",
        "Lớp học nằm ở tầng ba",
        "Kỳ thi sẽ diễn ra vào tuần sau",
        "Giảng viên phụ trách môn này là thầy Nam",
        "Sinh viên nộp bài qua hệ thống trực tuyến",
        "Thời khóa biểu được cập nhật hàng tuần",
        "Phòng thi được thông báo trước một ngày",
    ]
    topics_map = {0: pos[:3] + neg[:3], 1: pos[3:5] + neg[3:5],
                  2: pos[5:7] + neg[5:7], 3: pos[7:] + neg[7:] + neu}

    def build(sent_list, label):
        return [(s, label) for s in sent_list]

    all_pairs = build(pos, 2) + build(neg, 0) + build(neu, 1)
    # Xáo trộn có kiểm soát (seed cố định) để mỗi tập train/dev/test đều
    # có đủ các lớp nhãn -- tránh hiện tượng lệch phân bố khi chia tuần tự.
    import random
    rng = random.Random(42)
    rng.shuffle(all_pairs)

    sents = [p[0] for p in all_pairs]
    sentiments = [p[1] for p in all_pairs]
    # gán topic giả lập tuần hoàn 0..3 (chỉ để pipeline chạy demo được)
    topics = [i % 4 for i in range(len(sents))]

    n = len(sents)
    n_train = int(n * 0.7)
    n_dev = int(n * 0.15)
    return {
        "train": (sents[:n_train], sentiments[:n_train], topics[:n_train]),
        "dev": (sents[n_train:n_train + n_dev], sentiments[n_train:n_train + n_dev],
                topics[n_train:n_train + n_dev]),
        "test": (sents[n_train + n_dev:], sentiments[n_train + n_dev:],
                 topics[n_train + n_dev:]),
    }


def load_uit_vsfc(data_dir: str = "data") -> Dict[str, Tuple[List[str], List[int], List[int]]]:
    """
    Trả về dict {'train': (sents, sentiments, topics), 'dev': ..., 'test': ...}.
    Ưu tiên dữ liệu thật trong data_dir; nếu không tìm thấy -> dùng bộ DEMO.
    """
    splits = {}
    all_found = True
    for split in ("train", "dev", "test"):
        split_dir = os.path.join(data_dir, split)
        if os.path.exists(os.path.join(split_dir, "sents.txt")):
            splits[split] = _load_split(split_dir)
        else:
            all_found = False

    if all_found:
        print(f"[data_loader] Đã tải dữ liệu THẬT từ '{data_dir}'.")
        return splits

    print(f"[data_loader] KHÔNG tìm thấy dữ liệu UIT-VSFC thật trong '{data_dir}'.")
    print("[data_loader] -> Dùng bộ DEMO (synthetic, nhỏ) để pipeline chạy thử.")
    print("[data_loader] Để dùng dữ liệu thật: tải UIT-VSFC và đặt vào "
          f"{data_dir}/train|dev|test/{{sents,sentiments,topics}}.txt")
    return _demo_dataset()


if __name__ == "__main__":
    data = load_uit_vsfc("../data")
    for split, (sents, sentiments, topics) in data.items():
        print(f"{split}: {len(sents)} mẫu, ví dụ: '{sents[0]}' -> sentiment={sentiments[0]}")
