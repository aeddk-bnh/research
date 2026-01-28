from PySide6.QtCore import QThread, Signal, QTimer
import time
from datetime import datetime

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
        # Timer sẽ được tạo trong luồng worker
        self.kz_timer = None

    def run(self):
        """Vòng lặp chính của bot, chạy trong một luồng riêng."""
        self.signals.log_message.emit("Khởi tạo bot trong worker...")
        
        # Lấy nền tảng từ cấu hình
        platform = config_manager.get('platform', 'mt5')

        # Khởi tạo connector
        try:
            self.connector = get_connector(platform, signals=self.signals)
            self.connector.connect()
            self.signals.log_message.emit(f"Đã kết nối thành công với {platform.upper()}.")
        except Exception as e:
            self.signals.log_message.emit(f"Lỗi kết nối: {e}")
            self.signals.bot_status.emit("Lỗi kết nối")
            return

        self.signals.log_message.emit(f"Sử dụng nền tảng: {platform.upper()}")
        self.signals.log_message.emit(f"Theo dõi cặp: {self.connector.get_symbol()}")
        self.signals.log_message.emit("Bot sẽ chỉ tìm kiếm cơ hội trong các khung giờ Kill Zone.")
        self.signals.bot_status.emit("Đang chạy")
        
        # Tạo và bắt đầu timer cập nhật Kill Zone trong luồng worker
        self.kz_timer = QTimer()
        self.kz_timer.timeout.connect(self.check_and_emit_kz_status)
        self.kz_timer.start(10000) # 10 giây

        # Vòng lặp chính
        while self._is_running:
            try:
                self.signals.log_message.emit(f"[DEBUG] Vòng lặp chính đang chạy...") # Log debug
                if is_kill_zone_time(signals=self.signals):
                    self.signals.log_message.emit(f"\\n[{datetime.now().strftime('%H:%M:%S')}] Đang trong Kill Zone. Bắt đầu quét tín hiệu...")
                    execute_strategy(self.connector, signals=self.signals) 
                else:
                    self.signals.log_message.emit(f"[{datetime.now().strftime('%H:%M:%S')}] Ngoài giờ Kill Zone. Đang chờ...")
                    time.sleep(300) # Chờ 5 phút
                
                # Tạm thời ngủ 1 phút để tránh vòng lặp quá nhanh
                time.sleep(60)

            except KeyboardInterrupt:
                self.signals.log_message.emit("Nhận tín hiệu Ctrl+C, đang dừng...")
                break
            except Exception as e:
                self.signals.log_message.emit(f"\\nLỗi trong vòng lặp chính: {e}")
                import traceback
                self.signals.log_message.emit(f"Chi tiết lỗi:\\n{traceback.format_exc()}")
                time.sleep(60)
        
        # Dừng timer trước khi kết thúc
        self.kz_timer.stop()
        # Vòng lặp kết thúc
        self.signals.log_message.emit("Bot đã dừng.")
        self.signals.bot_status.emit("Đã dừng")
        if self.connector:
            self.connector.disconnect()
            self.signals.log_message.emit("Đã ngắt kết nối.")

    def check_and_emit_kz_status(self):
        """Hàm này được gọi định kỳ bởi QTimer để cập nhật trạng thái KZ lên UI."""
        is_in_kz, status_str = get_kill_zone_status()
        self.signals.kill_zone_status.emit(status_str)

    def stop(self):
        """Dừng vòng lặp của bot một cách an toàn."""
        self._is_running = False
        # Dừng timer Kill Zone nếu nó đã được tạo
        if self.kz_timer:
            self.kz_timer.stop()
        # Đợi thread kết thúc tối đa 5 giây
        if self.wait(5000):
            print("BotWorker đã dừng thành công.")
        else:
            print("BotWorker không dừng kịp thời, buộc kết thúc.")
            # Không gọi terminate() vì nó không an toàn cho Python
            # Chỉ rely vào cờ _is_running
