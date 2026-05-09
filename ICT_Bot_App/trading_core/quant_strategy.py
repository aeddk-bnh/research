import pandas as pd
import pandas_ta as ta

def calculate_quant_signals(df: pd.DataFrame, fast_sma: int = 20, slow_sma: int = 50, rsi_period: int = 14) -> pd.DataFrame:
    """
    Tính toán các tín hiệu Quantitative (SMA Crossover + RSI).
    Yêu cầu DataFrame có các cột: Open, High, Low, Close (tên cột có thể cần chuẩn hóa).
    """
    # Đảm bảo có đủ nến để tính SMA chậm
    if len(df) < slow_sma:
        df['quant_signal'] = 0
        df['quant_trend'] = 0
        return df
        
    # Chuẩn hóa tên cột thành viết hoa chữ cái đầu cho pandas-ta nếu cần
    # Tuy nhiên, thông thường CCXT/MT5 dataframe nên có sẵn 'Open', 'High', 'Low', 'Close'
    # Nếu df đang dùng viết thường 'close', cần đổi tên tạm thời.
    col_mapping = {}
    if 'close' in df.columns:
        col_mapping = {'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume', 'tick_volume': 'Volume'}
        df_calc = df.rename(columns=col_mapping).copy()
    else:
        df_calc = df.copy()
        
    if 'Close' not in df_calc.columns:
        df['quant_signal'] = 0
        df['quant_trend'] = 0
        return df
        
    # Tính toán các chỉ báo
    df_calc.ta.sma(length=fast_sma, append=True)
    df_calc.ta.sma(length=slow_sma, append=True)
    df_calc.ta.rsi(length=rsi_period, append=True)
    
    fast_col = f"SMA_{fast_sma}"
    slow_col = f"SMA_{slow_sma}"
    rsi_col = f"RSI_{rsi_period}"
    
    df_calc['quant_signal'] = 0
    df_calc['quant_trend'] = 0
    
    if fast_col not in df_calc.columns or slow_col not in df_calc.columns or rsi_col not in df_calc.columns:
        df['quant_signal'] = 0
        df['quant_trend'] = 0
        return df
        
    # Xác định xu hướng (1: Tăng, -1: Giảm)
    df_calc.loc[df_calc[fast_col] > df_calc[slow_col], 'quant_trend'] = 1
    df_calc.loc[df_calc[fast_col] < df_calc[slow_col], 'quant_trend'] = -1
    
    # Tính sự thay đổi xu hướng (Crossover)
    df_calc['trend_shift'] = df_calc['quant_trend'].diff()
    
    # Tín hiệu Mua: Cắt lên (trend_shift = 2) và RSI không quá mua (< 70)
    df_calc.loc[(df_calc['trend_shift'] == 2) & (df_calc[rsi_col] < 70), 'quant_signal'] = 1
    
    # Tín hiệu Bán: Cắt xuống (trend_shift = -2) và RSI không quá bán (> 30)
    df_calc.loc[(df_calc['trend_shift'] == -2) & (df_calc[rsi_col] > 30), 'quant_signal'] = -1
    
    # Trả kết quả về df gốc
    df['quant_signal'] = df_calc['quant_signal'].fillna(0)
    df['quant_trend'] = df_calc['quant_trend'].fillna(0)
    df[fast_col] = df_calc[fast_col]
    df[slow_col] = df_calc[slow_col]
    df[rsi_col] = df_calc[rsi_col]
    
    return df
