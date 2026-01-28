import ccxt
import pandas as pd
from .base_connector import BaseConnector
from ..config_loader import BINANCE_API_KEY, BINANCE_SECRET_KEY, BINANCE_SYMBOL

class BinanceConnector(BaseConnector):
    def __init__(self, signals=None):
        self.exchange = ccxt.binance({
            'apiKey': BINANCE_API_KEY,
            'secret': BINANCE_SECRET_KEY,
            'options': {'defaultType': 'future'},
            'enableRateLimit': True,
        })
        self.symbol = BINANCE_SYMBOL
        self.signals = signals

    def log(self, message):
        """Gửi log thông qua signal nếu có, nếu không thì print."""
        if self.signals:
            self.signals.log_message.emit(message)
        else:
            print(message)

    def connect(self):
        self.log("Đang kết nối tới Binance...")
        self.exchange.load_markets()
        self.log("Kết nối Binance thành công.")

    def disconnect(self):
        self.log("Ngắt kết nối Binance.")
        # ccxt không có hàm disconnect rõ ràng, sẽ được xử lý khi thoát chương trình

    def get_symbol(self):
        return self.symbol

    def get_account_balance(self):
        """Lấy số dư tài khoản hiện tại."""
        try:
            balance = self.exchange.fetch_balance()
            # Lấy số dư USDT (hoặc token cơ bản của bạn)
            usdt_balance = balance['total']['USDT']
            # Phát tín hiệu cập nhật tài khoản
            if self.signals:
                self.signals.account_summary.emit({'balance': usdt_balance, 'pnl': 0}) # PNL cần logic riêng
            return usdt_balance
        except Exception as e:
            self.log(f"[Binance] Lỗi khi lấy số dư tài khoản: {e}")
            return None

    def get_symbol_info(self):
        """Lấy thông tin chi tiết của symbol."""
        try:
            market = self.exchange.market(self.symbol)
            # Trả về một object giả lập có các thuộc tính cần thiết cho strategy
            class MockSymbolInfo:
                def __init__(self, market):
                    self.tick_value = market.get('info', {}).get('tickSize', 0.01) # Giả định
                    self.tick_size = market.get('info', {}).get('tickSize', 0.01) # Giả định
                    self.volume_step = market.get('info', {}).get('quantityPrecision', 1) # Giả định
                    self.volume_min = market.get('limits', {}).get('amount', {}).get('min', 0.001)
                    self.volume_max = market.get('limits', {}).get('amount', {}).get('max', 1000000)
                    self.point = market.get('precision', {}).get('price', 0.01) # Giả định
            return MockSymbolInfo(market)
        except Exception as e:
            self.log(f"[Binance] Lỗi khi lấy thông tin symbol: {e}")
            return None

    def fetch_ohlcv(self, timeframe, limit=100):
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            self.log(f"[Binance] Lỗi khi lấy dữ liệu OHLCV: {e}")
            return None

    def place_order(self, order_type, quantity, sl_price, tp_price):
        try:
            side = 'buy' if order_type == 'long' else 'sell'
            market_order = self.exchange.create_market_order(self.symbol, side, quantity)
            self.log(f"[Binance] Đã đặt lệnh market {side} {quantity} {self.symbol}.")

            # Đặt lệnh SL/TP
            sl_side = 'sell' if side == 'buy' else 'buy'
            sl_params = {'stopPrice': sl_price, 'reduceOnly': True}
            self.exchange.create_order(self.symbol, 'STOP_MARKET', sl_side, quantity, params=sl_params)
            
            tp_params = {'stopPrice': tp_price, 'reduceOnly': True}
            self.exchange.create_order(self.symbol, 'TAKE_PROFIT_MARKET', sl_side, quantity, params=tp_params)
            
            self.log(f"[Binance] Đã đặt lệnh SL tại {sl_price} và TP tại {tp_price}.")
            # Phát tín hiệu lệnh mới
            if self.signals:
                self.signals.new_position.emit({
                    'id': str(market_order['id']),
                    'symbol': self.symbol,
                    'side': order_type.upper(),
                    'quantity': quantity,
                    'entry_price': market_order.get('price', 0),
                    'sl': sl_price,
                    'tp': tp_price,
                    'status': 'OPEN'
                })
            return market_order['id']
        except Exception as e:
            self.log(f"[Binance] Lỗi khi đặt lệnh: {e}")
            return None

    def get_open_positions(self):
        try:
            positions = self.exchange.fetch_positions([self.symbol])
            open_positions = [p for p in positions if float(p.get('contracts', 0)) != 0]
            return len(open_positions) > 0
        except Exception as e:
            self.log(f"[Binance] Lỗi khi kiểm tra vị thế: {e}")
            return False

