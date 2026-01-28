# Cẩm Nang Toàn Diện Phương Pháp Giao Dịch ICT (Inner Circle Trader)
*Tài liệu chi tiết dựa trên nghiên cứu từ trang web `innercircletrader.net`*

---

## Phần 1: Nền Tảng Triết Lý

### 1. Giới thiệu về ICT
- **Người sáng lập:** Michael J. Huddleston.
- **Triết lý cốt lõi:** Thị trường không di chuyển ngẫu nhiên mà được điều khiển bởi một thuật toán gọi là **Inter-Bank Price Delivery Algorithm (IPDA)**, hay "Smart Money". Mục tiêu của IPDA là tìm kiếm và tận dụng **thanh khoản (Liquidity)**, thường là ở các đỉnh và đáy cũ.

### 2. Thuật Ngữ (Glossary) - Điều Kiện Tiên Quyết
Việc học thuộc các thuật ngữ và từ viết tắt là **bắt buộc**. Đây là ngôn ngữ của phương pháp ICT.
- **BOS:** Break of Structure (Phá vỡ cấu trúc để tiếp diễn xu hướng).
- **CHOCH:** Change of Character (Thay đổi tính chất, tín hiệu đảo chiều xu hướng).
- **FVG:** Fair Value Gap (Khoảng trống giá trị hợp lý).
- **OB:** Order Block (Khối lệnh).
- **BB:** Breaker Block (Khối phá vỡ).
- **PD Array:** Premium/Discount Array (Các vùng giá quan trọng).
- **Premium:** Vùng giá đắt (trên 50%), dùng để tìm cơ hội Bán.
- **Discount:** Vùng giá rẻ (dưới 50%), dùng để tìm cơ hội Mua.
- **Liquidity:** Thanh khoản (thường là các vùng đỉnh/đáy cũ, nơi các lệnh dừng lỗ tập trung).

---

## Phần 2: Phân Tích Cấu Trúc Thị Trường - "Xương Sống" Của Hệ Thống

Mục tiêu của phần này là xác định **xu hướng chính (Daily Bias)** để biết nên tập trung vào Mua hay Bán.

- **Xu hướng tăng (Bullish):** Giá liên tục tạo các đỉnh cao hơn (Higher Highs) và đáy cao hơn (Higher Lows).
    - **Tín hiệu tiếp diễn:** Giá tạo một **Break of Structure (BOS)** bằng cách phá vỡ đỉnh cũ.
- **Xu hướng giảm (Bearish):** Giá liên tục tạo các đỉnh thấp hơn (Lower Highs) và đáy thấp hơn (Lower Lows).
    - **Tín hiệu tiếp diễn:** Giá tạo một **BOS** bằng cách phá vỡ đáy cũ.
- **Tín hiệu đảo chiều (Reversal):**
    - Trong xu hướng tăng, giá thất bại trong việc tạo đỉnh cao hơn và thay vào đó phá vỡ đáy gần nhất. Đây là một **Change of Character (CHOCH)**, báo hiệu khả năng đảo chiều từ tăng sang giảm.
    - Trong xu hướng giảm, giá thất bại trong việc tạo đáy thấp hơn và thay vào đó phá vỡ đỉnh gần nhất. Đây cũng là một **CHOCH**, báo hiệu khả năng đảo chiều từ giảm sang tăng.

---

## Phần 3: Các Công Cụ Xác Định Vùng Giao Dịch (PD Arrays)

Sau khi biết xu hướng, chúng ta cần xác định **NƠI** để vào lệnh. Các PD Arrays là những vùng có xác suất phản ứng giá cao.

### 1. Fair Value Gap (FVG) - Vùng Mất Cân Bằng
- **Định nghĩa chi tiết:** Là một mô hình 3 nến, nơi có một "khoảng trống" giữa **đỉnh của nến thứ nhất** và **đáy của nến thứ ba**. Vùng trống này chính là FVG.
- **Tâm lý:** Giá di chuyển quá nhanh, để lại một vùng mất cân bằng chưa được khớp lệnh hiệu quả. Giá có xu hướng quay lại để "tái cân bằng" (rebalance) vùng này.
- **Cách giao dịch:**
    1.  Xác định xu hướng chính (ví dụ: Tăng).
    2.  Chờ giá tạo ra một FVG trong một con sóng đẩy.
    3.  Chờ giá hồi về (retrace) và *test* vào vùng FVG này.
    4.  Vùng FVG này hoạt động như một vùng hỗ trợ (trong xu hướng tăng) hoặc kháng cự (trong xu hướng giảm).
    5.  Vào lệnh khi giá có phản ứng tại FVG (ví dụ: nến rút chân, hoặc có CHOCH ở khung thời gian nhỏ hơn).
    6.  **Stop Loss:** Đặt ngay bên dưới FVG (cho lệnh Mua).

### 2. Order Block (OB) - Dấu Chân Của Smart Money
- **Định nghĩa chi tiết:**
    - **Bullish OB:** Là **nến giảm cuối cùng** trước một đợt tăng giá mạnh mẽ gây ra sự phá vỡ cấu trúc (BOS).
    - **Bearish OB:** Là **nến tăng cuối cùng** trước một đợt giảm giá mạnh mẽ gây ra sự phá vỡ cấu trúc (BOS).
- **Điều kiện để một OB hợp lệ:**
    1.  Phải gây ra một sự phá vỡ cấu trúc (BOS).
    2.  Thường tạo ra sự mất cân bằng (FVG) ngay sau đó.
    3.  Phải "quét thanh khoản" (sweep liquidity) của một đỉnh/đáy trước đó.
- **Cách giao dịch:**
    1.  Xác định một OB hợp lệ theo xu hướng chính.
    2.  Chờ giá hồi về *test* lại vùng OB này.
    3.  Đây là vùng có xác suất vào lệnh rất cao.
    4.  **Stop Loss:** Đặt ngay bên dưới toàn bộ cây nến OB (cho lệnh Mua).

### 3. Breaker Block (BB) - Vùng "Bẫy" Bị Phá Vỡ
- **Định nghĩa chi tiết:** Một **Order Block thất bại**. Khi giá phá vỡ một OB và đóng cửa vượt qua nó, OB đó sẽ đảo ngược vai trò và trở thành một Breaker Block.
- **So sánh OB và BB:**
    - **Order Block:** Là một vùng hỗ trợ/kháng cự được *tôn trọng*. Giá chạm vào và đảo chiều.
    - **Breaker Block:** Là một vùng hỗ trợ/kháng cự bị *phá vỡ*. Khi giá quay lại test, nó có xu hướng đi theo hướng phá vỡ.
- **Cách giao dịch (ví dụ với Bearish BB):**
    1.  Xác định một Bullish Order Block (vùng hỗ trợ).
    2.  Giá phá xuống dưới và **đóng cửa** bên dưới Bullish OB này. Bullish OB này giờ đã trở thành một **Bearish Breaker Block**.
    3.  Chờ giá hồi lên và *test* lại vùng Bearish BB này.
    4.  Vào lệnh Bán tại đây.
    5.  **Stop Loss:** Đặt ngay trên vùng Breaker Block.

---

## Phần 4: Yếu Tố Thời Gian - Kill Zones (KZ)

Giao dịch đúng **VÙNG** là chưa đủ, cần phải đúng **THỜI ĐIỂM**.
**(Luôn đặt múi giờ biểu đồ theo giờ New York: America/New_York)**

- **Asian Kill Zone (7:00 PM – 10:00 PM EST):** Giai đoạn tích lũy, tạo ra các đỉnh/đáy (thanh khoản) cho phiên sau.
- **London Kill Zone (1:00 AM – 5:00 AM EST):** **Quan trọng nhất.** Thường bắt đầu bằng một cú **Judas Swing** để quét thanh khoản phiên Á, sau đó hình thành xu hướng chính trong ngày. Đỉnh/đáy của ngày thường được tạo ra ở đây.
- **New York Kill Zone (7:00 AM – 10:00 AM EST):** Tiếp tục xu hướng từ phiên London hoặc tạo ra một cú đảo chiều nhỏ. Biến động cao.
- **London Close Kill Zone (10:00 AM – 12:00 PM EST):** Thường có sự hồi giá nhỏ, phù hợp cho các lệnh scalp ngắn.

---

## Phần 5: Tổng Hợp - Một Mô Hình Giao Dịch Mua Hoàn Chỉnh

1.  **Bối cảnh (WHY):**
    -   Trên khung H4/H1, xác định Cấu trúc Thị trường đang trong xu hướng **tăng** (giá tạo BOS lên trên).

2.  **Thời điểm (WHEN):**
    -   Chờ đến phiên **London** hoặc **New York Kill Zone**.

3.  **Vị trí (WHERE):**
    -   Chờ giá hồi về một vùng **Discount** (dưới mức 50% của con sóng tăng gần nhất).
    -   Trong vùng Discount đó, tìm một **PD Array** rõ ràng và mạnh mẽ (ví dụ: một Order Block chưa được test hoặc một Fair Value Gap lớn).

4.  **Tín hiệu vào lệnh (HOW):**
    -   Chờ giá chạm vào PD Array đã chọn.
    -   Trên khung thời gian nhỏ hơn (M15/M5), chờ một tín hiệu xác nhận: giá tạo một **CHOCH nhỏ** (từ giảm sang tăng).
    -   Vào lệnh **Mua** sau khi có tín hiệu xác nhận này.

5.  **Quản lý rủi ro:**
    -   **Stop Loss:** Đặt bên dưới đáy của tín hiệu CHOCH nhỏ, hoặc bên dưới PD Array.
    -   **Take Profit:** Đặt mục tiêu tại các vùng thanh khoản ở phía trên (ví dụ: các đỉnh cũ mà bạn dự đoán giá sẽ tìm đến).
