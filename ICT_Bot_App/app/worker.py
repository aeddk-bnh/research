from PySide6.QtCore import QThread, Signal
import time
from datetime import datetime
import traceback # Import traceback

# Import các thành phần từ thư mục trading_core
from trading_core.time_filter import is_kill_zone_time, get_kill_zone_status
from trading_core.strategy import execute_strategy
from trading_core.connectors import get_connector

# Import các thành phần của app
from app.signals import WorkerSignals
from app.config_manager import config_manager

class BotWorker(QThread):
    def __init__(self):
        super().__init__()
        self.signals = WorkerSignals()
        self._is_running = True
        self.connector = None

    def run(self):
        """Vòng lặp chính của bot, chạy trong một luồng riêng."""
        self.signals.log_message.emit("Khởi tạo bot trong worker...")
        
        # Lấy nền tảng từ cấu hình
        platform = config_manager.get('platform', 'mt5')
        if not platform: # Đảm bảo platform không phải None
            self.signals.log_message.emit("Lỗi: Nền tảng không được cấu hình.")
            self.signals.bot_status.emit("Lỗi cấu hình")
            return

        # Khởi tạo connector
        try:
            self.connector = get_connector(platform, signals=self.signals)
            if self.connector is None: # Xử lý trường hợp get_connector trả về None
                self.signals.log_message.emit(f"Không thể khởi tạo connector cho nền tảng '{platform}'.")
                self.signals.bot_status.emit("Lỗi kết nối")
                return

            self.connector.connect()
            self.signals.log_message.emit(f"Đã kết nối thành công với {platform.upper()}.")
        except Exception as e:
            self.signals.log_message.emit(f"Lỗi kết nối: {e}")
            self.signals.bot_status.emit("Lỗi kết nối")
            return

        self.signals.log_message.emit(f"Sử dụng nền tảng: {platform.upper()}")
        symbol = self.connector.get_symbol()
        if not symbol: # Đảm bảo symbol không phải None
            self.signals.log_message.emit("Lỗi: Không thể lấy symbol từ connector.")
            self.signals.bot_status.emit("Lỗi cấu hình")
            return
        self.signals.log_message.emit(f"Theo dõi cặp: {symbol}")
        self.signals.log_message.emit("Bot sẽ chỉ tìm kiếm cơ hội trong các khung giờ Kill Zone.")
        self.signals.bot_status.emit("Đang chạy")
        self.signals.market_bias.emit("Chưa xác định") # Đặt trạng thái ban đầu

        # Vòng lặp chính
        while self._is_running:
            try:
                self.signals.log_message.emit(f"[DEBUG] Vòng lặp chính đang chạy...") # Log debug
                
                if is_kill_zone_time(signals=self.signals):
                    self.signals.log_message.emit(f"\n[{datetime.now().strftime('%H:%M:%S')}] Đang trong Kill Zone. Bắt đầu quét tín hiệu...")
                    execute_strategy(self.connector, signals=self.signals) 
                else:
                    self.signals.log_message.emit(f"[{datetime.now().strftime('%H:%M:%S')}] Ngoài giờ Kill Zone. Đang chờ...")
                    # Cập nhật bias khi ngoài KZ
                    self.signals.market_bias.emit("Chưa kích hoạt (Ngoài KZ)")
                    time.sleep(300) # Chờ 5 phút
                
                # Tạm thời ngủ 1 phút để tránh vòng lặp quá nhanh
                time.sleep(60)

            except KeyboardInterrupt:
                self.signals.log_message.emit("Nhận tín hiệu Ctrl+C, đang dừng...")
                break
            except Exception as e:
                self.signals.log_message.emit(f"\nLỗi trong vòng lặp chính: {e}")
                self.signals.log_message.emit(f"Chi tiết lỗi:\n{traceback.format_exc()}")
                time.sleep(60)
        # Vòng lặp kết thúc
        self.signals.log_message.emit("Bot đã dừng.")
        self.signals.bot_status.emit("Đã dừng")
        self.signals.market_bias.emit("Đã dừng") # Cập nhật trạng thái bias khi bot dừng
        if self.connector:
            self.connector.disconnect()
            self.signals.log_message.emit("Đã ngắt kết nối.")

    def stop(self):
        """Dừng vòng lặp của bot một cách an toàn."""
        self._is_running = False
        # Đợi thread kết thúc tối đa 5 giây
        if self.wait(5000):
            print("BotWorker đã dừng thành công.")
        else:
            print("BotWorker không dừng kịp thời, buộc kết thúc.")
            # Không gọi terminate() vì nó không an toàn cho Python
            # Chỉ rely vào cờ _is_running
