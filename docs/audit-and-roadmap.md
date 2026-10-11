# Rà soát và hướng phát triển

## Đã xác nhận và chỉnh sửa

| Vấn đề | Ảnh hưởng | Xử lý |
|---|---|---|
| Cài đặt cũ không khai báo EasyOCR, VietOCR, QReader | Pipeline có thể trả rỗng hoặc bỏ qua QR do import lỗi | Đưa thư viện OCR/QR vào dependency mặc định và cập nhật `uv.lock` |
| Cài nền thiếu Pillow dù module OCR import từ lúc khởi động | Package lỗi import trong môi trường sạch | Thêm Pillow vào dependency nền |
| YAML VietOCR chứa đường dẫn tuyệt đối tới máy khác | Máy mới không tải được trọng số | Dùng URL trọng số; vẫn ưu tiên file local |
| Wheel thiếu YAML và ghi model vào `site-packages` | Cài wheel không có cấu hình hoặc thiếu quyền ghi cache | Đóng gói YAML và dùng cache ở thư mục người dùng |
| VietOCR kéo theo `gdown` dùng `pkg_resources` | Lỗi import với setuptools mới | Giới hạn `setuptools<81` trong dependency mặc định |
| API upload bytes không phải ảnh | Request phát sinh 500 | Trả HTTP 400; xử lý OCR trong worker thread của FastAPI |
| Test VietOCR giả định thư viện luôn được cài | Bộ test nền cũ đỏ | Giữ điều kiện bỏ qua test khi chạy trong môi trường thiếu thư viện |
| README cũ trỏ ảnh không có trong repo | Người dùng không chạy được ví dụ | Thay ví dụ bằng file hiện có |
| `test_run.py` cũ âm thầm bỏ qua nhiều ảnh không tồn tại | Chạy script nhưng hầu như không kiểm thử gì | Viết lại thành script chọn ảnh và in JSON |

## Rủi ro còn lại, theo ưu tiên

1. **Khả năng quan sát lỗi model:** `OCREngine.recognize` và `QRDecoder.decode` bắt ngoại lệ rộng rồi trả kết quả rỗng. Cần tách trạng thái “không thấy chữ/QR” khỏi “model thiếu, tải lỗi, OOM”, trả mã lỗi hoặc log có cấu trúc, nhưng vẫn giữ fallback cho MRZ tùy chọn.
2. **Độ chính xác và an toàn dữ liệu:** `success` được bật khi có bất kỳ trường nhận dạng/cấp thẻ. QR được ưu tiên nhưng không có chứng thực mật mã. Cần bộ ảnh gán nhãn hợp pháp, đo tỷ lệ đúng từng trường và chính sách bảo vệ dữ liệu cá nhân trước khi dùng trong quy trình nhạy cảm.
3. **Tự phân loại một ảnh:** OCR sơ bộ chạy với `is_front=True`; mặt sau ít chữ hoặc MRZ mờ có thể bị mặc định thành mặt trước. Ưu tiên cho người gọi ép mặt hoặc bổ sung điểm tin cậy từ ảnh đã gán nhãn.
4. **Đầu vào API:** ứng dụng chưa có xác thực, giới hạn upload, quota hoặc timeout riêng cho inference. Chỉ bind localhost trong ví dụ; trước triển khai cần reverse proxy và giới hạn tài nguyên phù hợp.
5. **Đồng thời khi nạp model:** API dùng một pipeline chung, nhưng các model được nạp lười khi xử lý request. Nhiều request đầu tiên cùng lúc có thể khởi tạo model trùng, tăng đột biến RAM/VRAM. Cần prewarm hoặc đồng bộ bước khởi tạo trước khi tăng số worker.
6. **Tính lặp lại của model:** `uv.lock` chỉ khóa thư viện, không khóa trọng số tải từ URL. Cần lưu checksum và quy trình phát hành model nếu kết quả phải tái lập chính xác.
7. **Dữ liệu mẫu:** nhiều file `image/` và `output/` có thể chứa thông tin định danh. Cần duyệt quyền chia sẻ và thay bằng fixture đã ẩn danh.

## Thứ tự phát triển đề xuất

1. Chuẩn hóa lỗi theo từng stage và thêm bài test cho thiếu model, QR lỗi và OOM. Cần biết hệ thống thất bại ở đâu trước khi tối ưu độ chính xác.
2. Xây tập dữ liệu đã được phép sử dụng, có nhãn chuẩn cho hai mẫu thẻ; đo tỷ lệ đúng từng trường và lỗi phân loại mặt; dùng số liệu để chọn quy tắc cần sửa.
3. Đóng gói trọng số có checksum/version, prewarm model lúc khởi động dịch vụ và đặt giới hạn upload, timeout, worker phù hợp.
4. Chỉ sau khi có benchmark, tối ưu độ trễ OCR, thử phân loại mặt bằng hình ảnh hoặc bổ sung mẫu thẻ mới.
