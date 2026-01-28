import os
from datetime import timezone

# --- Cấu hình Nền tảng ---
# Chọn 'binance' hoặc 'mt5'
PLATFORM = 'mt5' 

# --- Cấu hình API Binance ---
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', 'your_api_key_here')
BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY', 'your_secret_key_here')
BINANCE_SYMBOL = 'BTC/USDT'  # Định dạng cho CCXT

# --- Cấu hình MT5 (Exness) ---
# Điền thông tin đăng nhập của bạn vào đây
MT5_LOGIN = 270873003
MT5_PASSWORD = 'Mgnaermgnaer1.'
MT5_SERVER = 'Exness-MT5Trial17' # Kiểm tra lại tên server chính xác trong terminal MT5 của bạn
MT5_PATH = 'C:\\Program Files\\MetaTrader 5\\terminal64.exe' # Đường dẫn tới file thực thi MT5
MT5_SYMBOL = 'BTCUSDm' # Tên symbol có thể khác nhau, ví dụ: 'BTCUSD', 'BTCUSDT.m', 'BTCUSDm'

# --- Cấu hình Giao dịch chung ---
TIMEFRAME = '1h'    
TIMEFRAME_SMALLER = '15m' 
RISK_PERCENT_PER_TRADE = 1.0 # Rủi ro 1% tài khoản cho mỗi lệnh

# --- Cấu hình Thời gian (Kill Zones - theo múi giờ New York) ---
KILL_ZONES = [
    {'start': (19, 0), 'end': (22, 0)},   # Asian KZ (EST: 7PM - 10PM)
    {'start': (1, 0), 'end': (5, 0)},     # London KZ (EST: 1AM - 5AM)
    {'start': (7, 0), 'end': (10, 0)},    # NY KZ (EST: 7AM - 10AM)
    {'start': (10, 0), 'end': (12, 0)},   # London Close KZ (EST: 10AM - 12PM)
]

# --- Cấu hình Rủi ro ---
STOP_LOSS_POINTS = 2000 # Số points cho MT5 (tương đương 200 pips)
TAKE_PROFIT_POINTS = 4000 # Số points cho MT5 (tương đương 400 pips)
STOP_LOSS_PERCENT = 2.0  # Phần trăm cho Binance
TAKE_PROFIT_PERCENT = 4.0 # Phần trăm cho Binance

# --- Cấu hình khác ---
LOG_FILE = 'bot.log'
