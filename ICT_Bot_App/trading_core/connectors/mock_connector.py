import pandas as pd
from .base_connector import BaseConnector

class MockConnector(BaseConnector):
    def __init__(self, signals=None, data_file='mock_data.csv'):
        self.signals = signals
        self.data_file = data_file
        self.df = None

    def connect(self):
        try:
            self.df = pd.read_csv(self.data_file)
            self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
            self.df.set_index('timestamp', inplace=True)
            self.log(f"Mock data loaded from {self.data_file}")
            return True
        except Exception as e:
            self.log(f"Failed to load mock data: {e}")
            return False

    def disconnect(self):
        self.log("Mock connector disconnected.")

    def fetch_ohlcv(self, timeframe: str, limit: int) -> pd.DataFrame | None:
        if self.df is None:
            return None
        return self.df.copy()

    def get_account_balance(self) -> float | None:
        return 10000.0

    def get_symbol_info(self) -> object | None:
        class MockSymbolInfo:
            def __init__(self):
                self.point = 0.01
                self.volume_step = 0.01
                self.volume_min = 0.01
                self.volume_max = 1000.0
                self.tick_value = 0.01
                self.tick_size = 0.01
        return MockSymbolInfo()

    def place_order(self, order_type: str, quantity: float, sl_price: float, tp_price: float, comment: str = "") -> str | int | None:
        return 12345 
        
    def get_open_positions(self) -> list | None:
        return []

    def get_symbol(self) -> str:
        return "BTCUSDm"

    def get_all_tradable_symbols(self) -> list[str]:
        return ["BTCUSDm", "ETHUSDm", "XAUUSDm"]

    def log(self, message: str):
        if self.signals:
            self.signals.log_message.emit(message)
        else:
            try:
                print(message)
            except UnicodeEncodeError:
                print(message.encode('utf-8', 'ignore').decode('ascii', 'ignore'))
