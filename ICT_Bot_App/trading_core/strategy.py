from .market_structure import get_current_bias, detect_bos_choch, find_swings, get_dealing_range, is_in_premium_or_discount
from .pd_arrays import detect_fvg, detect_order_block, detect_breaker_block
from .config_loader import TIMEFRAME, TIMEFRAME_SMALLER, RISK_PERCENT_PER_TRADE, TAKE_PROFIT_RR, ENABLE_LOGGING, SL_BUFFER_POINTS
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
        return None

    risk_percent = float(RISK_PERCENT_PER_TRADE)
    if risk_percent <= 0:
        msg = "Tỷ lệ rủi ro phải lớn hơn 0."
        if signals: signals.log_message.emit(msg)
        return None

    risk_amount = balance * (risk_percent / 100)
    sl_pips = abs(entry_price - sl_price)
    if sl_pips == 0:
        msg = "Khoảng cách SL bằng 0, không thể tính khối lượng."
        if signals: signals.log_message.emit(msg)
        return None

    tick_value = getattr(symbol_info, 'tick_value', 0.0)
    tick_size = getattr(symbol_info, 'tick_size', 0.0)
    point_value = tick_value / tick_size if tick_size > 0 else 0.0
    point_digits = abs(str(tick_size)[::-1].find('.'))
    
    loss_per_lot = (sl_pips * (10**point_digits)) * point_value
    
    if loss_per_lot <= 0:
        msg = "Không thể tính khối lượng, mức lỗ trên mỗi lot <= 0."
        if signals: signals.log_message.emit(msg)
        return None

    volume = risk_amount / loss_per_lot
    volume_step = getattr(symbol_info, 'volume_step', 0.01)
    volume = math.floor(volume / volume_step) * volume_step
    
    volume_min = getattr(symbol_info, 'volume_min', 0.01)
    volume_max = getattr(symbol_info, 'volume_max', 1000.0)

    if volume < volume_min:
        msg = f"Khối lượng tính toán ({volume}) nhỏ hơn mức tối thiểu ({volume_min}). Hủy lệnh."
        if signals: signals.log_message.emit(msg)
        return None
    if volume > volume_max:
        volume = volume_max
        msg = f"Khối lượng tính toán vượt mức tối đa, sử dụng khối lượng tối đa: {volume}"
        if signals: signals.log_message.emit(msg)

    return volume

def evaluate_signal(df_main: pd.DataFrame, df_small: pd.DataFrame, connector: 'BaseConnector', signals=None) -> tuple[str, float | None, float | None]:
    bias = get_current_bias(df_main, signals)
    if ENABLE_LOGGING and signals: signals.log_message.emit(f"[EVAL] Bias: {bias}")
    if bias == 'neutral':
        return 'none', None, None

    # Phân tích FVG cho LTF trước
    df_small_with_fvg = detect_fvg(df_small.copy())

    dr_low, dr_high = get_dealing_range(df_main)
    
    if dr_low is None or dr_high is None:
        if ENABLE_LOGGING and signals: signals.log_message.emit("[EVAL] Không xác định được Dealing Range.")
        return 'none', None, None

    equilibrium = (dr_high + dr_low) / 2
    latest_close = df_main['close'].iloc[-1]
    latest_high = df_main['high'].iloc[-1]
    latest_low = df_main['low'].iloc[-1]
    
    if ENABLE_LOGGING and signals: signals.log_message.emit(f"[EVAL] Dealing Range: {dr_low:.5f} - {dr_high:.5f} (Eq={equilibrium:.5f}) | Price: {latest_close:.5f}")

    # Tính toán giá trị buffer
    point_value = getattr(connector.get_symbol_info(), 'point', 0.00001)
    sl_buffer_value = SL_BUFFER_POINTS * point_value

    if bias == 'long':
        if latest_close > equilibrium:
             if ENABLE_LOGGING and signals: signals.log_message.emit(f"[EVAL] Price in PREMIUM. Skipping LONG.")
             return 'none', None, None
        
        if ENABLE_LOGGING and signals: signals.log_message.emit("[EVAL] Price in DISCOUNT. Looking for Bullish PD Arrays...")
        
        # 1. Tìm Bullish Order Block
        bullish_ob_list = df_main[(df_main['ob_bullish']) & (df_main['ob_zone_low'] < equilibrium)]
        if not bullish_ob_list.empty:
            bullish_ob = bullish_ob_list.iloc[-1]
            if latest_low <= bullish_ob['ob_zone_high']:
                if ENABLE_LOGGING and signals: signals.log_message.emit(f"[EVAL] Price touched Bullish OB. Checking LTF Confirmation...")
                
                found, entry, _ = check_ltf_confirmation(df_small_with_fvg, 'bullish', signals)
                if found:
                     sl_price = bullish_ob['ob_zone_low'] - sl_buffer_value
                     if entry > sl_price:
                         if ENABLE_LOGGING and signals: signals.log_message.emit("[EVAL] Signal found: LONG from OB")
                         return 'long', entry, sl_price
                     elif ENABLE_LOGGING and signals: signals.log_message.emit(f"[EVAL] INVALID (OB): Entry Price <= SL.")

        # 2. Tìm Bullish FVG
        bullish_fvg_list = df_main[(df_main['fvg_bullish_high'].notna()) & (df_main['fvg_bullish_low'] < equilibrium)]
        if not bullish_fvg_list.empty:
            bullish_fvg = bullish_fvg_list.iloc[-1]
            if latest_low <= bullish_fvg['fvg_bullish_high']:
                if ENABLE_LOGGING and signals: signals.log_message.emit(f"[EVAL] Price touched Bullish FVG. Checking LTF Confirmation...")
                
                found, entry, _ = check_ltf_confirmation(df_small_with_fvg, 'bullish', signals)
                if found:
                     sl_price = bullish_fvg['fvg_bullish_low'] - sl_buffer_value
                     if entry > sl_price:
                         if ENABLE_LOGGING and signals: signals.log_message.emit("[EVAL] Signal found: LONG from FVG")
                         return 'long', entry, sl_price
                     elif ENABLE_LOGGING and signals: signals.log_message.emit(f"[EVAL] INVALID (FVG): Entry Price <= SL.")

        # 3. Tìm Bullish Breaker Block
        bullish_bb_list = df_main[(df_main['bb_bullish']) & (df_main['ob_zone_low'] < equilibrium)]
        if not bullish_bb_list.empty:
            bullish_bb = bullish_bb_list.iloc[-1]
            if latest_low <= bullish_bb['ob_zone_high']:
                if ENABLE_LOGGING and signals: signals.log_message.emit(f"[EVAL] Price touched Bullish BB. Checking LTF Confirmation...")

                found, entry, _ = check_ltf_confirmation(df_small_with_fvg, 'bullish', signals)
                if found:
                     sl_price = bullish_bb['ob_zone_low'] - sl_buffer_value
                     if entry > sl_price:
                         if ENABLE_LOGGING and signals: signals.log_message.emit("[EVAL] Signal found: LONG from BB")
                         return 'long', entry, sl_price
                     elif ENABLE_LOGGING and signals: signals.log_message.emit(f"[EVAL] INVALID (BB): Entry Price <= SL.")

    elif bias == 'short':
        if latest_close < equilibrium:
            if ENABLE_LOGGING and signals: signals.log_message.emit(f"[EVAL] Price in DISCOUNT. Skipping SHORT.")
            return 'none', None, None

        if ENABLE_LOGGING and signals: signals.log_message.emit("[EVAL] Price in PREMIUM. Looking for Bearish PD Arrays...")

        # 1. Tìm Bearish Order Block
        bearish_ob_list = df_main[(df_main['ob_bearish']) & (df_main['ob_zone_high'] > equilibrium)]
        if not bearish_ob_list.empty:
            bearish_ob = bearish_ob_list.iloc[-1]
            if latest_high >= bearish_ob['ob_zone_low']:
                if ENABLE_LOGGING and signals: signals.log_message.emit(f"[EVAL] Price touched Bearish OB. Checking LTF Confirmation...")

                found, entry, _ = check_ltf_confirmation(df_small_with_fvg, 'bearish', signals)
                if found:
                     sl_price = bearish_ob['ob_zone_high'] + sl_buffer_value
                     if entry < sl_price:
                        if ENABLE_LOGGING and signals: signals.log_message.emit("[EVAL] Signal found: SHORT from OB")
                        return 'short', entry, sl_price
                     elif ENABLE_LOGGING and signals: signals.log_message.emit(f"[EVAL] INVALID (OB): Entry Price >= SL.")
        
        # 2. Tìm Bearish FVG
        bearish_fvg_list = df_main[(df_main['fvg_bearish_high'].notna()) & (df_main['fvg_bearish_high'] > equilibrium)]
        if not bearish_fvg_list.empty:
            bearish_fvg = bearish_fvg_list.iloc[-1]
            if latest_high >= bearish_fvg['fvg_bearish_low']:
                if ENABLE_LOGGING and signals: signals.log_message.emit(f"[EVAL] Price touched Bearish FVG. Checking LTF Confirmation...")

                found, entry, _ = check_ltf_confirmation(df_small_with_fvg, 'bearish', signals)
                if found:
                     sl_price = bearish_fvg['fvg_bearish_high'] + sl_buffer_value
                     if entry < sl_price:
                        if ENABLE_LOGGING and signals: signals.log_message.emit("[EVAL] Signal found: SHORT from FVG")
                        return 'short', entry, sl_price
                     elif ENABLE_LOGGING and signals: signals.log_message.emit(f"[EVAL] INVALID (FVG): Entry Price >= SL.")

        # 3. Tìm Bearish Breaker Block
        bearish_bb_list = df_main[(df_main['bb_bearish']) & (df_main['ob_zone_high'] > equilibrium)]
        if not bearish_bb_list.empty:
            bearish_bb = bearish_bb_list.iloc[-1]
            if latest_high >= bearish_bb['ob_zone_low']:
                if ENABLE_LOGGING and signals: signals.log_message.emit(f"[EVAL] Price touched Bearish BB. Checking LTF Confirmation...")
                
                found, entry, _ = check_ltf_confirmation(df_small_with_fvg, 'bearish', signals)
                if found:
                     sl_price = bearish_bb['ob_zone_high'] + sl_buffer_value
                     if entry < sl_price:
                        if ENABLE_LOGGING and signals: signals.log_message.emit("[EVAL] Signal found: SHORT from BB")
                        return 'short', entry, sl_price
                     elif ENABLE_LOGGING and signals: signals.log_message.emit(f"[EVAL] INVALID (BB): Entry Price >= SL.")

    return 'none', None, None

def check_ltf_confirmation(df_small: pd.DataFrame, trend: str, signals=None) -> tuple[bool, float | None, float | None]:
    """
    Kiểm tra xác nhận (BOS/CHOCH) trên khung thời gian thấp và tìm điểm vào lệnh tối ưu.
    Trả về: (found, entry_price, sl_price_offset)
    """
    recent_choch = df_small[df_small['choch'] == trend].tail(1)
    recent_bos = df_small[df_small['bos'] == trend].tail(1)
    
    confirmation_found = False
    confirm_idx = None
    
    try:
        # Kiểm tra CHOCH trong 20 nến gần nhất
        if not recent_choch.empty:
            loc = df_small.index.get_loc(recent_choch.index[0])
            if isinstance(loc, slice): loc = loc.start
            if loc >= len(df_small) - 20:
                confirmation_found = True
                confirm_idx = loc
                if ENABLE_LOGGING and signals: signals.log_message.emit(f"[EVAL] Confirmed by: LTF {trend.upper()} CHOCH")
        
        # Kiểm tra BOS trong 20 nến gần nhất nếu chưa tìm thấy CHOCH
        if not confirmation_found and not recent_bos.empty:
            loc = df_small.index.get_loc(recent_bos.index[0])
            if isinstance(loc, slice): loc = loc.start
            if loc >= len(df_small) - 20:
                confirmation_found = True
                confirm_idx = loc
                if ENABLE_LOGGING and signals: signals.log_message.emit(f"[EVAL] Confirmed by: LTF {trend.upper()} BOS")

        if confirmation_found:
            # Tối ưu hóa điểm vào lệnh (Entry Optimization)
            # Tìm FVG gần nhất trên LTF
            entry_price = df_small['close'].iloc[-1]

            # Quét ngược lại từ nến hiện tại về nến confirm để tìm FVG
            fvg_col = 'fvg_bullish_high' if trend == 'bullish' else 'fvg_bearish_low'
            
            # Chúng ta chỉ tìm FVG trong khoảng từ nến confirm đến hiện tại
            scan_start = confirm_idx
            ltf_slice = df_small.iloc[scan_start:]
            
            # Logic tìm FVG
            ltf_fvgs = ltf_slice[ltf_slice[fvg_col].notna()]
            
            if not ltf_fvgs.empty:
                best_fvg = ltf_fvgs.iloc[-1] # Lấy FVG mới nhất
                if trend == 'bullish':
                     entry_price = best_fvg['fvg_bullish_high']
                     if ENABLE_LOGGING and signals: signals.log_message.emit(f"[EVAL] Optimized Entry at LTF Bullish FVG: {entry_price}")
                else:
                     entry_price = best_fvg['fvg_bearish_low']
                     if ENABLE_LOGGING and signals: signals.log_message.emit(f"[EVAL] Optimized Entry at LTF Bearish FVG: {entry_price}")
            else:
                if ENABLE_LOGGING and signals: signals.log_message.emit(f"[EVAL] No LTF FVG found, using Market Entry: {entry_price}")

            return True, entry_price, None # SL sẽ dùng SL của HTF setup

    except Exception as e:
        if signals:
            signals.log_message.emit(f"[ERROR] Lỗi khi check LTF confirmation: {e}")
        return False, None, None

    return False, None, None

def execute_strategy(connector: 'BaseConnector', signals=None) -> None:
    if connector.get_open_positions():
        return

    main_timeframe = str(TIMEFRAME)
    small_timeframe = str(TIMEFRAME_SMALLER)

    df_main = connector.fetch_ohlcv(main_timeframe, limit=200)
    df_small = connector.fetch_ohlcv(small_timeframe, limit=100)

    if df_main is None or df_small is None: return

    df_with_fvg = detect_fvg(df_main.copy())
    df_with_swings = find_swings(df_with_fvg)
    df_with_bos = detect_bos_choch(df_with_swings)
    df_with_ob = detect_order_block(df_with_bos)
    df_main_analyzed = detect_breaker_block(df_with_ob)
    df_small_swings = find_swings(df_small.copy())
    df_small_analyzed = detect_bos_choch(df_small_swings)
    
    signal, entry_price, sl_price = evaluate_signal(df_main_analyzed, df_small_analyzed, connector, signals)

    if signal != 'none' and entry_price is not None and sl_price is not None:
        rr = float(TAKE_PROFIT_RR)
        sl_distance = abs(entry_price - sl_price)
        tp_price = entry_price + (sl_distance * rr) if signal == 'long' else entry_price - (sl_distance * rr)

        quantity = calculate_position_size(connector, sl_price, entry_price, signals)
        
        if quantity is not None and quantity > 0:
            msg = f"Tín hiệu {signal.upper()}: Giá={entry_price:.5f}, SL={sl_price:.5f}, TP={tp_price:.5f}, Khối lượng={quantity}"
            if ENABLE_LOGGING and signals: signals.log_message.emit(msg)
            connector.place_order(signal, quantity, sl_price, tp_price) 
    else:
        if ENABLE_LOGGING and signals: signals.log_message.emit("Không có tín hiệu giao dịch rõ ràng.")

