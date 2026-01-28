import MetaTrader5 as mt5
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, MT5_PATH

print("Khởi động MT5...")
print(f"Đang kết nối với tài khoản: {MT5_LOGIN}")
print(f"Server: {MT5_SERVER}")

if mt5.initialize(path=MT5_PATH, login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
    print("Khởi động thành công.")
    
    # Lấy thông tin tài khoản hiện tại
    account_info = mt5.account_info()
    if account_info:
        print(f"\n=== Thông tin tài khoản ===")
        print(f"Login: {account_info.login}")
        print(f"Server: {account_info.server}")
        print(f"Name: {account_info.name}")
        print(f"Balance: {account_info.balance}")
        print(f"Equity: {account_info.equity}")
        print(f"Margin: {account_info.margin}")
        print(f"Free Margin: {account_info.margin_free}")
        print(f"Leverage: 1:{account_info.leverage}")
        print(f"Currency: {account_info.currency}")
    else:
        print("Không thể lấy thông tin tài khoản.")
    
    mt5.shutdown()
    print("\n✓ Kết nối và ngắt kết nối MT5 thành công!")
else:
    print(f"Khởi động thất bại, lỗi = {mt5.last_error()}")
    print("\nVui lòng kiểm tra:")
    print("1. Thông tin đăng nhập (login, password, server) trong config.py")
    print("2. Đường dẫn MT5_PATH có chính xác không")
    print("3. Terminal MT5 có đang chạy không (nếu cần)")
    print("4. Kết nối internet ổn định không")
