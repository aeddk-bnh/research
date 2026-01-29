from .market_structure import get_current_bias, detect_bos_choch, find_swings
from .pd_arrays import detect_fvg, detect_order_block, get_swing_and_premium_discount, detect_breaker_block
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

    df_main_with_swings = find_swings(df_main.copy())
    swing_highs = df_main_with_swings['swing_high'].dropna()
    swing_lows = df_main_with_swings['swing_low'].dropna()
    
    swing_high, swing_low, equilibrium = get_swing_and_premium_discount(df_main, swing_highs, swing_lows)

    if equilibrium is None:
        msg = "Không xác định được con sóng để tính Premium/Discount."
        if signals: signals.log_message.emit(f"[EVAL] {msg}")
        else: print(msg)
        return 'none', None, None
        
    latest_close = df_main['close'].iloc[-1]
    latest_high = df_main['high'].iloc[-1]
    latest_low = df_main['low'].iloc[-1]
    
    if signals: signals.log_message.emit(f"[EVAL] Price: C={latest_close:.4f} H={latest_high:.4f} L={latest_low:.4f}, Eq={equilibrium:.4f}")

    if bias == 'long':
        if latest_close > equilibrium:
            if signals: signals.log_message.emit("[EVAL] Price is in Premium zone for a LONG setup. Skipping.")
            return 'none', None, None
            
        if signals: signals.log_message.emit("[EVAL] Price in Discount zone. Looking for Bullish PD Arrays...")
        
        # --- Order Block ---
        bullish_ob_list = df_main[(df_main['ob_bullish']) & (df_main['ob_zone_low'] < equilibrium)]
        if not bullish_ob_list.empty:
            if signals: signals.log_message.emit("[EVAL] Found potential Bullish OB.")
            bullish_ob = bullish_ob_list.iloc[-1]
            
            # Check if Low touches the OB zone
            if latest_low <= bullish_ob['ob_zone_high']:
                if signals: signals.log_message.emit(f"[EVAL] Price (Low={latest_low}) touched Bullish OB (High={bullish_ob['ob_zone_high']}). Checking for LTF CHOCH...")
                recent_choch = df_small[df_small['choch'] == 'bullish'].tail(1)
                
                # Nới lỏng điều kiện thời gian CHOCH: từ 5 nến lên 20 nến
                choch_lookback = 20 
                if not recent_choch.empty and recent_choch.index[0] >= df_small.index[-choch_lookback]:
                    if signals: signals.log_message.emit("[EVAL] SUCCESS: Recent LTF Bullish CHOCH found! Firing LONG signal.")
                    sl_price = bullish_ob['ob_zone_low']
                    
                    if latest_close <= sl_price:
                        if signals: signals.log_message.emit(f"[EVAL] INVALID: Price ({latest_close:.5f}) <= SL ({sl_price:.5f}). Too late to enter.")
                        return 'none', None, None
                        
                    return 'long', latest_close, sl_price
                elif signals:
                    if recent_choch.empty:
                        signals.log_message.emit("[EVAL] FAILED: No recent LTF Bullish CHOCH found.")
                    else:
                        signals.log_message.emit(f"[EVAL] FAILED: LTF Bullish CHOCH is too old. (Found at {recent_choch.index[0]}, need >= {df_small.index[-choch_lookback]})")

        # --- Fair Value Gap (FVG) ---
        bullish_fvg_list = df_main[(df_main['fvg_bullish_low'].notna()) & (df_main['fvg_bullish_low'] < equilibrium)]
        if not bullish_fvg_list.empty:
            if signals: signals.log_message.emit("[EVAL] Found potential Bullish FVG.")
            bullish_fvg = bullish_fvg_list.iloc[-1]
            
            # Check if Low enters the FVG zone
            if latest_low <= bullish_fvg['fvg_bullish_high'] and latest_high >= bullish_fvg['fvg_bullish_low']:
                if signals: signals.log_message.emit(f"[EVAL] Price (Low={latest_low}) touched Bullish FVG ({bullish_fvg['fvg_bullish_low']}-{bullish_fvg['fvg_bullish_high']}). Checking for LTF CHOCH...")
                recent_choch = df_small[df_small['choch'] == 'bullish'].tail(1)
                
                choch_lookback = 20
                if not recent_choch.empty and recent_choch.index[0] >= df_small.index[-choch_lookback]:
                    if signals: signals.log_message.emit("[EVAL] SUCCESS: Recent LTF Bullish CHOCH found! Firing LONG signal.")
                    sl_price = bullish_fvg['fvg_bullish_low']
                    
                    if latest_close <= sl_price:
                        if signals: signals.log_message.emit(f"[EVAL] INVALID: Price ({latest_close:.5f}) <= SL ({sl_price:.5f}). Too late to enter.")
                        return 'none', None, None

                    return 'long', latest_close, sl_price
                elif signals:
                    if recent_choch.empty:
                        signals.log_message.emit("[EVAL] FAILED: No recent LTF Bullish CHOCH found.")
                    else:
                        signals.log_message.emit(f"[EVAL] FAILED: LTF Bullish CHOCH is too old. (Found at {recent_choch.index[0]}, need >= {df_small.index[-choch_lookback]})")

        # --- Breaker Block (BB) ---
        bullish_bb_list = df_main[(df_main['bb_bullish']) & (df_main['ob_zone_low'] < equilibrium)]
        if not bullish_bb_list.empty:
            if signals: signals.log_message.emit("[EVAL] Found potential Bullish BB.")
            bullish_bb = bullish_bb_list.iloc[-1]
            
            if latest_low <= bullish_bb['ob_zone_high']:
                if signals: signals.log_message.emit(f"[EVAL] Price touched Bullish BB. Checking for LTF CHOCH...")
                recent_choch = df_small[df_small['choch'] == 'bullish'].tail(1)
                
                choch_lookback = 20
                if not recent_choch.empty and recent_choch.index[0] >= df_small.index[-choch_lookback]:
                    if signals: signals.log_message.emit("[EVAL] SUCCESS: Recent LTF Bullish CHOCH found! Firing LONG signal.")
                    sl_price = bullish_bb['ob_zone_low']
                    
                    if latest_close <= sl_price:
                        if signals: signals.log_message.emit(f"[EVAL] INVALID: Price ({latest_close:.5f}) <= SL ({sl_price:.5f}). Too late to enter.")
                        return 'none', None, None

                    return 'long', latest_close, sl_price
                elif signals:
                    if recent_choch.empty:
                        signals.log_message.emit("[EVAL] FAILED: No recent LTF Bullish CHOCH found.")
                    else:
                        signals.log_message.emit(f"[EVAL] FAILED: LTF Bullish CHOCH is too old. (Found at {recent_choch.index[0]}, need >= {df_small.index[-choch_lookback]})")

    elif bias == 'short':
        if latest_close < equilibrium:
            if signals: signals.log_message.emit("[EVAL] Price is in Discount zone for a SHORT setup. Skipping.")
            return 'none', None, None

        if signals: signals.log_message.emit("[EVAL] Price in Premium zone. Looking for Bearish PD Arrays...")

        # --- Order Block ---
        bearish_ob_list = df_main[(df_main['ob_bearish']) & (df_main['ob_zone_high'] > equilibrium)]
        if not bearish_ob_list.empty:
            if signals: signals.log_message.emit("[EVAL] Found potential Bearish OB.")
            bearish_ob = bearish_ob_list.iloc[-1]
            
            # Check if High touches the OB zone
            if latest_high >= bearish_ob['ob_zone_low']:
                if signals: signals.log_message.emit(f"[EVAL] Price (High={latest_high}) touched Bearish OB (Low={bearish_ob['ob_zone_low']}). Checking for LTF CHOCH...")
                recent_choch = df_small[df_small['choch'] == 'bearish'].tail(1)
                
                choch_lookback = 20
                if not recent_choch.empty and recent_choch.index[0] >= df_small.index[-choch_lookback]:
                    if signals: signals.log_message.emit("[EVAL] SUCCESS: Recent LTF Bearish CHOCH found! Firing SHORT signal.")
                    sl_price = bearish_ob['ob_zone_high']
                    
                    if latest_close >= sl_price:
                        if signals: signals.log_message.emit(f"[EVAL] INVALID: Price ({latest_close:.5f}) >= SL ({sl_price:.5f}). Too late to enter.")
                        return 'none', None, None

                    return 'short', latest_close, sl_price
                elif signals:
                    if recent_choch.empty:
                        signals.log_message.emit("[EVAL] FAILED: No recent LTF Bearish CHOCH found.")
                    else:
                        signals.log_message.emit(f"[EVAL] FAILED: LTF Bearish CHOCH is too old. (Found at {recent_choch.index[0]}, need >= {df_small.index[-choch_lookback]})")
        
        # --- Fair Value Gap (FVG) ---
        bearish_fvg_list = df_main[(df_main['fvg_bearish_low'].notna()) & (df_main['fvg_bearish_high'] > equilibrium)]
        if not bearish_fvg_list.empty:
            if signals: signals.log_message.emit("[EVAL] Found potential Bearish FVG.")
            bearish_fvg = bearish_fvg_list.iloc[-1]
            
            # Check if High enters the FVG zone
            if latest_high >= bearish_fvg['fvg_bearish_low'] and latest_low <= bearish_fvg['fvg_bearish_high']:
                if signals: signals.log_message.emit(f"[EVAL] Price (High={latest_high}) touched Bearish FVG ({bearish_fvg['fvg_bearish_low']}-{bearish_fvg['fvg_bearish_high']}). Checking for LTF CHOCH...")
                recent_choch = df_small[df_small['choch'] == 'bearish'].tail(1)
                
                choch_lookback = 20
                if not recent_choch.empty and recent_choch.index[0] >= df_small.index[-choch_lookback]:
                    if signals: signals.log_message.emit("[EVAL] SUCCESS: Recent LTF Bearish CHOCH found! Firing SHORT signal.")
                    sl_price = bearish_fvg['fvg_bearish_high']
                    
                    if latest_close >= sl_price:
                        if signals: signals.log_message.emit(f"[EVAL] INVALID: Price ({latest_close:.5f}) >= SL ({sl_price:.5f}). Too late to enter.")
                        return 'none', None, None

                    return 'short', latest_close, sl_price
                elif signals:
                    if recent_choch.empty:
                        signals.log_message.emit("[EVAL] FAILED: No recent LTF Bearish CHOCH found.")
                    else:
                        signals.log_message.emit(f"[EVAL] FAILED: LTF Bearish CHOCH is too old. (Found at {recent_choch.index[0]}, need >= {df_small.index[-choch_lookback]})")

        # --- Breaker Block (BB) ---
        bearish_bb_list = df_main[(df_main['bb_bearish']) & (df_main['ob_zone_high'] > equilibrium)]
        if not bearish_bb_list.empty:
            if signals: signals.log_message.emit("[EVAL] Found potential Bearish BB.")
            bearish_bb = bearish_bb_list.iloc[-1]
            
            if latest_high >= bearish_bb['ob_zone_low']:
                if signals: signals.log_message.emit(f"[EVAL] Price touched Bearish BB. Checking for LTF CHOCH...")
                recent_choch = df_small[df_small['choch'] == 'bearish'].tail(1)
                
                choch_lookback = 20
                if not recent_choch.empty and recent_choch.index[0] >= df_small.index[-choch_lookback]:
                    if signals: signals.log_message.emit("[EVAL] SUCCESS: Recent LTF Bearish CHOCH found! Firing SHORT signal.")
                    sl_price = bearish_bb['ob_zone_high']
                    
                    if latest_close >= sl_price:
                        if signals: signals.log_message.emit(f"[EVAL] INVALID: Price ({latest_close:.5f}) >= SL ({sl_price:.5f}). Too late to enter.")
                        return 'none', None, None

                    return 'short', latest_close, sl_price
                elif signals:
                    if recent_choch.empty:
                        signals.log_message.emit("[EVAL] FAILED: No recent LTF Bearish CHOCH found.")
                    else:
                        signals.log_message.emit(f"[EVAL] FAILED: LTF Bearish CHOCH is too old. (Found at {recent_choch.index[0]}, need >= {df_small.index[-choch_lookback]})")

    return 'none', None, None

def execute_strategy(connector: 'BaseConnector', signals=None) -> None:
    if connector.get_open_positions():
        msg = "Đã có vị thế đang mở. Bỏ qua."
        if signals: signals.log_message.emit(msg)
        else: print(msg)
        return

    msg = "Đang lấy và phân tích dữ liệu..."
    if signals: signals.log_message.emit(msg)
    else: print(msg)
    
    main_timeframe = str(TIMEFRAME)
    small_timeframe = str(TIMEFRAME_SMALLER)

    df_main = connector.fetch_ohlcv(main_timeframe, limit=200)
    df_small = connector.fetch_ohlcv(small_timeframe, limit=100)

    if df_main is None or df_small is None: return

    # Analysis pipeline
    df_with_fvg = detect_fvg(df_main.copy())
    df_with_swings = find_swings(df_with_fvg)
    df_with_bos = detect_bos_choch(df_with_swings)
    df_with_ob = detect_order_block(df_with_bos)
    df_main_analyzed = detect_breaker_block(df_with_ob)
    df_small_swings = find_swings(df_small.copy())
    df_small_analyzed = detect_bos_choch(df_small_swings)
    
    signal, entry_price, sl_price = evaluate_signal(df_main_analyzed, df_small_analyzed, signals)

    if signal != 'none' and entry_price is not None and sl_price is not None:
        
        # Calculate TP based on RR
        rr = float(TAKE_PROFIT_RR)
        sl_distance = abs(entry_price - sl_price)
        if signal == 'long':
            tp_price = entry_price + (sl_distance * rr)
        else: # short
            tp_price = entry_price - (sl_distance * rr)

        # Calculate position size
        quantity = calculate_position_size(connector, sl_price, entry_price, signals)
        
        if quantity is not None and quantity > 0:
            msg = f"Tín hiệu {signal.upper()}: Giá={entry_price:.5f}, SL={sl_price:.5f}, TP={tp_price:.5f}, Khối lượng={quantity}"
            if signals:
                signals.log_message.emit(msg)
                signals.new_position.emit({
                    'id': 'N/A',
                    'symbol': connector.get_symbol(),
                    'side': signal.upper(),
                    'quantity': quantity,
                    'entry_price': entry_price,
                    'sl': sl_price,
                    'tp': tp_price,
                    'status': 'OPEN'
                })
            else:
                print(msg)

            connector.place_order(signal, quantity, sl_price, tp_price) 
        else:
            msg = "Không thể xác định khối lượng giao dịch. Hủy lệnh."
            if signals: signals.log_message.emit(msg)
            else: print(msg)
    else:
        msg = "Không có tín hiệu giao dịch rõ ràng."
        if signals: signals.log_message.emit(msg)
        else: print(msg)
