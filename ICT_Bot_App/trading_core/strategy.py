from .market_structure import (
    get_current_bias, detect_bos_choch, find_swings, get_dealing_range, 
    is_in_premium_or_discount, calculate_ote_levels, is_price_in_ote_zone, 
    get_recent_swing_range, detect_equal_highs_lows, detect_liquidity_sweep,
    get_htf_bias
)
from .pd_arrays import detect_fvg, detect_order_block, detect_breaker_block
from .silver_bullet import detect_silver_bullet_setup
from .config_loader import (
    TIMEFRAME, TIMEFRAME_SMALLER, RISK_PERCENT_PER_TRADE, TAKE_PROFIT_RR, 
    ENABLE_LOGGING, SL_BUFFER_POINTS, OTE_ENABLED, OTE_LEVEL_PRIMARY,
    PARTIAL_PROFITS_ENABLED, PARTIAL_TP1_PERCENT, PARTIAL_TP1_RR, 
    PARTIAL_TP2_PERCENT, PARTIAL_TP2_RR, PARTIAL_TP3_RR
)
import math
import pandas as pd

try:
    from app.config_manager import config_manager
except ImportError:
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from app.config_manager import config_manager


from typing import TYPE_CHECKING, cast, Any
if TYPE_CHECKING:
    from .connectors.base_connector import BaseConnector

def calculate_position_size(connector: 'BaseConnector', sl_price: float, entry_price: float, signals=None) -> float | None:
    balance = connector.get_account_balance()
    symbol_info = connector.get_symbol_info()

    if balance is None or symbol_info is None:
        return None

    risk_percent = float(RISK_PERCENT_PER_TRADE)
    if risk_percent <= 0:
        return None

    risk_amount = balance * (risk_percent / 100)
    sl_pips = abs(entry_price - sl_price)
    if sl_pips == 0:
        return None

    tick_value = getattr(symbol_info, 'tick_value', 0.0)
    tick_size = getattr(symbol_info, 'tick_size', 0.0)
    point_value = tick_value / tick_size if tick_size > 0 else 0.0
    point_digits = abs(str(tick_size)[::-1].find('.'))
    
    loss_per_lot = (sl_pips * (10**point_digits)) * point_value
    
    if loss_per_lot <= 0:
        return None

    volume = risk_amount / loss_per_lot
    volume_step = getattr(symbol_info, 'volume_step', 0.01)
    volume = math.floor(volume / volume_step) * volume_step
    
    volume_min = getattr(symbol_info, 'volume_min', 0.01)
    volume_max = getattr(symbol_info, 'volume_max', 1000.0)

    if volume < volume_min:
        return None
    if volume > volume_max:
        volume = volume_max

    return volume


def calculate_partial_orders(
    total_quantity: float, 
    entry_price: float, 
    sl_price: float, 
    signal: str,
    connector: 'BaseConnector'
) -> list[dict]:
    if not PARTIAL_PROFITS_ENABLED:
        sl_distance = abs(entry_price - sl_price)
        tp = entry_price + (sl_distance * TAKE_PROFIT_RR) if signal == 'long' else entry_price - (sl_distance * TAKE_PROFIT_RR)
        return [{'quantity': total_quantity, 'tp': tp, 'label': 'FULL'}]
    
    symbol_info = connector.get_symbol_info()
    volume_step = getattr(symbol_info, 'volume_step', 0.01)
    volume_min = getattr(symbol_info, 'volume_min', 0.01)
    
    sl_distance = abs(entry_price - sl_price)
    
    if signal == 'long':
        tp1 = entry_price + (sl_distance * PARTIAL_TP1_RR)
        tp2 = entry_price + (sl_distance * PARTIAL_TP2_RR)
        tp3 = entry_price + (sl_distance * PARTIAL_TP3_RR)
    else:
        tp1 = entry_price - (sl_distance * PARTIAL_TP1_RR)
        tp2 = entry_price - (sl_distance * PARTIAL_TP2_RR)
        tp3 = entry_price - (sl_distance * PARTIAL_TP3_RR)
    
    qty1_raw = total_quantity * (PARTIAL_TP1_PERCENT / 100)
    qty2_raw = total_quantity * (PARTIAL_TP2_PERCENT / 100)
    qty3_raw = total_quantity - qty1_raw - qty2_raw
    
    qty1 = math.floor(qty1_raw / volume_step) * volume_step
    qty2 = math.floor(qty2_raw / volume_step) * volume_step
    qty3 = math.floor(qty3_raw / volume_step) * volume_step
    
    orders = []
    
    if qty1 >= volume_min:
        orders.append({'quantity': qty1, 'tp': tp1, 'label': f'TP1 ({PARTIAL_TP1_PERCENT}%@{PARTIAL_TP1_RR}:1)'})
    
    if qty2 >= volume_min:
        orders.append({'quantity': qty2, 'tp': tp2, 'label': f'TP2 ({PARTIAL_TP2_PERCENT}%@{PARTIAL_TP2_RR}:1)'})
    
    if qty3 >= volume_min:
        orders.append({'quantity': qty3, 'tp': tp3, 'label': f'TP3 (Rest@{PARTIAL_TP3_RR}:1)'})
    
    if not orders:
        tp = entry_price + (sl_distance * TAKE_PROFIT_RR) if signal == 'long' else entry_price - (sl_distance * TAKE_PROFIT_RR)
        orders = [{'quantity': total_quantity, 'tp': tp, 'label': 'FULL (min qty)'}]
    
    return orders


def check_ote_confluence(df: pd.DataFrame, current_price: float, bias: str, signals=None) -> tuple[bool, dict | None]:
    if not OTE_ENABLED:
        return True, None
    
    direction = 'bullish' if bias == 'long' else 'bearish'
    swing_low, swing_high = get_recent_swing_range(df, direction)
    
    if swing_low is None or swing_high is None:
        return True, None
    
    ote_levels = calculate_ote_levels(swing_high, swing_low, direction)
    in_ote, position = is_price_in_ote_zone(current_price, ote_levels, direction)
    
    return in_ote, ote_levels

def evaluate_signal(df_main: pd.DataFrame, df_small: pd.DataFrame, daily_bias: str, connector: 'BaseConnector', signals=None) -> tuple[str, float | None, float | None, str]:
    reason_parts = [f"HTF BIAS: {daily_bias.upper()}"]

    if daily_bias == 'neutral':
        return 'none', None, None, "HTF Bias is Neutral"

    ltf_bias = get_current_bias(df_main, signals)
    reason_parts.append(f"Main TF BIAS: {ltf_bias.upper()}")

    if ltf_bias == 'neutral' or (ltf_bias != daily_bias):
        return 'none', None, None, f"Signal ({ltf_bias}) against HTF Bias ({daily_bias})"

    bias = ltf_bias
    df_small_with_fvg = detect_fvg(df_small.copy())
    dr_low, dr_high = get_dealing_range(df_main)
    
    if dr_low is None or dr_high is None:
        return 'none', None, None, "No Dealing Range"

    equilibrium = (dr_high + dr_low) / 2
    latest_close = df_main['close'].iloc[-1]
    latest_high = df_main['high'].iloc[-1]
    latest_low = df_main['low'].iloc[-1]
    point_value = getattr(connector.get_symbol_info(), 'point', 0.00001)
    sl_buffer_value = SL_BUFFER_POINTS * point_value

    zone = "PREMIUM" if latest_close > equilibrium else "DISCOUNT"
    reason_parts.append(f"Zone: {zone}")

    if bias == 'long':
        if zone == "PREMIUM":
            return 'none', None, None, "Price in Premium, skipping LONG"
        
        in_ote, _ = check_ote_confluence(df_main, latest_close, bias, signals)
        if OTE_ENABLED:
            reason_parts.append(f"OTE: {'Yes' if in_ote else 'No'}")
            if not in_ote:
                return 'none', None, None, "Price not in OTE zone"

        for poi_type in ["OB", "FVG", "BB"]:
            found_poi = False
            poi_data = None
            if poi_type == "OB":
                poi_list = df_main[(df_main['ob_bullish']) & (df_main['ob_zone_low'] < equilibrium)]
                if not poi_list.empty:
                    poi_data = poi_list.iloc[-1]
                    if latest_low <= poi_data['ob_zone_high']: found_poi = True
            elif poi_type == "FVG":
                poi_list = df_main[(df_main['fvg_bullish_high'].notna()) & (df_main['fvg_bullish_low'] < equilibrium)]
                if not poi_list.empty:
                    poi_data = poi_list.iloc[-1]
                    if latest_low <= poi_data['fvg_bullish_high']: found_poi = True
            elif poi_type == "BB":
                poi_list = df_main[(df_main['bb_bullish']) & (df_main['ob_zone_low'] < equilibrium)]
                if not poi_list.empty:
                    poi_data = poi_list.iloc[-1]
                    if latest_low <= poi_data['ob_zone_high']: found_poi = True
            
            if found_poi and poi_data is not None:
                reason_parts.append(f"POI: Bullish {poi_type}")
                found_ltf, entry, ltf_reason = check_ltf_confirmation(df_small_with_fvg, 'bullish', signals)
                if found_ltf:
                    reason_parts.append(f"Confirm: {ltf_reason}")
                    sl_price = (poi_data['ob_zone_low'] if 'ob_zone_low' in poi_data and not pd.isna(poi_data['ob_zone_low']) else poi_data.get('fvg_bullish_low', latest_low)) - sl_buffer_value
                    if entry is not None and entry > sl_price:
                        return 'long', entry, sl_price, ' -> '.join(reason_parts)

    elif bias == 'short':
        if zone == "DISCOUNT":
            return 'none', None, None, "Price in Discount, skipping SHORT"

        in_ote, _ = check_ote_confluence(df_main, latest_close, bias, signals)
        if OTE_ENABLED:
            reason_parts.append(f"OTE: {'Yes' if in_ote else 'No'}")
            if not in_ote:
                return 'none', None, None, "Price not in OTE zone"

        for poi_type in ["OB", "FVG", "BB"]:
            found_poi = False
            poi_data = None
            if poi_type == "OB":
                poi_list = df_main[(df_main['ob_bearish']) & (df_main['ob_zone_high'] > equilibrium)]
                if not poi_list.empty:
                    poi_data = poi_list.iloc[-1]
                    if latest_high >= poi_data['ob_zone_low']: found_poi = True
            elif poi_type == "FVG":
                poi_list = df_main[(df_main['fvg_bearish_high'].notna()) & (df_main['fvg_bearish_high'] > equilibrium)]
                if not poi_list.empty:
                    poi_data = poi_list.iloc[-1]
                    if latest_high >= poi_data['fvg_bearish_low']: found_poi = True
            elif poi_type == "BB":
                poi_list = df_main[(df_main['bb_bearish']) & (df_main['ob_zone_high'] > equilibrium)]
                if not poi_list.empty:
                    poi_data = poi_list.iloc[-1]
                    if latest_high >= poi_data['ob_zone_low']: found_poi = True
            
            if found_poi and poi_data is not None:
                reason_parts.append(f"POI: Bearish {poi_type}")
                found_ltf, entry, ltf_reason = check_ltf_confirmation(df_small_with_fvg, 'bearish', signals)
                if found_ltf:
                    reason_parts.append(f"Confirm: {ltf_reason}")
                    sl_price = (poi_data['ob_zone_high'] if 'ob_zone_high' in poi_data and not pd.isna(poi_data['ob_zone_high']) else poi_data.get('fvg_bearish_high', latest_high)) + sl_buffer_value
                    if entry is not None and entry < sl_price:
                        return 'short', entry, sl_price, ' -> '.join(reason_parts)

    sb_found, sb_entry, sb_sl = detect_silver_bullet_setup(df_small, latest_close, bias, signals)
    if sb_found and sb_entry is not None and sb_sl is not None:
        reason_parts.append("POI: Silver Bullet")
        if bias == 'long':
            sb_sl -= sl_buffer_value
            if sb_entry > sb_sl:
                return 'long', sb_entry, sb_sl, ' -> '.join(reason_parts)
        else:
            sb_sl += sl_buffer_value
            if sb_entry < sb_sl:
                return 'short', sb_entry, sb_sl, ' -> '.join(reason_parts)

    return 'none', None, None, ' -> '.join(reason_parts)

def check_ltf_confirmation(df_small: pd.DataFrame, trend: str, signals=None) -> tuple[bool, float | None, str | None]:
    recent_choch = df_small[df_small['choch'] == trend].tail(1)
    recent_bos = df_small[df_small['bos'] == trend].tail(1)
    
    confirmation_found = False
    confirm_idx = None
    reason = ""
    
    try:
        if not recent_choch.empty:
            loc = df_small.index.get_loc(recent_choch.index[0])
            if isinstance(loc, slice): loc = loc.start
            if loc >= len(df_small) - 20:
                confirmation_found = True
                confirm_idx = loc
                reason = "LTF CHOCH"
                
                for k in range(max(0, confirm_idx - 10), confirm_idx):
                    sweep_type = detect_liquidity_sweep(df_small, k, lookback=20)
                    if sweep_type:
                        reason = f"ICT 2022 Model ({sweep_type})"
                        break
        
        if not confirmation_found and not recent_bos.empty:
            loc = df_small.index.get_loc(recent_bos.index[0])
            if isinstance(loc, slice): loc = loc.start
            if loc >= len(df_small) - 20:
                confirmation_found = True
                confirm_idx = loc
                reason = "LTF BOS"

        if confirmation_found and confirm_idx is not None:
            entry_price = df_small['close'].iloc[-1]
            fvg_col = 'fvg_bullish_high' if trend == 'bullish' else 'fvg_bearish_low'
            ltf_slice = df_small.iloc[confirm_idx:]
            ltf_fvgs = ltf_slice[ltf_slice[fvg_col].notna()]
            
            if not ltf_fvgs.empty:
                best_fvg = ltf_fvgs.iloc[-1]
                entry_price = best_fvg['fvg_bullish_high'] if trend == 'bullish' else best_fvg['fvg_bearish_low']
                reason += " w/ FVG Entry"
            else:
                reason += " w/ Market Entry"
            
            return True, entry_price, reason

    except Exception as e:
        if signals:
            signals.log_message.emit(f"[ERROR] Lỗi khi check LTF confirmation: {e}")
        return False, None, None

    return False, None, None

def analyze_dataframe(df: pd.DataFrame, is_ltf=False) -> pd.DataFrame:
    df_fvg = detect_fvg(df.copy())
    df_swings = find_swings(df_fvg)
    df_bos = detect_bos_choch(df_swings)
    if not is_ltf:
        df_ob = detect_order_block(df_bos)
        return detect_breaker_block(df_ob)
    return df_bos

def execute_strategy(connector: 'BaseConnector', signals=None) -> None:
    if connector.get_open_positions():
        return

    main_timeframe = config_manager.get('trading.timeframe', 'H1') or 'H1'
    small_timeframe = config_manager.get('trading.timeframe_smaller', 'M15') or 'M15'
    htf_timeframe = config_manager.get('trading.htf_timeframe', 'H4') or 'H4'

    df_main = connector.fetch_ohlcv(main_timeframe, limit=200)
    df_small = connector.fetch_ohlcv(small_timeframe, limit=100)
    df_htf = connector.fetch_ohlcv(htf_timeframe, limit=200)

    if df_main is None or df_small is None or df_htf is None:
        return
        
    htf_bias = get_htf_bias(df_htf, htf_label=htf_timeframe)
        
    df_main_analyzed = analyze_dataframe(df_main.copy())
    df_small_analyzed = analyze_dataframe(df_small.copy(), is_ltf=True)

    signal, entry_price, sl_price, reason = evaluate_signal(df_main_analyzed, df_small_analyzed, htf_bias, connector, signals)

    if signal != 'none' and entry_price is not None and sl_price is not None:
        quantity = calculate_position_size(connector, sl_price, entry_price, signals)
        
        if quantity is not None and quantity > 0:
            partial_orders = calculate_partial_orders(quantity, entry_price, sl_price, signal, connector)
            
            if PARTIAL_PROFITS_ENABLED:
                for i, order in enumerate(partial_orders):
                    connector.place_order(signal, order['quantity'], sl_price, order['tp'])
            else:
                rr = float(TAKE_PROFIT_RR)
                sl_distance = abs(entry_price - sl_price)
                tp_price = entry_price + (sl_distance * rr) if signal == 'long' else entry_price - (sl_distance * rr)
                
                connector.place_order(signal, quantity, sl_price, tp_price)
