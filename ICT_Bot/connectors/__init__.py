from connectors.binance_connector import BinanceConnector
from connectors.mt5_connector import MT5Connector

def get_connector(platform_name):
    if platform_name == 'binance':
        return BinanceConnector()
    elif platform_name == 'mt5':
        return MT5Connector()
    else:
        raise ValueError(f"Nền tảng không được hỗ trợ: {platform_name}")
