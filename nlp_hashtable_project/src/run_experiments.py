# -*- coding: utf-8 -*-
"""
Script thực nghiệm MỞ RỘNG cho bài NCKH.
- Chạy Feature Hashing với nhiều n_buckets hơn để thấy rõ xu hướng
- Vẽ 4 biểu đồ chuẩn cho chương Thực nghiệm & Đánh giá
- Xuất bảng số liệu chi tiết ra file CSV và JSON
"""

import os
import sys
import time
import json
import csv

# pyrefly: ignore [missing-import]
import numpy as np
# pyrefly: ignore [missing-import]
import matplotlib
matplotlib.use("Agg")  # không cần cửa sổ GUI
# pyrefly: ignore [missing-import]
import matplotlib.pyplot as plt
# pyrefly: ignore [missing-import]
import matplotlib.ticker as mticker

from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

from data_loader import load_uit_vsfc, SENTIMENT_LABELS
from features import HashingFeatureExtractor, build_tfidf_features

# ─────────────────────────── cấu hình ───────────────────────────
# Dãy n_buckets: 64 → 128 → 256 → 512 → 1024 → 2048 → 4096 → 8192
BUCKET_SIZES = [2**6, 2**7, 2**8, 2**9, 2**10, 2**11, 2**12, 2**13]

MODELS = {
    "Naive Bayes":        lambda: MultinomialNB(),
    "Logistic Regression":lambda: LogisticRegression(max_iter=1000, random_state=42),
    "Linear SVM":         lambda: LinearSVC(random_state=42),
    "Random Forest":      lambda: RandomForestClassifier(n_estimators=200, random_state=42),
}

OUTPUT_DIR = "../outputs"
CHART_DIR  = os.path.join(OUTPUT_DIR, "charts")
# ─────────────────────────────────────────────────────────────────

PALETTE = {
    "Naive Bayes":         "#4C9BE8",
    "Logistic Regression": "#F4845F",
    "Linear SVM":          "#6FCF97",
    "Random Forest":       "#BB6BD9",
    "TF-IDF":              "#F2C94C",
}


def evaluate_model(model, X_train, y_train, X_test, y_test) -> dict:
    t0 = time.time()
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
        "accuracy":         round(acc,       4),
        "precision_macro":  round(precision,  4),
        "recall_macro":     round(recall,     4),
        "f1_macro":         round(f1,         4),
        "train_time_sec":   round(train_time, 4),
        "predict_time_sec": round(predict_time, 4),
    }


def run_hashing(train_sents, y_train, test_sents, y_test):
    results = []
    all_sents = train_sents + test_sents
    for n in BUCKET_SIZES:
        print(f"  [Feature Hashing] n_buckets={n} ...", flush=True)
        extractor = HashingFeatureExtractor(n_buckets=n)
        t0 = time.time()
        X_train = extractor.fit_transform(train_sents)
        X_test  = extractor.transform(test_sents)
        extract_time = round(time.time() - t0, 4)

        cstats   = extractor.collision_stats(all_sents)
        mem_kb   = (X_train.data.nbytes + X_train.indices.nbytes + X_train.indptr.nbytes) / 1024

        for mname, mfn in MODELS.items():
            m = evaluate_model(mfn(), X_train, y_train, X_test, y_test)
            results.append({
                "method":                  "Feature Hashing",
                "n_buckets":               n,
                "model":                   mname,
                "feature_extract_time_sec": extract_time,
                "feature_matrix_mem_kb":   round(mem_kb, 2),
                "collision_rate":          cstats["collision_rate_over_used_columns"],
                "distinct_tokens":         cstats["distinct_tokens"],
                **m,
            })
    return results


def run_tfidf(train_sents, y_train, test_sents, y_test):
    print("  [TF-IDF] ...", flush=True)
    t0 = time.time()
    X_train, X_test, vec = build_tfidf_features(train_sents, test_sents)
    extract_time = round(time.time() - t0, 4)
    mem_kb = (X_train.data.nbytes + X_train.indices.nbytes + X_train.indptr.nbytes) / 1024
    vocab_size = X_train.shape[1]

    results = []
    for mname, mfn in MODELS.items():
        m = evaluate_model(mfn(), X_train, y_train, X_test, y_test)
        results.append({
            "method":                  "TF-IDF",
            "n_buckets":               vocab_size,
            "model":                   mname,
            "feature_extract_time_sec": extract_time,
            "feature_matrix_mem_kb":   round(mem_kb, 2),
            "collision_rate":          0.0,
            "distinct_tokens":         vocab_size,
            **m,
        })
    return results


# ═══════════════════════════ CHARTS ═══════════════════════════════

def _setup_ax(ax, title, xlabel, ylabel):
    ax.set_title(title, fontsize=13, fontweight="bold", pad=10)
    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def chart_f1_vs_buckets(hashing_results, tfidf_results, out_path):
    """Biểu đồ 1: F1-macro theo n_buckets cho từng mô hình + TF-IDF đường ngang."""
    fig, ax = plt.subplots(figsize=(9, 5))

    buckets = sorted(set(r["n_buckets"] for r in hashing_results))
    for mname in MODELS:
        f1s = [
            next(r["f1_macro"] for r in hashing_results if r["n_buckets"] == b and r["model"] == mname)
            for b in buckets
        ]
        ax.plot(buckets, f1s, marker="o", label=f"FH - {mname}", color=PALETTE[mname], linewidth=2)

    # Đường ngang TF-IDF
    for mname in MODELS:
        tval = next(r["f1_macro"] for r in tfidf_results if r["model"] == mname)
        ax.axhline(tval, linestyle="--", color=PALETTE[mname], alpha=0.5)

    ax.set_xscale("log", base=2)
    ax.xaxis.set_major_formatter(mticker.ScalarFormatter())
    ax.set_xticks(buckets)
    _setup_ax(ax, "F1-macro theo kích thước bảng băm (n_buckets)\n(đường nét đứt = TF-IDF cùng màu)",
              "n_buckets (log₂ scale)", "F1-macro")
    ax.legend(fontsize=8, ncol=2)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"  -> Đã lưu: {out_path}")


def chart_collision_vs_buckets(hashing_results, out_path):
    """Biểu đồ 2: Collision rate theo n_buckets."""
    fig, ax = plt.subplots(figsize=(8, 4))

    buckets = sorted(set(r["n_buckets"] for r in hashing_results))
    col_rates = [
        next(r["collision_rate"] for r in hashing_results if r["n_buckets"] == b)
        for b in buckets
    ]

    bars = ax.bar([str(b) for b in buckets], col_rates,
                  color="#4C9BE8", edgecolor="white", width=0.6)
    for i, v in enumerate(col_rates):
        ax.text(i, v + 0.01, f"{v:.3f}", ha="center", fontsize=9)

    _setup_ax(ax, "Tỉ lệ va chạm hash (Collision Rate) theo n_buckets",
              "n_buckets", "Collision Rate")
    ax.set_ylim(0, 1.15)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"  -> Đã lưu: {out_path}")


def chart_accuracy_comparison(hashing_results, tfidf_results, out_path):
    """Biểu đồ 3: Cột so sánh Accuracy – Feature Hashing (bucket tốt nhất) vs TF-IDF."""
    best_bucket = max(
        set(r["n_buckets"] for r in hashing_results),
        key=lambda b: np.mean([r["f1_macro"] for r in hashing_results if r["n_buckets"] == b])
    )
    fh_rows    = [r for r in hashing_results if r["n_buckets"] == best_bucket]
    tfidf_rows = tfidf_results

    models  = list(MODELS.keys())
    fh_accs = [next(r["accuracy"] for r in fh_rows    if r["model"] == m) for m in models]
    tf_accs = [next(r["accuracy"] for r in tfidf_rows if r["model"] == m) for m in models]

    x = np.arange(len(models))
    w = 0.35
    fig, ax = plt.subplots(figsize=(9, 5))
    bars1 = ax.bar(x - w/2, fh_accs, w,
                   label=f"Feature Hashing ({best_bucket} buckets)", color="#4C9BE8", edgecolor="white")
    bars2 = ax.bar(x + w/2, tf_accs, w,
                   label="TF-IDF", color="#F2C94C", edgecolor="white")

    for bar in list(bars1) + list(bars2):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.003,
                f"{bar.get_height():.4f}", ha="center", va="bottom", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=10)
    ax.set_ylim(0, 1.05)
    _setup_ax(ax, f"So sánh Accuracy: Feature Hashing vs TF-IDF", "Mô hình", "Accuracy")
    ax.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"  -> Đã lưu: {out_path}")


def chart_memory_comparison(hashing_results, tfidf_results, out_path):
    """Biểu đồ 4: So sánh bộ nhớ Feature Hashing (các bucket) vs TF-IDF."""
    fig, ax = plt.subplots(figsize=(9, 4))

    buckets = sorted(set(r["n_buckets"] for r in hashing_results))
    mem_fh  = [
        next(r["feature_matrix_mem_kb"] for r in hashing_results
             if r["n_buckets"] == b and r["model"] == "Logistic Regression")
        for b in buckets
    ]
    mem_tfidf = next(r["feature_matrix_mem_kb"] for r in tfidf_results
                     if r["model"] == "Logistic Regression")

    labels = [str(b) for b in buckets] + ["TF-IDF"]
    values = mem_fh + [mem_tfidf]
    colors = ["#4C9BE8"] * len(buckets) + ["#F2C94C"]

    bars = ax.bar(labels, values, color=colors, edgecolor="white", width=0.6)
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 3,
                f"{v:.0f} KB", ha="center", fontsize=8)

    _setup_ax(ax, "Bộ nhớ ma trận đặc trưng: Feature Hashing vs TF-IDF",
              "Phương pháp (n_buckets)", "Bộ nhớ (KB)")
    # pyrefly: ignore [missing-import]
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color="#4C9BE8", label="Feature Hashing"),
                        Patch(color="#F2C94C", label="TF-IDF")])
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"  -> Đã lưu: {out_path}")


# ═══════════════════════════ MAIN ═══════════════════════════════

def print_table(all_results):
    header = f"{'Method':16}{'Buckets':>8}{'Model':22}{'Acc':>8}{'F1':>8}{'Collision':>11}{'MemKB':>9}"
    print("\n" + header)
    print("-" * len(header))
    for r in all_results:
        print(f"{r['method']:16}{r['n_buckets']:>8}{r['model']:22}"
              f"{r['accuracy']:>8}{r['f1_macro']:>8}{r['collision_rate']:>11}"
              f"{r['feature_matrix_mem_kb']:>9.1f}")


def save_csv(all_results, path):
    if not all_results:
        return
    keys = list(all_results[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(all_results)
    print(f"  -> Đã lưu CSV: {path}")


def main():
    print("=" * 70)
    print("THỰC NGHIỆM MỞ RỘNG: NLP + HASHTABLE + HỌC MÁY CÓ GIÁM SÁT")
    print("=" * 70)

    os.makedirs(CHART_DIR, exist_ok=True)

    data = load_uit_vsfc("../data")
    train_sents, y_train, _ = data["train"]
    test_sents,  y_test,  _ = data["test"]

    print(f"\nDữ liệu: {len(train_sents)} train | {len(test_sents)} test")
    label_dist = {v: y_train.count(k) for k, v in SENTIMENT_LABELS.items()}
    print(f"Phân bố nhãn train: {label_dist}")
    print(f"\nDãy n_buckets thử nghiệm: {BUCKET_SIZES}")

    print("\n>>> Feature Hashing ...")
    hashing_results = run_hashing(train_sents, y_train, test_sents, y_test)

    print("\n>>> TF-IDF baseline ...")
    tfidf_results = run_tfidf(train_sents, y_train, test_sents, y_test)

    all_results = hashing_results + tfidf_results
    print_table(all_results)

    json_path = os.path.join(OUTPUT_DIR, "results_extended.json")
    csv_path  = os.path.join(OUTPUT_DIR, "results_extended.csv")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n  -> Đã lưu JSON: {json_path}")
    save_csv(all_results, csv_path)

    print("\n>>> Đang vẽ biểu đồ ...")
    chart_f1_vs_buckets(
        hashing_results, tfidf_results,
        os.path.join(CHART_DIR, "01_f1_vs_buckets.png")
    )
    chart_collision_vs_buckets(
        hashing_results,
        os.path.join(CHART_DIR, "02_collision_rate.png")
    )
    chart_accuracy_comparison(
        hashing_results, tfidf_results,
        os.path.join(CHART_DIR, "03_accuracy_comparison.png")
    )
    chart_memory_comparison(
        hashing_results, tfidf_results,
        os.path.join(CHART_DIR, "04_memory_comparison.png")
    )

    print("\n" + "=" * 70)
    print(f"HOÀN THÀNH! Biểu đồ lưu tại: {CHART_DIR}/")
    print("=" * 70)


if __name__ == "__main__":
    main()
