# Base Connector
from abc import ABC, abstractmethod
import pandas as pd # Import pandas cho kiểu trả về DataFrame

class BaseConnector(ABC):
    @abstractmethod
    def connect(self) -> bool:
        """Kết nối tới sàn giao dịch. Trả về True nếu thành công, False nếu thất bại."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Ngắt kết nối khỏi sàn giao dịch."""
        pass

    @abstractmethod
    def get_symbol(self) -> str:
        """Trả về tên symbol đang giao dịch (e.g., 'BTCUSDm', 'BTC/USDT')."""
        pass

    @abstractmethod
    def get_account_balance(self) -> float | None:
        """Lấy số dư tài khoản hiện tại."""
        pass

    @abstractmethod
    def get_symbol_info(self) -> object | None:
        """Lấy thông tin chi tiết của symbol."""
        pass

    @abstractmethod
    def fetch_ohlcv(self, timeframe: str, limit: int) -> pd.DataFrame | None:
        """Lấy dữ liệu OHLCV (Open, High, Low, Close, Volume) của symbol."""
        pass

    @abstractmethod
    def place_order(self, order_type: str, quantity: float, sl_price: float, tp_price: float, comment: str = "") -> str | int | None:
        """Đặt một lệnh giao dịch."""
        pass

    @abstractmethod
    def get_open_positions(self) -> list | None:
        """Lấy danh sách các vị thế đang mở. Trả về list hoặc None nếu lỗi."""
        pass

    @abstractmethod
    def get_all_tradable_symbols(self) -> list[str]:
        """Lấy danh sách tất cả các symbol có thể giao dịch trên nền tảng."""
        pass
