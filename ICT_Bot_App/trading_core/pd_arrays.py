import pandas as pd
import numpy as np
from .market_structure import find_swings, detect_liquidity_sweep

# Displacement threshold: % of average candle range để xác định "strong move"
DISPLACEMENT_THRESHOLD = 1.5  # 150% of average range = displacement


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


def check_displacement(df, start_idx: int, direction: str, lookforward: int = 3) -> bool:
    """
    Kiểm tra xem có Displacement (sự dịch chuyển mạnh) sau một nến không.
    
    ICT Displacement:
    - Một hoặc nhiều nến có body lớn hơn bình thường
    - Tạo ra FVG hoặc có range lớn hơn 150% average
    
    Args:
        df: DataFrame
        start_idx: Index bắt đầu kiểm tra (nến OB)
        direction: 'bullish' hoặc 'bearish'
        lookforward: Số nến nhìn về phía trước để check
    
    Returns:
        bool: True nếu có displacement
    """
    if start_idx + lookforward >= len(df):
        return False
    
    # Tính average range của 20 nến trước
    lookback = min(20, start_idx)
    if lookback < 5:
        return True  # Không đủ data để check, bỏ qua
    
    avg_range = (df['high'].iloc[start_idx-lookback:start_idx] - 
                 df['low'].iloc[start_idx-lookback:start_idx]).mean()
    
    if avg_range <= 0:
        return True
    
    # Check các nến sau OB
    for j in range(start_idx + 1, min(start_idx + lookforward + 1, len(df))):
        candle_range = df['high'].iloc[j] - df['low'].iloc[j]
        candle_body = abs(df['close'].iloc[j] - df['open'].iloc[j])
        
        # Displacement check: range hoặc body phải lớn hơn threshold
        if candle_range > avg_range * DISPLACEMENT_THRESHOLD:
            # Kiểm tra direction
            if direction == 'bullish' and df['close'].iloc[j] > df['open'].iloc[j]:
                return True
            elif direction == 'bearish' and df['close'].iloc[j] < df['open'].iloc[j]:
                return True
        
        # Hoặc body lớn (strong conviction)
        if candle_body > avg_range * DISPLACEMENT_THRESHOLD:
            if direction == 'bullish' and df['close'].iloc[j] > df['open'].iloc[j]:
                return True
            elif direction == 'bearish' and df['close'].iloc[j] < df['open'].iloc[j]:
                return True
    
    return False

def detect_order_block(df):
    """
    Phát hiện Order Block (OB) với các điều kiện ICT nâng cao.
    
    ICT Order Block Requirements:
    1. Nến ngược chiều (down candle cho bullish OB, up candle cho bearish OB)
    2. BOS: Gây ra phá vỡ cấu trúc trong 5 nến tiếp theo
    3. Imbalance: Phải tạo ra FVG trong 3 nến tiếp theo
    4. Displacement: Phải có sự dịch chuyển mạnh (nến lớn bất thường)
    
    Optional (đã bỏ requirement bắt buộc):
    - Liquidity Sweep: Quét thanh khoản đỉnh/đáy trước
    """
    df['ob_bullish'] = False
    df['ob_bearish'] = False
    df['ob_zone_high'] = np.nan
    df['ob_zone_low'] = np.nan
    df['liquidity_sweep'] = 'none'
    df['has_displacement'] = False

    # Đảm bảo đã có FVG
    if 'fvg_bullish_high' not in df.columns:
        df = detect_fvg(df)

    df_with_swings = find_swings(df.copy())

    for i in range(15, len(df_with_swings)-5): 
        
        # 1. KIỂM TRA LIQUIDITY SWEEP (optional, chỉ để tracking)
        sweep_type = detect_liquidity_sweep(df_with_swings, i)
        df.loc[df.index[i], 'liquidity_sweep'] = sweep_type

        # 2. XÁC ĐỊNH OB VÀ KIỂM TRA BOS + IMBALANCE + DISPLACEMENT
        
        # --- Bullish OB ---
        # Phải là nến giảm (down candle) trước đợt tăng mạnh
        if df_with_swings['close'].iloc[i] < df_with_swings['open'].iloc[i]:
            # Điều kiện a: Có BOS Bullish trong 5 nến tới?
            bos_found = False
            for j in range(i + 1, min(i + 6, len(df_with_swings))):
                if 'bos' in df_with_swings.columns and df_with_swings['bos'].iloc[j] == 'bullish':
                    bos_found = True
                    break
            
            # Điều kiện b: Có FVG Bullish trong 3 nến tới?
            fvg_found = False
            for k in range(i + 1, min(i + 4, len(df_with_swings))):
                if pd.notna(df_with_swings['fvg_bullish_high'].iloc[k]):
                    fvg_found = True
                    break

            # Điều kiện c: Có Displacement (sự dịch chuyển mạnh)?
            has_displacement = check_displacement(df_with_swings, i, 'bullish')

            # Logic: BOS + FVG + Displacement = Valid OB
            if bos_found and fvg_found and has_displacement:
                df.loc[df.index[i], 'ob_bullish'] = True
                df.loc[df.index[i], 'ob_zone_high'] = df_with_swings['high'].iloc[i]
                df.loc[df.index[i], 'ob_zone_low'] = df_with_swings['low'].iloc[i]
                df.loc[df.index[i], 'has_displacement'] = True

        # --- Bearish OB ---
        # Phải là nến tăng (up candle) trước đợt giảm mạnh
        elif df_with_swings['close'].iloc[i] > df_with_swings['open'].iloc[i]:
            # Điều kiện a: Có BOS Bearish trong 5 nến tới?
            bos_found = False
            for j in range(i + 1, min(i + 6, len(df_with_swings))):
                if 'bos' in df_with_swings.columns and df_with_swings['bos'].iloc[j] == 'bearish':
                    bos_found = True
                    break
            
            # Điều kiện b: Có FVG Bearish trong 3 nến tới?
            fvg_found = False
            for k in range(i + 1, min(i + 4, len(df_with_swings))):
                if pd.notna(df_with_swings['fvg_bearish_high'].iloc[k]):
                    fvg_found = True
                    break

            # Điều kiện c: Có Displacement?
            has_displacement = check_displacement(df_with_swings, i, 'bearish')

            # Logic: BOS + FVG + Displacement = Valid OB
            if bos_found and fvg_found and has_displacement:
                df.loc[df.index[i], 'ob_bearish'] = True
                df.loc[df.index[i], 'ob_zone_high'] = df_with_swings['high'].iloc[i]
                df.loc[df.index[i], 'ob_zone_low'] = df_with_swings['low'].iloc[i]
                df.loc[df.index[i], 'has_displacement'] = True
                
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
