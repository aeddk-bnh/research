from datetime import datetime
import pytz
from .config_loader import KILL_ZONES

def get_kill_zone_status(timestamp=None):
    """
    Kiểm tra trạng thái Kill Zone và trả về chuỗi mô tả.
    Trả về: (bool, str) -> (có trong KZ không, chuỗi trạng thái)
    """
    try:
        if timestamp:
            if timestamp.tzinfo is None:
                utc_now = pytz.utc.localize(timestamp)
            else:
                utc_now = timestamp.astimezone(pytz.utc)
        else:
            utc_now = datetime.now(pytz.utc)
            
        ny_tz = pytz.timezone('America/New_York')
        ny_now = utc_now.astimezone(ny_tz)
        current_time_tuple = (ny_now.hour, ny_now.minute)

        kill_zones = KILL_ZONES
        if kill_zones is None:
            kill_zones = []

        for zone in kill_zones:
            if not zone.get('enabled', True):
                continue
            
            start_hour, start_min = zone['start']
            end_hour, end_min = zone['end']
            start_time = (start_hour, start_min)
            end_time = (end_hour, end_min)

            if start_time <= current_time_tuple < end_time:
                zone_name = zone.get('name', 'Unknown')
                status_string = f"{zone_name} ({start_hour}:{start_min:02d} - {end_hour}:{end_min:02d} EST)"
                return True, status_string
    
    except Exception as e:
        return False, f"Lỗi: {e}"

    return False, "Ngoài giờ Kill Zone"

def is_kill_zone_time(timestamp=None, signals=None):
    """
    Chỉ kiểm tra xem có đang trong Kill Zone không.
    Hàm này được dùng cho logic chính của bot.
    """
    is_in_kz, status_str = get_kill_zone_status(timestamp=timestamp)
    # Ghi log trạng thái hiện tại nếu cần
    if signals and timestamp is None: # Chỉ log cho live trading để tránh spam
        # Logic log sẽ được xử lý ở nơi khác
        pass 
        
    return is_in_kz

if __name__ == "__main__":
    # Test
    # Cần cài đặt pytz: pip install pytz
    if is_kill_zone_time():
        ny_time = datetime.now(pytz.timezone('America/New_York')).strftime('%H:%M:%S')
        print(f"Thời gian hiện tại ở New York là {ny_time}. Đang trong Kill Zone.")
    else:
        ny_time = datetime.now(pytz.timezone('America/New_York')).strftime('%H:%M:%S')
        print(f"Thời gian hiện tại ở New York là {ny_time}. KHÔNG trong Kill Zone.")
