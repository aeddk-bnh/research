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
        msg = f"Market Bias: LONG (dựa trên {latest_event_name.replace('_', ' ').upper()})"
        if signals:
            signals.log_message.emit(msg)
            signals.market_bias.emit("LONG")
        else:
            print(msg)
        return 'long'
    elif 'bearish' in latest_event_name:
        msg = f"Market Bias: SHORT (dựa trên {latest_event_name.replace('_', ' ').upper()})"
        if signals:
            signals.log_message.emit(msg)
            signals.market_bias.emit("SHORT")
        else:
            print(msg)
        return 'short'
    else:
        if signals:
            signals.market_bias.emit("NEUTRAL")
        return 'neutral'



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

    candle = df.loc[index]
    lookback_df = df.iloc[max(0, index - lookback):index]

    # Bullish Sweep Check (quét đáy)
    # Nến hiện tại (có thể là Bullish OB) phải là một nến giảm
    if candle['close'] < candle['open']:
        # Tìm các swing low trong vùng lookback
        recent_swing_lows = lookback_df[lookback_df['swing_low'].notna()]
        if not recent_swing_lows.empty:
            # Kiểm tra xem low của nến hiện tại có phá vỡ (quét) bất kỳ swing low nào gần đây không
            for _, swing_low in recent_swing_lows.iterrows():
                if candle['low'] < swing_low['swing_low']:
                    return 'bullish'
    
    # Bearish Sweep Check (quét đỉnh)
    # Nến hiện tại (có thể là Bearish OB) phải là một nến tăng
    if candle['close'] > candle['open']:
        # Tìm các swing high trong vùng lookback
        recent_swing_highs = lookback_df[lookback_df['swing_high'].notna()]
        if not recent_swing_highs.empty:
            # Kiểm tra xem high của nến hiện tại có phá vỡ (quét) bất kỳ swing high nào gần đây không
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

    # Gộp và sắp xếp các swing points
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
            
            # Nếu đang trong xu hướng tăng và tạo đỉnh cao hơn -> BOS
            if trend == 'up' and last_swing_high > swing_points[swing_points['type'] == 'high'].iloc[-2]['swing_high']:
                 # Tìm nến thực sự phá vỡ đỉnh cũ
                prev_high_val = swing_points[swing_points['type'] == 'high'].iloc[-2]['swing_high']
                breakout_candle_idx = df[(df.index > swing_points.index[i-1]) & (df.index <= current_time) & (df['high'] > prev_high_val)].first_valid_index()
                if breakout_candle_idx:
                    df.loc[breakout_candle_idx, 'bos'] = 'bullish'
            
            # Nếu đang trong xu hướng giảm và phá vỡ đỉnh -> CHOCH
            elif trend == 'down':
                # Tìm swing high gần nhất trước đó
                prev_highs = swing_points[(swing_points.index < current_time) & (swing_points['type'] == 'high')]
                if not prev_highs.empty:
                    prev_high_val = prev_highs.iloc[-1]['swing_high']
                    if last_swing_high > prev_high_val:
                         # Tìm nến thực sự phá vỡ
                        breakout_candle_idx = df[(df.index > prev_highs.index[-1]) & (df.index <= current_time) & (df['high'] > prev_high_val)].first_valid_index()
                        if breakout_candle_idx:
                            df.loc[breakout_candle_idx, 'choch'] = 'bullish'
                            trend = 'up' # Thay đổi xu hướng

        elif current_point['type'] == 'low':
            last_swing_low = current_point['swing_low']
            
            # Nếu đang trong xu hướng giảm và tạo đáy thấp hơn -> BOS
            if trend == 'down' and last_swing_low < swing_points[swing_points['type'] == 'low'].iloc[-2]['swing_low']:
                prev_low_val = swing_points[swing_points['type'] == 'low'].iloc[-2]['swing_low']
                breakout_candle_idx = df[(df.index > swing_points.index[i-1]) & (df.index <= current_time) & (df['low'] < prev_low_val)].first_valid_index()
                if breakout_candle_idx:
                    df.loc[breakout_candle_idx, 'bos'] = 'bearish'
            
            # Nếu đang trong xu hướng tăng và phá vỡ đáy -> CHOCH
            elif trend == 'up':
                prev_lows = swing_points[(swing_points.index < current_time) & (swing_points['type'] == 'low')]
                if not prev_lows.empty:
                    prev_low_val = prev_lows.iloc[-1]['swing_low']
                    if last_swing_low < prev_low_val:
                        breakout_candle_idx = df[(df.index > prev_lows.index[-1]) & (df.index <= current_time) & (df['low'] < prev_low_val)].first_valid_index()
                        if breakout_candle_idx:
                            df.loc[breakout_candle_idx, 'choch'] = 'bearish'
                            trend = 'down' # Thay đổi xu hướng
                            
        # Khởi tạo trend ban đầu
        if trend is None and i > 0:
            prev_point = swing_points.iloc[i-1]
            if current_point['type'] == 'high' and prev_point['type'] == 'low':
                if current_point['swing_high'] > prev_point['swing_high']:
                    trend = 'up'
                else:
                    trend = 'down'
            elif current_point['type'] == 'low' and prev_point['type'] == 'high':
                if current_point['swing_low'] < prev_point['swing_low']:
                    trend = 'down'
                else:
                    trend = 'up'

    return df
