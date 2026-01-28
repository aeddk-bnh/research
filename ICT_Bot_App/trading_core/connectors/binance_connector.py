import ccxt # type: ignore
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

    def log(self, message: str) -> None:
        """Gửi log thông qua signal nếu có, nếu không thì print."""
        if self.signals:
            self.signals.log_message.emit(message)
        else:
            print(message)

    def connect(self) -> bool:
        self.log("Đang kết nối tới Binance...")
        try:
            self.exchange.load_markets()
            self.log("Kết nối Binance thành công.")
            return True
        except Exception as e:
            self.log(f"Kết nối Binance thất bại: {e}")
            return False

    def disconnect(self) -> None:
        self.log("Ngắt kết nối Binance.")
        # ccxt không có hàm disconnect rõ ràng, sẽ được xử lý khi thoát chương trình

    def get_symbol(self) -> str:
        return str(self.symbol) # Đảm bảo trả về string

    def get_account_balance(self) -> float | None:
        """Lấy số dư tài khoản hiện tại."""
        try:
            balance_data = self.exchange.fetch_balance()
            # Lấy số dư USDT (hoặc token cơ bản của bạn)
            usdt_balance = balance_data.get('total', {}).get('USDT')
            if usdt_balance is None:
                self.log("[Binance] Không tìm thấy số dư USDT.")
                return None
            
            # PNL cần logic riêng. Tạm thời giả định 0 hoặc tính toán từ lệnh đang mở.
            # Với Binance Futures, PnL thường nằm trong fetch_positions hoặc fetch_balance for futures
            # Hiện tại, chỉ gửi balance.
            if self.signals:
                # Sẽ cần logic phức tạp hơn để tính PnL thực tế cho Binance
                self.signals.account_summary.emit({'balance': float(usdt_balance), 'pnl': 0.0}) 
            return float(usdt_balance)
        except Exception as e:
            self.log(f"[Binance] Lỗi khi lấy số dư tài khoản: {e}")
            return None

    class BinanceSymbolInfo:
        """Mock object để giả lập MetaTrader5.symbol_info cho Binance."""
        def __init__(self, market_data):
            self._market = market_data
            # Các giá trị này cần được kiểm tra và điều chỉnh tùy theo yêu cầu của chiến lược
            self.point = market_data.get('precision', {}).get('price', 0.00001) # Ví dụ: 0.01 cho BTC/USDT, 0.00001 cho FX
            self.tick_size = market_data.get('precision', {}).get('price', 0.00001)
            self.tick_value = self.tick_size # Giả định cho đơn giản
            self.volume_step = market_data.get('limits', {}).get('amount', {}).get('min', 0.001)
            self.volume_min = market_data.get('limits', {}).get('amount', {}).get('min', 0.001)
            self.volume_max = market_data.get('limits', {}).get('amount', {}).get('max', 1000000)

    def get_symbol_info(self) -> object | None:
        """Lấy thông tin chi tiết của symbol."""
        try:
            market = self.exchange.market(self.symbol)
            if market is None:
                self.log(f"[Binance] Không tìm thấy thông tin thị trường cho symbol: {self.symbol}")
                return None
            return self.BinanceSymbolInfo(market)
        except Exception as e:
            self.log(f"[Binance] Lỗi khi lấy thông tin symbol: {e}")
            return None

    def fetch_ohlcv(self, timeframe: str, limit: int) -> pd.DataFrame | None:
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True) # Đặt timestamp làm index
            return df[['open', 'high', 'low', 'close', 'volume']]
        except Exception as e:
            self.log(f"[Binance] Lỗi khi lấy dữ liệu OHLCV: {e}")
            return None

    def place_order(self, order_type: str, quantity: float, sl_price: float, tp_price: float) -> str | int | None:
        try:
            side = 'buy' if order_type == 'long' else 'sell'
            market_order = self.exchange.create_market_order(self.symbol, side, quantity)
            self.log(f"[Binance] Đã đặt lệnh market {side} {quantity} {self.symbol}. ID: {market_order['id']}")

            # Đặt lệnh SL/TP (Binance Futures)
            # Lưu ý: cần kiểm tra xem lệnh market_order có id hợp lệ không
            order_id = market_order.get('id')
            if order_id:
                # Binance Futures thường dùng stop-market cho SL/TP
                # SL
                sl_type = 'STOP_MARKET'
                tp_type = 'TAKE_PROFIT_MARKET'
                
                self.exchange.create_order(self.symbol, sl_type, side, quantity, price=None, params={'stopPrice': sl_price, 'reduceOnly': True, 'closePosition': True})
                self.log(f"[Binance] Đã đặt SL tại {sl_price}.")
                
                # TP
                self.exchange.create_order(self.symbol, tp_type, side, quantity, price=None, params={'stopPrice': tp_price, 'reduceOnly': True, 'closePosition': True})
                self.log(f"[Binance] Đã đặt TP tại {tp_price}.")

            # Phát tín hiệu lệnh mới
            if self.signals:
                self.signals.new_position.emit({
                    'id': str(order_id),
                    'symbol': self.symbol,
                    'side': order_type.upper(),
                    'quantity': quantity,
                    'entry_price': market_order.get('price', 0), # Giá thực tế của lệnh
                    'sl': sl_price,
                    'tp': tp_price,
                    'status': 'OPEN'
                })
            return order_id
        except Exception as e:
            self.log(f"[Binance] Lỗi khi đặt lệnh: {e}")
            return None

    def get_open_positions(self) -> bool:
        try:
            # Đối với Binance Futures, cần kiểm tra các vị thế
            positions = self.exchange.fetch_positions([self.symbol])
            open_positions = [p for p in positions if float(p.get('contracts', 0)) != 0]
            return len(open_positions) > 0
        except Exception as e:
            self.log(f"[Binance] Lỗi khi kiểm tra vị thế: {e}")
            return False
