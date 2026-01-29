from datetime import datetime, timedelta
import pytz
from .config_loader import KILL_ZONES

# Múi giờ
NY_TZ = pytz.timezone('America/New_York')
UTC_PLUS_7 = pytz.timezone('Asia/Bangkok')  # UTC+7 (Vietnam, Thailand, etc.)

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
            
        ny_now = utc_now.astimezone(NY_TZ)
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


def get_all_kill_zones_with_utc7():
    """
    Trả về danh sách tất cả Kill Zones với thời gian đã chuyển đổi sang UTC+7.
    Returns: list of dict với format:
        {
            'name': str,
            'est_start': str (HH:MM),
            'est_end': str (HH:MM),
            'utc7_start': str (HH:MM),
            'utc7_end': str (HH:MM),
            'enabled': bool
        }
    """
    result = []
    kill_zones = KILL_ZONES if KILL_ZONES else []
    
    # Tạo một ngày tham chiếu để convert timezone
    # Dùng ngày hôm nay ở NY để tính đúng DST
    today_ny = datetime.now(NY_TZ).date()
    
    for zone in kill_zones:
        start_hour, start_min = zone['start']
        end_hour, end_min = zone['end']
        
        # Tạo datetime objects ở múi giờ NY
        start_ny = NY_TZ.localize(datetime(today_ny.year, today_ny.month, today_ny.day, start_hour, start_min))
        end_ny = NY_TZ.localize(datetime(today_ny.year, today_ny.month, today_ny.day, end_hour, end_min))
        
        # Convert sang UTC+7
        start_utc7 = start_ny.astimezone(UTC_PLUS_7)
        end_utc7 = end_ny.astimezone(UTC_PLUS_7)
        
        result.append({
            'name': zone.get('name', 'Unknown'),
            'est_start': f"{start_hour:02d}:{start_min:02d}",
            'est_end': f"{end_hour:02d}:{end_min:02d}",
            'utc7_start': start_utc7.strftime('%H:%M'),
            'utc7_end': end_utc7.strftime('%H:%M'),
            'utc7_start_next_day': start_utc7.date() > today_ny,
            'utc7_end_next_day': end_utc7.date() > today_ny,
            'enabled': zone.get('enabled', True)
        })
    
    return result

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
