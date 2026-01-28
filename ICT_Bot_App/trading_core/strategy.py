from .market_structure import get_current_bias, detect_bos_choch, find_swings
from .pd_arrays import detect_fvg, detect_order_block, get_swing_and_premium_discount
from .config_loader import TIMEFRAME, TIMEFRAME_SMALLER, RISK_PERCENT_PER_TRADE, STOP_LOSS_POINTS, TAKE_PROFIT_POINTS
import math
import pandas as pd # Import pandas

# Định nghĩa một type alias cho BaseConnector để dễ dàng sử dụng type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .connectors.base_connector import BaseConnector

def calculate_sl_tp(entry_price: float, order_type: str, point: float) -> tuple[float | None, float | None]:
    """Tính toán SL/TP dựa trên points."""
    if order_type == 'long':
        sl = entry_price - STOP_LOSS_POINTS * point
        tp = entry_price + TAKE_PROFIT_POINTS * point
    elif order_type == 'short':
        sl = entry_price + STOP_LOSS_POINTS * point
        tp = entry_price - TAKE_PROFIT_POINTS * point
    else:
        return None, None
    return sl, tp

def calculate_position_size(connector: 'BaseConnector', sl_points: float, signals=None) -> float | None:
    """Tính toán khối lượng giao dịch dựa trên % rủi ro."""
    balance = connector.get_account_balance()
    symbol_info = connector.get_symbol_info()

    if balance is None or symbol_info is None:
        msg = "Không thể tính khối lượng, thiếu thông tin tài khoản hoặc symbol."
        if signals:
            signals.log_message.emit(msg)
        else:
            print(msg)
        return None

    # Đảm bảo RISK_PERCENT_PER_TRADE là float và lớn hơn 0
    risk_percent = float(RISK_PERCENT_PER_TRADE) # Đã được ép kiểu trong config_loader
    if risk_percent <= 0:
        msg = "Tỷ lệ rủi ro phải lớn hơn 0."
        if signals:
            signals.log_message.emit(msg)
        else:
            print(msg)
        return None

    # 1. Tính toán rủi ro bằng tiền
    risk_amount = balance * (risk_percent / 100)

    # 2. Tính toán mức lỗ trên mỗi Lot
    # Sử dụng getattr để truy cập thuộc tính một cách an toàn
    tick_value = getattr(symbol_info, 'tick_value', 0.0)
    tick_size = getattr(symbol_info, 'tick_size', 0.0)
    
    # Giá trị của mỗi point
    point_value = tick_value / tick_size if tick_size > 0 else 0.0
    
    # Mức lỗ trên mỗi Lot
    loss_per_lot = sl_points * point_value
    
    if loss_per_lot <= 0:
        msg = "Không thể tính khối lượng, mức lỗ trên mỗi lot <= 0."
        if signals:
            signals.log_message.emit(msg)
        else:
            print(msg)
        return None

    # 3. Tính toán khối lượng
    volume = risk_amount / loss_per_lot
    
    # Làm tròn khối lượng về bước khối lượng cho phép của sàn
    volume_step = getattr(symbol_info, 'volume_step', 0.001)
    volume = math.floor(volume / volume_step) * volume_step
    
    # Kiểm tra khối lượng tối thiểu và tối đa
    volume_min = getattr(symbol_info, 'volume_min', 0.0)
    volume_max = getattr(symbol_info, 'volume_max', float('inf'))

    if volume < volume_min:
        msg = f"Khối lượng tính toán ({volume}) nhỏ hơn mức tối thiểu ({volume_min}). Hủy lệnh."
        if signals:
            signals.log_message.emit(msg)
        else:
            print(msg)
        return None
    if volume > volume_max:
        volume = volume_max
        msg = f"Khối lượng tính toán vượt mức tối đa, sử dụng khối lượng tối đa: {volume}"
        if signals:
            signals.log_message.emit(msg)
        else:
            print(msg)

    return volume

def evaluate_signal(df_main: pd.DataFrame, df_small: pd.DataFrame, signals=None) -> tuple[str, float | None]:
    """
    Đánh giá tín hiệu giao dịch, tích hợp logic Premium/Discount.
    """
    # 1. Xác định xu hướng chính
    bias = get_current_bias(df_main, signals)
    if bias == 'neutral':
        return 'none', None

    # 2. Xác định con sóng và vùng Premium/Discount
    df_main_with_swings = find_swings(df_main.copy())
    swing_highs = df_main_with_swings['swing_high'].dropna()
    swing_lows = df_main_with_swings['swing_low'].dropna()
    
    swing_high, swing_low, equilibrium = get_swing_and_premium_discount(df_main, swing_highs, swing_lows)

    if equilibrium is None:
        msg = "Không xác định được con sóng để tính Premium/Discount."
        if signals:
            signals.log_message.emit(msg)
        else:
            print(msg)
        return 'none', None
        
    latest_price = df_main['close'].iloc[-1]

    # 3. Logic vào lệnh
    if bias == 'long':
        # Điều kiện MUA: Giá phải nằm trong vùng Discount
        if latest_price > equilibrium:
            msg = f"Giá hiện tại {latest_price} đang ở vùng Premium, không tìm lệnh Mua."
            if signals:
                signals.log_message.emit(msg)
            else:
                print(msg)
            return 'none', None
            
        # --- Tìm kiếm tín hiệu từ Order Block ---
        # Tìm Bullish OB trong vùng Discount
        bullish_ob_list = df_main[(df_main['ob_bullish']) & (df_main['ob_zone_low'] < equilibrium)]
        if not bullish_ob_list.empty:
            bullish_ob = bullish_ob_list.iloc[-1] # Lấy OB gần nhất
            if abs(latest_price - bullish_ob['ob_zone_low']) / bullish_ob['ob_zone_low'] < 0.005:
                if not df_small[df_small['choch'] == 'bullish'].empty:
                    msg = f"Tín hiệu MUA từ OB: Giá ({latest_price}) về OB tại vùng Discount và có CHOCH xác nhận."
                    if signals:
                        signals.log_message.emit(msg)
                    else:
                        print(msg)
                    return 'long', latest_price

        # --- Tìm kiếm tín hiệu từ Fair Value Gap (FVG) ---
        bullish_fvg_list = df_main[(df_main['fvg_bullish_low'].notna()) & (df_main['fvg_bullish_low'] < equilibrium)]
        if not bullish_fvg_list.empty:
            bullish_fvg = bullish_fvg_list.iloc[-1] # Lấy FVG gần nhất
            # Kiểm tra giá có đang trong vùng FVG không
            if bullish_fvg['fvg_bullish_low'] <= latest_price <= bullish_fvg['fvg_bullish_high']:
                if not df_small[df_small['choch'] == 'bullish'].empty:
                    msg = f"Tín hiệu MUA từ FVG: Giá ({latest_price}) vào FVG tại vùng Discount và có CHOCH xác nhận."
                    if signals:
                        signals.log_message.emit(msg)
                    else:
                        print(msg)
                    return 'long', latest_price

    elif bias == 'short':
        # Điều kiện BÁN: Giá phải nằm trong vùng Premium
        if latest_price < equilibrium:
            msg = f"Giá hiện tại {latest_price} đang ở vùng Discount, không tìm lệnh Bán."
            if signals:
                signals.log_message.emit(msg)
            else:
                print(msg)
            return 'none', None

        # --- Tìm kiếm tín hiệu từ Order Block ---
        bearish_ob_list = df_main[(df_main['ob_bearish']) & (df_main['ob_zone_high'] > equilibrium)]
        if not bearish_ob_list.empty:
            bearish_ob = bearish_ob_list.iloc[-1] # Lấy OB gần nhất
            if abs(latest_price - bearish_ob['ob_zone_high']) / bearish_ob['ob_zone_high'] < 0.005:
                if not df_small[df_small['choch'] == 'bearish'].empty:
                    msg = f"Tín hiệu BÁN từ OB: Giá ({latest_price}) về OB tại vùng Premium và có CHOCH xác nhận."
                    if signals:
                        signals.log_message.emit(msg)
                    else:
                        print(msg)
                    return 'short', latest_price
        
        # --- Tìm kiếm tín hiệu từ Fair Value Gap (FVG) ---
        bearish_fvg_list = df_main[(df_main['fvg_bearish_low'].notna()) & (df_main['fvg_bearish_high'] > equilibrium)]
        if not bearish_fvg_list.empty:
            bearish_fvg = bearish_fvg_list.iloc[-1]
            # Kiểm tra giá có đang trong vùng FVG không
            if bearish_fvg['fvg_bearish_low'] <= latest_price <= bearish_fvg['fvg_bearish_high']:
                if not df_small[df_small['choch'] == 'bearish'].empty:
                    msg = f"Tín hiệu BÁN từ FVG: Giá ({latest_price}) vào FVG tại vùng Premium và có CHOCH xác nhận."
                    if signals:
                        signals.log_message.emit(msg)
                    else:
                        print(msg)
                    return 'short', latest_price

    return 'none', None

def execute_strategy(connector: 'BaseConnector', signals=None) -> None:
    """Thực thi chiến lược, với khối lượng động."""
    if connector.get_open_positions():
        msg = "Đã có vị thế đang mở. Bỏ qua."
        if signals:
            signals.log_message.emit(msg)
        else:
            print(msg)
        return

    msg = "Đang lấy và phân tích dữ liệu..."
    if signals:
        signals.log_message.emit(msg)
    else:
        print(msg)
    
    # Đảm bảo TIMEFRAME và TIMEFRAME_SMALLER không phải là None
    main_timeframe = str(TIMEFRAME) # Đã được ép kiểu trong config_loader
    small_timeframe = str(TIMEFRAME_SMALLER) # Đã được ép kiểu trong config_loader

    df_main = connector.fetch_ohlcv(main_timeframe, limit=200)
    df_small = connector.fetch_ohlcv(small_timeframe, limit=100)

    if df_main is None or df_small is None: return

    # Chạy pipeline phân tích
    df_with_fvg = detect_fvg(df_main.copy())
    df_with_bos = detect_bos_choch(df_with_fvg)
    df_main_analyzed = detect_order_block(df_with_bos)
    df_small_analyzed = detect_bos_choch(df_small.copy())
    
    signal, entry_price = evaluate_signal(df_main_analyzed, df_small_analyzed, signals)

    if signal != 'none':
        symbol_info = connector.get_symbol_info()
        if symbol_info is None:
            msg = "Không thể lấy thông tin symbol để tính SL/TP."
            if signals:
                signals.log_message.emit(msg)
            else:
                print(msg)
            return
        
        # Đảm bảo symbol_info.point là float
        point_value = getattr(symbol_info, 'point', 0.00001)
        
        # entry_price có thể là None từ evaluate_signal
        if entry_price is None:
            msg = "Giá vào lệnh không hợp lệ."
            if signals:
                signals.log_message.emit(msg)
            else:
                print(msg)
            return

        sl, tp = calculate_sl_tp(entry_price, signal, point_value)
        
        # Tính toán khối lượng động
        quantity = calculate_position_size(connector, STOP_LOSS_POINTS, signals)
        
        if quantity is not None and quantity > 0:
            msg = f"Tín hiệu {signal.upper()}: Giá={entry_price}, SL={sl}, TP={tp}, Khối lượng={quantity}"
            if signals:
                signals.log_message.emit(msg)
                # Có thể phát thêm tín hiệu cho lệnh mới
                signals.new_position.emit({
                    'id': 'N/A', # Connector nên cung cấp ID thực tế
                    'symbol': connector.get_symbol(),
                    'side': signal.upper(),
                    'quantity': quantity,
                    'entry_price': entry_price,
                    'sl': sl,
                    'tp': tp,
                    'status': 'OPEN'
                })
            else:
                print(msg)
            # Chú ý: place_order cần trả về ID lệnh, không phải None.
            # Và cần xử lý kết quả trả về của place_order.
            # sl và tp có thể là None từ calculate_sl_tp
            if sl is not None and tp is not None:
                connector.place_order(signal, quantity, sl, tp) 
            else:
                msg = "SL/TP không hợp lệ. Hủy lệnh."
                if signals:
                    signals.log_message.emit(msg)
                else:
                    print(msg)
        else:
            msg = "Không thể xác định khối lượng giao dịch. Hủy lệnh."
            if signals:
                signals.log_message.emit(msg)
            else:
                print(msg)
    else:
        msg = "Không có tín hiệu giao dịch rõ ràng."
        if signals:
            signals.log_message.emit(msg)
        else:
            print(msg)