# Bot Giao Dịch ICT (Inner Circle Trader)

Bot giao dịch tự động này được xây dựng để thực hiện các chiến lược giao dịch dựa trên phương pháp của Inner Circle Trader (ICT). Bot hỗ trợ cả hai nền tảng: Binance (qua API) và Exness (qua MetaTrader 5).

## Tính năng

*   **Hỗ trợ đa nền tảng:** Có thể giao dịch trên Binance và MetaTrader 5 (Exness).
*   **Tuân thủ ICT:** Tự động phát hiện các tín hiệu dựa trên Cấu trúc Thị trường (Market Structure), PD Arrays (FVG, OB), và Kill Zones.
*   **Quản lý rủi ro:** Tự động tính toán khối lượng giao dịch dựa trên phần trăm rủi ro tài khoản.
*   **Linh hoạt:** Cấu hình dễ dàng thông qua tệp `config.py`.

## Cài đặt

1.  **Clone hoặc tải về dự án:**
    ```bash
    git clone <URL_CỦA_REPO_NÀY>
    cd <Tên_Thư_Mục_Dự_Án> # Ví dụ: cd research
    ```

2.  **Tạo môi trường ảo (khuyến khích):**
    ```bash
    python -m venv ict_bot_env
    ```
    *   **Windows:**
        ```bash
        ict_bot_env\Scripts\activate
        ```
    *   **macOS/Linux:**
        ```bash
        source ict_bot_env/bin/activate
        ```

3.  **Cài đặt thư viện:**
    ```bash
    pip install ccxt pandas numpy pytz MetaTrader5
    ```

## Cấu hình

1.  Mở tệp `ICT_Bot/config.py`.
2.  Đặt `PLATFORM` thành `'binance'` hoặc `'mt5'`.
3.  **Nếu sử dụng Binance:**
    *   Điền `BINANCE_API_KEY` và `BINANCE_SECRET_KEY` của bạn.
    *   Điều chỉnh `BINANCE_SYMBOL` nếu cần.
4.  **Nếu sử dụng Exness/MT5:**
    *   Điền `MT5_LOGIN`, `MT5_PASSWORD`, và `MT5_SERVER` chính xác.
    *   Cập nhật `MT5_PATH` nếu đường dẫn đến MT5 của bạn khác.
    *   Đảm bảo Terminal MT5 đang chạy, bạn đã đăng nhập bằng tài khoản trên, và đã bật "Allow algorithmic trading" trong `Tools -> Options -> Expert Advisors`.
    *   Đảm bảo nút "Algo Trading" trên thanh công cụ của MT5 được bật (màu xanh lá).
    *   Điều chỉnh `MT5_SYMBOL` nếu cần (có thể dùng script `check_symbols.py` để xác định tên chính xác).

## Cách chạy

1.  Đảm bảo bạn đã kích hoạt môi trường ảo (nếu có).
2.  Đảm bảo Terminal MT5 đang chạy (nếu sử dụng MT5).
3.  Từ thư mục gốc của dự án, chạy lệnh:
    ```bash
    python ICT_Bot/main.py
    ```
    Bot sẽ bắt đầu hoạt động theo cấu hình đã đặt.

## Cấu trúc Dự án

```
research/
├── ICT_Bot/
│   ├── config.py           # Cấu hình chính
│   ├── main.py             # Vòng lặp chính của bot
│   ├── strategy.py         # Logic giao dịch chính
│   ├── market_structure.py # Phát hiện xu hướng, BOS, CHOCH
│   ├── pd_arrays.py        # Phát hiện FVG, OB, BB
│   ├── time_filter.py      # Kiểm tra Kill Zones
│   └── connectors/         # Module kết nối nền tảng
│       ├── __init__.py
│       ├── base_connector.py
│       ├── binance_connector.py
│       └── mt5_connector.py
├── ICT_Trading_Method_Summary.md  # Tài liệu tổng hợp ICT
├── README.md              # Tệp hướng dẫn này
└── context.md             # Bối cảnh dự án
```

## Lưu ý Quan Trọng

*   **Giao dịch Rủi ro Cao:** Sử dụng bot giao dịch mang lại rủi ro mất vốn. Chỉ sử dụng với số tiền bạn sẵn sàng mất và hiểu rõ rủi ro.
*   **Kiểm thử trên Tài khoản Demo:** Trước khi sử dụng với tiền thật, hãy kiểm tra kỹ lưỡng bot trên tài khoản demo.
*   **MT5 và Quyền truy cập IPC:** Kết nối Python với MT5 có thể yêu cầu Terminal MT5 chạy với quyền Administrator.
*   **Tính chính xác của các hàm phát hiện:** Các hàm phát hiện BOS, CHOCH, FVG, OB trong mã nguồn hiện là phiên bản đơn giản hóa. Hiệu suất thực tế có thể khác so với phương pháp ICT đầy đủ.