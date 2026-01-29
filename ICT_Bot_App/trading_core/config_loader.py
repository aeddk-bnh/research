# trading_core/config_loader.py
# Module này cung cấp các hằng số và cấu hình cho các thành phần bên trong trading_core
# Nó sẽ lấy dữ liệu từ app.config_manager

from app.config_manager import config_manager

# Helper function for safe type conversion
def _safe_float(value, default):
    try:
        return float(value) if value is not None else float(default)
    except (ValueError, TypeError):
        return float(default)

def _safe_int(value, default):
    try:
        return int(value) if value is not None else int(default)
    except (ValueError, TypeError):
        return int(default)

# --- Cấu hình Giao dịch chung ---
TIMEFRAME = str(config_manager.get('trading.timeframe', '1h'))
TIMEFRAME_SMALLER = str(config_manager.get('trading.timeframe_smaller', '15m'))
RISK_PERCENT_PER_TRADE = _safe_float(config_manager.get('trading.risk_percent_per_trade', 1.0), 1.0)
TAKE_PROFIT_RR = _safe_float(config_manager.get('trading.take_profit_rr', 2.0), 2.0)

# --- Cấu hình Rủi ro ---
STOP_LOSS_POINTS = _safe_int(config_manager.get('risk_management.mt5.stop_loss_points', 2000), 2000)
TAKE_PROFIT_POINTS = _safe_int(config_manager.get('risk_management.mt5.take_profit_points', 4000), 4000)
STOP_LOSS_PERCENT = _safe_float(config_manager.get('risk_management.binance.stop_loss_percent', 2.0), 2.0)
TAKE_PROFIT_PERCENT = _safe_float(config_manager.get('risk_management.binance.take_profit_percent', 4.0), 4.0)

# --- Cấu hình khác ---
LOG_FILE = str(config_manager.get('logging.log_file', 'bot.log'))

# --- Cấu hình Nền tảng ---
PLATFORM = str(config_manager.get('platform', 'mt5'))

# --- Cấu hình MT5 ---
MT5_LOGIN = _safe_int(config_manager.get('mt5.login', 0), 0)
MT5_PASSWORD = str(config_manager.get('mt5.password', ''))
MT5_SERVER = str(config_manager.get('mt5.server', ''))
MT5_PATH = str(config_manager.get('mt5.path', ''))
MT5_SYMBOL = str(config_manager.get('mt5.symbol', ''))

# --- Cấu hình Binance ---
BINANCE_API_KEY = str(config_manager.get('binance.api_key', ''))
BINANCE_SECRET_KEY = str(config_manager.get('binance.secret_key', ''))
BINANCE_SYMBOL = str(config_manager.get('binance.symbol', 'BTC/USDT'))

# --- Cấu hình Kill Zones ---
KILL_ZONES = config_manager.get('kill_zones', [])
