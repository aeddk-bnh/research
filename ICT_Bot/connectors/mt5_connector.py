import MetaTrader5 as mt5
import pandas as pd
import pytz
from datetime import datetime
from .base_connector import BaseConnector
from config import MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, MT5_PATH, MT5_SYMBOL

class MT5Connector(BaseConnector):
    def __init__(self):
        self.symbol = MT5_SYMBOL
        self.timezone = pytz.timezone("Etc/UTC") # MT5 server time is UTC

    def connect(self):
        print("Đang kết nối tới MetaTrader 5...")
        # Thử khởi tạo mà không có path và server, chỉ dùng login và password
        # Điều này giả định rằng MT5 đã chạy và đăng nhập sẵn, và ta sẽ xác thực tài khoản cụ thể
        if not mt5.initialize(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
            print(f"kết nối MT5 thất bại, lỗi = {mt5.last_error()}")
            return False
        print("Kết nối MT5 thành công.")
        return True

    def disconnect(self):
        print("Ngắt kết nối MT5.")
        mt5.shutdown()

    def get_symbol(self):
        return self.symbol

    def get_account_balance(self):
        """Lấy số dư tài khoản hiện tại."""
        account_info = mt5.account_info()
        if account_info is None:
            print("[MT5] Không thể lấy thông tin tài khoản.")
            return None
        return account_info.balance

    def get_symbol_info(self):
        """Lấy thông tin chi tiết của symbol."""
        return mt5.symbol_info(self.symbol)

    def fetch_ohlcv(self, timeframe, limit=100):
        try:
            tf_map = {
                '1m': mt5.TIMEFRAME_M1, '5m': mt5.TIMEFRAME_M5, '15m': mt5.TIMEFRAME_M15,
                '1h': mt5.TIMEFRAME_H1, '4h': mt5.TIMEFRAME_H4, '1d': mt5.TIMEFRAME_D1,
            }
            rates = mt5.copy_rates_from_pos(self.symbol, tf_map[timeframe], 0, limit)
            if rates is None:
                print(f"[MT5] Không lấy được dữ liệu cho {self.symbol}. Lỗi: {mt5.last_error()}")
                return None
            
            df = pd.DataFrame(rates)
            df['timestamp'] = pd.to_datetime(df['time'], unit='s')
            df.rename(columns={'tick_volume': 'volume'}, inplace=True)
            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        except Exception as e:
            print(f"[MT5] Lỗi khi lấy dữ liệu OHLCV: {e}")
            return None

    def place_order(self, order_type, quantity, sl_price, tp_price):
        symbol_info = self.get_symbol_info()
        if symbol_info is None:
            print(f"[MT5] Không tìm thấy thông tin symbol: {self.symbol}")
            return None

        point = symbol_info.point
        price = mt5.symbol_info_tick(self.symbol).ask if order_type == 'long' else mt5.symbol_info_tick(self.symbol).bid
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": float(quantity),
            "type": mt5.ORDER_TYPE_BUY if order_type == 'long' else mt5.ORDER_TYPE_SELL,
            "price": price,
            "sl": float(sl_price),
            "tp": float(tp_price),
            "deviation": 20,
            "magic": 234000,
            "comment": "ICT Bot Order",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        try:
            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                print(f"[MT5] Đặt lệnh thất bại, retcode={result.retcode}, comment={result.comment}")
                return None
            
            print(f"[MT5] Đã đặt lệnh thành công. Order ID: {result.order}")
            return result.order
        except Exception as e:
            print(f"[MT5] Lỗi khi đặt lệnh: {e}")
            return None

    def get_open_positions(self):
        try:
            positions = mt5.positions_get(symbol=self.symbol)
            if positions is None:
                return False
            return len(positions) > 0
        except Exception as e:
            print(f"[MT5] Lỗi khi kiểm tra vị thế: {e}")
            return False
