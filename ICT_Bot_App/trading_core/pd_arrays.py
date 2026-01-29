import pandas as pd
import numpy as np
from .market_structure import find_swings, detect_liquidity_sweep


def detect_fvg(df):
    """
    Phát hiện Fair Value Gap (FVG).
    """
    df['fvg_bullish_high'] = np.nan
    df['fvg_bullish_low'] = np.nan
    df['fvg_bearish_high'] = np.nan
    df['fvg_bearish_low'] = np.nan

    for i in range(2, len(df)):
        # Bullish FVG: Khoảng trống giữa đỉnh nến (i-2) và đáy nến (i)
        if df['high'].iloc[i-2] < df['low'].iloc[i]:
            df.loc[df.index[i-1], 'fvg_bullish_high'] = df['low'].iloc[i]
            df.loc[df.index[i-1], 'fvg_bullish_low'] = df['high'].iloc[i-2]

        # Bearish FVG: Khoảng trống giữa đáy nến (i-2) và đỉnh nến (i)
        if df['low'].iloc[i-2] > df['high'].iloc[i]:
            df.loc[df.index[i-1], 'fvg_bearish_high'] = df['low'].iloc[i-2]
            df.loc[df.index[i-1], 'fvg_bearish_low'] = df['high'].iloc[i]

    return df

def detect_order_block(df):
    """
    Phát hiện Order Block (OB) với các điều kiện ICT nâng cao.
    - Phải quét thanh khoản (liquidity sweep).
    - Phải gây ra phá vỡ cấu trúc (BOS).
    - Thường tạo ra FVG (điều kiện tùy chọn, có thể thêm sau).
    """
    df['ob_bullish'] = False
    df['ob_bearish'] = False
    df['ob_zone_high'] = np.nan
    df['ob_zone_low'] = np.nan
    df['liquidity_sweep'] = 'none' # Thêm cột để debug

    # Cần chạy find_swings trước để detect_liquidity_sweep hoạt động
    df_with_swings = find_swings(df.copy())

    # Lặp qua các nến, bắt đầu từ chỉ số có đủ dữ liệu lookback
    for i in range(15, len(df_with_swings)-3):
        
        # 1. KIỂM TRA LIQUIDITY SWEEP
        sweep_type = detect_liquidity_sweep(df_with_swings, i)
        
        if sweep_type == 'none':
            continue # Bỏ qua nếu không có sweep

        df.loc[df.index[i], 'liquidity_sweep'] = sweep_type

        # 2. XÁC ĐỊNH OB VÀ KIỂM TRA BOS
        
        # Bullish OB
        # Sweep phải là 'bullish' (quét đáy) và nến OB phải là nến giảm
        if sweep_type == 'bullish' and df_with_swings['close'].iloc[i] < df_with_swings['open'].iloc[i]:
            # Kiểm tra xem có BOS Bullish trong 3 nến tiếp theo không
            bos_found = False
            for j in range(i + 1, min(i + 4, len(df_with_swings))):
                if df_with_swings['bos'].iloc[j] == 'bullish':
                    bos_found = True
                    break
            
            if bos_found:
                df.loc[df.index[i], 'ob_bullish'] = True
                df.loc[df.index[i], 'ob_zone_high'] = df_with_swings['high'].iloc[i]
                df.loc[df.index[i], 'ob_zone_low'] = df_with_swings['low'].iloc[i]

        # Bearish OB
        # Sweep phải là 'bearish' (quét đỉnh) và nến OB phải là nến tăng
        elif sweep_type == 'bearish' and df_with_swings['close'].iloc[i] > df_with_swings['open'].iloc[i]:
            # Kiểm tra xem có BOS Bearish trong 3 nến tiếp theo không
            bos_found = False
            for j in range(i + 1, min(i + 4, len(df_with_swings))):
                if df_with_swings['bos'].iloc[j] == 'bearish':
                    bos_found = True
                    break
            
            if bos_found:
                df.loc[df.index[i], 'ob_bearish'] = True
                df.loc[df.index[i], 'ob_zone_high'] = df_with_swings['high'].iloc[i]
                df.loc[df.index[i], 'ob_zone_low'] = df_with_swings['low'].iloc[i]
                
    return df


def get_swing_and_premium_discount(df, swing_highs, swing_lows):
    """
    Xác định con sóng gần nhất và tính toán các vùng Premium/Discount.
    Trả về một tuple: (swing_high, swing_low, equilibrium).
    """
    if swing_highs.empty or swing_lows.empty:
        return None, None, None

    # Lấy swing high và swing low gần nhất
    last_swing_high_time = swing_highs.index[-1]
    last_swing_low_time = swing_lows.index[-1]

    # Xác định con sóng gần nhất dựa trên thời gian
    if last_swing_high_time > last_swing_low_time:
        # Con sóng giảm gần nhất (từ đỉnh xuống đáy)
        swing_high_price = swing_highs.iloc[-1]
        # Tìm swing low trước swing high này
        relevant_lows = swing_lows[swing_lows.index < last_swing_high_time]
        if relevant_lows.empty:
            return None, None, None
        swing_low_price = relevant_lows.iloc[-1]
    else:
        # Con sóng tăng gần nhất (từ đáy lên đỉnh)
        swing_low_price = swing_lows.iloc[-1]
        # Tìm swing high trước swing low này
        relevant_highs = swing_highs[swing_highs.index < last_swing_low_time]
        if relevant_highs.empty:
            return None, None, None
        swing_high_price = relevant_highs.iloc[-1]

    # Tính toán mức cân bằng (Equilibrium)
    equilibrium = (swing_high_price + swing_low_price) / 2

    return swing_high_price, swing_low_price, equilibrium


def detect_breaker_block(df):
    """
    Phát hiện Breaker Block (BB).
    Là một OB đã bị phá vỡ.
    """
    df['bb_bullish'] = False
    df['bb_bearish'] = False

    # Lấy danh sách các vị trí integer có OB
    ob_indices = [i for i in range(len(df)) if df['ob_bullish'].iloc[i] or df['ob_bearish'].iloc[i]]

    for i in ob_indices:
        ob_row = df.iloc[i]
        zone_high = ob_row['ob_zone_high']
        zone_low = ob_row['ob_zone_low']

        # Kiểm tra các nến sau OB
        # Sử dụng iloc để lấy slice
        if i + 1 >= len(df):
            continue
            
        subset_after_ob = df.iloc[i+1:]
        
        if ob_row['ob_bullish']: # Nếu là Bullish OB (hỗ trợ)
            # Tìm nến đầu tiên đóng cửa dưới vùng hỗ trợ
            broken = subset_after_ob[subset_after_ob['close'] < zone_low]
            if not broken.empty:
                # Dùng index gốc (Timestamp) để gán giá trị
                df.loc[df.index[i], 'bb_bearish'] = True # Trở thành Bearish BB
        
        elif ob_row['ob_bearish']: # Nếu là Bearish OB (kháng cự)
            # Tìm nến đầu tiên đóng cửa trên vùng kháng cự
            broken = subset_after_ob[subset_after_ob['close'] > zone_high]
            if not broken.empty:
                df.loc[df.index[i], 'bb_bullish'] = True # Trở thành Bullish BB
    
    return df
