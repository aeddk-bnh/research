import pandas as pd
import numpy as np

def find_swings(df, swing_length=10):
    """Tìm các đỉnh và đáy (swings) trong dữ liệu."""
    df['swing_high'] = df['high'].rolling(window=swing_length*2+1, center=True).apply(lambda x: x.iloc[swing_length] if x.iloc[swing_length] == x.max() else np.nan)
    df['swing_low'] = df['low'].rolling(window=swing_length*2+1, center=True).apply(lambda x: x.iloc[swing_length] if x.iloc[swing_length] == x.min() else np.nan)
    return df

def get_current_bias(df, sma_period=50):
    """Xác định xu hướng chính dựa trên đường SMA và các swing gần nhất."""
    df[f'SMA_{sma_period}'] = df['close'].rolling(window=sma_period).mean()
    
    last_close = df['close'].iloc[-1]
    last_sma = df[f'SMA_{sma_period}'].iloc[-1]
    
    swing_highs = df['swing_high'].dropna()
    swing_lows = df['swing_low'].dropna()
    
    if swing_highs.empty or swing_lows.empty:
        return 'neutral'
        
    last_swing_high = swing_highs.iloc[-1]
    last_swing_low = swing_lows.iloc[-1]

    if last_close > last_sma and last_close > last_swing_low:
        return 'long'
    elif last_close < last_sma and last_close < last_swing_high:
        return 'short'
    else:
        return 'neutral'

def detect_bos_choch(df):
    """
    Phát hiện Break of Structure (BOS) và Change of Character (CHOCH).
    Đây là một logic đơn giản hóa.
    """
    df = find_swings(df)
    df['bos'] = None
    df['choch'] = None

    swing_highs = df[df['swing_high'].notna()]
    swing_lows = df[df['swing_low'].notna()]

    # Phát hiện BOS/CHOCH Bullish
    for i in range(1, len(swing_highs)):
        prev_high = swing_highs['swing_high'].iloc[i-1]
        current_high = swing_highs['swing_high'].iloc[i]
        
        # Tìm đáy thấp nhất giữa 2 đỉnh
        lows_between = df.loc[swing_highs.index[i-1]:swing_highs.index[i]]['low']
        
        if current_high > prev_high: # Tạo đỉnh cao hơn -> có thể là BOS
            df.loc[swing_highs.index[i], 'bos'] = 'bullish'
        elif not lows_between.empty and df['close'].iloc[-1] < lows_between.min(): # Phá vỡ đáy giữa -> CHOCH
             df.loc[df.index[-1], 'choch'] = 'bearish'


    # Phát hiện BOS/CHOCH Bearish
    for i in range(1, len(swing_lows)):
        prev_low = swing_lows['swing_low'].iloc[i-1]
        current_low = swing_lows['swing_low'].iloc[i]
        
        # Tìm đỉnh cao nhất giữa 2 đáy
        highs_between = df.loc[swing_lows.index[i-1]:swing_lows.index[i]]['high']

        if current_low < prev_low: # Tạo đáy thấp hơn -> có thể là BOS
            df.loc[swing_lows.index[i], 'bos'] = 'bearish'
        elif not highs_between.empty and df['close'].iloc[-1] > highs_between.max(): # Phá vỡ đỉnh giữa -> CHOCH
             df.loc[df.index[-1], 'choch'] = 'bullish'
             
    return df
