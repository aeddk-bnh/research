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
    if bias == 'neutral':
        return 'none', None, None

    df_main_with_swings = find_swings(df_main.copy())
    swing_highs = df_main_with_swings['swing_high'].dropna()
    swing_lows = df_main_with_swings['swing_low'].dropna()
    
    swing_high, swing_low, equilibrium = get_swing_and_premium_discount(df_main, swing_highs, swing_lows)

    if equilibrium is None:
        msg = "Không xác định được con sóng để tính Premium/Discount."
        if signals: signals.log_message.emit(msg)
        else: print(msg)
        return 'none', None, None
        
    latest_price = df_main['close'].iloc[-1]

    if bias == 'long':
        if latest_price > equilibrium:
            return 'none', None, None
            
        # --- Order Block ---
        bullish_ob_list = df_main[(df_main['ob_bullish']) & (df_main['ob_zone_low'] < equilibrium)]
        if not bullish_ob_list.empty:
            bullish_ob = bullish_ob_list.iloc[-1]
            if abs(latest_price - bullish_ob['ob_zone_high']) / bullish_ob['ob_zone_high'] < 0.005: # Test the top of the OB
                recent_choch = df_small[df_small['choch'] == 'bullish'].tail(1)
                if not recent_choch.empty and recent_choch.index[0] >= df_small.index[-5]:
                    sl_price = bullish_ob['ob_zone_low']
                    return 'long', latest_price, sl_price

        # --- Fair Value Gap (FVG) ---
        bullish_fvg_list = df_main[(df_main['fvg_bullish_low'].notna()) & (df_main['fvg_bullish_low'] < equilibrium)]
        if not bullish_fvg_list.empty:
            bullish_fvg = bullish_fvg_list.iloc[-1]
            if bullish_fvg['fvg_bullish_low'] <= latest_price <= bullish_fvg['fvg_bullish_high']:
                recent_choch = df_small[df_small['choch'] == 'bullish'].tail(1)
                if not recent_choch.empty and recent_choch.index[0] >= df_small.index[-5]:
                    sl_price = bullish_fvg['fvg_bullish_low']
                    return 'long', latest_price, sl_price

        # --- Breaker Block (BB) ---
        bullish_bb_list = df_main[(df_main['bb_bullish']) & (df_main['ob_zone_low'] < equilibrium)]
        if not bullish_bb_list.empty:
            bullish_bb = bullish_bb_list.iloc[-1]
            if abs(latest_price - bullish_bb['ob_zone_high']) / bullish_bb['ob_zone_high'] < 0.005:
                recent_choch = df_small[df_small['choch'] == 'bullish'].tail(1)
                if not recent_choch.empty and recent_choch.index[0] >= df_small.index[-5]:
                    sl_price = bullish_bb['ob_zone_low']
                    return 'long', latest_price, sl_price

    elif bias == 'short':
        if latest_price < equilibrium:
            return 'none', None, None

        # --- Order Block ---
        bearish_ob_list = df_main[(df_main['ob_bearish']) & (df_main['ob_zone_high'] > equilibrium)]
        if not bearish_ob_list.empty:
            bearish_ob = bearish_ob_list.iloc[-1]
            if abs(latest_price - bearish_ob['ob_zone_low']) / bearish_ob['ob_zone_low'] < 0.005:
                recent_choch = df_small[df_small['choch'] == 'bearish'].tail(1)
                if not recent_choch.empty and recent_choch.index[0] >= df_small.index[-5]:
                    sl_price = bearish_ob['ob_zone_high']
                    return 'short', latest_price, sl_price
        
        # --- Fair Value Gap (FVG) ---
        bearish_fvg_list = df_main[(df_main['fvg_bearish_low'].notna()) & (df_main['fvg_bearish_high'] > equilibrium)]
        if not bearish_fvg_list.empty:
            bearish_fvg = bearish_fvg_list.iloc[-1]
            if bearish_fvg['fvg_bearish_low'] <= latest_price <= bearish_fvg['fvg_bearish_high']:
                recent_choch = df_small[df_small['choch'] == 'bearish'].tail(1)
                if not recent_choch.empty and recent_choch.index[0] >= df_small.index[-5]:
                    sl_price = bearish_fvg['fvg_bearish_high']
                    return 'short', latest_price, sl_price

        # --- Breaker Block (BB) ---
        bearish_bb_list = df_main[(df_main['bb_bearish']) & (df_main['ob_zone_high'] > equilibrium)]
        if not bearish_bb_list.empty:
            bearish_bb = bearish_bb_list.iloc[-1]
            if abs(latest_price - bearish_bb['ob_zone_low']) / bearish_bb['ob_zone_low'] < 0.005:
                recent_choch = df_small[df_small['choch'] == 'bearish'].tail(1)
                if not recent_choch.empty and recent_choch.index[0] >= df_small.index[-5]:
                    sl_price = bearish_bb['ob_zone_high']
                    return 'short', latest_price, sl_price

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
    df_with_bos = detect_bos_choch(df_with_fvg)
    df_with_ob = detect_order_block(df_with_bos)
    df_main_analyzed = detect_breaker_block(df_with_ob)
    df_small_analyzed = detect_bos_choch(df_small.copy())
    
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
