import pandas as pd
import numpy as np

# OTE Fibonacci Levels (Optimal Trade Entry)
OTE_FIB_LEVELS = {
    'shallow': 0.62,   # 62% - Mức OTE chính
    'optimal': 0.705,  # 70.5% - Mức OTE sweet spot (ICT recommend)
    'deep': 0.79       # 79% - Mức OTE deep
}


def calculate_ote_levels(swing_high: float, swing_low: float, direction: str) -> dict:
    """
    Tính toán các mức OTE Fibonacci dựa trên swing range.
    
    Args:
        swing_high: Điểm swing high
        swing_low: Điểm swing low
        direction: 'bullish' (retracement từ low lên) hoặc 'bearish' (retracement từ high xuống)
    
    Returns:
        dict với các mức Fibonacci:
        - ote_62: Mức 62%
        - ote_705: Mức 70.5% (sweet spot)
        - ote_79: Mức 79%
        - equilibrium: Mức 50%
    
    ICT OTE Logic:
    - Bullish: Giá retrace xuống từ swing high, ta tìm mức buy trong OTE zone
    - Bearish: Giá retrace lên từ swing low, ta tìm mức sell trong OTE zone
    """
    range_size = swing_high - swing_low
    
    if direction == 'bullish':
        # Bullish: OTE zone nằm ở phần dưới của range (discount)
        # Tính từ swing_high retrace xuống
        return {
            'ote_62': swing_high - (range_size * OTE_FIB_LEVELS['shallow']),
            'ote_705': swing_high - (range_size * OTE_FIB_LEVELS['optimal']),
            'ote_79': swing_high - (range_size * OTE_FIB_LEVELS['deep']),
            'equilibrium': swing_high - (range_size * 0.5),
            'swing_high': swing_high,
            'swing_low': swing_low
        }
    else:  # bearish
        # Bearish: OTE zone nằm ở phần trên của range (premium)
        # Tính từ swing_low retrace lên
        return {
            'ote_62': swing_low + (range_size * OTE_FIB_LEVELS['shallow']),
            'ote_705': swing_low + (range_size * OTE_FIB_LEVELS['optimal']),
            'ote_79': swing_low + (range_size * OTE_FIB_LEVELS['deep']),
            'equilibrium': swing_low + (range_size * 0.5),
            'swing_high': swing_high,
            'swing_low': swing_low
        }


def is_price_in_ote_zone(price: float, ote_levels: dict, direction: str) -> tuple[bool, str]:
    """
    Kiểm tra xem giá có nằm trong vùng OTE không.
    
    Args:
        price: Giá hiện tại
        ote_levels: Dict chứa các mức OTE
        direction: 'bullish' hoặc 'bearish'
    
    Returns:
        (bool, str): (có trong OTE zone không, mô tả vị trí)
    """
    ote_62 = ote_levels['ote_62']
    ote_705 = ote_levels['ote_705']
    ote_79 = ote_levels['ote_79']
    
    if direction == 'bullish':
        # Bullish OTE zone: giá nằm giữa ote_62 (cao) và ote_79 (thấp)
        if ote_79 <= price <= ote_62:
            if price <= ote_705:
                return True, 'deep_ote'  # Gần 70.5% - 79%
            else:
                return True, 'shallow_ote'  # Gần 62% - 70.5%
        elif price < ote_79:
            return False, 'below_ote'  # Quá sâu
        else:
            return False, 'above_ote'  # Chưa retrace đủ
    else:  # bearish
        # Bearish OTE zone: giá nằm giữa ote_62 (thấp) và ote_79 (cao)
        if ote_62 <= price <= ote_79:
            if price >= ote_705:
                return True, 'deep_ote'
            else:
                return True, 'shallow_ote'
        elif price > ote_79:
            return False, 'above_ote'
        else:
            return False, 'below_ote'


def get_recent_swing_range(df: pd.DataFrame, direction: str, lookback: int = 50) -> tuple[float | None, float | None]:
    """
    Tìm swing range gần nhất để tính OTE.
    
    Args:
        df: DataFrame với swing_high và swing_low columns
        direction: 'bullish' (tìm range cho setup long) hoặc 'bearish' (tìm range cho setup short)
        lookback: Số nến nhìn lại
    
    Returns:
        (swing_low, swing_high) hoặc (None, None) nếu không tìm thấy
    """
    if 'swing_high' not in df.columns or 'swing_low' not in df.columns:
        return None, None
    
    recent_df = df.iloc[-lookback:] if len(df) > lookback else df
    
    swing_highs = recent_df[recent_df['swing_high'].notna()]
    swing_lows = recent_df[recent_df['swing_low'].notna()]
    
    if swing_highs.empty or swing_lows.empty:
        return None, None
    
    if direction == 'bullish':
        # Cho bullish: tìm swing low gần nhất (điểm bắt đầu move) và swing high sau đó
        last_swing_low = swing_lows.iloc[-1]['swing_low']
        last_swing_low_idx = swing_lows.index[-1]
        
        # Tìm swing high SAU swing low này
        highs_after_low = swing_highs[swing_highs.index > last_swing_low_idx]
        if not highs_after_low.empty:
            last_swing_high = highs_after_low.iloc[-1]['swing_high']
        else:
            # Nếu không có, lấy swing high cuối cùng
            last_swing_high = swing_highs.iloc[-1]['swing_high']
        
        return last_swing_low, last_swing_high
    
    else:  # bearish
        # Cho bearish: tìm swing high gần nhất (điểm bắt đầu move) và swing low sau đó
        last_swing_high = swing_highs.iloc[-1]['swing_high']
        last_swing_high_idx = swing_highs.index[-1]
        
        # Tìm swing low SAU swing high này
        lows_after_high = swing_lows[swing_lows.index > last_swing_high_idx]
        if not lows_after_high.empty:
            last_swing_low = lows_after_high.iloc[-1]['swing_low']
        else:
            last_swing_low = swing_lows.iloc[-1]['swing_low']
        
        return last_swing_low, last_swing_high

def find_swings(df, swing_length=10):
    df['swing_high'] = df['high'].rolling(window=swing_length*2+1, center=True).apply(lambda x: x.iloc[swing_length] if x.iloc[swing_length] == x.max() else np.nan)
    df['swing_low'] = df['low'].rolling(window=swing_length*2+1, center=True).apply(lambda x: x.iloc[swing_length] if x.iloc[swing_length] == x.min() else np.nan)
    return df

def get_current_bias(df, signals=None):
    if 'bos' not in df.columns or 'choch' not in df.columns:
        return 'neutral'

    last_bos_bullish_idx = df[df['bos'] == 'bullish'].index.max()
    last_bos_bearish_idx = df[df['bos'] == 'bearish'].index.max()
    last_choch_bullish_idx = df[df['choch'] == 'bullish'].index.max()
    last_choch_bearish_idx = df[df['choch'] == 'bearish'].index.max()

    events = {
        'bos_bullish': last_bos_bullish_idx,
        'bos_bearish': last_bos_bearish_idx,
        'choch_bullish': last_choch_bullish_idx,
        'choch_bearish': last_choch_bearish_idx,
    }

    valid_events = {name: time for name, time in events.items() if pd.notna(time)}

    if not valid_events:
        return 'neutral'

    latest_event_name = max(valid_events, key=valid_events.get)

    if 'bullish' in latest_event_name:
        msg = f"Market Bias: LONG (dựa trên {latest_event_name.replace('_', ' ').upper()})"
        if signals:
            signals.log_message.emit(msg)
            signals.market_bias.emit("LONG")
        return 'long'
    elif 'bearish' in latest_event_name:
        msg = f"Market Bias: SHORT (dựa trên {latest_event_name.replace('_', ' ').upper()})"
        if signals:
            signals.log_message.emit(msg)
            signals.market_bias.emit("SHORT")
        return 'short'
    else:
        if signals:
            signals.market_bias.emit("NEUTRAL")
        return 'neutral'

def get_dealing_range(df):
    if df.empty: return None, None
    latest_price = df['close'].iloc[-1]
    
    if 'swing_high' not in df.columns or 'swing_low' not in df.columns:
        df = find_swings(df)
        
    swing_highs = df[df['swing_high'].notna()]
    swing_lows = df[df['swing_low'].notna()]

    if swing_highs.empty or swing_lows.empty: return None, None

    higher_highs = swing_highs[swing_highs['swing_high'] > latest_price]
    dealing_range_high = higher_highs.iloc[-1]['swing_high'] if not higher_highs.empty else None

    lower_lows = swing_lows[swing_lows['swing_low'] < latest_price]
    dealing_range_low = lower_lows.iloc[-1]['swing_low'] if not lower_lows.empty else None

    return dealing_range_low, dealing_range_high

def is_in_premium_or_discount(price, dealing_range_low, dealing_range_high):
    if dealing_range_low is None or dealing_range_high is None or dealing_range_high == dealing_range_low:
        return None 
    equilibrium = (dealing_range_high + dealing_range_low) / 2.0
    if price > equilibrium: return 'premium'
    elif price < equilibrium: return 'discount'
    else: return 'equilibrium'

def detect_liquidity_sweep(df, index, lookback=20):
    """
    Kiểm tra xem nến tại 'index' có quét thanh khoản (swing points) trong 'lookback' nến trước đó không.
    Trả về: 'bullish' (quét đáy), 'bearish' (quét đỉnh), hoặc 'none'
    """
    if index < lookback: return 'none'
    candle = df.iloc[index]
    lookback_df = df.iloc[max(0, index - lookback):index]

    # Bullish Sweep: Giá thấp nhất của nến quét qua Swing Low cũ, nhưng đóng cửa phía trên (tùy chọn)
    # ICT: Sweep là khi wick vượt qua swing point.
    recent_swing_lows = lookback_df[lookback_df['swing_low'].notna()]
    if not recent_swing_lows.empty:
        # Lấy swing low thấp nhất trong vùng nhìn lại
        min_swing_low = recent_swing_lows['swing_low'].min()
        if candle['low'] < min_swing_low:
             return 'bullish'
    
    # Bearish Sweep: Giá cao nhất của nến quét qua Swing High cũ
    recent_swing_highs = lookback_df[lookback_df['swing_high'].notna()]
    if not recent_swing_highs.empty:
        max_swing_high = recent_swing_highs['swing_high'].max()
        if candle['high'] > max_swing_high:
            return 'bearish'

    return 'none'


def detect_equal_highs_lows(df, threshold_percent=0.0005, lookback=50):
    """
    Phát hiện Equal Highs (EQH) và Equal Lows (EQL) - dấu hiệu của Liquidity Pool.
    
    Args:
        df: DataFrame with 'swing_high', 'swing_low'
        threshold_percent: Độ lệch cho phép (mặc định 0.05%)
        lookback: Số nến nhìn lại
        
    Returns:
        df với cột 'eqh' và 'eql' (True/False)
    """
    df['eqh'] = False
    df['eql'] = False
    
    if 'swing_high' not in df.columns or 'swing_low' not in df.columns:
        return df
        
    recent_df = df.iloc[-lookback:]
    
    # Check EQH
    swing_highs = recent_df[recent_df['swing_high'].notna()]
    if len(swing_highs) >= 2:
        # So sánh swing high mới nhất với các swing high trước đó
        latest_high = swing_highs.iloc[-1]['swing_high']
        latest_idx = swing_highs.index[-1]
        
        for idx, row in swing_highs.iloc[:-1].iterrows():
            prev_high = row['swing_high']
            diff = abs(latest_high - prev_high)
            
            # Nếu chênh lệch < threshold -> EQH
            if diff <= latest_high * threshold_percent:
                df.loc[latest_idx, 'eqh'] = True
                # Đánh dấu cả điểm cũ
                df.loc[idx, 'eqh'] = True
                
    # Check EQL
    swing_lows = recent_df[recent_df['swing_low'].notna()]
    if len(swing_lows) >= 2:
        latest_low = swing_lows.iloc[-1]['swing_low']
        latest_idx = swing_lows.index[-1]
        
        for idx, row in swing_lows.iloc[:-1].iterrows():
            prev_low = row['swing_low']
            diff = abs(latest_low - prev_low)
            
            if diff <= latest_low * threshold_percent:
                df.loc[latest_idx, 'eql'] = True
                df.loc[idx, 'eql'] = True
                
    return df


def detect_bos_choch(df):
    """
    Phát hiện BOS (Break of Structure) và CHOCH (Change of Character).
    Logic cải tiến: Dựa trên sự phá vỡ giá đóng cửa qua các Swing High/Low gần nhất.
    """
    df['bos'] = None
    df['choch'] = None
    
    # Đảm bảo đã có swing points
    if 'swing_high' not in df.columns or 'swing_low' not in df.columns:
        df = find_swings(df)

    swing_highs = df[df['swing_high'].notna()]
    swing_lows = df[df['swing_low'].notna()]

    if swing_highs.empty or swing_lows.empty: return df
    
    # Biến theo dõi trạng thái
    current_trend = None # 'up' hoặc 'down'
    last_high_val = None
    last_low_val = None
    
    # Khởi tạo giá trị ban đầu (dựa trên swing đầu tiên)
    # Tìm swing đầu tiên
    first_high_idx = swing_highs.index[0]
    first_low_idx = swing_lows.index[0]
    
    if first_high_idx < first_low_idx:
        current_trend = 'down'
        last_high_val = swing_highs.loc[first_high_idx, 'swing_high']
    else:
        current_trend = 'up'
        last_low_val = swing_lows.loc[first_low_idx, 'swing_low']

    # Lặp qua từng nến để kiểm tra phá vỡ
    for i in range(1, len(df)):
        current_idx = df.index[i]
        current_close = df['close'].iloc[i]
        
        # Cập nhật last_high/last_low nếu nến hiện tại là điểm swing
        if pd.notna(df.loc[current_idx, 'swing_high']):
            last_high_val = df.loc[current_idx, 'swing_high']
        
        if pd.notna(df.loc[current_idx, 'swing_low']):
            last_low_val = df.loc[current_idx, 'swing_low']
            
        # Kiểm tra phá vỡ
        if current_trend == 'up':
            # Trong xu hướng tăng, kiểm tra BOS (phá đỉnh) hoặc CHOCH (phá đáy)
            if last_high_val and current_close > last_high_val:
                # Đã phá đỉnh -> BOS Bullish tiếp diễn
                # Chỉ đánh dấu nếu chưa đánh dấu gần đây để tránh spam
                # Ở đây ta đánh dấu vào chính cây nến breakout
                df.loc[current_idx, 'bos'] = 'bullish'
                last_high_val = current_close # Cập nhật đỉnh tạm thời để tránh BOS liên tục cùng 1 đỉnh
            
            elif last_low_val and current_close < last_low_val:
                # Đã phá đáy -> Đảo chiều thành giảm -> Bearish CHOCH
                df.loc[current_idx, 'choch'] = 'bearish'
                current_trend = 'down'
                last_low_val = current_close # Reset mốc

        elif current_trend == 'down':
            # Trong xu hướng giảm, kiểm tra BOS (phá đáy) hoặc CHOCH (phá đỉnh)
            if last_low_val and current_close < last_low_val:
                # Đã phá đáy -> BOS Bearish tiếp diễn
                df.loc[current_idx, 'bos'] = 'bearish'
                last_low_val = current_close

            elif last_high_val and current_close > last_high_val:
                # Đã phá đỉnh -> Đảo chiều thành tăng -> Bullish CHOCH
                df.loc[current_idx, 'choch'] = 'bullish'
                current_trend = 'up'
                last_high_val = current_close

        # Xử lý trường hợp chưa có trend (đầu data)
        elif current_trend is None:
             if last_high_val and current_close > last_high_val:
                 current_trend = 'up'
             elif last_low_val and current_close < last_low_val:
                 current_trend = 'down'
                 
    return df
