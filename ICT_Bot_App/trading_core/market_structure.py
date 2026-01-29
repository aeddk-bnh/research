import pandas as pd
import numpy as np

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

def detect_liquidity_sweep(df, index, lookback=15):
    if index < lookback: return 'none'
    candle = df.iloc[index]
    lookback_df = df.iloc[max(0, index - lookback):index]

    if candle['close'] < candle['open']:
        recent_swing_lows = lookback_df[lookback_df['swing_low'].notna()]
        if not recent_swing_lows.empty:
            for _, swing_low in recent_swing_lows.iterrows():
                if candle['low'] < swing_low['swing_low']: return 'bullish'
    
    if candle['close'] > candle['open']:
        recent_swing_highs = lookback_df[lookback_df['swing_high'].notna()]
        if not recent_swing_highs.empty:
            for _, swing_high in recent_swing_highs.iterrows():
                if candle['high'] > swing_high['swing_high']: return 'bearish'

    return 'none'
    
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
