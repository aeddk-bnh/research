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
        # Bullish FVG
        if df['high'].iloc[i-2] < df['low'].iloc[i]:
            df.loc[df.index[i-1], 'fvg_bullish_high'] = df['low'].iloc[i]
            df.loc[df.index[i-1], 'fvg_bullish_low'] = df['high'].iloc[i-2]

        # Bearish FVG
        if df['low'].iloc[i-2] > df['high'].iloc[i]:
            df.loc[df.index[i-1], 'fvg_bearish_high'] = df['low'].iloc[i-2]
            df.loc[df.index[i-1], 'fvg_bearish_low'] = df['high'].iloc[i]

    return df

def detect_order_block(df):
    """
    Phát hiện Order Block (OB) với các điều kiện ICT nâng cao.
    1. Liquidity Sweep: Quét thanh khoản đỉnh/đáy trước.
    2. BOS: Gây ra phá vỡ cấu trúc.
    3. Imbalance (Mới): Phải tạo ra FVG ngay sau đó.
    """
    df['ob_bullish'] = False
    df['ob_bearish'] = False
    df['ob_zone_high'] = np.nan
    df['ob_zone_low'] = np.nan
    df['liquidity_sweep'] = 'none'

    # Đảm bảo đã có FVG
    if 'fvg_bullish_high' not in df.columns:
        df = detect_fvg(df)

    df_with_swings = find_swings(df.copy())

    for i in range(15, len(df_with_swings)-5): 
        
        # 1. KIỂM TRA LIQUIDITY SWEEP
        sweep_type = detect_liquidity_sweep(df_with_swings, i)
        df.loc[df.index[i], 'liquidity_sweep'] = sweep_type

        # 2. XÁC ĐỊNH OB VÀ KIỂM TRA BOS + IMBALANCE
        
        # --- Bullish OB ---
        # Chỉ cần là nến giảm (hoặc nến cuối cùng) trước đợt tăng mạnh
        if df_with_swings['close'].iloc[i] < df_with_swings['open'].iloc[i]:
            # Điều kiện a: Có BOS Bullish trong 5 nến tới?
            bos_found = False
            for j in range(i + 1, i + 6):
                # Kiểm tra cột 'bos' nếu nó tồn tại
                if 'bos' in df_with_swings.columns and df_with_swings['bos'].iloc[j] == 'bullish':
                    bos_found = True
                    break
            
            # Điều kiện b: Có FVG Bullish trong 3 nến tới?
            fvg_found = False
            for k in range(i + 1, i + 4):
                if pd.notna(df_with_swings['fvg_bullish_high'].iloc[k]):
                    fvg_found = True
                    break

            # Logic mới: Chỉ cần BOS + FVG là đủ điều kiện OB
            if bos_found and fvg_found:
                df.loc[df.index[i], 'ob_bullish'] = True
                df.loc[df.index[i], 'ob_zone_high'] = df_with_swings['high'].iloc[i]
                df.loc[df.index[i], 'ob_zone_low'] = df_with_swings['low'].iloc[i]

        # --- Bearish OB ---
        # Chỉ cần là nến tăng trước đợt giảm mạnh
        elif df_with_swings['close'].iloc[i] > df_with_swings['open'].iloc[i]:
            # Điều kiện a: Có BOS Bearish trong 5 nến tới?
            bos_found = False
            for j in range(i + 1, i + 6):
                if 'bos' in df_with_swings.columns and df_with_swings['bos'].iloc[j] == 'bearish':
                    bos_found = True
                    break
            
            # Điều kiện b: Có FVG Bearish trong 3 nến tới?
            fvg_found = False
            for k in range(i + 1, i + 4):
                if pd.notna(df_with_swings['fvg_bearish_high'].iloc[k]):
                    fvg_found = True
                    break

            # Logic mới: Chỉ cần BOS + FVG là đủ điều kiện OB
            if bos_found and fvg_found:
                df.loc[df.index[i], 'ob_bearish'] = True
                df.loc[df.index[i], 'ob_zone_high'] = df_with_swings['high'].iloc[i]
                df.loc[df.index[i], 'ob_zone_low'] = df_with_swings['low'].iloc[i]
                
    return df

def detect_breaker_block(df):
    """
    Phát hiện Breaker Block (BB).
    Là một OB đã bị phá vỡ.
    """
    df['bb_bullish'] = False
    df['bb_bearish'] = False

    ob_indices = [i for i in range(len(df)) if df['ob_bullish'].iloc[i] or df['ob_bearish'].iloc[i]]

    for i in ob_indices:
        ob_row = df.iloc[i]
        zone_high = ob_row['ob_zone_high']
        zone_low = ob_row['ob_zone_low']

        if i + 1 >= len(df): continue
            
        subset_after_ob = df.iloc[i+1:]
        
        if ob_row['ob_bullish']: 
            broken = subset_after_ob[subset_after_ob['close'] < zone_low]
            if not broken.empty:
                df.loc[df.index[i], 'bb_bearish'] = True 
        
        elif ob_row['ob_bearish']: 
            broken = subset_after_ob[subset_after_ob['close'] > zone_high]
            if not broken.empty:
                df.loc[df.index[i], 'bb_bullish'] = True 
    
    return df
