# my_list = [None, None, None, None, None, None, None, None, None, None]
# print(my_list)

# def hash_value(value):
#     total = 0
#     for char in value:
#         total += ord(char)
#     return total % 10

# def add_data(value):
#     my_hash = hash_value(value)
#     if my_list[my_hash] is None:
#         my_list[my_hash] = value
#     else:
#         print("Hash value already exists")

# add_data("Bob")

# print(my_list)

from collections import defaultdict
import string


class SpellingCheckerAI:

  def __init__(self):
    # Hash table (Set) lưu trữ từ điển chuẩn để tra cứu siêu tốc O(1)
    self.dictionary = set()
    # Hash table lưu mô hình ký tự để hỗ trợ đánh giá
    self.char_model = defaultdict(lambda: defaultdict(int))

  def train(self, corpus):
    # Xây dựng từ điển từ văn bản mẫu
    words = corpus.lower().split()
    for word in words:
      clean_word = word.strip(string.punctuation)
      if clean_word:
        self.dictionary.add(clean_word)
        # Học mối quan hệ ký tự trong từ
        for i in range(len(clean_word) - 1):
          self.char_model[clean_word[i]][clean_word[i + 1]] += 1

  def check_text(self, text):
    # Tách câu thành các từ để kiểm tra lỗi
    words = text.lower().split()
    errors = []
    for word in words:
      clean_word = word.strip(string.punctuation)
      # Nếu từ không tồn tại trong Hash Table từ điển -> nghi ngờ lỗi
      if clean_word and clean_word not in self.dictionary:
        errors.append(clean_word)
    return errors

  def suggest_correction(self, misspelled_word):
    if not self.dictionary:
      return []
    # Gợi ý từ đúng dựa trên độ tương đồng ký tự với từ trong từ điển
    suggestions = sorted(
        self.dictionary,
        key=lambda w: abs(len(w) - len(misspelled_word))
        + sum(1 for c in misspelled_word if c not in w),
    )
    return suggestions[:2]  # Trả về 2 gợi ý hàng đầu


# --- Chạy thử nghiệm ứng dụng ---
ai = SpellingCheckerAI()
corpus_data = (
    "lap trinh python rat hay va thu vi, lap trinh ai giup giai quyet nhieu"
    " bai toan kho"
)
ai.train(corpus_data)

# Câu kiểm tra có lỗi ("pythong" và "ratt")
input_text = "lap trinh pythong ratt hay"
detected_errors = ai.check_text(input_text)

print(f"Văn bản kiểm tra: '{input_text}'")
print(f"Phát hiện lỗi chính tả: {detected_errors}")

for err in detected_errors:
  suggestions = ai.suggest_correction(err)
  print(f"-> Gợi ý cho từ '{err}': {suggestions}")