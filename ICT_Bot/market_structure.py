import pandas as pd
import numpy as np

def find_swings(df, swing_length=10):
    """Tìm các đỉnh và đáy (swings) trong dữ liệu."""
    df['swing_high'] = df['high'].rolling(window=swing_length*2+1, center=True).apply(lambda x: x.iloc[swing_length] if x.iloc[swing_length] == x.max() else np.nan)
    df['swing_low'] = df['low'].rolling(window=swing_length*2+1, center=True).apply(lambda x: x.iloc[swing_length] if x.iloc[swing_length] == x.min() else np.nan)
    return df

def get_current_bias(df):
    """
    Xác định xu hướng chính (bias) dựa trên sự kiện cấu trúc thị trường gần nhất (BOS/CHOCH).
    """
    # Đảm bảo cột 'bos' và 'choch' đã tồn tại
    if 'bos' not in df.columns or 'choch' not in df.columns:
        return 'neutral' # Không có dữ liệu cấu trúc để phân tích

    # Tìm chỉ số (index) của sự kiện BOS và CHOCH gần nhất
    last_bos_bullish_idx = df[df['bos'] == 'bullish'].index.max()
    last_bos_bearish_idx = df[df['bos'] == 'bearish'].index.max()
    last_choch_bullish_idx = df[df['choch'] == 'bullish'].index.max()
    last_choch_bearish_idx = df[df['choch'] == 'bearish'].index.max()

    # Tạo một dictionary để lưu các sự kiện và thời gian của chúng
    events = {
        'bos_bullish': last_bos_bullish_idx,
        'bos_bearish': last_bos_bearish_idx,
        'choch_bullish': last_choch_bullish_idx,
        'choch_bearish': last_choch_bearish_idx,
    }

    # Lọc bỏ các sự kiện không xảy ra (giá trị là NaT)
    valid_events = {name: time for name, time in events.items() if pd.notna(time)}

    if not valid_events:
        return 'neutral' # Không có sự kiện cấu trúc nào

    # Tìm sự kiện gần nhất bằng cách tìm giá trị thời gian lớn nhất
    latest_time = max(valid_events.values())
    latest_event_name = None
    for name, time in valid_events.items():
        if time == latest_time:
            latest_event_name = name
            break

    # Kiểm tra lại nếu không tìm được tên sự kiện (trường hợp hiếm khi có sự trùng lặp chỉ số)
    if latest_event_name is None:
        return 'neutral'

    # Xác định xu hướng dựa trên sự kiện gần nhất
    if 'bullish' in latest_event_name:
        print(f"Market Bias: LONG (dựa trên {latest_event_name.replace('_', ' ').upper()})")
        return 'long'
    elif 'bearish' in latest_event_name:
        print(f"Market Bias: SHORT (dựa trên {latest_event_name.replace('_', ' ').upper()})")
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
