# Design Spec: Pipeline Trích xuất CCCD Đa Định dạng 2 Mặt (VN_ID)

* **Ngày cập nhật:** 2026-10-06
* **Trạng thái:** Đã cập nhật yêu cầu xử lý 2 mặt & Mapping mặt sau (Pending Review)
* **Tác giả:** Antigravity Pair Programming

---

## 1. Tổng quan & Mục tiêu

### 1.1 Bối cảnh
Thẻ Căn cước Việt Nam có 2 mặt với các cấu trúc thông tin thay đổi theo các thời kỳ:
1. **Mặt trước:**
   - **CCCD gắn chip (2021):** Số định danh 12 số, Họ và tên, Ngày sinh, Giới tính, Quốc tịch, Quê quán, Nơi thường trú, Có giá trị đến (`expiry_date`), QR Code.
   - **Thẻ Căn cước mới (Luật 2024):** Số định danh cá nhân, Họ chữ đệm và tên, Ngày sinh, Giới tính, Quốc tịch, Nơi cư trú, Nơi đăng ký khai sinh, QR Code.
2. **Mặt sau:**
   - **CCCD gắn chip (2021):** "Ngày, tháng, năm / Date, month, year" $\rightarrow$ **Ngày cấp** (`issue_date`); Dòng "CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" (bỏ từ "CỤC TRƯỞNG") $\rightarrow$ **Nơi cấp** (`issue_loc`); Chip & dải mã đọc máy (MRZ). *(Không cần trích xuất Đặc điểm nhận dạng)*.
   - **Thẻ Căn cước mới (Luật 2024):** 
     - "Ngày, tháng, năm cấp" $\rightarrow$ **Ngày cấp** (`issue_date`).
     - "Ngày, tháng, năm hết hạn" $\rightarrow$ **Ngày hết hạn** (`expiry_date` - tương đương trường "Có giá trị đến" của CCCD cũ).
     - "BỘ CÔNG AN" $\rightarrow$ **Nơi cấp** (`issue_loc`).

### 1.2 Mục tiêu thiết kế
1. **Xử lý linh hoạt cả 2 mặt:** Tự động phân loại mặt thẻ (`FRONT` / `BACK`), hỗ trợ xử lý 1 mặt đơn lẻ hoặc nhận đồng thời cả 2 mặt để hợp nhất thành một hồ sơ hoàn chỉnh.
2. **Xử lý mặt sau bằng Rule/Heuristic chuyên sâu:** Vì mô hình NER (`phobert-cccd-ner`) không được huấn luyện cho mặt sau, toàn bộ mặt sau được bóc tách bằng bộ luật regex & neo từ khóa tối ưu cho cả thẻ 2021 lẫn thẻ 2024.
3. **Ground Truth Validation & Đối soát logic:** Ưu tiên QR Code mặt trước; đối soát 12 số định danh và fuzzy match địa danh.
4. **Triển khai trọn gói (Ponytail/YAGNI):** Cung cấp Core Library, CLI, và FastAPI REST service có sẵn Mock Engine.

---

## 2. Kiến trúc Hệ thống & Luồng Xử lý 2 Mặt

### 2.1 Sơ đồ Phân luồng Xử lý (Dual-side Workflow)

```text
               [Ảnh đầu vào: 1 ảnh hoặc Cặp Front & Back]
                                    │
                                    ▼
                ┌───────────────────────────────────────┐
                │ Chặng 1: Aligner & Side Classifier    │
                └───────────────────┬───────────────────┘
                                    │
         ┌──────────────────────────┴──────────────────────────┐
         ▼                                                     ▼
   [MẶT TRƯỚC (FRONT)]                                   [MẶT SAU (BACK)]
         │                                                     │
         ├───────────────────────────────┐                     │
         ▼                               ▼                     ▼
┌─────────────────┐             ┌─────────────────┐   ┌─────────────────┐
│  Chặng 2: OCR   │             │  Chặng 4: QR    │   │  Chặng 2: OCR   │
│ • DBNet BBoxes  │             │ • QReader/CV2   │   │ • DBNet BBoxes  │
│ • Reading Order │             │ • Parse '|'     │   │ • Reading Order │
│ • VietOCR Text  │             └────────┬────────┘   │ • VietOCR Text  │
└────────┬────────┘                      │            └────────┬────────┘
         │ OCR Full Text                 │                     │ Text Mặt Sau
         ▼                               │                     ▼
┌─────────────────┐                      │            ┌─────────────────┐
│  Chặng 3: NER   │                      │            │ Rule Extractor  │
│ • PhoBERT-NER   │                      │            │ (Back Side)     │
│ • Fallback 2024 │                      │            │ • Ngày cấp      │
└────────┬────────┘                      │            │ • Nơi cấp       │
         │ NER Front                     │            │ • Ngày hết hạn  │
         └───────────────┬───────────────┘            │ • Nhân dạng     │
                         ▼                            └────────┬────────┘
             ┌───────────────────────┐                         │
             │ Front Data Candidate  │                         │ Back Data
             └───────────┬───────────┘                         │
                         └───────────────────┬─────────────────┘
                                             ▼
                             ┌───────────────────────────────┐
                             │ Chặng 5: Fusion & Validator   │
                             │ • Gộp Front + Back + QR       │
                             │ • Kiểm tra logic 12 số        │
                             │ • Chuẩn hóa địa chỉ hành chính│
                             └───────────────┬───────────────┘
                                             ▼
                                   FinalCCCDResult (JSON)
```

---

## 3. Cấu trúc Dữ liệu Trung gian (Data Contracts)

### 3.1 Nhận diện Mặt Thẻ (`CardSideResult`)
```python
class CardSide(str, Enum):
    FRONT = "front"
    BACK = "back"
    UNKNOWN = "unknown"

class AlignedCardResult(BaseModel):
    aligned_image: Any              # np.ndarray: Ảnh nắn phẳng 1000x630
    qr_crop_image: Any | None       # np.ndarray: Vùng góc trên phải (nếu là mặt trước)
    side: CardSide                  # FRONT / BACK / UNKNOWN
    corners: list[tuple[int, int]]
    is_aligned: bool
    confidence: float
```

### 3.2 Kết quả Bóc tách Mặt sau (`BackSideResult`)
```python
class BackSideResult(BaseModel):
    card_version: str               # "cccd_chip_2021" | "can_cuoc_2024" | "unknown"
    issue_date: str | None = None   # DD/MM/YYYY (Ngày cấp)
    expiry_date: str | None = None  # DD/MM/YYYY (Ngày hết hạn - đối với thẻ Căn cước mới)
    issue_loc: str | None = None    # "Cục Cảnh sát QLHC về TTXH" hoặc "Bộ Công an"
    mrz_raw: str | None = None      # 3 dòng MRZ (nếu nhận dạng được)
    raw_text: str
```

### 3.3 Quy tắc Bóc tách Chi tiết cho Mặt sau (`BackSideExtractor`)
1. **Nhận diện Phiên bản Thẻ Mặt Sau:**
   - Nếu xuất hiện từ khóa `"BỘ CÔNG AN"` hoặc `"Nơi cư trú"` hoặc `"Ngày, tháng, năm hết hạn"` $\rightarrow$ **Thẻ Căn cước mới (Luật 2024)**.
   - Nếu xuất hiện từ khóa `"CỤC CẢNH SÁT"` hoặc `"QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI"` hoặc `"CỤC TRƯỞNG"` $\rightarrow$ **CCCD gắn chip (2021)**.
2. **Quy tắc Thẻ CCCD gắn chip (2021):**
   - **Ngày cấp (`issue_date`):** Neo từ khóa `"Ngày, tháng, năm"` hoặc `"Date, month, year"`. Regex bắt định dạng ngày: `(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})`. Ví dụ trong ảnh mẫu: `24/06/2021`.
   - **Nơi cấp (`issue_loc`):** Tìm dòng chứa `"CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI"`. **Lưu ý: Bỏ từ "CỤC TRƯỞNG"**, nơi cấp chuẩn hóa là: `"Cục Cảnh sát Quản lý hành chính về trật tự xã hội"`.
   *(Không bóc tách trường Đặc điểm nhận dạng)*.
3. **Quy tắc Thẻ Căn cước mới (2024):**
   - **Ngày cấp (`issue_date`):** Neo từ khóa `"Ngày, tháng, năm cấp"` $\rightarrow$ Regex bắt ngày `DD/MM/YYYY`.
   - **Ngày hết hạn (`expiry_date`):** Neo từ khóa `"Ngày, tháng, năm hết hạn"` $\rightarrow$ Regex bắt ngày `DD/MM/YYYY`. (Trường này có giá trị tương đương với `"Có giá trị đến"` ở mặt trước của thẻ CCCD cũ).
   - **Nơi cấp (`issue_loc`):** Neo từ khóa `"BỘ CÔNG AN"` $\rightarrow$ Gán giá trị chuẩn `"Bộ Công an"`.

### 3.4 Kết quả Hợp nhất Toàn diện (`FinalCCCDResult`)
```python
class CCCDData(BaseModel):
    # Thông tin định danh & nhân thân (Mặt trước / QR)
    id: str | None = None                   # 12 số CCCD
    cmnd_old: str | None = None             # 9 số CMND cũ (nếu có trong QR)
    name: str | None = None                 # Họ và tên
    dob: str | None = None                  # Ngày sinh (DD/MM/YYYY)
    gender: str | None = None               # Nam / Nữ
    nationality: str = "Việt Nam"
    origin: str | None = None               # Quê quán / Nơi ĐK khai sinh
    residence: str | None = None            # Nơi thường trú / Nơi cư trú
    
    # Thông tin hiệu lực & cấp thẻ (Mặt trước / Mặt sau)
    issue_date: str | None = None           # Ngày cấp
    expiry_date: str | None = None          # Ngày hết hạn / Có giá trị đến
    issue_loc: str | None = None            # Nơi cấp (Cục Cảnh sát QLHC về TTXH / Bộ Công an)

class FinalCCCDResult(BaseModel):
    success: bool
    side_detected: list[str]                # ["front"], ["back"], hoặc ["front", "back"]
    data: CCCDData                          # Dữ liệu đầy đủ sau khi gộp
    field_sources: dict[str, str]           # Nguồn gốc: {"name": "qr", "issue_date": "back_rules", ...}
    validation: ValidationReport            # Đối soát 12 số, logic năm sinh, mã tỉnh
    timings: dict[str, float]
```

---

## 4. Giao diện Sản phẩm (Delivery Interfaces)

### 4.1 Python Core SDK
```python
from vn_id import CCCDPipeline

pipeline = CCCDPipeline(device="auto", mock_mode=False)

# Xử lý 1 ảnh đơn (tự nhận diện mặt trước hoặc mặt sau)
result_single = pipeline.process("front.jpg")

# Xử lý trọn bộ 2 mặt (tự động ghép thành 1 hồ sơ đầy đủ)
result_both = pipeline.process_both_sides(front_image="front.jpg", back_image="back.jpg")
print(result_both.data.issue_date)  # 24/06/2021
print(result_both.data.issue_loc)   # Cục Cảnh sát Quản lý hành chính về trật tự xã hội
```

### 4.2 CLI Tool (`vn-id`)
```bash
# Xử lý ảnh đơn lẻ
vn-id extract photo.jpg --mock

# Xử lý trọn vẹn cả 2 mặt
vn-id extract --front front.jpg --back back.jpg --output result.json

# Xử lý thư mục hàng loạt
vn-id batch ./dataset/ --output ./output_json/
```

### 4.3 REST API Service (FastAPI)
* `POST /api/v1/extract`: Upload 1 ảnh bất kỳ (`file`), tự nhận diện mặt và trả về thông tin.
* `POST /api/v1/extract-both`: Upload 2 file (`front` và `back`), trả về hồ sơ `FinalCCCDResult` gộp đầy đủ.
* `GET /health`: Kiểm tra sức khỏe dịch vụ.

---

## 5. Chiến lược Kiểm thử & Mock Strategy

1. **Unit tests độc lập:**
   - `test_back_rules_2021.py`: Test bóc tách `issue_date` ("Ngày, tháng, năm 24/06/2021") và `issue_loc` ("CỤC TRƯỞNG CỤC CẢNH SÁT...") từ chuỗi OCR của ảnh user vừa upload.
   - `test_back_rules_2024.py`: Test bóc tách `issue_date` ("Ngày, tháng, năm cấp"), `expiry_date` ("Ngày, tháng, năm hết hạn"), và `issue_loc` ("BỘ CÔNG AN").
   - `test_side_classifier.py`: Kiểm tra nhận diện mặt thẻ FRONT vs BACK dựa trên từ khóa / đặc trưng.
   - `test_cccd_validator.py`: Kiểm tra 12 số định danh và so khớp với năm sinh / giới tính / tỉnh thành.
   - `test_dual_side_fusion.py`: Kiểm tra logic hợp nhất dữ liệu từ Front (QR/OCR) + Back (Rules).
   - `test_api_endpoints.py`: Kiểm thử cả 2 API `/extract` và `/extract-both`.

---

## 6. Cấu trúc Module Cập nhật

```text
VN_ID/
├── docs/
│   ├── plan.md
│   └── superpowers/specs/2026-10-06-vn-id-cccd-pipeline-design.md
├── vn_id/
│   ├── __init__.py
│   ├── pipeline.py               # Orchestrator (process & process_both_sides)
│   ├── core/
│   │   ├── schemas.py            # AlignedCardResult, BackSideResult, FinalCCCDResult...
│   │   └── constants.py          # 63 mã tỉnh, từ khóa nhận diện 2021/2024
│   ├── aligner/
│   │   ├── classifier.py         # Phân loại mặt trước / mặt sau
│   │   ├── detector.py           # Warp perspective
│   │   └── mock.py
│   ├── ocr/
│   │   ├── sorter.py             # Reading order algorithm
│   │   ├── engine.py             # DBNet + VietOCR
│   │   └── mock.py
│   ├── ner/
│   │   ├── phobert.py            # PhoBERT-NER cho mặt trước
│   │   ├── front_rules.py        # Fallback từ khóa mặt trước thẻ 2024
│   │   ├── back_rules.py         # Mapping mặt sau (2021 & 2024)
│   │   └── mock.py
│   ├── qr/
│   │   ├── decoder.py
│   │   └── mock.py
│   ├── validator/
│   │   ├── cccd_rules.py         # Logic 12 số
│   │   ├── fuzzy_address.py      # Chuẩn hóa địa chỉ
│   │   └── fusion.py             # Hợp nhất Front + Back + QR
│   ├── api/
│   │   └── app.py                # FastAPI endpoints
│   └── cli/
│       └── main.py               # Click / Argparse CLI
└── tests/
    ├── test_reading_order.py
    ├── test_back_rules.py
    ├── test_side_classifier.py
    ├── test_cccd_validator.py
    ├── test_qr_parser.py
    ├── test_dual_side_fusion.py
    └── test_api.py
```

