import MetaTrader5 as mt5
from config import MT5_LOGIN, MT5_PASSWORD, MT5_SERVER

def check_symbols():
    if not mt5.initialize(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
        print(f"kết nối MT5 thất bại, lỗi = {mt5.last_error()}")
        return

    print("Kết nối thành công. Đang lấy danh sách symbols...")
    
    symbols = mt5.symbols_get()
    if symbols:
        print(f"Tìm thấy {len(symbols)} symbols. Dưới đây là một vài symbols liên quan đến Crypto:")
        crypto_count = 0
        for s in symbols:
            # Tìm các symbol có chứa 'BTC' hoặc 'ETH' để lọc bớt
            if 'BTC' in s.name.upper() or 'ETH' in s.name.upper():
                print(f" - {s.name}")
                crypto_count += 1
        
        if crypto_count == 0:
            print("Không tìm thấy symbol crypto nào. Dưới đây là 10 symbol đầu tiên:")
            for i in range(min(10, len(symbols))):
                print(f" - {symbols[i].name}")

    else:
        print("Không thể lấy danh sách symbols.")
        
    mt5.shutdown()

if __name__ == "__main__":
    check_symbols()
