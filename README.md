# VN_ID: Pipeline Trích Xuất & Đối Soát CCCD / Thẻ Căn Cước Đa Định Dạng

Hệ thống trích xuất thông tin tự động, toàn diện từ ảnh Căn cước công dân Việt Nam, hỗ trợ đồng thời cả hai thế hệ thẻ:
- **CCCD gắn chip (mẫu 2021)**: Mã QR mặt trước, dòng MRZ mặt sau, do Cục Cảnh sát QLHC về TTXH cấp.
- **Thẻ Căn cước (mẫu mới 2024)**: Mã QR mặt sau, kích thước QR lớn, do Bộ Công an cấp, Nơi đăng ký khai sinh & Nơi cư trú được in ở mặt sau, hỗ trợ thông tin thân nhân (Cha/Mẹ) cho trẻ em.

---

## 🚀 Điểm Nổi Bật

1. **Kiến trúc Hybrid 100% Rule-Based Parser (Loại bỏ hoàn toàn PhoBERT / NER cồng kềnh)**:
   - **Text Detector**: Sử dụng mô hình DBNet18 (EasyOCR) phát hiện bounding box chữ chính xác.
   - **Text Recognizer**: Sử dụng mô hình VietOCR (VGG Seq2Seq) tối ưu cho tiếng Việt có dấu với cơ chế đệm an toàn `pad_y = 4`, `pad_x = 2` bảo toàn trọn vẹn dấu thanh (`?`, `~`, `.`).
   - **Bóc tách thực thể thuần Regex Rules**: Bóc tách họ tên, số định danh, ngày sinh, quê quán, nơi cư trú, hạn sử dụng, cơ quan cấp và MRZ với tốc độ siêu nhanh ($\approx 1\text{ms}$), không phụ thuộc mô hình NER nặng nề.
2. **Multi-Fallback QR Decoder (Ground Truth Accuracy)**:
   - Sử dụng **QReader (YOLOv8 + pyzbar)** kết hợp dự phòng **zxing-cpp**.
   - Tự động crop và giải mã vùng QR theo từng mặt (mặt trước cho CCCD 2021 và mặt sau góc trên cho Căn cước 2024).
   - Khi đọc được QR code, dữ liệu đạt độ chính xác 100%, triệt tiêu hoàn toàn sai sót từ OCR.
3. **Data Fusion & Đối Soát Nghiệp Vụ Tự Động**:
   - Cơ chế ưu tiên dữ liệu thông minh: `QR Code > Front Parser > Back Parser`.
   - Đối soát chéo 12 số định danh: Kiểm tra tính hợp lệ của mã 63 tỉnh/thành, chữ số thế kỷ & giới tính, 2 chữ số năm sinh.
   - Tự động suy luận giới tính từ chữ số thứ 4 của mã số CCCD nếu hình ảnh bị mờ trường giới tính.
   - Chuẩn hóa Unicode tiếng Việt chuẩn dựng sẵn (NFC).
4. **Đo Độ Trễ (Latency Breakdown) Toàn Diện & Chi Tiết**:
   - Đo đạc chính xác thời gian thực thi (milliseconds) của từng bước độc lập:
     - `front_align_ms`, `back_align_ms` (Căn chỉnh 4 góc thẻ).
     - `qr_ms` (Giải mã QR code).
     - `front_ocr_det_ms`, `back_ocr_det_ms` (Text Detection - mô hình DBNet18).
     - `front_ocr_rec_ms`, `back_ocr_rec_ms` (Text Recognition - mô hình VietOCR VGG Seq2Seq).
     - `front_ocr_sort_ms`, `back_ocr_sort_ms` (Sắp xếp thứ tự đọc ReadingOrderSorter).
     - `front_ocr_ms`, `back_ocr_ms` (Tổng thời gian OCR từng mặt).
     - `front_rules_ms`, `back_rules_ms` (Bóc tách quy tắc thực thể Regex).
     - `fusion_ms` (Hợp nhất dữ liệu & đối soát nghiệp vụ).
     - `total_ms` (Tổng thời gian xử lý toàn bộ pipeline).

---

## 📁 Cấu Trúc Thư Mục

```
VN_ID/
├── vn_id/
│   ├── pipeline.py            # Orchestrator trung tâm quản lý luồng xử lý & đo latency
│   ├── core/
│   │   ├── config.py          # Quản lý đường dẫn model weights (.models/) & kích thước chuẩn
│   │   ├── constants.py       # Bảng mã 63 tỉnh/thành, bảng thế kỷ & giới tính, keywords thẻ
│   │   ├── schemas.py         # Pydantic schemas (FinalCCCDResult, CCCDData, FrontSideResult, ...)
│   │   └── utils.py           # Tiện ích bỏ dấu tiếng Việt, chuẩn hóa ngày tháng DD/MM/YYYY
│   ├── aligner/               # Nắn thẳng thẻ (Perspective Warp), phân loại mặt & cắt vùng QR
│   ├── ocr/                   # EasyOCR (DBNet18 detector) + VietOCR (VGG Seq2Seq recognizer)
│   ├── parser/                # Bóc tách thực thể 100% Rule-based Regex
│   │   ├── common.py          # Regex patterns chung (ngày tháng, cư trú, khai sinh)
│   │   ├── front.py           # FrontRuleExtractor (bóc tách mặt trước)
│   │   ├── back.py            # BackRuleExtractor (bóc tách mặt sau 2021 & 2024, MRZ)
│   │   └── mock.py            # MockRuleExtractor cho kiểm thử độc lập
│   ├── qr/                    # Giải mã mã QR (QReader + zxing-cpp)
│   ├── validator/             # Đối soát 12 số CCCD, hợp nhất dữ liệu (DataFusion), chuẩn hóa địa chỉ
│   ├── api/                   # REST API backend (FastAPI)
│   └── cli/                   # Giao diện dòng lệnh CLI (Click)
├── tests/                     # Toàn bộ 42 unit & integration tests
├── image/                     # Bộ ảnh mẫu thực tế (CCCD 2021, Căn cước 2024, ảnh mờ, QR hỏng)
├── output/                    # Thư mục lưu file JSON kết quả trích xuất
├── test_run.py                # Script chạy kiểm thử toàn diện trên dữ liệu ảnh thực tế
├── test_pipeline.ipynb        # Jupyter Notebook kiểm thử trực quan với latency breakdown
└── pyproject.toml             # Khai báo package & dependencies
```

---

## 🛠️ Cài Đặt

Yêu cầu Python >= 3.10:

```bash
git clone <repo-url>
cd VN_ID
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

---

## 💻 Hướng Dẫn Sử Dụng

### 1. Dùng trong Python Code

```python
from vn_id import CCCDPipeline

# Khởi tạo pipeline (device="auto" tự động nhận diện GPU/CPU)
pipeline = CCCDPipeline(device="auto", mock_mode=False)

# Trích xuất cả 2 mặt (Mặt trước + Mặt sau)
result = pipeline.process_both_sides(
    front_image="image/front_moi_2.jpg",
    back_image="image/back_moi_2.jpg",
)

# In kết quả trích xuất
print("Họ và tên:", result.data.name)
print("Số CCCD  :", result.data.id)
print("Ngày sinh:", result.data.dob)
print("Địa chỉ  :", result.data.residence)

# In bảng đo độ trễ từng bước
print("\n[Latency Breakdown]")
for step, ms in result.timings.items():
    print(f"  - {step:<18}: {ms:8.2f} ms")
```

### 2. Dùng Script Kiểm Thử Thực Tế (`test_run.py`)

Chạy script kiểm tra tự động trên tất cả các mẫu thẻ (CCCD 2021, Căn cước 2024, QR mờ):

```bash
python test_run.py
```

### 3. Dùng Jupyter Notebook (`test_pipeline.ipynb`)

Mở notebook để xem trực quan hình ảnh thẻ, kết quả trích xuất dạng bảng và biểu đồ độ trễ:

```bash
jupyter notebook test_pipeline.ipynb
```

### 4. Dùng Giao Diện Dòng Lệnh (CLI)

```bash
# Trích xuất 1 ảnh (tự động nhận diện mặt)
vn-id extract image/front_cu.jpg -o output/result.json

# Trích xuất cặp 2 mặt
vn-id extract --front image/front_moi_2.jpg --back image/back_moi_2.jpg -o output/result.json

# Chạy chế độ Mock test nhanh không cần load model
vn-id extract image/front_cu.jpg --mock
```

### 5. Dùng REST API (FastAPI)

Khởi động server backend:
```bash
uvicorn vn_id.api.app:app --host 0.0.0.0 --port 8000 --reload
```
- Truy cập tài liệu tương tác Swagger UI: `http://localhost:8000/docs`
- `POST /api/v1/extract`: Trích xuất 1 ảnh (upload file)
- `POST /api/v1/extract-both`: Trích xuất cặp 2 ảnh mặt trước và mặt sau

---

## 🧪 Chạy Toàn Bộ Kiểm Thử (Unit Tests)

Hệ thống đi kèm bộ kiểm thử toàn diện gồm **42 test cases**:

```bash
pytest
```
