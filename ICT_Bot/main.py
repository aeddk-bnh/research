import time
from datetime import datetime
from time_filter import is_kill_zone_time
from strategy import execute_strategy
from config import PLATFORM
from connectors import get_connector

def main_loop():
    """
    Vòng lặp chính của bot, được tái cấu trúc để hỗ trợ nhiều nền tảng.
    """
    print(f"Bot ICT đã khởi động!")
    
    # Khởi tạo connector dựa trên config
    try:
        connector = get_connector(PLATFORM)
        connector.connect()
    except Exception as e:
        print(f"Không thể khởi tạo connector: {e}")
        return

    print(f"Sử dụng nền tảng: {PLATFORM.upper()}")
    print(f"Theo dõi cặp {connector.get_symbol()}")
    print("Bot sẽ chỉ tìm kiếm cơ hội trong các khung giờ Kill Zone.")
    
    while True:
        try:
            if is_kill_zone_time():
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Đang trong Kill Zone. Bắt đầu quét tín hiệu...")
                execute_strategy(connector) # Truyền connector vào strategy
                time.sleep(60) 
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Ngoài giờ Kill Zone. Đang chờ...", end="\r")
                time.sleep(300)

        except KeyboardInterrupt:
            print("\nBot đang dừng...")
            connector.disconnect()
            break
        except Exception as e:
            print(f"\nLỗi trong vòng lặp chính: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main_loop()
