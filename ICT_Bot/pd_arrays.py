import pandas as pd
import numpy as np
from market_structure import find_swings


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
    Phát hiện Order Block (OB).
    Bullish OB: nến giảm cuối cùng trước một đợt tăng mạnh gây ra BOS.
    Bearish OB: nến tăng cuối cùng trước một đợt giảm mạnh gây ra BOS.
    """
    df['ob_bullish'] = False
    df['ob_bearish'] = False
    df['ob_zone_high'] = np.nan
    df['ob_zone_low'] = np.nan

    for i in range(1, len(df)-3): # -3 để đảm bảo có nến sau để kiểm tra BOS
        # Bullish OB
        if df['close'].iloc[i-1] < df['open'].iloc[i-1] and df['close'].iloc[i] > df['open'].iloc[i]:
            # Nếu nến hiện tại tăng mạnh và nến trước đó giảm
            if (df['close'].iloc[i] - df['open'].iloc[i]) > (df['open'].iloc[i-1] - df['close'].iloc[i-1]):
                # Kiểm tra xem có BOS Bullish trong 3 nến tiếp theo không
                bos_found = False
                for j in range(i+1, min(i+4, len(df))): # Kiểm tra 3 nến sau OB
                    if df['bos'].iloc[j] == 'bullish':
                        bos_found = True
                        break
                
                if bos_found:
                    df.loc[df.index[i-1], 'ob_bullish'] = True
                    df.loc[df.index[i-1], 'ob_zone_high'] = df['high'].iloc[i-1]
                    df.loc[df.index[i-1], 'ob_zone_low'] = df['low'].iloc[i-1]
        
        # Bearish OB
        if df['close'].iloc[i-1] > df['open'].iloc[i-1] and df['close'].iloc[i] < df['open'].iloc[i]:
             # Nếu nến hiện tại giảm mạnh và nến trước đó tăng
            if (df['open'].iloc[i] - df['close'].iloc[i]) > (df['close'].iloc[i-1] - df['open'].iloc[i-1]):
                # Kiểm tra xem có BOS Bearish trong 3 nến tiếp theo không
                bos_found = False
                for j in range(i+1, min(i+4, len(df))): # Kiểm tra 3 nến sau OB
                    if df['bos'].iloc[j] == 'bearish':
                        bos_found = True
                        break
                
                if bos_found:
                    df.loc[df.index[i-1], 'ob_bearish'] = True
                    df.loc[df.index[i-1], 'ob_zone_high'] = df['high'].iloc[i-1]
                    df.loc[df.index[i-1], 'ob_zone_low'] = df['low'].iloc[i-1]
   
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

    ob_indices = df[df['ob_bullish'] | df['ob_bearish']].index

    for idx in ob_indices:
        ob_row = df.loc[idx]
        zone_high = ob_row['ob_zone_high']
        zone_low = ob_row['ob_zone_low']

        # Kiểm tra các nến sau OB
        subset_after_ob = df.loc[idx+1:]
        if ob_row['ob_bullish']: # Nếu là Bullish OB (hỗ trợ)
            # Tìm nến đầu tiên đóng cửa dưới vùng hỗ trợ
            broken = subset_after_ob[subset_after_ob['close'] < zone_low]
            if not broken.empty:
                df.loc[idx, 'bb_bearish'] = True # Trở thành Bearish BB
        
        elif ob_row['ob_bearish']: # Nếu là Bearish OB (kháng cự)
            # Tìm nến đầu tiên đóng cửa trên vùng kháng cự
            broken = subset_after_ob[subset_after_ob['close'] > zone_high]
            if not broken.empty:
                df.loc[idx, 'bb_bullish'] = True # Trở thành Bullish BB
    
    return df
