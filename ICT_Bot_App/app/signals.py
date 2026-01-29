from PySide6.QtCore import QObject, Signal

class WorkerSignals(QObject):
    """
    Định nghĩa các tín hiệu có sẵn từ một luồng worker.
    """
    # Tín hiệu log_message: Gửi một chuỗi (str) làm thông điệp log
    log_message = Signal(str)

    # Tín hiệu bot_status: Gửi một chuỗi (str) để cập nhật trạng thái bot
    bot_status = Signal(str)

    # Tín hiệu market_bias: Gửi một chuỗi (str) để cập nhật xu hướng thị trường
    market_bias = Signal(str)

    # Tín hiệu account_summary: Gửi một dict chứa thông tin tài khoản
    # Ví dụ: {'balance': 10000, 'pnl': 150.75}
    account_summary = Signal(dict)

    # Tín hiệu new_position: Gửi một dict chứa thông tin lệnh mới
    new_position = Signal(dict)

    # Tín hiệu position_closed: Gửi ID của lệnh đã đóng (str hoặc int)
    position_closed = Signal(str, dict) # Gửi ID và thông tin lệnh đã đóng

    # Tín hiệu kill_zone_status: Gửi một chuỗi (str) để cập nhật trạng thái Kill Zone
    kill_zone_status = Signal(str)

class BacktestSignals(QObject):
    """
    Định nghĩa các tín hiệu cho luồng backtesting.
    """
    log_message = Signal(str)      # Gửi thông điệp log từ backtester
    market_bias = Signal(str)      # Tín hiệu market_bias để tương thích với market_structure.py
    progress = Signal(int)         # Gửi % tiến trình (0-100)
    trade_closed = Signal(dict)    # Gửi thông tin của một giao dịch đã đóng
    finished = Signal(dict)        # Gửi kết quả cuối cùng khi hoàn tất
