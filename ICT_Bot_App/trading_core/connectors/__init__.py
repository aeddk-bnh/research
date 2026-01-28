from .binance_connector import BinanceConnector
from .mt5_connector import MT5Connector
from .base_connector import BaseConnector # Import BaseConnector

def get_connector(platform_name: str, signals=None) -> BaseConnector | None:
    """
    Trả về một instance của connector dựa trên tên nền tảng.
    """
    if platform_name == 'binance':
        return BinanceConnector(signals=signals)
    elif platform_name == 'mt5':
        return MT5Connector(signals=signals)
    else:
        # Thay vì raise Exception, có thể log lỗi và trả về None
        if signals:
            signals.log_message.emit(f"Lỗi: Nền tảng '{platform_name}' không được hỗ trợ.")
        else:
            print(f"Lỗi: Nền tảng '{platform_name}' không được hỗ trợ.")
        return None