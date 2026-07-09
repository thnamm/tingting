import string

#Những mật khẩu dễ bị bẻ khóa!
def load_common_passwords(file_path):
    try:
        with open(file_path, "r", encoding = "utf-8", errors = "ignore") as f:
            return set(line.strip() for line in f)
    except FileNotFoundError:
        print("[!] Password dataset file not found!")
        exit()

common_passwords = load_common_passwords("xato-net-10-million-passwords-100.txt")

password = input("Enter your password: ")
print("-" * 30)
if password in common_passwords:
    print("Password exists in common password dataset!")
    exit()

score = 0
charset_size = 0

lowercase = string.ascii_lowercase
uppercase = string.ascii_uppercase
digits = string.digits
symbols = string.punctuation

#Check độ dài của mật khẩu!
if len(password) >= 8:
    score += 1
if len(password) >= 16:
    score += 1
if len(password) >= 24:
    score += 1

print("Phân tích mật khẩu...")

if any(c.islower() for c in password):
    charset_size += len(lowercase)

if any(c.isupper() for c in password):
    count_upper = sum(1 for c in password if c.isupper())
    charset_size += len(uppercase)
    score += 1
    print(f"Mật khẩu có {count_upper} chữ cái hoa!")

if any(c in symbols for c in password):
    count_symbols = sum(1 for c in password if c in symbols)
    charset_size += len(symbols)
    score += 1
    print(f"Mật khẩu có {count_symbols} ký tự đặc biệt!")

if any(c.isdigit() for c in password):
    count_digits = sum(1 for c in password if c.isdigit())
    charset_size += len(digits)
    score += 1
    print(f"Mật khẩu có {count_digits} chữ số!")

if charset_size == 0:
    charset_size = 26

combinations = charset_size ** len(password)

guesses_per_second = 1_000_000_000

second = combinations / guesses_per_second

def convert_time(seconds):
    minutes = seconds / 60
    hours = minutes / 60
    days = hours / 24
    years = days / 365
    
    if seconds < 60:
        return f"{seconds: .2f} seconds"
    elif minutes < 60:
        return f"{minutes: .2f} minutes"
    elif hours < 24:
        return f"{hours: .2f} hours"
    elif days < 365:
        return f"{days: .2f} days"
    else:
        return f"{years: .2f} years"
print("-" * 30)

print(f"Điểm số của mật khẩu bạn là: {score}đ")

if score <= 1:
    print("Mật khẩu yếu!!!")
elif score == 2:
    print("Mật khẩu trung bình!")
elif score == 3:
    print("Mật khẩu mạnh!")
else:
    print("Mật khẩu rất mạnh!")


print(f"Thời gian để bẻ khóa mật khẩu:{convert_time(second)}")
