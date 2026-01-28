# trading_core/config_loader.py
# Module này cung cấp các hằng số và cấu hình cho các thành phần bên trong trading_core
# Nó sẽ lấy dữ liệu từ app.config_manager

from app.config_manager import config_manager

# --- Cấu hình Giao dịch chung ---
TIMEFRAME = config_manager.get('trading.timeframe', '1h')
TIMEFRAME_SMALLER = config_manager.get('trading.timeframe_smaller', '15m')
RISK_PERCENT_PER_TRADE = float(config_manager.get('trading.risk_percent_per_trade', 1.0))

# --- Cấu hình Rủi ro ---
STOP_LOSS_POINTS = int(config_manager.get('risk_management.mt5.stop_loss_points', 2000))
TAKE_PROFIT_POINTS = int(config_manager.get('risk_management.mt5.take_profit_points', 4000))
STOP_LOSS_PERCENT = float(config_manager.get('risk_management.binance.stop_loss_percent', 2.0))
TAKE_PROFIT_PERCENT = float(config_manager.get('risk_management.binance.take_profit_percent', 4.0))

# --- Cấu hình khác ---
LOG_FILE = config_manager.get('logging.log_file', 'bot.log')

# --- Cấu hình Nền tảng ---
PLATFORM = config_manager.get('platform', 'mt5')

# --- Cấu hình MT5 ---
MT5_LOGIN = int(config_manager.get('mt5.login', 0))
MT5_PASSWORD = config_manager.get('mt5.password', '')
MT5_SERVER = config_manager.get('mt5.server', '')
MT5_PATH = config_manager.get('mt5.path', '')
MT5_SYMBOL = config_manager.get('mt5.symbol', '')

# --- Cấu hình Binance ---
BINANCE_API_KEY = config_manager.get('binance.api_key', '')
BINANCE_SECRET_KEY = config_manager.get('binance.secret_key', '')
BINANCE_SYMBOL = config_manager.get('binance.symbol', 'BTC/USDT')

# --- Cấu hình Kill Zones ---
KILL_ZONES = config_manager.get('kill_zones', [])
