import pandas as pd
import numpy as np

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
    Bullish OB: nến giảm cuối cùng trước một đợt tăng mạnh.
    Bearish OB: nến tăng cuối cùng trước một đợt giảm mạnh.
    """
    df['ob_bullish'] = False
    df['ob_bearish'] = False
    df['ob_zone_high'] = np.nan
    df['ob_zone_low'] = np.nan

    for i in range(1, len(df)):
        # Bullish OB
        if df['close'].iloc[i-1] < df['open'].iloc[i-1] and df['close'].iloc[i] > df['open'].iloc[i]:
            # Nếu nến hiện tại tăng mạnh và nến trước đó giảm
            if (df['close'].iloc[i] - df['open'].iloc[i]) > (df['open'].iloc[i-1] - df['close'].iloc[i-1]):
                df.loc[df.index[i-1], 'ob_bullish'] = True
                df.loc[df.index[i-1], 'ob_zone_high'] = df['high'].iloc[i-1]
                df.loc[df.index[i-1], 'ob_zone_low'] = df['low'].iloc[i-1]
        
        # Bearish OB
        if df['close'].iloc[i-1] > df['open'].iloc[i-1] and df['close'].iloc[i] < df['open'].iloc[i]:
             # Nếu nến hiện tại giảm mạnh và nến trước đó tăng
            if (df['open'].iloc[i] - df['close'].iloc[i]) > (df['close'].iloc[i-1] - df['open'].iloc[i-1]):
                df.loc[df.index[i-1], 'ob_bearish'] = True
                df.loc[df.index[i-1], 'ob_zone_high'] = df['high'].iloc[i-1]
                df.loc[df.index[i-1], 'ob_zone_low'] = df['low'].iloc[i-1]
                
    return df

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
