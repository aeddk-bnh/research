# Bối Cảnh Dự Án: Xây Dựng Bot Giao Dịch Theo Phương Pháp ICT

Tài liệu này tóm tắt toàn bộ quá trình làm việc, từ giai đoạn nghiên cứu ban đầu đến khi triển khai thành công một bot giao dịch tự động.

---

## Giai đoạn 1: Nghiên cứu và Tổng hợp kiến thức

- **Mục tiêu:** Xây dựng một kế hoạch chi tiết để nghiên cứu và hiểu sâu về phương pháp giao dịch ICT (Inner Circle Trader) từ trang web `innercircletrader.net`.
- **Thực thi:**
    1.  Khám phá trang web để hiểu cấu trúc và các nội dung chính.
    2.  Nghiên cứu các khái niệm nền tảng: Tác giả, thuật ngữ, cấu trúc thị trường (Market Structure).
    3.  Phân tích các công cụ cốt lõi: Fair Value Gap (FVG), Order Block (OB), Breaker Block (BB).
    4.  Tìm hiểu về yếu tố thời gian: Kill Zones (KZ).
- **Kết quả:** Tạo thành công tệp `ICT_Trading_Method_Summary.md`, một cẩm nang chi tiết và đầy đủ về phương pháp giao dịch ICT.

---

## Giai đoạn 2: Lên kế hoạch và Xây dựng Bot Giao dịch

- **Mục tiêu:** Chuyển đổi các quy tắc trong tài liệu `ICT_Trading_Method_Summary.md` thành một bot giao dịch tự động.
- **Thực thi:**
    1.  **Lên kế hoạch kiến trúc:** Thiết kế một bot module hóa, bao gồm các thành phần riêng biệt cho việc xử lý dữ liệu, phân tích chiến lược, quản lý lệnh và cấu hình.
    2.  **Xây dựng các module ban đầu:** Tạo các tệp Python cho các chức năng cốt lõi, ban đầu nhắm đến nền tảng Binance.

---

## Giai đoạn 3: Tái cấu trúc hỗ trợ đa nền tảng (Binance & Exness/MT5)

- **Mục tiêu:** Mở rộng khả năng của bot để có thể hoạt động trên cả sàn Binance và nền tảng MetaTrader 5 (cho Exness).
- **Thực thi:**
    1.  **Nghiên cứu kết nối MT5:** Tìm hiểu cách sử dụng thư viện `MetaTrader5` của Python để kết nối, lấy dữ liệu và đặt lệnh.
    2.  **Tái cấu trúc mã nguồn:**
        -   Tạo thư mục `connectors` để chứa logic giao tiếp riêng cho từng nền tảng (`binance_connector.py`, `mt5_connector.py`).
        -   Định nghĩa một `base_connector.py` để đảm bảo tính nhất quán.
        -   Cập nhật `config.py` để cho phép người dùng chọn nền tảng và điền thông tin tương ứng.
        -   Sửa đổi `main.py` và `strategy.py` để làm việc với một "đối tượng connector" chung, giúp mã nguồn trở nên linh hoạt.

---

## Giai đoạn 4: Cài đặt, Chạy thử và Gỡ lỗi với Exness MT5

- **Mục tiêu:** Thiết lập môi trường và chạy bot thành công với tài khoản demo Exness do người dùng cung cấp.
- **Thông tin tài khoản:**
    - **Tài khoản:** `270873003`
    - **Mật khẩu:** `Mgnaermganer1.`
    - **Máy chủ:** `Exness-MT5Trial17`
- **Thực thi và Gỡ lỗi:**
    1.  **Tạo môi trường ảo:** Tạo môi trường `ict_bot_env` để quản lý các gói phụ thuộc.
    2.  **Cài đặt gói:** Cài đặt thành công các thư viện `ccxt`, `pandas`, `numpy`, `pytz`, `MetaTrader5`.
    3.  **Cấu hình:** Cập nhật `config.py` với thông tin tài khoản demo.
    4.  **Chạy thử và Gỡ lỗi (Quá trình lặp lại):**
        -   **Lỗi `Authorization failed`:** Xác định vấn đề nằm ở thông tin đăng nhập hoặc cài đặt MT5. Đã thử nhiều biến thể mật khẩu.
        -   **Lỗi `Invalid params`:** Thử nhiều cách kết nối khác nhau với hàm `mt5.initialize()`.
        -   **Kết nối thành công:** Tìm ra cấu hình `initialize` đúng.
        -   **Lỗi `Call failed`:** Xác định vấn đề nằm ở tên symbol không chính xác. Đã chạy script `check_symbols.py` để tìm ra tên đúng là `BTCUSDm`.
        -   **Cập nhật Symbol:** Sửa `config.py` với `MT5_SYMBOL = 'BTCUSDm'`.
        -   **Lỗi `AutoTrading disabled by client`:** Phát hiện ra nút "Algo Trading" trên Terminal MT5 chưa được bật. Đã hướng dẫn người dùng bật nút này.
- **Kết quả cuối cùng:**
    -   Sau khi người dùng bật "Algo Trading", bot đã chạy thành công.
    -   Bot đã **kết nối, lấy dữ liệu, phân tích, và đặt một lệnh mua (BUY) thành công** trên tài khoản demo với **Order ID: 1224908866**.
    -   Dự án đã đạt được mục tiêu đề ra.

---

## Giai đoạn 5: Đánh giá và Tối ưu hóa Logic Giao dịch

- **Mục tiêu:** Đánh giá mức độ tuân thủ của bot với phương pháp ICT và xác định các điểm cần cải thiện.
- **Thực thi:**
    1.  **Đánh giá mã nguồn:** So sánh logic trong các tệp Python (`market_structure.py`, `pd_arrays.py`, `strategy.py`) với tài liệu `ICT_Trading_Method_Summary.md`.
    2.  **Xác định điểm yếu:**
        -   **Thiếu khái niệm Premium/Discount:** Bot chưa kiểm tra xem tín hiệu có nằm trong vùng giá rẻ/đắt theo xu hướng hay không.
        -   **Logic Order Block (OB) quá đơn giản:** Chưa kiểm tra các điều kiện cốt lõi như "OB gây ra BOS", "OB quét thanh khoản".
        -   **Chưa sử dụng FVG và BB:** Bot chỉ sử dụng OB trong logic giao dịch chính.
        -   **Logic BOS/CHOCH cần cải thiện:** Có thể chưa phản ánh chính xác định nghĩa ICT.
    3.  **Đề xuất cải tiến:**
        -   **(Ưu tiên #1)** Tích hợp xác định vùng Premium/Discount vào `strategy.py`.
        -   **(Ưu tiên #2)** Nâng cấp logic `detect_order_block` để kiểm tra các điều kiện BOS và sweep.
        -   **(Ưu tiên #3)** Cập nhật `evaluate_signal` để sử dụng cả FVG.
        -   **(Tùy chọn)** Thêm logic sử dụng Breaker Block (BB).
- **Kết quả:** Xác định được các điểm chính yếu trong logic giao dịch hiện tại, tạo nền tảng cho các giai đoạn phát triển tiếp theo nhằm nâng cao chất lượng và độ tin cậy của bot.

---

## Giai đoạn 6: Chuyển đổi sang Ứng dụng Desktop với UI

- **Mục tiêu:** Chuyển đổi bot giao dịch dòng lệnh thành một ứng dụng desktop có giao diện người dùng (UI) chuyên nghiệp sử dụng PySide6.
- **Thực thi:**
    1.  **Tái cấu trúc mã nguồn:** Tách biệt logic giao dịch (`trading_core`) khỏi logic giao diện người dùng (`app`).
    2.  **Tách cấu hình:** Chuyển từ `config.py` sang `config.json` và tạo `ConfigManager` để quản lý cấu hình.
    3.  **Tạo luồng nền (Worker Thread):** Di chuyển vòng lặp chính của bot vào một `QThread` riêng biệt (`BotWorker`) để tránh làm "đơ" giao diện.
    4.  **Sử dụng Signals/Slots:** Thiết lập hệ thống giao tiếp giữa `BotWorker` và `MainWindow` thông qua các tín hiệu (`Signal`) và slot để cập nhật UI một cách an toàn từ luồng khác.
    5.  **Xây dựng UI:** Tạo giao diện chính với các tab: Dashboard, Cấu hình, Nhật ký, Giao dịch.
    6.  **Tích hợp chức năng:** Kết nối các nút bấm (Bắt đầu/Dừng Bot, Lưu Cấu hình), cập nhật trạng thái, hiển thị log, và bảng lệnh.
    7.  **Gỡ lỗi và hoàn thiện:**
        -   Cải thiện chức năng "Lưu Cấu hình" để xử lý lỗi người dùng nhập sai.
        -   Cải thiện logic "Bắt đầu/Dừng Bot" để đảm bảo thread được quản lý đúng cách.
        -   Thêm chức năng "Lịch sử giao dịch".
        -   Cập nhật P&L theo thời gian thực.
        -   Ghi log ra file.
        -   Thêm hộp thoại xác nhận khi đóng ứng dụng.
        -   **(Hiện tại)** Sửa lỗi cập nhật trạng thái Kill Zone lên UI. Ban đầu, trạng thái không cập nhật do `QTimer` được khởi tạo trong luồng sai. Đã sửa bằng cách tạo và quản lý `QTimer` hoàn toàn bên trong `BotWorker` (luồng worker).
- **Kết quả:** Ứng dụng desktop có UI đã được tạo, cho phép người dùng dễ dàng quản lý và giám sát bot giao dịch ICT.

