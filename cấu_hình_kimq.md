# Quy tắc và Bối cảnh Dự án KimQ Attendance

Dự án này là hệ thống Web Tra cứu và Bổ sung công quẹt thẻ Hanet dành cho công ty KimQ. Khi làm việc với dự án này, luôn tuân thủ các hướng dẫn cấu hình và thiết kế sau:

## 1. Cơ sở dữ liệu & Cấu hình Cloud (Railway)
* **Hệ cơ sở dữ liệu:** PostgreSQL (Đã kết nối thành công và lưu trữ vĩnh viễn).
* **Biến môi trường trên Railway:** Luôn cấu hình `DATABASE_URL` trỏ tới `${{Postgres.DATABASE_URL}}` (Không sử dụng `PRIVATE_URL` vì sẽ bị rỗng và hệ thống sẽ tự động chạy lùi về SQLite làm mất dữ liệu khi deploy lại).

## 2. Truy cập công khai (Public Access)
* **Không yêu cầu đăng nhập nhân viên:** Toàn bộ lịch sử chấm công được mở công khai cho tất cả mọi người. Bất kỳ ai truy cập vào trang web đều có thể xem danh sách quẹt thẻ và sử dụng thanh tìm kiếm để tra cứu mà không cần đăng nhập.
* **Đăng nhập Admin/CEO:** Vẫn giữ nguyên chức năng đăng nhập Admin/CEO để quản trị hệ thống (cấp mã PIN, theo dõi nhân sự).

## 3. Tính năng Yêu cầu Bổ sung (Tạm ẩn)
* **Trạng thái:** Tạm thời ẩn khỏi giao diện (không hiển thị trên app), nhưng mã nguồn xử lý vẫn được giữ lại nguyên vẹn trong code.
* **Cách ẩn:** Các bảng điều khiển `#employee-requests-panel` và `#admin-requests-panel` được ẩn đi bằng CSS/JS trong `updateUIForLoginState()`.

## 4. Giao diện Chọn ngày & Thư viện Flatpickr
* **Không dùng altInput:** Tránh dùng thuộc tính `altInput: true` trong cấu hình Flatpickr vì sẽ tạo ra ô nhập phụ gây đè lớp (overlap) hoặc mất ô nhập trên một số trình duyệt.
* **Chọn khoảng ngày (Range):** Thiết kế thân thiện là chia thành 2 ô nhập độc lập:
  * Ô 1: `Ngày cần bổ sung` (hoặc `Từ ngày` khi chọn Nghỉ phép/WFH).
  * Ô 2: `Đến ngày` (chỉ hiển thị khi chọn Nghỉ phép/WFH).

## 5. Quy chuẩn Báo cáo Excel (Chế độ Admin)
* **Phân quyền xuất file:** Nút **"Xuất Excel"** chỉ hiển thị và hoạt động khi đăng nhập bằng tài khoản quản trị (Admin / CEO). Ẩn hoàn toàn nút này ở phiên bản xem chung của công chúng.
* **Cột Thứ:** Thêm cột "Thứ" ngay sau cột "Ngày" (Định dạng: `Thứ Hai`, `Thứ Ba`...).
* **Bao gồm ngày cuối tuần:** Báo cáo Excel phải hiển thị toàn bộ các ngày trong khoảng tìm kiếm. 
  * Nếu là thứ 7 hoặc chủ nhật không có quẹt thẻ: Ghi chú là `Ngày nghỉ`.
  * Nếu là ngày thường không quẹt thẻ: Ghi chú là `Vắng mặt`.
* **Sắp xếp:** Sắp xếp theo tên nhân sự, sau đó tăng dần theo trình tự thời gian (chronological).
* **Lược bỏ cột:** Xóa bớt 3 cột khỏi file Excel gồm: **"Loại ngày nghỉ"**, **"Loại bổ sung công"**, **"Người duyệt"** để báo cáo gọn gàng.
* **Thêm cột quản lý vi phạm:** Bổ sung 2 cột **"Lần vi phạm trong tháng"** và **"Hình thức xử lý vi phạm"** để tự động kết xuất thống kê nhắc nhở/phạt tiền của nhân sự theo tháng.

## 6. Quy định đi trễ & Cảnh báo phê duyệt Lark
* **Thời gian bắt đầu đi trễ:** Sau 9h15 mới tính là đi trễ (tức là từ 09:15:01 trở đi).
* **Công thức tính thời gian trễ:** Thời gian trễ (phút) = Giờ vào (phút) - 9h15 (555 phút).
* **Điều kiện Cảnh báo phê duyệt Lark (Quá 30 phút):**
  * Nếu giờ quét vào muộn hơn **9h30** (sau 9:30 AM).
  * Hoặc nếu giờ quét ra sớm hơn **17h30** (trước 5:30 PM).
  * ➔ Hệ thống hiển thị nhãn cảnh báo đỏ: **"Trễ so với quy định, phải xin phê duyệt qua Lark"**.

## 7. Quy chế phạt đi trễ / về sớm trong tháng
* **Hạn mức miễn phạt:** Mỗi nhân sự được miễn phạt **3 lần đầu tiên** đi trễ hoặc về sớm cộng dồn trong 1 tháng dương lịch (Ví dụ: đi trễ 2 lần + về sớm 1 lần = 3 lần vi phạm).
* **Mức phạt áp dụng:**
  * Vi phạm lần thứ 4: **Cảnh báo nhắc nhở** (Nhãn: *Cảnh báo nhắc nhở (Lần 4)*).
  * Vi phạm lần thứ 5: **Thu phạt 50.000đ** (Nhãn: *Phạt 50k (Lần 5)*).
  * Vi phạm từ lần thứ 6 trở đi: **Thu phạt 150.000đ mỗi lần** (Nhãn: *Phạt 150k (Lần X)*).
* **Tự động hóa:** Hệ thống tự động tính thứ tự vi phạm theo thời gian tăng dần trong tháng của từng nhân viên và hiển thị trực quan lên cả thẻ chấm công (web) lẫn báo cáo Excel.
