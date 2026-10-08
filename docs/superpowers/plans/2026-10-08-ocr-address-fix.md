# OCR Address Bug Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Đọc đúng `origin = "Phường 7, Quận 8, TP. Hồ Chí Minh"` từ mặt sau của cặp `front_moi_1.jpg` / `back_moi_1.jpg`.

**Architecture:** Trước OCR, dùng bộ phát hiện QR hiện có để che vùng QR trên một bản sao ảnh. Tận dụng tham số gom ô chữ của EasyOCR để VietOCR đọc trọn dòng địa chỉ trên mặt sau. Chia sẻ cùng một `QRDecoder` trong pipeline để dùng lại model đã tải.

**Tech Stack:** Python, NumPy, OpenCV, QReader/QRDet, EasyOCR DBNet, VietOCR, pytest; sử dụng các thư viện đã có.

**Spec:** Yêu cầu lập kế hoạch sửa lỗi `origin` trong cuộc trao đổi ngày 08/10/2026; phạm vi là OCR của pipeline hiện tại, không thiết kế subsystem mới.

## Phạm vi và bằng chứng

- JSON ghi `field_sources.origin = "back_rules"`; giá trị được lấy từ OCR của `image/back_moi_1.jpg`.
- Đã tái hiện text OCR: `Nơi đăng là 19 khai sinh /Place of birth: ALLE` và `Phường Quận TP. Hồ Chí Minh`.
- Ô `ALLE` có bbox `[874, 140, 935, 160]` trên ảnh đã resize 1000 × 630; ô này nằm trong QR.
- QReader phát hiện QR với confidence khoảng 0.946 và bbox khoảng `[748, 56, 937, 245]` trên chính ảnh đã resize. OpenCV `QRCodeDetector.detect` không phát hiện được QR ở ảnh này, nên không dùng nó làm bộ phát hiện duy nhất.
- Thử nghiệm chỉ trong bộ nhớ: che polygon `quad_xy` của QR, gọi `detector.detect(masked, width_ths=2.0)`, giữ padding hiện tại. VietOCR đọc vùng `[37, 158, 597, 202]` thành `Phường 7, Quận 8, TP. Hồ Chí Minh`, confidence khoảng 0.902.
- `width_ths=1.0` chưa giữ được hai số; `1.5` mới giữ được số 7; `2.0` đọc được cả 7 và 8 trong mẫu này.
- Khi lập kế hoạch chưa sửa source OCR hay ghi lại JSON đầu ra. Thử nghiệm một mẫu chưa chứng minh cấu hình phù hợp mọi ảnh; kết quả triển khai và hồi quy được ghi ở cuối tài liệu.

## Global Constraints

- Chỉ che QR trên bản sao ảnh dành cho OCR; ảnh gốc vẫn được dùng để giải mã QR.
- Tọa độ QR phải được phát hiện trên chính ảnh đưa vào OCR, không lấy trực tiếp tọa độ từ ảnh crop hoặc ảnh gốc có kích thước khác.
- Dùng vùng QR được phát hiện, không che cố định toàn bộ góc phải của thẻ.
- Không thêm dependency hoặc model; không thay đổi schema JSON và thứ tự ưu tiên fusion.
- Không hardcode địa chỉ, số 7, số 8 hoặc xóa riêng chuỗi `ALLE`.
- Đổi ngưỡng gom ô trên mặt sau; giữ ngưỡng mặt trước hiện tại để hạn chế ảnh hưởng bố cục ảnh chân dung/ngày hết hạn.
- Nếu không tìm thấy QR hoặc bộ phát hiện QR lỗi, OCR vẫn tiếp tục với ảnh chưa che.

## Review Focus

1. Ảnh không có QR hoặc thiếu QReader: OCR vẫn chạy; kiểm tra trong Task 1.
2. QR xoay hoặc sát mép: che polygon hợp lệ, không lỗi tọa độ hay che chữ ở ngoài; kiểm tra trong Task 1.
3. Input grayscale/BGR/BGRA và ảnh gốc được dùng lại: giữ shape/dtype, không sửa mảng gốc; kiểm tra trong Task 1.
4. Mặt trước có hai cột hoặc mặt sau có hai trường sát nhau: tránh ghép thành một giá trị; kiểm tra trong Task 2.
5. Nhãn nơi khai sinh và địa chỉ ở hai dòng: không làm mất số hoặc kéo ngày cấp vào `origin`; kiểm tra trong Task 2.

## Task 1: Che vùng QR trước khi chạy OCR

**Files:** Modify `vn_id/qr/decoder.py`, `vn_id/ocr/engine.py`, `vn_id/pipeline.py`; test `tests/test_qr_parser.py` và tạo `tests/test_ocr_engine.py`.

**Interfaces:**
- Thêm `QRDecoder.mask_qr_regions(image: np.ndarray) -> np.ndarray`: trả bản sao ảnh đã che các polygon QR bằng màu trắng; lỗi phát hiện hoặc không có QR thì trả bản sao chưa che.
- Mở rộng constructor `OCREngine.__init__(use_mock: bool = False, device: str = "cpu", qr_decoder: QRDecoder | None = None)`. Dùng instance được truyền vào; khi dùng độc lập, tạo một `QRDecoder` với cùng device và tải model theo cơ chế lazy hiện có.
- Giữ `OCREngine.recognize(image, is_front)` và schema `OCRResult` hiện tại.
- Trong pipeline thật, tạo `self.qr_decoder` trước và truyền nó vào `self.ocr_engine`; luồng mock tiếp tục dùng các mock hiện có.

- [x] **Viết test thất bại trước.** Test `test_mask_qr_regions_preserves_input_and_text`: stub riêng kết quả `QReader.detect` với polygon `[20,20]`, `[40,20]`, `[40,40]`, `[20,40]` trên ảnh 64 × 64. Chạy hàm mask thật; assert pixel `(30,30)` trắng, pixel ngoài QR không đổi, ảnh gốc không đổi, shape/dtype giữ nguyên. Tham số hóa grayscale/BGR/BGRA.
- [x] **Bổ sung trường hợp biên.** `test_mask_qr_regions_without_detection` và `test_mask_qr_regions_detection_failure` assert output bằng input nhưng không sửa input. `test_mask_qr_regions_clips_rotated_polygon` dùng polygon xoay chạm mép; assert vùng trong QR được che và vùng chữ ở ngoài giữ nguyên.
- [x] **Chạy test để thấy lỗi đúng nguyên nhân:** `.venv/bin/python -m pytest tests/test_qr_parser.py -q`. Các test mới phải fail vì chưa có hành vi mask.
- [x] **Implement `mask_qr_regions`.** Dùng `self._get_qreader().detect`, chuyển grayscale/BGRA thành BGR khi cần, lấy `quad_xy` và dùng `cv2.fillConvexPoly` trên bản sao; để OpenCV cắt polygon tại biên ảnh, tránh biến dạng polygon QR xoay. Catch lỗi phát hiện để OCR tiếp tục; không sửa dữ liệu QR payload.
- [x] **Nối vào OCR và pipeline.** Gọi mask sau kiểm tra input và trước DBNet; dùng ảnh đã che cho detection và recognition. Test `test_ocr_masks_qr_before_detection` kiểm tra ảnh thực sự được đưa vào detector, thay vì chỉ kiểm tra constructor. Test `test_pipeline_shares_qr_decoder_with_ocr` xác nhận dùng chung instance. Giữ đường trả sớm của mock.
- [x] **Verify:** `.venv/bin/python -m pytest tests/test_qr_parser.py tests/test_ocr_engine.py tests/test_pipeline_mock.py -q`. Các test mới và test giải mã tiếng Việt phải pass.

**Kết quả riêng của task:** OCR không đọc họa tiết QR thành chữ; giải mã QR vẫn dùng ảnh nguyên vẹn. Hai số trong địa chỉ có thể vẫn thiếu ở giai đoạn này.

## Task 2: Đọc trọn dòng địa chỉ và kiểm tra hồi quy

**Files:** Modify `vn_id/ocr/engine.py`; test `tests/test_ocr_engine.py`, `tests/test_user_image_e2e.py`. Parser và sorter hiện có được dùng để kiểm tra kết quả, không sửa regex chỉ để bù lỗi OCR.

**Interfaces:** Tiếp tục dùng `recognize(image: np.ndarray, is_front: bool = True) -> OCRResult`; gọi EasyOCR với `width_ths=2.0` chỉ khi `is_front=False` và QR đã được che; mọi trường hợp khác dùng `width_ths=0.5`. Điều kiện này được thu hẹp sau khi kiểm tra hồi quy. EasyOCR gom các ô trước khi VietOCR nhận dạng; sorter hiện tại chỉ sắp xếp text sau đó.

- [x] **Viết regression test thất bại trước.** `test_can_cuoc_2024_origin_keeps_ward_and_district_numbers` dùng `CardAligner` và OCR thật trên `image/back_moi_1.jpg`, rồi `BackRuleExtractor.extract`. Assert `origin == "Phường 7, Quận 8, TP. Hồ Chí Minh"`, `issue_date == "18/11/2024"`, `expiry_date == "14/09/2043"`, và không có text box `ALLE`. Test chỉ chạy khi đủ ảnh/model/dependency; nếu thiếu phải báo skip rõ ràng.
- [x] **Chạy test để xác nhận thất bại:** `.venv/bin/python -m pytest tests/test_user_image_e2e.py::test_can_cuoc_2024_origin_keeps_ward_and_district_numbers -q`. Sau Task 1, lỗi mong đợi là thiếu số 7/8.
- [x] **Đổi tham số gom ô tại lời gọi detector.** Giữ padding hiện tại (`pad_x=2`, `pad_y=4`) và ngưỡng nhận dạng `prob >= 0.35`; chỉ đổi `width_ths` theo mặt thẻ. Không tạo thuật toán gom ô mới nếu cấu hình có sẵn đáp ứng được test.
- [x] **Kiểm tra bố cục.** Test `test_ocr_front_keeps_column_gap` dùng các polygon có khoảng cách lớn giữa ngày hết hạn và địa chỉ; dùng grouping thật của EasyOCR để assert hai vùng vẫn tách. Test `test_ocr_back_keeps_distinct_fields` dùng hai trường cùng hàng nhưng cách nhau hơn hai lần chiều cao ô chữ, assert không gom. Kiểm tra bằng ảnh thật mặt trước 2021 và mặt sau 2021 để phát hiện mất tên/ngày/MRZ so với baseline chụp trước khi đổi ngưỡng.
- [x] **Chạy end-to-end cặp ảnh mục tiêu.** `CCCDPipeline(device="cpu").process_both_sides("image/front_moi_1.jpg", "image/back_moi_1.jpg")`: assert `data.origin` đúng chuỗi mục tiêu, `field_sources.origin == "back_rules"`, ID `079183034888`, tên `Huỳnh Thị Thanh Hiền`, ngày cấp `18/11/2024`, ngày hết hạn `14/09/2043`.
- [x] **Verify toàn bộ:** `.venv/bin/python -m pytest -q` và `git diff --check`. Báo mọi fail/skip; test ảnh thật mục tiêu phải thực sự chạy trên môi trường có model, không suy ra thành công từ suite toàn mock.
- [x] **Ghi kết quả để review.** Lưu JSON và preview bbox của lần chạy mới vào một thư mục riêng, ví dụ `output/ocr_address_fix/`; so sánh origin trước/sau và thời gian OCR. Không ghi đè các snapshot cũ trong lúc kiểm tra. Nếu ngưỡng mới làm hỏng ảnh hồi quy, thu hẹp điều kiện áp dụng sau khi đối chiếu bbox; không chấp nhận fix chỉ đúng một ảnh.

## Tiêu chí hoàn tất

- `origin` đúng `Phường 7, Quận 8, TP. Hồ Chí Minh` qua cả OCR/parser và pipeline hai mặt.
- Không còn chữ OCR giả từ QR trong ảnh mục tiêu.
- Hai con số được nhận dạng từ pixel ảnh; không thêm số bằng quy tắc thay text.
- Các test QR, parser, fusion, mock, bố cục và ảnh hồi quy đạt; báo rõ trường hợp chưa kiểm tra được.

## Cách thực hiện đề xuất

Thực hiện tuần tự trong phiên hiện tại, mỗi task theo test thất bại → sửa tối thiểu → kiểm tra. Hai task cùng chạm OCR nên chưa cần chạy agent song song. Source đã được sửa trực tiếp trong workspace và để chưa commit cho người dùng review.


## Kết quả triển khai

- Che QR trên bản sao bằng QReader; pipeline dùng chung QRDecoder.
- Chỉ gom rộng trên mặt sau có QR: gom rộng tất cả mặt sau làm mất issuer của `back_cu_7.jpg`, nên đã thu hẹp điều kiện và thêm regression test. Nếu không phát hiện được QR trên thẻ 2024, giữ cách gom cũ.
- Review phát hiện clamp từng đỉnh làm hở QR xoay sát mép: regression test đã fail trước khi sửa, sau đó chuyển sang clipping polygon bằng OpenCV và test pass.
- `.venv/bin/python -m pytest -q`: **63 passed**, không skip; có 4 cảnh báo deprecation từ thư viện. `git diff --check`: pass.
- So sánh `front_cu_6.jpg`, `front_cu_7.jpg`, `back_cu_6.jpg`, `back_cu_7.jpg`: toàn bộ trường parsed giữ nguyên so với baseline.
- Pipeline ảnh thật cặp `front_moi_1.jpg` / `back_moi_1.jpg` trả origin đúng. Kết quả và ảnh bbox: `output/ocr_address_fix/`. Các snapshot cũ chưa bị ghi đè.
