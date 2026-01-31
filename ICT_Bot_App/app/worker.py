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
                self.signals.bot_status.emit("Lỗi cấu hình")
                return

            # Thử kết nối lần đầu
            self.signals.connection_status.emit("Đang kết nối...")
            if self.connector.connect():
                self.signals.log_message.emit(f"Đã kết nối thành công với {platform.upper()}.")
                self.signals.connection_status.emit("Đã kết nối")
            else:
                self.signals.connection_status.emit("Kết nối thất bại")
                self.signals.bot_status.emit("Lỗi kết nối")
                return
        except Exception as e:
            self.signals.log_message.emit(f"Lỗi kết nối: {e}")
            self.signals.bot_status.emit("Lỗi kết nối")
            self.signals.connection_status.emit("Lỗi kết nối")
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
             self.previous_position_count = len(initial_positions) if initial_positions is not None else 0
        except:
             self.previous_position_count = 0

        max_retries = 10
        retry_delay = 30 # giây

        while self._is_running:
            try:
                # 1. KIỂM TRA VÀ KHÔI PHỤC KẾT NỐI
                current_positions = self.connector.get_open_positions()
                
                if current_positions is None: # Tín hiệu mất kết nối
                    self.signals.connection_status.emit("Đang kết nối lại...")
                    self.signals.log_message.emit("Mất kết nối. Bắt đầu quá trình kết nối lại...")
                    
                    is_reconnected = False
                    for i in range(max_retries):
                        if not self._is_running: break
                        self.signals.log_message.emit(f"Đang thử kết nối lại lần {i+1}/{max_retries}...")
                        try:
                            self.connector.disconnect()
                            self.msleep(1000)
                            if self.connector.connect():
                                if self.connector.get_open_positions() is not None:
                                    self.signals.log_message.emit("Kết nối lại thành công!")
                                    self.signals.connection_status.emit("Đã kết nối")
                                    is_reconnected = True
                                    break
                        except Exception as e:
                            self.signals.log_message.emit(f"Lỗi khi kết nối lại: {e}")
                        
                        self.msleep(retry_delay * 1000)

                    if not is_reconnected or not self._is_running:
                        if self._is_running:
                            self.signals.log_message.emit("Không thể khôi phục kết nối. Dừng bot.")
                            self.signals.connection_status.emit("Mất kết nối")
                            self.signals.bot_status.emit("Lỗi kết nối")
                        break # Thoát khỏi vòng lặp chính
                    
                    current_positions = self.connector.get_open_positions()
                    if current_positions is None: break
                
                # 2. XỬ LÝ LOGIC BOT
                current_count = len(current_positions)
                
                if current_count < self.previous_position_count:
                    self.last_trade_close_time = time.time()
                    self.signals.log_message.emit(f"Phát hiện lệnh vừa đóng. Kích hoạt hạ nhiệt {self.cooldown_period/60} phút.")
                
                self.previous_position_count = current_count

                if self.last_trade_close_time:
                    elapsed = time.time() - self.last_trade_close_time
                    if elapsed < self.cooldown_period:
                        remaining = int((self.cooldown_period - elapsed) / 60)
                        self.signals.log_message.emit(f"Đang hạ nhiệt... Còn lại {remaining} phút.")
                        self.msleep(60000) 
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
                    self.msleep(300000) 
                
                self.msleep(60000)

            except Exception as e:
                self.signals.log_message.emit(f"\nLỗi trong vòng lặp chính: {e}")
                self.msleep(60000)
        
        self.signals.log_message.emit("Bot đã dừng.")
        self.signals.bot_status.emit("Đã dừng")
        self.signals.market_bias.emit("Đã dừng") 
        if self.connector:
            self.connector.disconnect()
            self.signals.log_message.emit("Đã ngắt kết nối.")

    def msleep(self, milliseconds):
        """Sleep interruptible by self._is_running."""
        for _ in range(int(milliseconds / 100)):
            if not self._is_running:
                break
            time.sleep(0.1)
        
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
