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

---

## Giai đoạn 8: Xây dựng và Tinh chỉnh Module Backtesting

- **Mục tiêu:** Xây dựng một module backtesting mạnh mẽ để mô phỏng và đánh giá hiệu quả của chiến lược giao dịch trên dữ liệu lịch sử, cho phép tối ưu hóa mà không cần rủi ro vốn thật.

- **Thực thi:**
    1.  **Tích hợp Giao diện Người dùng (UI):**
        -   Thêm tab "Backtesting" mới vào `app/main_window.py`.
        -   Tạo các ô nhập liệu cho Cặp giao dịch (Symbol), Khung thời gian (Timeframe), và Khoảng thời gian (Ngày bắt đầu/kết thúc).
        -   Thêm thanh tiến trình (progress bar) và bảng kết quả để hiển thị trực quan quá trình và kết quả backtest.
    2.  **Xây dựng Engine Backtest:**
        -   Tạo `trading_core/backtester.py` làm lõi xử lý của module.
        -   Engine này tìm nạp dữ liệu lịch sử từ `MT5Connector`, lặp qua từng cây nến, thực thi logic từ `strategy.py`, và theo dõi các chỉ số hiệu suất chính (Lợi nhuận/Thua lỗ, Tỷ lệ thắng, Mức sụt giảm tối đa).
    3.  **Xử lý Đồng thời (Concurrency):**
        -   Sử dụng `BacktestWorker` và `BacktestSignals` (`app/worker.py`, `app/signals.py`) để chạy toàn bộ quá trình mô phỏng trong một luồng nền (background thread).
        -   Cách tiếp cận này đảm bảo giao diện người dùng không bị "đơ" hoặc không phản hồi trong suốt quá trình backtest, ngay cả với lượng dữ liệu lớn.
    4.  **Gỡ lỗi và Tinh chỉnh Logic:**
        -   **Sửa lỗi `KeyError`:** Khắc phục các sự cố treo ứng dụng trong `market_structure.py` và `pd_arrays.py` bằng cách chuyển từ truy cập dựa trên nhãn (`.loc`) sang truy cập dựa trên chỉ số nguyên (`.iloc`) cho các phép tính nội bộ, giúp tăng tính ổn định.
        -   **Tinh chỉnh Chiến lược (`strategy.py`):** Thêm các bản ghi `[EVAL]` chi tiết để theo dõi quá trình ra quyết định của bot một cách minh bạch.
        -   **Xác thực Tín hiệu:** Bổ sung logic quan trọng để xác thực và loại bỏ các "chiến thắng giả" — các tín hiệu mà tại thời điểm tạo ra, giá vào lệnh đã vượt qua mức cắt lỗ, đảm bảo kết quả backtest trung thực và đáng tin cậy.

- **Kết quả:**
    -   Module backtesting đã hoạt động đầy đủ và cung cấp kết quả chính xác, trung thực.
    -   Một bài kiểm tra gần đây cho thấy Lợi nhuận/Thua lỗ âm (Profit Factor ~0.65), điều này xác nhận rằng **engine mô phỏng hoạt động chính xác**, nhưng **các tham số của chiến lược giao dịch cần được tối ưu hóa**.
    -   Dự án hiện có một công cụ mạnh mẽ để lặp lại và cải thiện logic giao dịch một cách có hệ thống.

---

## Giai đoạn 9: Thêm Bộ lọc Premium/Discount và Cơ chế Cooldown

- **Mục tiêu:** Nâng cao chất lượng tín hiệu và quản lý rủi ro bằng cách thêm hai bộ lọc ICT quan trọng: chỉ giao dịch ở vùng giá thuận lợi và tránh giao dịch liên tục sau khi có kết quả.

- **Thực thi:**
    1.  **Nghiên cứu & Phân tích:**
        -   Phân tích lại trang `innercircletrader.net` và xác định `Premium/Discount` là thiếu sót cơ bản trong logic hiện tại.
        -   Phân tích kết quả backtest và phát hiện vấn đề "spam lệnh" khi giá dao động quanh một vùng SL.
    2.  **Tích hợp Premium/Discount:**
        -   Tạo các hàm `get_dealing_range` và `is_in_premium_or_discount` trong `market_structure.py` để xác định phạm vi giao dịch và vùng giá hiện tại.
        -   Cập nhật `evaluate_signal` trong `strategy.py` để chỉ chấp nhận lệnh MUA trong vùng Discount và lệnh BÁN trong vùng Premium.
    3.  **Tích hợp Cooldown (Thời gian hạ nhiệt):**
        -   Thêm logic vào `backtester.py` để tạm dừng tìm kiếm tín hiệu trong 30 phút sau khi một lệnh được đóng, giúp ngăn chặn việc vào lệnh liên tiếp thất bại.
        -   Đồng bộ hóa logic tương tự vào `app/worker.py` (luồng chạy thực tế) để đảm bảo tính nhất quán giữa backtest và live trading.
    4.  **Kiểm tra và Xác thực:**
        -   Tạo script `run_backtest_cli.py` để thực hiện backtest nhanh từ dòng lệnh.
        -   Chạy lại backtest và xác nhận rằng bộ lọc Premium/Discount đã giảm đáng kể số lượng tín hiệu nhiễu, và cơ chế Cooldown đã ngăn chặn hiệu quả việc "spam" lệnh.

- **Kết quả:**
    -   Bot hiện tại tuân thủ chặt chẽ hơn các quy tắc cốt lõi của ICT.
    -   Cả backtest và live trading đều được trang bị các biện pháp quản lý rủi ro nâng cao, giúp bot hoạt động an toàn và có chọn lọc hơn.
    -   Mặc dù kết quả backtest vẫn âm, nền tảng logic đã được củng cố vững chắc, sẵn sàng cho các bước tối ưu hóa tiếp theo về chất lượng tín hiệu.
