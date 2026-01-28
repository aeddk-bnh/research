from market_structure import get_current_bias, detect_bos_choch
from pd_arrays import detect_fvg, detect_order_block
from config import TIMEFRAME, TIMEFRAME_SMALLER, RISK_PERCENT_PER_TRADE, STOP_LOSS_POINTS, TAKE_PROFIT_POINTS, PLATFORM
import math

def calculate_sl_tp(entry_price, order_type, point):
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

def calculate_position_size(connector, sl_points):
    """Tính toán khối lượng giao dịch dựa trên % rủi ro."""
    balance = connector.get_account_balance()
    symbol_info = connector.get_symbol_info()

    if balance is None or symbol_info is None:
        print("Không thể tính khối lượng, thiếu thông tin tài khoản hoặc symbol.")
        return None

    # 1. Tính toán rủi ro bằng tiền
    risk_amount = balance * (RISK_PERCENT_PER_TRADE / 100)

    # 2. Tính toán mức lỗ trên mỗi Lot
    tick_value = symbol_info.tick_value
    tick_size = symbol_info.tick_size
    
    # Giá trị của mỗi point
    point_value = tick_value / tick_size if tick_size > 0 else 0
    
    # Mức lỗ trên mỗi Lot
    loss_per_lot = sl_points * point_value
    
    if loss_per_lot <= 0:
        print("Không thể tính khối lượng, mức lỗ trên mỗi lot <= 0.")
        return None

    # 3. Tính toán khối lượng
    volume = risk_amount / loss_per_lot
    
    # Làm tròn khối lượng về bước khối lượng cho phép của sàn
    volume_step = symbol_info.volume_step
    volume = math.floor(volume / volume_step) * volume_step
    
    # Kiểm tra khối lượng tối thiểu và tối đa
    if volume < symbol_info.volume_min:
        print(f"Khối lượng tính toán ({volume}) nhỏ hơn mức tối thiểu ({symbol_info.volume_min}). Hủy lệnh.")
        return None
    if volume > symbol_info.volume_max:
        volume = symbol_info.volume_max
        print(f"Khối lượng tính toán vượt mức tối đa, sử dụng khối lượng tối đa: {volume}")

    return volume

def evaluate_signal(df_main, df_small):
    """Đánh giá tín hiệu giao dịch (logic không đổi)."""
    bias = get_current_bias(df_main)
    if bias == 'neutral':
        return 'none', None
    latest_price = df_main['close'].iloc[-1]
    if bias == 'long':
        bullish_ob = df_main[df_main['ob_bullish']].tail(1)
        if not bullish_ob.empty and abs(latest_price - bullish_ob['ob_zone_low'].iloc[0]) / bullish_ob['ob_zone_low'].iloc[0] < 0.005:
            if not df_small[df_small['choch'] == 'bullish'].empty:
                return 'long', latest_price
    elif bias == 'short':
        bearish_ob = df_main[df_main['ob_bearish']].tail(1)
        if not bearish_ob.empty and abs(latest_price - bearish_ob['ob_zone_high'].iloc[0]) / bearish_ob['ob_zone_high'].iloc[0] < 0.005:
            if not df_small[df_small['choch'] == 'bearish'].empty:
                return 'short', latest_price
    return 'none', None

def execute_strategy(connector):
    """Thực thi chiến lược, với khối lượng động."""
    if connector.get_open_positions():
        print("Đã có vị thế đang mở. Bỏ qua.")
        return

    print("Đang lấy và phân tích dữ liệu...")
    df_main = connector.fetch_ohlcv(TIMEFRAME, limit=200)
    df_small = connector.fetch_ohlcv(TIMEFRAME_SMALLER, limit=100)

    if df_main is None or df_small is None: return

    df_main = detect_bos_choch(detect_order_block(detect_fvg(df_main)))
    df_small = detect_bos_choch(df_small)
    
    signal, entry_price = evaluate_signal(df_main, df_small)

    if signal != 'none':
        symbol_info = connector.get_symbol_info()
        if symbol_info is None:
            print("Không thể lấy thông tin symbol để tính SL/TP.")
            return
        
        sl, tp = calculate_sl_tp(entry_price, signal, symbol_info.point)
        
        # Tính toán khối lượng động
        quantity = calculate_position_size(connector, STOP_LOSS_POINTS)
        
        if quantity is not None and quantity > 0:
            print(f"Tín hiệu {signal.upper()}: Giá={entry_price}, SL={sl}, TP={tp}, Khối lượng={quantity}")
            connector.place_order(signal, quantity, sl_price=sl, tp_price=tp)
        else:
            print("Không thể xác định khối lượng giao dịch. Hủy lệnh.")
    else:
        print("Không có tín hiệu giao dịch rõ ràng.")

