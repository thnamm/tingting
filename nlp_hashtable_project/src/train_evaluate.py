# -*- coding: utf-8 -*-
"""
Pipeline huấn luyện & đánh giá:
  - So sánh 2 phương pháp trích xuất đặc trưng: Feature Hashing (hashtable tự cài) vs TF-IDF
  - So sánh 4 thuật toán học máy có giám sát: Naive Bayes, Logistic Regression, SVM (linear), Random Forest
  - Đo: Accuracy, Precision, Recall, F1 (macro), thời gian huấn luyện, bộ nhớ đặc trưng
  - Phân tích ảnh hưởng của n_buckets (kích thước bảng băm) đến độ chính xác
"""

import time
import json
import sys
from typing import List

from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

from data_loader import load_uit_vsfc, SENTIMENT_LABELS
from features import HashingFeatureExtractor, build_tfidf_features

MODELS = {
    "Naive Bayes": lambda: MultinomialNB(),
    "Logistic Regression": lambda: LogisticRegression(max_iter=1000),
    "Linear SVM": lambda: LinearSVC(),
    "Random Forest": lambda: RandomForestClassifier(n_estimators=200, random_state=42),
}


def evaluate_model(model, X_train, y_train, X_test, y_test) -> dict:
    t0 = time.time()
    # MultinomialNB không nhận giá trị âm -> đảm bảo non-negative (feature hashing dùng count nên ổn)
    model.fit(X_train, y_train)
    train_time = time.time() - t0

    t0 = time.time()
    y_pred = model.predict(X_test)
    predict_time = time.time() - t0

    acc = accuracy_score(y_test, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average="macro", zero_division=0
    )
    return {
        "accuracy": round(acc, 4),
        "precision_macro": round(precision, 4),
        "recall_macro": round(recall, 4),
        "f1_macro": round(f1, 4),
        "train_time_sec": round(train_time, 4),
        "predict_time_sec": round(predict_time, 4),
    }


def run_feature_hashing_experiments(train_sents, y_train, test_sents, y_test,
                                     bucket_sizes: List[int]):
    """Thực nghiệm chính: Feature Hashing với nhiều kích thước bảng băm khác nhau."""
    results = []
    for n_buckets in bucket_sizes:
        extractor = HashingFeatureExtractor(n_buckets=n_buckets)
        t0 = time.time()
        X_train = extractor.fit_transform(train_sents)
        X_test = extractor.transform(test_sents)
        extract_time = round(time.time() - t0, 4)

        collision_info = extractor.collision_stats(train_sents + test_sents)
        mem_bytes = X_train.data.nbytes + X_train.indices.nbytes + X_train.indptr.nbytes

        for model_name, model_fn in MODELS.items():
            metrics = evaluate_model(model_fn(), X_train, y_train, X_test, y_test)
            results.append({
                "method": "Feature Hashing",
                "n_buckets": n_buckets,
                "model": model_name,
                "feature_extract_time_sec": extract_time,
                "feature_matrix_mem_bytes": int(mem_bytes),
                "collision_rate": collision_info["collision_rate_over_used_columns"],
                **metrics,
            })
    return results


def run_tfidf_experiment(train_sents, y_train, test_sents, y_test):
    """Baseline TF-IDF truyền thống để đối chiếu."""
    t0 = time.time()
    X_train, X_test, vectorizer = build_tfidf_features(train_sents, test_sents)
    extract_time = round(time.time() - t0, 4)
    mem_bytes = X_train.data.nbytes + X_train.indices.nbytes + X_train.indptr.nbytes

    results = []
    for model_name, model_fn in MODELS.items():
        metrics = evaluate_model(model_fn(), X_train, y_train, X_test, y_test)
        results.append({
            "method": "TF-IDF",
            "n_buckets": X_train.shape[1],  # kích thước vocab thực tế
            "model": model_name,
            "feature_extract_time_sec": extract_time,
            "feature_matrix_mem_bytes": int(mem_bytes),
            "collision_rate": 0.0,  # TF-IDF không có va chạm hash
            **metrics,
        })
    return results


def main():
    print("=" * 70)
    print("PIPELINE THỰC NGHIỆM: NLP + HASHTABLE + HỌC MÁY CÓ GIÁM SÁT")
    print("=" * 70)

    data = load_uit_vsfc("../data")
    train_sents, y_train, _ = data["train"]
    test_sents, y_test, _ = data["test"]
    print(f"\nSố mẫu train: {len(train_sents)} | Số mẫu test: {len(test_sents)}")
    print(f"Phân bố nhãn train: {[y_train.count(i) for i in sorted(SENTIMENT_LABELS)]}"
          f"  ({list(SENTIMENT_LABELS.values())})")

    bucket_sizes = [2 ** 6, 2 ** 8, 2 ** 12]  # nhỏ -> lớn để thấy rõ ảnh hưởng va chạm
    print(f"\n>>> Thực nghiệm Feature Hashing với n_buckets = {bucket_sizes}")
    hashing_results = run_feature_hashing_experiments(
        train_sents, y_train, test_sents, y_test, bucket_sizes
    )

    print(">>> Thực nghiệm baseline TF-IDF")
    tfidf_results = run_tfidf_experiment(train_sents, y_train, test_sents, y_test)

    all_results = hashing_results + tfidf_results

    # In bảng kết quả gọn
    header = f"{'Method':16}{'n_buckets':>10}{'Model':22}{'Acc':>8}{'F1':>8}{'Collision':>11}{'MemKB':>10}"
    print("\n" + header)
    print("-" * len(header))
    for r in all_results:
        print(f"{r['method']:16}{r['n_buckets']:>10}{r['model']:22}"
              f"{r['accuracy']:>8}{r['f1_macro']:>8}{r['collision_rate']:>11}"
              f"{r['feature_matrix_mem_bytes']/1024:>10.1f}")

    out_path = "../outputs/results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\nĐã lưu kết quả chi tiết vào {out_path}")

    return all_results


if __name__ == "__main__":
    main()
