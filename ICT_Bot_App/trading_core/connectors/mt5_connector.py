import MetaTrader5 as mt5 # type: ignore
import pandas as pd
import pytz
from datetime import datetime
from .base_connector import BaseConnector
from ..config_loader import MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, MT5_PATH, MT5_SYMBOL

class MT5Connector(BaseConnector):
    def __init__(self, signals=None):
        self.symbol = MT5_SYMBOL
        self.timezone = pytz.timezone("Etc/UTC")
        self.signals = signals

    def log(self, message: str) -> None:
        """Gửi log thông qua signal nếu có, nếu không thì print."""
        if self.signals:
            self.signals.log_message.emit(message)
        else:
            print(message)

    def connect(self) -> bool:
        self.log("Đang kết nối tới MetaTrader 5...")
        # Đảm bảo khởi tạo MT5 với các tham số đúng
        if not mt5.initialize(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER, path=MT5_PATH):
            self.log(f"Kết nối MT5 thất bại, lỗi = {mt5.last_error()}")
            return False
        self.log("Kết nối MT5 thành công.")
        return True

    def disconnect(self) -> None:
        self.log("Ngắt kết nối MT5.")
        mt5.shutdown()

    def get_symbol(self) -> str:
        # Đảm bảo self.symbol luôn là str
        return str(self.symbol)

    def get_account_balance(self) -> float | None:
        """Lấy số dư tài khoản hiện tại."""
        account_info = mt5.account_info()
        if account_info is None:
            self.log("[MT5] Không thể lấy thông tin tài khoản.")
            return None
        balance = account_info.balance
        # Phát tín hiệu cập nhật tài khoản
        if self.signals:
            # account_info.profit có thể không có hoặc là None
            profit = getattr(account_info, 'profit', 0.0) 
            self.signals.account_summary.emit({'balance': float(balance), 'pnl': float(profit)})
        return float(balance)

    def get_symbol_info(self) -> object | None: # object vì kiểu của mt5.symbol_info không phải là kiểu Python chuẩn
        """Lấy thông tin chi tiết của symbol."""
        s_info = mt5.symbol_info(self.symbol)
        if s_info is None:
            self.log(f"[MT5] Không thể lấy thông tin symbol: {self.symbol}")
            return None
        return s_info # MetaTrader5.symbol_info trả về một object có các thuộc tính cần thiết

    def fetch_ohlcv(self, timeframe: str, limit: int) -> pd.DataFrame | None:
        try:
            tf_map = {
                'M1': mt5.TIMEFRAME_M1, 'M5': mt5.TIMEFRAME_M5, 'M15': mt5.TIMEFRAME_M15,
                'H1': mt5.TIMEFRAME_H1, 'H4': mt5.TIMEFRAME_H4, 'D1': mt5.TIMEFRAME_D1,
                # Add old keys for compatibility if needed, but new UI uses the above
                '1m': mt5.TIMEFRAME_M1, '5m': mt5.TIMEFRAME_M5, '15m': mt5.TIMEFRAME_M15,
                '1h': mt5.TIMEFRAME_H1, '4h': mt5.TIMEFRAME_H4, '1d': mt5.TIMEFRAME_D1,
            }
            rates = mt5.copy_rates_from_pos(self.symbol, tf_map[timeframe], 0, limit)
            if rates is None:
                self.log(f"[MT5] Không lấy được dữ liệu cho {self.symbol}. Lỗi: {mt5.last_error()}")
                return None
            
            df = pd.DataFrame(rates)
            df['timestamp'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('timestamp', inplace=True) # Đặt timestamp làm index
            df.rename(columns={'tick_volume': 'volume'}, inplace=True)
            return df[['open', 'high', 'low', 'close', 'volume']]
        except Exception as e:
            self.log(f"[MT5] Lỗi khi lấy dữ liệu OHLCV: {e}")
            return None

    def place_order(self, order_type: str, quantity: float, sl_price: float, tp_price: float) -> str | int | None:
        symbol_info = self.get_symbol_info()
        if symbol_info is None:
            self.log(f"[MT5] Không tìm thấy thông tin symbol: {self.symbol}")
            return None

        # Lấy giá hiện tại
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            self.log(f"[MT5] Không lấy được tick info cho {self.symbol}")
            return None

        price = tick.ask if order_type == 'long' else tick.bid
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": float(quantity),
            "type": mt5.ORDER_TYPE_BUY if order_type == 'long' else mt5.ORDER_TYPE_SELL,
            "price": price,
            "sl": float(sl_price),
            "tp": float(tp_price),
            "deviation": 20, # Deviation trong points
            "magic": 234000,
            "comment": "ICT Bot Order",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC, # Immediate or Cancel
        }
        
        try:
            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.log(f"[MT5] Đặt lệnh thất bại, retcode={result.retcode}, comment={result.comment}")
                return None
            
            self.log(f"[MT5] Đã đặt lệnh thành công. Order ID: {result.order}")
            # Phát tín hiệu lệnh mới
            if self.signals:
                self.signals.new_position.emit({
                    'id': str(result.order),
                    'symbol': self.symbol,
                    'side': order_type.upper(),
                    'quantity': quantity,
                    'entry_price': result.price, # Giá thực tế của lệnh
                    'sl': sl_price,
                    'tp': tp_price,
                    'status': 'OPEN'
                })
            return result.order
        except Exception as e:
            self.log(f"[MT5] Lỗi khi đặt lệnh: {e}")
            return None

    def get_open_positions(self) -> list | None:
        """Lấy danh sách các vị thế đang mở. Trả về list hoặc None nếu lỗi."""
        try:
            positions = mt5.positions_get(symbol=self.symbol)
            if positions is None:
                # Lỗi này có thể do mất kết nối
                self.log(f"[MT5] Không thể lấy vị thế, có thể đã mất kết nối. Lỗi: {mt5.last_error()}")
                return None # Sử dụng None để báo hiệu lỗi / mất kết nối
            return list(positions)
        except Exception as e:
            self.log(f"[MT5] Lỗi khi kiểm tra vị thế: {e}")
            return None

    def get_all_tradable_symbols(self) -> list[str]:
        """Lấy tất cả các symbol có thể giao dịch."""
        try:
            symbols = mt5.symbols_get()
            if symbols is not None:
                # Trả về danh sách tên các symbol
                return sorted([s.name for s in symbols])
            return []
        except Exception as e:
            self.log(f"[MT5] Lỗi khi lấy danh sách symbol: {e}")
            return []
