import pandas as pd
import numpy as np
from typing import cast, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from pandas import DataFrame

# OTE Fibonacci Levels (Optimal Trade Entry)
OTE_FIB_LEVELS = {
    'shallow': 0.62,
    'optimal': 0.705,
    'deep': 0.79
}


def calculate_ote_levels(swing_high: float, swing_low: float, direction: str) -> dict:
    range_size = swing_high - swing_low
    
    if direction == 'bullish':
        return {
            'ote_62': swing_high - (range_size * OTE_FIB_LEVELS['shallow']),
            'ote_705': swing_high - (range_size * OTE_FIB_LEVELS['optimal']),
            'ote_79': swing_high - (range_size * OTE_FIB_LEVELS['deep']),
            'equilibrium': swing_high - (range_size * 0.5),
            'swing_high': swing_high,
            'swing_low': swing_low
        }
    else:  # bearish
        return {
            'ote_62': swing_low + (range_size * OTE_FIB_LEVELS['shallow']),
            'ote_705': swing_low + (range_size * OTE_FIB_LEVELS['optimal']),
            'ote_79': swing_low + (range_size * OTE_FIB_LEVELS['deep']),
            'equilibrium': swing_low + (range_size * 0.5),
            'swing_high': swing_high,
            'swing_low': swing_low
        }


def is_price_in_ote_zone(price: float, ote_levels: dict, direction: str) -> tuple[bool, str]:
    ote_62 = ote_levels['ote_62']
    ote_705 = ote_levels['ote_705']
    ote_79 = ote_levels['ote_79']
    
    if direction == 'bullish':
        if ote_79 <= price <= ote_62:
            return (True, 'deep_ote') if price <= ote_705 else (True, 'shallow_ote')
        return (False, 'below_ote') if price < ote_79 else (False, 'above_ote')
    else:  # bearish
        if ote_62 <= price <= ote_79:
            return (True, 'deep_ote') if price >= ote_705 else (True, 'shallow_ote')
        return (False, 'above_ote') if price > ote_79 else (False, 'below_ote')


def get_recent_swing_range(df: pd.DataFrame, direction: str, lookback: int = 50) -> tuple[float | None, float | None]:
    if 'swing_high' not in df.columns or 'swing_low' not in df.columns:
        return None, None
    
    recent_df = df.iloc[-lookback:] if len(df) > lookback else df
    
    swing_highs = recent_df[recent_df['swing_high'].notna()]
    swing_lows = recent_df[recent_df['swing_low'].notna()]
    
    swing_highs = cast(pd.DataFrame, swing_highs)
    swing_lows = cast(pd.DataFrame, swing_lows)
    
    if swing_highs.empty or swing_lows.empty:
        return None, None
    
    if direction == 'bullish':
        last_swing_low = swing_lows.iloc[-1]['swing_low']
        last_swing_low_idx = swing_lows.index[-1]
        
        highs_after_low = swing_highs[swing_highs.index > last_swing_low_idx]
        highs_after_low = cast(pd.DataFrame, highs_after_low)
        
        last_swing_high = highs_after_low.iloc[-1]['swing_high'] if not highs_after_low.empty else swing_highs.iloc[-1]['swing_high']
        return last_swing_low, last_swing_high
    
    else:  # bearish
        last_swing_high = swing_highs.iloc[-1]['swing_high']
        last_swing_high_idx = swing_highs.index[-1]
        
        lows_after_high = swing_lows[swing_lows.index > last_swing_high_idx]
        lows_after_high = cast(pd.DataFrame, lows_after_high)
        
        last_swing_low = lows_after_high.iloc[-1]['swing_low'] if not lows_after_high.empty else swing_lows.iloc[-1]['swing_low']
        return last_swing_low, last_swing_high

def get_htf_bias(df_htf: pd.DataFrame, htf_label: str = "H4") -> str:
    if df_htf is None or df_htf.empty:
        return 'neutral'
    
    swing_len = 5 if htf_label.upper() == 'D1' else 10
    
    df = find_swings(df_htf.copy(), swing_length=swing_len)
    df = detect_bos_choch(df)
    
    return get_current_bias(df)

def find_swings(df, swing_length=10):
    df['swing_high'] = df['high'].rolling(window=swing_length*2+1, center=True).apply(lambda x: x.iloc[swing_length] if x.iloc[swing_length] == x.max() else np.nan)
    df['swing_low'] = df['low'].rolling(window=swing_length*2+1, center=True).apply(lambda x: x.iloc[swing_length] if x.iloc[swing_length] == x.min() else np.nan)
    return df

def get_current_bias(df, signals=None):
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

    latest_event_name = max(valid_events, key=lambda k: cast(Any, valid_events.get(k)))

    if 'bullish' in latest_event_name:
        msg = f"Market Bias: LONG (based on {latest_event_name.replace('_', ' ').upper()})"
        if signals:
            signals.log_message.emit(msg)
            signals.market_bias.emit("LONG")
        return 'long'
    elif 'bearish' in latest_event_name:
        msg = f"Market Bias: SHORT (based on {latest_event_name.replace('_', ' ').upper()})"
        if signals:
            signals.log_message.emit(msg)
            signals.market_bias.emit("SHORT")
        return 'short'
    else:
        if signals:
            signals.market_bias.emit("NEUTRAL")
        return 'neutral'

def get_dealing_range(df):
    if df.empty: return None, None
    latest_price = df['close'].iloc[-1]
    
    if 'swing_high' not in df.columns or 'swing_low' not in df.columns:
        df = find_swings(df)
        
    swing_highs = df[df['swing_high'].notna()]
    swing_lows = df[df['swing_low'].notna()]
    
    swing_highs = cast(pd.DataFrame, swing_highs)
    swing_lows = cast(pd.DataFrame, swing_lows)
    
    if swing_highs.empty or swing_lows.empty: return None, None

    higher_highs = swing_highs[swing_highs['swing_high'] > latest_price]
    higher_highs = cast(pd.DataFrame, higher_highs)
    dealing_range_high = higher_highs.iloc[-1]['swing_high'] if not higher_highs.empty else None

    lower_lows = swing_lows[swing_lows['swing_low'] < latest_price]
    lower_lows = cast(pd.DataFrame, lower_lows)
    dealing_range_low = lower_lows.iloc[-1]['swing_low'] if not lower_lows.empty else None

    return dealing_range_low, dealing_range_high

def is_in_premium_or_discount(price, dealing_range_low, dealing_range_high):
    if dealing_range_low is None or dealing_range_high is None or dealing_range_high == dealing_range_low:
        return None 
    equilibrium = (dealing_range_high + dealing_range_low) / 2.0
    if price > equilibrium: return 'premium'
    elif price < equilibrium: return 'discount'
    else: return 'equilibrium'

def detect_liquidity_sweep(df, index, lookback=20):
    if index < lookback: return 'none'
    candle = df.iloc[index]
    lookback_df = df.iloc[max(0, index - lookback):index]

    recent_swing_lows = lookback_df[lookback_df['swing_low'].notna()]
    recent_swing_lows = cast(pd.DataFrame, recent_swing_lows)
    if not recent_swing_lows.empty:
        min_swing_low = recent_swing_lows['swing_low'].min()
        if candle['low'] < min_swing_low:
             return 'bullish'
    
    recent_swing_highs = lookback_df[lookback_df['swing_high'].notna()]
    recent_swing_highs = cast(pd.DataFrame, recent_swing_highs)
    if not recent_swing_highs.empty:
        max_swing_high = recent_swing_highs['swing_high'].max()
        if candle['high'] > max_swing_high:
            return 'bearish'

    return 'none'


def detect_equal_highs_lows(df, threshold_percent=0.0005, lookback=50):
    df['eqh'] = False
    df['eql'] = False
    
    if 'swing_high' not in df.columns or 'swing_low' not in df.columns:
        return df
        
    recent_df = df.iloc[-lookback:]
    
    swing_highs = recent_df[recent_df['swing_high'].notna()]
    swing_highs = cast(pd.DataFrame, swing_highs)
    if len(swing_highs) >= 2:
        latest_high = swing_highs.iloc[-1]['swing_high']
        latest_idx = swing_highs.index[-1]
        
        for idx, row in swing_highs.iloc[:-1].iterrows():
            prev_high = row['swing_high']
            diff = abs(latest_high - prev_high)
            
            if diff <= latest_high * threshold_percent:
                df.loc[latest_idx, 'eqh'] = True
                df.loc[idx, 'eqh'] = True
                
    swing_lows = recent_df[recent_df['swing_low'].notna()]
    swing_lows = cast(pd.DataFrame, swing_lows)
    if len(swing_lows) >= 2:
        latest_low = swing_lows.iloc[-1]['swing_low']
        latest_idx = swing_lows.index[-1]
        
        for idx, row in swing_lows.iloc[:-1].iterrows():
            prev_low = row['swing_low']
            diff = abs(latest_low - prev_low)
            
            if diff <= latest_low * threshold_percent:
                df.loc[latest_idx, 'eql'] = True
                df.loc[idx, 'eql'] = True
                
    return df


def detect_bos_choch(df):
    df['bos'] = None
    df['choch'] = None
    
    if 'swing_high' not in df.columns or 'swing_low' not in df.columns:
        df = find_swings(df)

    swing_highs = df[df['swing_high'].notna()]
    swing_lows = df[df['swing_low'].notna()]

    swing_highs = cast(pd.DataFrame, swing_highs)
    swing_lows = cast(pd.DataFrame, swing_lows)
    
    if swing_highs.empty or swing_lows.empty: return df
    
    current_trend = None
    last_high_val = None
    last_low_val = None
    
    first_high_idx = swing_highs.index[0]
    first_low_idx = swing_lows.index[0]
    
    if first_high_idx < first_low_idx:
        current_trend = 'down'
        last_high_val = swing_highs.loc[first_high_idx, 'swing_high']
    else:
        current_trend = 'up'
        last_low_val = swing_lows.loc[first_low_idx, 'swing_low']

    for i in range(1, len(df)):
        current_idx = df.index[i]
        current_close = df['close'].iloc[i]
        
        if pd.notna(df.loc[current_idx, 'swing_high']):
            last_high_val = df.loc[current_idx, 'swing_high']
        
        if pd.notna(df.loc[current_idx, 'swing_low']):
            last_low_val = df.loc[current_idx, 'swing_low']
            
        if current_trend == 'up':
            if last_high_val and current_close > last_high_val:
                df.loc[current_idx, 'bos'] = 'bullish'
                last_high_val = current_close
            
            elif last_low_val and current_close < last_low_val:
                df.loc[current_idx, 'choch'] = 'bearish'
                current_trend = 'down'
                last_low_val = current_close

        elif current_trend == 'down':
            if last_low_val and current_close < last_low_val:
                df.loc[current_idx, 'bos'] = 'bearish'
                last_low_val = current_close

            elif last_high_val and current_close > last_high_val:
                df.loc[current_idx, 'choch'] = 'bullish'
                current_trend = 'up'
                last_high_val = current_close

        elif current_trend is None:
             if last_high_val and current_close > last_high_val:
                 current_trend = 'up'
             elif last_low_val and current_close < last_low_val:
                 current_trend = 'down'
                 
    return df
