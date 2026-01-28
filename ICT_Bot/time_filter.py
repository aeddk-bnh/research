from datetime import datetime
import pytz
from config import KILL_ZONES

def is_kill_zone_time():
    """
    Kiểm tra xem thời gian hiện tại (theo múi giờ New York) có nằm trong bất kỳ Kill Zone nào không.
    """
    try:
        # Lấy thời gian hiện tại theo UTC
        utc_now = datetime.now(pytz.utc)
        # Chuyển đổi sang múi giờ New York
        ny_tz = pytz.timezone('America/New_York')
        ny_now = utc_now.astimezone(ny_tz)

        current_hour = ny_now.hour
        current_minute = ny_now.minute
        current_time_tuple = (current_hour, current_minute)

        for zone in KILL_ZONES:
            start_hour, start_min = zone['start']
            end_hour, end_min = zone['end']

            start_time = (start_hour, start_min)
            end_time = (end_hour, end_min)

            if start_time <= current_time_tuple < end_time:
                return True
    except Exception as e:
        print(f"Lỗi khi kiểm tra múi giờ: {e}")
        # Cài đặt pytz nếu chưa có
        import os
        os.system("pip install pytz")
        return False


    return False

if __name__ == "__main__":
    # Test
    # Cần cài đặt pytz: pip install pytz
    if is_kill_zone_time():
        ny_time = datetime.now(pytz.timezone('America/New_York')).strftime('%H:%M:%S')
        print(f"Thời gian hiện tại ở New York là {ny_time}. Đang trong Kill Zone.")
    else:
        ny_time = datetime.now(pytz.timezone('America/New_York')).strftime('%H:%M:%S')
        print(f"Thời gian hiện tại ở New York là {ny_time}. KHÔNG trong Kill Zone.")
