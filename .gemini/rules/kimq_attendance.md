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

## 5. Quy chuẩn Báo cáo Excel
* **Phân quyền xuất file:** Nút **"Xuất Excel"** chỉ hiển thị và hoạt động khi đăng nhập bằng tài khoản quản trị (Admin / CEO). Ẩn hoàn toàn nút này ở phiên bản xem chung của công chúng.
* **Cột Thứ:** Thêm cột "Thứ" ngay sau cột "Ngày" (Định dạng: `Thứ Hai`, `Thứ Ba`...).
* **Bao gồm ngày cuối tuần:** Báo cáo Excel phải hiển thị toàn bộ các ngày trong khoảng tìm kiếm. 
  * Nếu là thứ 7 hoặc chủ nhật không có quẹt thẻ: Ghi chú là `Ngày nghỉ`.
  * Nếu là ngày thường không quẹt thẻ: Ghi chú là `Vắng mặt`.
* **Sắp xếp:** Sắp xếp theo tên nhân sự, sau đó tăng dần theo trình tự thời gian (chronological).
