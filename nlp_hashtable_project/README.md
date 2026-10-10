# Pipeline thực nghiệm: NLP bằng Hashtable kết hợp Học máy có giám sát

## Cấu trúc project

```
nlp_hashtable_project/
├── src/
│   ├── preprocess.py       # Tiền xử lý văn bản tiếng Việt (clean, tokenize, stopword)
│   ├── hashtable.py         # Hashtable tự cài đặt (separate chaining) + thống kê va chạm
│   ├── features.py          # Feature Hashing (dùng hashtable) + TF-IDF baseline
│   ├── data_loader.py       # Tải dữ liệu UIT-VSFC (hoặc bộ demo nếu chưa có dữ liệu thật)
│   └── train_evaluate.py    # Huấn luyện, đánh giá, so sánh các phương pháp/mô hình
├── data/                    # Đặt dữ liệu UIT-VSFC thật vào đây (xem hướng dẫn bên dưới)
└── outputs/
    └── results.json         # Kết quả thực nghiệm chi tiết (sinh ra sau khi chạy)
```

## Cài đặt

```bash
pip install scikit-learn scipy pyvi numpy --break-system-packages
```

## CÁCH TÍCH HỢP DỮ LIỆU UIT-VSFC THẬT (quan trọng)

Hiện tại pipeline đang chạy với **bộ dữ liệu DEMO nhỏ (synthetic)** chỉ để
kiểm thử code chạy đúng đầu-cuối. Để có kết quả nghiên cứu thật, bạn cần:

1. Tải UIT-VSFC từ một trong các nguồn:
   - Chính thức: http://nlp.uit.edu.vn/datasets/
   - GitHub (mô tả + link Google Drive): https://github.com/kietnv/uit-vsfc
   - Hugging Face (định dạng JSON, dễ load bằng Python):
     https://huggingface.co/datasets/tridm/UIT-VSFC hoặc
     https://huggingface.co/datasets/SEACrowd/uit_vsfc

2. Sắp xếp lại thành cấu trúc mà `data_loader.py` yêu cầu:

```
data/
├── train/
│   ├── sents.txt        (mỗi dòng 1 câu phản hồi)
│   ├── sentiments.txt   (mỗi dòng 1 nhãn: 0/1/2)
│   └── topics.txt       (mỗi dòng 1 nhãn: 0..3, tùy chọn)
├── dev/
│   └── ... (tương tự)
└── test/
    └── ... (tương tự)
```

   Nếu tải bản JSON từ Hugging Face, viết một script nhỏ để tách trường
   `sentence` và `sentiment`/`topic` ra 3 file .txt tương ứng — mình có
   thể viết script này giúp bạn nếu bạn gửi cấu trúc file JSON tải về.

3. Chạy lại:
   ```bash
   cd src
   python3 train_evaluate.py
   ```
   Khi đó `data_loader.py` sẽ tự động phát hiện dữ liệu thật và dùng nó
   thay vì bộ demo (log sẽ hiện "Đã tải dữ liệu THẬT...").

## Chạy từng phần riêng lẻ (phục vụ viết báo cáo / demo)

```bash
python3 src/preprocess.py      # xem ví dụ tiền xử lý
python3 src/hashtable.py       # xem ví dụ đếm tần suất bằng hashtable tự cài
python3 src/features.py        # xem ví dụ feature hashing + thống kê va chạm
python3 src/data_loader.py     # xem thông tin bộ dữ liệu đang dùng
python3 src/train_evaluate.py  # chạy toàn bộ thực nghiệm, xuất outputs/results.json
```

## Nội dung thực nghiệm đã cài đặt sẵn (khớp với đề cương Chương 4)

- **So sánh Feature Hashing vs TF-IDF**: accuracy, precision/recall/F1 (macro),
  thời gian trích xuất đặc trưng, dung lượng bộ nhớ ma trận đặc trưng.
- **Phân tích ảnh hưởng kích thước bảng băm (n_buckets)**: chạy với
  64 / 256 / 4096 buckets để quan sát tỉ lệ va chạm giảm dần và tác động
  đến độ chính xác — có thể chỉnh trong `bucket_sizes` ở `train_evaluate.py`.
- **So sánh 4 thuật toán học máy có giám sát**: Naive Bayes, Logistic
  Regression, Linear SVM, Random Forest — trên cùng một bộ đặc trưng để
  đảm bảo so sánh công bằng.

## Gợi ý mở rộng cho báo cáo

- Vẽ biểu đồ: trục X = n_buckets, trục Y = accuracy/F1 và collision_rate,
  minh họa trade-off giữa kích thước bảng băm và độ chính xác.
- Vẽ biểu đồ so sánh bộ nhớ: Feature Hashing (cố định) vs TF-IDF (tăng
  theo kích thước tập dữ liệu) khi thử nghiệm trên tập con có kích thước
  tăng dần (1K, 5K, 10K, 16K mẫu).
- Thử thêm hàm băm khác (`hash_func="builtin"` trong `HashTable`) để so
  sánh phân bố va chạm giữa hàm băm đa thức tự cài và hàm băm built-in.
