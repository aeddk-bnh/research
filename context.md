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
- **Kết quả:** Ứng dụng desktop có UI đã được tạo, cho phép người dùng dễ dàng quản lý và giám sát bot giao dịch ICT.

---

## Giai đoạn 7: Tinh chỉnh Toàn diện Logic Giao dịch ICT

- **Mục tiêu:** Nâng cấp toàn diện logic giao dịch cốt lõi để tuân thủ chặt chẽ hơn với các quy tắc của phương pháp ICT, nhằm tăng chất lượng tín hiệu.
- **Thực thi (một chuỗi các cải tiến liên tiếp):**
    1.  **Đánh giá lại Toàn bộ Dự án:** Phân tích lại cấu trúc ứng dụng desktop mới để hiểu rõ luồng hoạt động.
    2.  **Nâng cấp #1: Phát hiện Order Block (OB):**
        -   Tạo hàm `detect_liquidity_sweep` trong `market_structure.py` để xác định một cây nến có quét thanh khoản của một đỉnh/đáy trước đó hay không.
        -   Cập nhật `detect_order_block` trong `pd_arrays.py` để chỉ công nhận một OB nếu nó **quét thanh khoản** VÀ **gây ra phá vỡ cấu trúc (BOS)**.
    3.  **Nâng cấp #2: Phát hiện Cấu trúc Thị trường (BOS/CHOCH):**
        -   Thiết kế lại hoàn toàn hàm `detect_bos_choch` trong `market_structure.py`.
        -   Logic mới theo dõi trạng thái xu hướng (tăng/giảm) và áp dụng định nghĩa chính xác của CHOCH (phá vỡ đáy cũ trong xu hướng tăng, hoặc phá vỡ đỉnh cũ trong xu hướng giảm).
    4.  **Nâng cấp #3: Tích hợp Breaker Block (BB):**
        -   Kích hoạt hàm `detect_breaker_block` trong pipeline phân tích của `strategy.py`.
        -   Thêm logic vào `evaluate_signal` để tìm kiếm và giao dịch theo tín hiệu từ cả Bullish và Bearish Breaker Block.
    5.  **Nâng cấp #4: Tinh chỉnh Logic Vào lệnh:**
        -   Cải thiện `evaluate_signal` để yêu cầu tín hiệu xác nhận (CHOCH trên khung thời gian thấp) phải xuất hiện **gần đây** (trong vòng 5 nến cuối) sau khi giá đã đi vào vùng PD Array, thay vì chỉ kiểm tra sự tồn tại của nó.
    6.  **Nâng cấp #5: Quản lý Rủi ro Động:**
        -   Loại bỏ hệ thống Stop Loss/Take Profit dựa trên số điểm cố định.
        -   Sửa đổi `evaluate_signal` để trả về **giá Stop Loss dựa trên cấu trúc** (ví dụ: đáy của Bullish OB).
        -   Sửa đổi `calculate_position_size` để tính toán khối lượng dựa trên khoảng cách (bằng đô la) tới mức SL động.
        -   Tính toán `tp_price` dựa trên một **tỷ lệ Rủi ro:Lợi nhuận (RR)** có thể cấu hình.
    7.  **Gỡ lỗi và Chạy:**
        -   Cài đặt thư viện `PySide6` còn thiếu.
        -   Gỡ lỗi `ImportError` do quên thêm `TAKE_PROFIT_RR` vào `config_loader.py`.
        -   Khắc phục các sự cố đường dẫn khi chạy ứng dụng trên Windows.
- **Kết quả:** Logic giao dịch của bot đã được tinh chỉnh sâu sắc, приблизительно tuân thủ các nguyên tắc cốt lõi của ICT. Bot hiện là một ứng dụng desktop hoàn chỉnh, sẵn sàng để kiểm tra và giám sát.
