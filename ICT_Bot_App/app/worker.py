from PySide6.QtCore import QThread, Signal
import time
from datetime import datetime
import traceback

from trading_core.time_filter import is_kill_zone_time, get_kill_zone_status
from trading_core.strategy import execute_strategy
from trading_core.connectors import get_connector
from app.signals import WorkerSignals, BacktestSignals
from app.config_manager import config_manager
from trading_core.backtester import Backtester

class BotWorker(QThread):
    def __init__(self):
        super().__init__()
        self.signals = WorkerSignals()
        self._is_running = True
        self.connector = None
        
        self.last_trade_close_time = None
        self.previous_position_count = 0
        self.cooldown_period = 1800 

    def run(self):
        self.signals.log_message.emit("Khởi tạo bot trong worker...")
        
        platform = config_manager.get('platform', 'mt5')
        if not platform: 
            self.signals.log_message.emit("Lỗi: Nền tảng không được cấu hình.")
            self.signals.bot_status.emit("Lỗi cấu hình")
            return

        try:
            self.connector = get_connector(platform, signals=self.signals)
            if self.connector is None: 
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
        if not symbol: 
            self.signals.log_message.emit("Lỗi: Không thể lấy symbol từ connector.")
            self.signals.bot_status.emit("Lỗi cấu hình")
            return
        self.signals.log_message.emit(f"Theo dõi cặp: {symbol}")
        self.signals.log_message.emit("Bot sẽ chỉ tìm kiếm cơ hội trong các khung giờ Kill Zone.")
        self.signals.bot_status.emit("Đang chạy")
        self.signals.market_bias.emit("Chưa xác định") 

        try:
             initial_positions = self.connector.get_open_positions()
             self.previous_position_count = len(initial_positions) if initial_positions else 0
        except:
             self.previous_position_count = 0

        while self._is_running:
            try:
                current_positions = self.connector.get_open_positions()
                current_count = len(current_positions) if current_positions else 0
                
                if current_count < self.previous_position_count:
                    self.last_trade_close_time = time.time()
                    self.signals.log_message.emit(f"Phát hiện lệnh vừa đóng. Kích hoạt hạ nhiệt {self.cooldown_period/60} phút.")
                
                self.previous_position_count = current_count

                if self.last_trade_close_time:
                    elapsed = time.time() - self.last_trade_close_time
                    if elapsed < self.cooldown_period:
                        remaining = int((self.cooldown_period - elapsed) / 60)
                        self.signals.log_message.emit(f"Đang hạ nhiệt... Còn lại {remaining} phút.")
                        time.sleep(60) 
                        continue
                    else:
                        self.last_trade_close_time = None 
                        self.signals.log_message.emit("Đã hết thời gian hạ nhiệt. Tiếp tục giao dịch.")

                if is_kill_zone_time(signals=self.signals):
                    self.signals.log_message.emit(f"\n[{datetime.now().strftime('%H:%M:%S')}] Đang trong Kill Zone. Bắt đầu quét tín hiệu...")
                    execute_strategy(self.connector, signals=self.signals) 
                else:
                    self.signals.log_message.emit(f"[{datetime.now().strftime('%H:%M:%S')}] Ngoài giờ Kill Zone. Đang chờ...")
                    self.signals.market_bias.emit("Chưa kích hoạt (Ngoài KZ)")
                    time.sleep(300) 
                
                time.sleep(60)

            except KeyboardInterrupt:
                self.signals.log_message.emit("Nhận tín hiệu Ctrl+C, đang dừng...")
                break
            except Exception as e:
                self.signals.log_message.emit(f"\nLỗi trong vòng lặp chính: {e}")
                self.signals.log_message.emit(f"Chi tiết lỗi:\n{traceback.format_exc()}")
                time.sleep(60)
        
        self.signals.log_message.emit("Bot đã dừng.")
        self.signals.bot_status.emit("Đã dừng")
        self.signals.market_bias.emit("Đã dừng") 
        if self.connector:
            self.connector.disconnect()
            self.signals.log_message.emit("Đã ngắt kết nối.")

    def stop(self):
        """Dừng vòng lặp của bot một cách an toàn."""
        self._is_running = False
        if self.wait(5000):
            print("BotWorker đã dừng thành công.")
        else:
            print("BotWorker không dừng kịp thời, buộc kết thúc.")


class BacktestWorker(QThread):
    def __init__(self, params: dict):
        super().__init__()
        self.params = params
        self.signals = BacktestSignals()
        self._is_running = True

    def run(self):
        self.signals.log_message.emit("Khởi tạo Backtester...")
        try:
            backtester = Backtester(self.params, self.signals)
            backtester.run()
        except Exception as e:
            self.signals.log_message.emit(f"Lỗi nghiêm trọng trong Backtester: {e}")
            self.signals.log_message.emit(f"Chi tiết: {traceback.format_exc()}")
        
        self.signals.log_message.emit("Worker backtest đã hoàn thành.")

    def stop(self):
        self._is_running = False
