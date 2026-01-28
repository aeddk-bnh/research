import ccxt
import pandas as pd
from .base_connector import BaseConnector
from config import BINANCE_API_KEY, BINANCE_SECRET_KEY, BINANCE_SYMBOL

class BinanceConnector(BaseConnector):
    def __init__(self):
        self.exchange = ccxt.binance({
            'apiKey': BINANCE_API_KEY,
            'secret': BINANCE_SECRET_KEY,
            'options': {'defaultType': 'future'},
            'enableRateLimit': True,
        })
        self.symbol = BINANCE_SYMBOL

    def connect(self):
        print("Đang kết nối tới Binance...")
        self.exchange.load_markets()
        print("Kết nối Binance thành công.")

    def disconnect(self):
        print("Ngắt kết nối Binance.")
        # ccxt không có hàm disconnect rõ ràng, sẽ được xử lý khi thoát chương trình

    def get_symbol(self):
        return self.symbol

    def fetch_ohlcv(self, timeframe, limit=100):
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            print(f"[Binance] Lỗi khi lấy dữ liệu OHLCV: {e}")
            return None

    def place_order(self, order_type, quantity, sl_price, tp_price):
        try:
            side = 'buy' if order_type == 'long' else 'sell'
            market_order = self.exchange.create_market_order(self.symbol, side, quantity)
            print(f"[Binance] Đã đặt lệnh market {side} {quantity} {self.symbol}.")

            # Đặt lệnh SL/TP
            sl_side = 'sell' if side == 'buy' else 'buy'
            sl_params = {'stopPrice': sl_price, 'reduceOnly': True}
            self.exchange.create_order(self.symbol, 'STOP_MARKET', sl_side, quantity, params=sl_params)
            
            tp_params = {'stopPrice': tp_price, 'reduceOnly': True}
            self.exchange.create_order(self.symbol, 'TAKE_PROFIT_MARKET', sl_side, quantity, params=tp_params)
            
            print(f"[Binance] Đã đặt lệnh SL tại {sl_price} và TP tại {tp_price}.")
            return market_order['id']
        except Exception as e:
            print(f"[Binance] Lỗi khi đặt lệnh: {e}")
            return None

    def get_open_positions(self):
        try:
            positions = self.exchange.fetch_positions([self.symbol])
            open_positions = [p for p in positions if float(p.get('contracts', 0)) != 0]
            return len(open_positions) > 0
        except Exception as e:
            print(f"[Binance] Lỗi khi kiểm tra vị thế: {e}")
            return False
