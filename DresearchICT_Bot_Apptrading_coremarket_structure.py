import pandas as pd
import numpy as np

def find_swings(df, swing_length=10):
    """Tìm các đỉnh và đáy (swings) trong dữ liệu."""
    df['swing_high'] = df['high'].rolling(window=swing_length*2+1, center=True).apply(lambda x: x.iloc[swing_length] if x.iloc[swing_length] == x.max() else np.nan)
    df['swing_low'] = df['low'].rolling(window=swing_length*2+1, center=True).apply(lambda x: x.iloc[swing_length] if x.iloc[swing_length] == x.min() else np.nan)
    return df

def get_current_bias(df, signals=None):
    """
    Xác định xu hướng chính (bias) dựa trên sự kiện cấu trúc thị trường gần nhất (BOS/CHOCH).
    """
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
    """
    Xác định phạm vi giao dịch hiện tại (Dealing Range) bằng cách tìm
    Swing High gần nhất ở trên và Swing Low gần nhất ở dưới giá hiện tại.
    """
    if df.empty:
        return None, None
        
    latest_price = df['close'].iloc[-1]
    
    if 'swing_high' not in df.columns or 'swing_low' not in df.columns:
        df = find_swings(df)
        
    swing_highs = df[df['swing_high'].notna()]
    swing_lows = df[df['swing_low'].notna()]

    if swing_highs.empty or swing_lows.empty:
        return None, None

    higher_highs = swing_highs[swing_highs['swing_high'] > latest_price]
    dealing_range_high = higher_highs.iloc[-1]['swing_high'] if not higher_highs.empty else None

    lower_lows = swing_lows[swing_lows['swing_low'] < latest_price]
    dealing_range_low = lower_lows.iloc[-1]['swing_low'] if not lower_lows.empty else None

    return dealing_range_low, dealing_range_high


def is_in_premium_or_discount(price, dealing_range_low, dealing_range_high):
    """
    Kiểm tra xem một mức giá nhất định nằm trong vùng Premium hay Discount
    của một Dealing Range đã cho.
    """
    if dealing_range_low is None or dealing_range_high is None or dealing_range_high == dealing_range_low:
        return None 

    equilibrium = (dealing_range_high + dealing_range_low) / 2.0

    if price > equilibrium:
        return 'premium'
    elif price < equilibrium:
        return 'discount'
    else:
        return 'equilibrium'


def detect_liquidity_sweep(df, index, lookback=15):
    """
    Kiểm tra xem một cây nến có quét thanh khoản của một đỉnh/đáy trước đó hay không.
    - Bullish Sweep: Low của nến hiện tại thấp hơn low của một swing low gần đó.
    - Bearish Sweep: High của nến hiện tại cao hơn high của một swing high gần đó.
    
    Args:
        df (pd.DataFrame): DataFrame chứa dữ liệu OHLC và swings.
        index (int): Index của cây nến cần kiểm tra.
        lookback (int): Số lượng nến để nhìn lại tìm swing.

    Returns:
        str: 'bullish' nếu có sweep bullish, 'bearish' nếu có sweep bearish, 'none' nếu không có.
    """
    if index < lookback:
        return 'none'

    candle = df.iloc[index]
    lookback_df = df.iloc[max(0, index - lookback):index]

    if candle['close'] < candle['open']:
        recent_swing_lows = lookback_df[lookback_df['swing_low'].notna()]
        if not recent_swing_lows.empty:
            for _, swing_low in recent_swing_lows.iterrows():
                if candle['low'] < swing_low['swing_low']:
                    return 'bullish'
    
    if candle['close'] > candle['open']:
        recent_swing_highs = lookback_df[lookback_df['swing_high'].notna()]
        if not recent_swing_highs.empty:
            for _, swing_high in recent_swing_highs.iterrows():
                if candle['high'] > swing_high['swing_high']:
                    return 'bearish'

    return 'none'
    
def detect_bos_choch(df):
    """
    Phát hiện Break of Structure (BOS) và Change of Character (CHOCH)
    với logic được cải tiến, bám sát định nghĩa của ICT.
    """
    df['bos'] = None
    df['choch'] = None

    swing_highs = df[df['swing_high'].notna()].copy()
    swing_lows = df[df['swing_low'].notna()].copy()

    if swing_highs.empty or swing_lows.empty:
        return df

    swing_points = pd.concat([
        swing_highs.assign(type='high'),
        swing_lows.assign(type='low')
    ]).sort_index()

    last_swing_high = None
    last_swing_low = None
    trend = None # 'up', 'down'

    for i in range(len(swing_points)):
        current_point = swing_points.iloc[i]
        current_time = swing_points.index[i]

        if current_point['type'] == 'high':
            last_swing_high = current_point['swing_high']
            
            # BOS Bullish: Phá đỉnh cũ trong xu hướng tăng
            if trend == 'up':
                prev_highs = swing_points[(swing_points.index < current_time) & (swing_points['type'] == 'high')]
                if not prev_highs.empty:
                    prev_high_val = prev_highs.iloc[-1]['swing_high']
                    if last_swing_high > prev_high_val:
                        breakout_candle_idx = df[(df.index > prev_highs.index[-1]) & (df.index <= current_time) & (df['high'] > prev_high_val)].first_valid_index()
                        if breakout_candle_idx:
                            df.loc[breakout_candle_idx, 'bos'] = 'bullish'

            # CHOCH Bullish: Phá đỉnh cũ trong xu hướng giảm
            elif trend == 'down':
                prev_highs = swing_points[(swing_points.index < current_time) & (swing_points['type'] == 'high')]
                if not prev_highs.empty:
                    prev_high_val = prev_highs.iloc[-1]['swing_high']
                    if last_swing_high > prev_high_val:
                        breakout_candle_idx = df[(df.index > prev_highs.index[-1]) & (df.index <= current_time) & (df['high'] > prev_high_val)].first_valid_index()
                        if breakout_candle_idx:
                            df.loc[breakout_candle_idx, 'choch'] = 'bullish'
                            trend = 'up'

        elif current_point['type'] == 'low':
            last_swing_low = current_point['swing_low']
            
            # BOS Bearish: Phá đáy cũ trong xu hướng giảm
            if trend == 'down':
                prev_lows = swing_points[(swing_points.index < current_time) & (swing_points['type'] == 'low')]
                if not prev_lows.empty:
                    prev_low_val = prev_lows.iloc[-1]['swing_low']
                    if last_swing_low < prev_low_val:
                        breakout_candle_idx = df[(df.index > prev_lows.index[-1]) & (df.index <= current_time) & (df['low'] < prev_low_val)].first_valid_index()
                        if breakout_candle_idx:
                            df.loc[breakout_candle_idx, 'bos'] = 'bearish'

            # CHOCH Bearish: Phá đáy cũ trong xu hướng tăng
            elif trend == 'up':
                prev_lows = swing_points[(swing_points.index < current_time) & (swing_points['type'] == 'low')]
 
