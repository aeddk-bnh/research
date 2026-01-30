from .market_structure import get_current_bias, detect_bos_choch, find_swings, get_dealing_range, is_in_premium_or_discount, calculate_ote_levels, is_price_in_ote_zone, get_recent_swing_range, detect_equal_highs_lows, detect_liquidity_sweep
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


def calculate_partial_orders(
    total_quantity: float, 
    entry_price: float, 
    sl_price: float, 
    signal: str,
    connector: 'BaseConnector'
) -> list[dict]:
    """
    Tính toán các lệnh partial profit theo ICT method.
    
    ICT Partial Profit Strategy:
    - TP1: 50% @ 1:1 R:R
    - TP2: 25% @ 2:1 R:R
    - TP3: 25% @ 3:1 R:R (hoặc trailing)
    
    Returns:
        List of order dicts: [{'quantity': float, 'tp': float, 'label': str}, ...]
    """
    if not PARTIAL_PROFITS_ENABLED:
        # Nếu tắt partial, trả về 1 lệnh duy nhất với TP mặc định
        sl_distance = abs(entry_price - sl_price)
        if signal == 'long':
            tp = entry_price + (sl_distance * TAKE_PROFIT_RR)
        else:
            tp = entry_price - (sl_distance * TAKE_PROFIT_RR)
        return [{'quantity': total_quantity, 'tp': tp, 'label': 'FULL'}]
    
    symbol_info = connector.get_symbol_info()
    volume_step = getattr(symbol_info, 'volume_step', 0.01)
    volume_min = getattr(symbol_info, 'volume_min', 0.01)
    
    sl_distance = abs(entry_price - sl_price)
    
    # Tính TP levels
    if signal == 'long':
        tp1 = entry_price + (sl_distance * PARTIAL_TP1_RR)
        tp2 = entry_price + (sl_distance * PARTIAL_TP2_RR)
        tp3 = entry_price + (sl_distance * PARTIAL_TP3_RR)
    else:
        tp1 = entry_price - (sl_distance * PARTIAL_TP1_RR)
        tp2 = entry_price - (sl_distance * PARTIAL_TP2_RR)
        tp3 = entry_price - (sl_distance * PARTIAL_TP3_RR)
    
    # Tính khối lượng cho từng phần
    qty1_raw = total_quantity * (PARTIAL_TP1_PERCENT / 100)
    qty2_raw = total_quantity * (PARTIAL_TP2_PERCENT / 100)
    qty3_raw = total_quantity - qty1_raw - qty2_raw  # Phần còn lại
    
    # Làm tròn theo volume_step
    qty1 = math.floor(qty1_raw / volume_step) * volume_step
    qty2 = math.floor(qty2_raw / volume_step) * volume_step
    qty3 = math.floor(qty3_raw / volume_step) * volume_step
    
    orders = []
    
    # Chỉ thêm lệnh nếu quantity >= volume_min
    if qty1 >= volume_min:
        orders.append({'quantity': qty1, 'tp': tp1, 'label': 'TP1 (50%@1:1)'})
    
    if qty2 >= volume_min:
        orders.append({'quantity': qty2, 'tp': tp2, 'label': 'TP2 (25%@2:1)'})
    
    if qty3 >= volume_min:
        orders.append({'quantity': qty3, 'tp': tp3, 'label': 'TP3 (25%@3:1)'})
    
    # Nếu không có lệnh nào đủ điều kiện, fallback về 1 lệnh
    if not orders:
        if signal == 'long':
            tp = entry_price + (sl_distance * TAKE_PROFIT_RR)
        else:
            tp = entry_price - (sl_distance * TAKE_PROFIT_RR)
        orders = [{'quantity': total_quantity, 'tp': tp, 'label': 'FULL (min qty)'}]
    
    return orders


def check_ote_confluence(df: pd.DataFrame, current_price: float, bias: str, signals=None) -> tuple[bool, dict | None]:
    """
    Kiểm tra xem giá hiện tại có nằm trong vùng OTE không.
    
    Args:
        df: DataFrame với swing data
        current_price: Giá hiện tại
        bias: 'long' hoặc 'short'
        signals: Signal object để log
    
    Returns:
        (bool, dict): (có trong OTE zone không, OTE levels dict)
    
    ICT OTE Logic:
    - Cho LONG: Giá cần retrace về vùng OTE (62%-79%) của swing range
    - Cho SHORT: Tương tự nhưng ngược lại
    """
    if not OTE_ENABLED:
        return True, None  # Bỏ qua OTE check nếu tắt
    
    direction = 'bullish' if bias == 'long' else 'bearish'
    swing_low, swing_high = get_recent_swing_range(df, direction)
    
    if swing_low is None or swing_high is None:
        if ENABLE_LOGGING and signals:
            signals.log_message.emit("[OTE] Không tìm thấy swing range cho OTE")
        return True, None  # Không block nếu không tìm thấy swing
    
    ote_levels = calculate_ote_levels(swing_high, swing_low, direction)
    in_ote, position = is_price_in_ote_zone(current_price, ote_levels, direction)
    
    if ENABLE_LOGGING and signals:
        signals.log_message.emit(
            f"[OTE] Range: {swing_low:.2f}-{swing_high:.2f} | "
            f"OTE Zone: {ote_levels['ote_62']:.2f}-{ote_levels['ote_79']:.2f} | "
            f"Price: {current_price:.2f} | Position: {position}"
        )
    
    return in_ote, ote_levels

def evaluate_signal(df_main: pd.DataFrame, df_small: pd.DataFrame, daily_bias: str, connector: 'BaseConnector', signals=None) -> tuple[str, float | None, float | None]:
    """Đánh giá tín hiệu dựa trên HTF bias, PD-arrays và xác nhận LTF."""
    
    # BỘ LỌC 1: HTF BIAS FILTER
    # ------------------------------------
    if daily_bias == 'neutral':
        if ENABLE_LOGGING and signals: signals.log_message.emit(f"[FILTER] HTF BIAS (D1) là NEUTRAL. Bỏ qua tín hiệu.")
        return 'none', None, None

    # Xác định bias của khung thời gian chính (M15/H1)
    ltf_bias = get_current_bias(df_main, signals)
    if ENABLE_LOGGING and signals: signals.log_message.emit(f"[EVAL] LTF Bias ({TIMEFRAME}): {ltf_bias}")
    
    if ltf_bias == 'neutral':
        return 'none', None, None
        
    # So sánh LTF bias với Daily bias
    if (ltf_bias == 'long' and daily_bias == 'short') or \
       (ltf_bias == 'short' and daily_bias == 'long'):
        if ENABLE_LOGGING and signals: 
            signals.log_message.emit(f"[FILTER] Tín hiệu {ltf_bias.upper()} ngược chiều HTF BIAS ({daily_bias.upper()}). Bỏ qua.")
        return 'none', None, None
    
    if ENABLE_LOGGING and signals: 
        signals.log_message.emit(f"[OK] Tín hiệu {ltf_bias.upper()} cùng chiều HTF BIAS ({daily_bias.upper()}).")

    bias = ltf_bias # Sử dụng ltf_bias cho phần còn lại của logic
    # ------------------------------------
    
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
        
        # OTE Confluence Check cho LONG
        in_ote, ote_levels = check_ote_confluence(df_main, latest_close, bias, signals)
        if OTE_ENABLED and not in_ote:
            if ENABLE_LOGGING and signals: 
                signals.log_message.emit("[EVAL] Price NOT in OTE zone. Skipping LONG entry.")
            return 'none', None, None
        
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

        # OTE Confluence Check cho SHORT
        in_ote, ote_levels = check_ote_confluence(df_main, latest_close, bias, signals)
        if OTE_ENABLED and not in_ote:
            if ENABLE_LOGGING and signals: 
                signals.log_message.emit("[EVAL] Price NOT in OTE zone. Skipping SHORT entry.")
            return 'none', None, None

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

    # --- SILVER BULLET STRATEGY CHECK ---
    # Nếu chưa có signal nào từ core strategy, check Silver Bullet
    # Lưu ý: Silver Bullet có thể hoạt động độc lập với Premium/Discount bias đôi khi, 
    # nhưng ở đây ta vẫn tuân thủ Bias chung để an toàn.
    
    # Sử dụng df_small (LTF) để check Silver Bullet vì nó cần độ chính xác cao về thời gian (M5/M15)
    sb_found, sb_entry, sb_sl = detect_silver_bullet_setup(df_small, latest_close, bias, signals)
    
    if sb_found and sb_entry is not None and sb_sl is not None:
        # Áp dụng buffer cho SL
        if bias == 'long':
            sb_sl -= sl_buffer_value
            if sb_entry > sb_sl:
                if ENABLE_LOGGING and signals: signals.log_message.emit(f"[EVAL] Signal found: Silver Bullet LONG")
                return 'long', sb_entry, sb_sl
        else:
            sb_sl += sl_buffer_value
            if sb_entry < sb_sl:
                if ENABLE_LOGGING and signals: signals.log_message.emit(f"[EVAL] Signal found: Silver Bullet SHORT")
                return 'short', sb_entry, sb_sl

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
                
                # Check ICT 2022 Model (Liquidity Sweep before CHOCH)
                # Check 10 nến trước CHOCH
                sweep_found = False
                for k in range(max(0, confirm_idx - 10), confirm_idx):
                    sweep_type = detect_liquidity_sweep(df_small, k, lookback=20)
                    expected_sweep = 'bullish' if trend == 'bullish' else 'bearish' # Bullish Setup cần Bullish Sweep (quét đáy)
                    if sweep_type == expected_sweep:
                        sweep_found = True
                        break
                
                if sweep_found and ENABLE_LOGGING and signals:
                    signals.log_message.emit(f"[ICT 2022] Liquidity Sweep detected before CHOCH! High Probability Setup.")
        
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
        if ENABLE_LOGGING and signals: signals.log_message.emit("Đã có lệnh đang mở, bỏ qua lần quét này.")
        return

    # Tải dữ liệu từ config
    main_timeframe = config_manager.get('trading.timeframe', 'H1')
    small_timeframe = config_manager.get('trading.timeframe_smaller', 'M15')
    htf_timeframe = config_manager.get('trading.htf_timeframe', 'H4')

    # 1. Tải dữ liệu OHLCV
    df_main = connector.fetch_ohlcv(main_timeframe, limit=200)
    df_small = connector.fetch_ohlcv(small_timeframe, limit=100)
    df_htf = connector.fetch_ohlcv(htf_timeframe, limit=200)

    if df_main is None or df_small is None or df_htf is None:
        if signals: signals.log_message.emit(f"Lỗi: Không tải được toàn bộ dữ liệu cần thiết ({main_timeframe}, {small_timeframe}, {htf_timeframe}).")
        return
        
    # 2. Xác định HTF Bias
    from .market_structure import get_htf_bias
    htf_bias = get_htf_bias(df_htf, htf_label=htf_timeframe)
    if signals:
        signals.log_message.emit(f"--- HTF Bias ({htf_timeframe}): {htf_bias.upper()} ---")
        # Cập nhật UI với bias đầy đủ
        # signals.market_bias.emit(f"HTF ({htf_timeframe}): {htf_bias.upper()}")
        
    # 3. Phân tích dữ liệu...
    # ... (giữ nguyên phần còn lại)

    # 4. Đánh giá tín hiệu với HTF Bias
    signal, entry_price, sl_price = evaluate_signal(df_main_analyzed, df_small_analyzed, htf_bias, connector, signals)

    if signal != 'none' and entry_price is not None and sl_price is not None:
        quantity = calculate_position_size(connector, sl_price, entry_price, signals)
        
        if quantity is not None and quantity > 0:
            # Tính toán các lệnh partial profit
            partial_orders = calculate_partial_orders(quantity, entry_price, sl_price, signal, connector)
            
            if PARTIAL_PROFITS_ENABLED:
                if ENABLE_LOGGING and signals: 
                    signals.log_message.emit(f"[PARTIAL] Chia {len(partial_orders)} lệnh partial profit:")
                
                for i, order in enumerate(partial_orders):
                    msg = f"  [{order['label']}] Qty={order['quantity']:.4f}, TP={order['tp']:.5f}"
                    if ENABLE_LOGGING and signals: signals.log_message.emit(msg)
                    connector.place_order(signal, order['quantity'], sl_price, order['tp'])
            else:
                # Lệnh đơn như cũ
                rr = float(TAKE_PROFIT_RR)
                sl_distance = abs(entry_price - sl_price)
                tp_price = entry_price + (sl_distance * rr) if signal == 'long' else entry_price - (sl_distance * rr)
                
                msg = f"Tín hiệu {signal.upper()}: Giá={entry_price:.5f}, SL={sl_price:.5f}, TP={tp_price:.5f}, Khối lượng={quantity}"
                if ENABLE_LOGGING and signals: signals.log_message.emit(msg)
                connector.place_order(signal, quantity, sl_price, tp_price)
    else:
        if ENABLE_LOGGING and signals: signals.log_message.emit("Không có tín hiệu giao dịch rõ ràng.")

