# run_test.py
import time
from datetime import datetime
from strategy import execute_strategy
from config import PLATFORM
from connectors import get_connector

def run_single_cycle():
    """
    Chạy một chu kỳ duy nhất của bot để kiểm tra.
    """
    print("--- Bắt đầu chu kỳ kiểm tra duy nhất ---")
    
    # Khởi tạo connector
    try:
        connector = get_connector(PLATFORM)
        if not connector.connect():
            print("--- Kết thúc chu kỳ kiểm tra do kết nối thất bại ---")
            return
    except Exception as e:
        print(f"Không thể khởi tạo connector: {e}")
        return

    print(f"Sử dụng nền tảng: {PLATFORM.upper()}")
    print(f"Theo dõi cặp {connector.get_symbol()}")
    
    # Thực thi chiến lược
    try:
        execute_strategy(connector)
    except Exception as e:
        print(f"Lỗi khi thực thi chiến lược: {e}")
    finally:
        # Ngắt kết nối sau khi hoàn thành
        connector.disconnect()
        print("--- Kết thúc chu kỳ kiểm tra ---")

if __name__ == "__main__":
    run_single_cycle()
