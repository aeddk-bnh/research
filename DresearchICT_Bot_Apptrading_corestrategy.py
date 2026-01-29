from .market_structure import get_current_bias, detect_bos_choch, find_swings, get_dealing_range, is_in_premium_or_discount
from .pd_arrays import detect_fvg, detect_order_block, detect_breaker_block
from .config_loader import TIMEFRAME, TIMEFRAME_SMALLER, RISK_PERCENT_PER_TRADE, TAKE_PROFIT_RR
import math
import pandas as pd

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .connectors.base_connector import BaseConnector

def calculate_position_size(connector: 'BaseConnector', sl_price: float, entry_price: float, signals=None) -> float | None:
    balance = connector.get_account_balance()
    symbol_info = connector.get_symbol_info()

    if balance is None or symbol_info is None:
        msg = "Không thể tính khối lượng, thiếu thông tin tài khoản hoặc symbol."
        if signals: signals.log_message.emit(msg)
        else: print(msg)
        return None

    risk_percent = float(RISK_PERCENT_PER_TRADE)
    if risk_percent <= 0:
        msg = "Tỷ lệ rủi ro phải lớn hơn 0."
        if signals: signals.log_message.emit(msg)
        else: print(msg)
        return None

    risk_amount = balance * (risk_percent / 100)
    
    sl_pips = abs(entry_price - sl_price)
    if sl_pips == 0:
        msg = "Khoảng cách SL bằng 0, không thể tính khối lượng."
        if signals: signals.log_message.emit(msg)
        else: print(msg)
        return None

    tick_value = getattr(symbol_info, 'tick_value', 0.0)
    tick_size = getattr(symbol_info, 'tick_size', 0.0)
    point_value = tick_value / tick_size if tick_size > 0 else 0.0
    point_digits = abs(str(tick_size)[::-1].find('.'))
    
    loss_per_lot = (sl_pips * (10**point_digits)) * point_value
    
    if loss_per_lot <= 0:
        msg = "Không thể tính khối lượng, mức lỗ trên mỗi lot <= 0."
        if signals: signals.log_message.emit(msg)
        else: print(msg)
        return None

    volume = risk_amount / loss_per_lot
    volume_step = getattr(symbol_info, 'volume_step', 0.01)
    volume = math.floor(volume / volume_step) * volume_step
    
    volume_min = getattr(symbol_info, 'volume_min', 0.01)
    volume_max = getattr(symbol_info, 'volume_max', 1000.0)

    if volume < volume_min:
        msg = f"Khối lượng tính toán ({volume}) nhỏ hơn mức tối thiểu ({volume_min}). Hủy lệnh."
        if signals: signals.log_message.emit(msg)
        else: print(msg)
        return None
    if volume > volume_max:
        volume = volume_max
        msg = f"Khối lượng tính toán vượt mức tối đa, sử dụng khối lượng tối đa: {volume}"
        if signals: signals.log_message.emit(msg)
        else: print(msg)

    return volume

def evaluate_signal(df_main: pd.DataFrame, df_small: pd.DataFrame, signals=None) -> tuple[str, float | None, float | None]:
    bias = get_current_bias(df_main, signals)
    if signals: signals.log_message.emit(f"[EVAL] Bias: {bias}")
    if bias == 'neutral':
        return 'none', None, None

    # Xác định Dealing Range và Equilibrium
    dr_low, dr_high = get_dealing_range(df_main)
    
    if dr_low is None or dr_high is None:
        msg = "Không xác định được Dealing Range để tính Premium/Discount."
        if signals: signals.log_message.emit(f"[EVAL] {msg}")
        return 'none', None, None

    equilibrium = (dr_high + dr_low) / 2
    latest_close = df_main['close'].iloc[-1]
    latest_high = df_main['high'].iloc[-1]
    latest_low = df_main['low'].iloc[-1]
    
    if signals: signals.log_message.emit(f"[EVAL] Dealing Range: {dr_low:.5f} - {dr_high:.5f} (Eq={equilibrium:.5f}) | Price: {latest_close:.5f}")

    if bias == 'long':
        # Kiểm tra điều kiện Discount
        if latest_close > equilibrium:
             if signals: signals.log_message.emit(f"[EVAL] Price ({latest_close:.5f}) > Equilibrium ({equilibrium:.5f}) -> PREMIUM Zone. Skipping LONG setup.")
             return 'none', None, None
        
        if signals: signals.log_message.emit("[EVAL] Price in DISCOUNT Zone. Looking for Bullish PD Arrays...")
        
        # --- Order Block ---
        bullish_ob_list = df_main[(df_main['ob_bullish']) & (df_main['ob_zone_low'] < equilibrium)]
        if not bullish_ob_list.empty:
            if signals: signals.log_message.emit("[EVAL] Found potential Bullish OB in Discount.")
            bullish_ob = bullish_ob_list.iloc[-1]
            
            # Check if Low touches the OB zone
            if latest_low <= bullish_ob['ob_zone_high']:
                if signals: signals.log_message.emit(f"[EVAL] Price (Low={latest_low}) touched Bullish OB (High={bullish_ob['ob_zone_high']}). Checking for LTF CHOCH...")
                recent_choch = df_small[df_small['choch'] == 'bullish'].tail(1)
                
                choch_lookback = 20 
                if not recent_choch.empty and recent_choch.index[0] >= df_small.index[-choch_lookback]:
                    if signals: signals.log_message.emit("[EVAL] SUCCESS: Recent LTF Bullish CHOCH found! Firing LONG signal.")
                    sl_price = bullish_ob['ob_zone_low']
                    
                    if latest_close <= sl_price:
                         if signals: signals.log_message.emit(f"[EVAL] INVALID: Price ({latest_close:.5f}) <= SL ({sl_price:.5f}). Too late.")
                         return 'none', None, None

                    return 'long', latest_close, sl_price
                elif signals:
                     if recent_choch.empty: signals.log_message.emit("[EVAL] FAILED: No recent LTF Bullish CHOCH found.")
                     else: signals.log_message.emit(f"[EVAL] FAILED: LTF Bullish CHOCH too old.")

        # --- Breaker Block (BB) ---
        bullish_bb_list = df_main[(df_main['bb_bullish']) & (df_main['ob_zone_low'] < equilibrium)]
        if not bullish_bb_list.empty:
            if signals: signals.log_message.emit("[EVAL] Found potential Bullish BB in Discount.")
            bullish_bb = bullish_bb_list.iloc[-1]
            
            if latest_low <= bullish_bb['ob_zone_high']:
                if signals: signals.log_message.emit(f"[EVAL] Price touched Bullish BB. Checking for LTF CHOCH...")
                recent_choch = df_small[df_small['choch'] == 'bullish'].tail(1)
                
                choch_lookback = 20
                if not recent_choch.empty and recent_choch.index[0] >= df_small.index[-choch_lookback]:
                    if signals: signals.log_message.emit("[EVAL] SUCCESS: Recent LTF Bullish CHOCH found! Firing LONG signal.")
                    sl_price = bullish_bb['ob_zone_low']
                    
                    if latest_close <= sl_price:
                        if signals: signals.log_message.emit(f"[EVAL] INVALID: Price ({latest_close:.5f}) <= SL ({sl_price:.5f}). Too late.")
                        return 'none', None, None

                    return 'long', latest_close, sl_price
                elif signals:
                     if recent_choch.empty: signals.log_message.emit("[EVAL] FAILED: No recent LTF Bullish CHOCH found.")
                     else: signals.log_message.emit(f"[EVAL] FAILED: LTF Bullish CHOCH too old.")

    elif bias == 'short':
        # Kiểm tra điều kiện Premium
        if latest_close < equilibrium:
            if signals: signals.log_message.emit(f"[EVAL] Price ({latest_close:.5f}) < Equilibrium ({equilibrium:.5f}) -> DISCOUNT Zone. Skipping SHORT setup.")
            return 'none', None, None

        if signals: signals.log_message.emit("[EVAL] Price in PREMIUM Zone. Looking for Bearish PD Arrays...")

        # --- Order Block ---
        bearish_ob_list = df_main[(df_main['ob_bearish']) & (df_main['ob_zone_high'] > equilibrium)]
        if not bearish_ob_list.empty:
            if signals: signals.log_message.emit("[EVAL] Found potential Bearish OB in Premium.")
            bearish_ob = bearish_ob_list.iloc[-1]
            
            # Check if High touches the OB zone
            if latest_high >= bearish_ob['ob_zone_low']:
                if signals: signals.log_message.emit(f"[EVAL] Price (High={latest_high}) touched Bearish OB (Low={bearish_ob['ob_zone_low']}). Checking for LTF CHOCH...")
                
