from datetime import datetime
import pandas as pd
import pytz
from .pd_arrays import detect_fvg

# Khung giờ Silver Bullet (EST)
SILVER_BULLET_WINDOWS = [
    {'name': 'London Open', 'start': 3, 'end': 4},      # 03:00 - 04:00
    {'name': 'NY AM Session', 'start': 10, 'end': 11},  # 10:00 - 11:00
    {'name': 'NY PM Session', 'start': 14, 'end': 15}   # 14:00 - 15:00
]

def is_silver_bullet_time(timestamp):
    """
    Kiểm tra xem thời gian hiện tại có nằm trong khung Silver Bullet không.
    """
    if timestamp.tzinfo is None:
        timestamp = pytz.utc.localize(timestamp)
        
    ny_tz = pytz.timezone('America/New_York')
    ny_time = timestamp.astimezone(ny_tz)
    
    for window in SILVER_BULLET_WINDOWS:
        if window['start'] <= ny_time.hour < window['end']:
            return True, window['name']
            
    return False, None

def detect_silver_bullet_setup(df, current_price, bias, signals=None):
    """
    Tìm setup Silver Bullet:
    1. Đang trong khung giờ Silver Bullet
    2. Xuất hiện FVG trong khung giờ này (M5 hoặc M15)
    3. Giá retest FVG
    """
    if df.empty:
        return False, None, None

    # Lấy nến hiện tại
    last_candle = df.iloc[-1]
    current_time = last_candle.name # Timestamp index
    
    in_window, window_name = is_silver_bullet_time(current_time)
    
    if not in_window:
        return False, None, None
        
    # Chỉ tìm FVG được tạo ra TRONG khung giờ này (hoặc ngay trước đó 1 chút)
    # Lấy 12 nến gần nhất (1 tiếng cho M5)
    recent_df = df.iloc[-12:].copy()
    
    if 'fvg_bullish_high' not in recent_df.columns:
        recent_df = detect_fvg(recent_df)
        
    # Logic entry theo Bias
    if bias == 'long':
        # Tìm Bullish FVG gần nhất
        fvg_candidates = recent_df[recent_df['fvg_bullish_high'].notna()]
        
        if not fvg_candidates.empty:
            best_fvg = fvg_candidates.iloc[-1]
            fvg_high = best_fvg['fvg_bullish_high']
            fvg_low = best_fvg['fvg_bullish_low']
            
            # Entry condition: Giá hiện tại chạm vào FVG
            if current_price <= fvg_high and current_price >= fvg_low:
                if signals: 
                    signals.log_message.emit(f"[Silver Bullet] {window_name} Bullish Setup found at {fvg_high}")
                return True, fvg_high, fvg_low # Entry, SL (dưới FVG)
                
    elif bias == 'short':
        # Tìm Bearish FVG gần nhất
        fvg_candidates = recent_df[recent_df['fvg_bearish_high'].notna()]
        
        if not fvg_candidates.empty:
            best_fvg = fvg_candidates.iloc[-1]
            fvg_high = best_fvg['fvg_bearish_high']
            fvg_low = best_fvg['fvg_bearish_low']
            
            # Entry condition: Giá hiện tại chạm vào FVG
            if current_price >= fvg_low and current_price <= fvg_high:
                if signals: 
                    signals.log_message.emit(f"[Silver Bullet] {window_name} Bearish Setup found at {fvg_low}")
                return True, fvg_low, fvg_high # Entry, SL (trên FVG)
                
    return False, None, None
