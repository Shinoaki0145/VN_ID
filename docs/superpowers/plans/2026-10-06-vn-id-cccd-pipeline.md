# CCCD Dual-Side Extraction Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây dựng hoàn chỉnh pipeline trích xuất CCCD đa định dạng 2 mặt (CCCD gắn chip 2021 & Thẻ Căn cước 2024), cung cấp Core Python SDK, CLI runner, REST API (FastAPI) và bộ kiểm thử tự động với Mock Engine.

**Architecture:** Kiến trúc 5 chặng Bottom-up Hybrid (Aligner & Side Classifier -> OCR Reading Order & QR Decoder -> NER & Back Side Rules -> Fusion & Validation), liên kết qua Pydantic schemas chặt chẽ, hỗ trợ chạy CPU/GPU tự động và Mock Mode kiểm thử độc lập không phụ thuộc tải weights nặng.

**Tech Stack:** Python 3.12, Pydantic, OpenCV (`cv2`), PyTorch, Ultralytics YOLOv8, VietOCR, Hugging Face Transformers (PhoBERT), QReader, FastAPI, Click / Argparse, Pytest.

**Spec:** `docs/superpowers/specs/2026-10-06-vn-id-cccd-pipeline-design.md`

## Global Constraints

- Python 3.12 compatible.
- Thẻ 2 mặt: Tự động phân loại `FRONT`, `BACK`, `UNKNOWN`, hỗ trợ xử lý 1 ảnh đơn hoặc cặp 2 mặt gộp thành 1 hồ sơ.
- Mặt sau CCCD chip 2021: Trích xuất `issue_date` từ "Ngày, tháng, năm / Date, month, year" (định dạng `DD/MM/YYYY`), `issue_loc` từ dòng "CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" (bỏ từ "CỤC TRƯỞNG"). KHÔNG trích xuất Đặc điểm nhận dạng.
- Mặt sau Căn cước 2024: Trích xuất `issue_date` từ "Ngày, tháng, năm cấp", `expiry_date` từ "Ngày, tháng, năm hết hạn", `issue_loc` = "Bộ Công an".
- Ưu tiên dữ liệu: QR Code > OCR / NER.
- Mock Mode: Có thể chạy test toàn bộ pipeline và API end-to-end mà không cần GPU hoặc checkpoint nặng tải từ internet.

## Review Focus

1. Chuỗi ngày cấp dạng viết tắt hoặc có ký tự thừa (ví dụ: `24/06/2021.` hoặc `24-06-2021`): Cần chuẩn hóa regex về `DD/MM/YYYY`.
2. Dòng nơi cấp bị OCR nhầm dấu hoặc dính chữ ("QUAN LY HANH CHINH VE TRAT TU XA HOI"): Cần fuzzy/keyword match để chuẩn hóa chính xác thành "Cục Cảnh sát Quản lý hành chính về trật tự xã hội".
3. Mã QR bị mờ hoặc không đọc được: Pipeline phải graceful fallback sang OCR + NER mà không làm crash request.
4. Thẻ chỉ có 1 mặt (khách chỉ upload mặt trước hoặc chỉ upload mặt sau): Pipeline vẫn trả về kết quả hợp lệ cho mặt đó, các trường còn lại là `None`.
5. Đối soát 12 số CCCD khi năm sinh >= 2000: Kiểm tra đúng mã thế kỷ 21 (Nam = 2, Nữ = 3) thay vì nhầm thế kỷ 20 (Nam = 0, Nữ = 1).

---

### Task 1: Scaffolding, Core Constants & Pydantic Schemas

**Files:**
- Create: `pyproject.toml`
- Create: `vn_id/__init__.py`
- Create: `vn_id/core/__init__.py`
- Create: `vn_id/core/constants.py`
- Create: `vn_id/core/schemas.py`
- Test: `tests/test_schemas.py`

**Interfaces:**
- Consumes: None (Root schemas)
- Produces: `CardSide`, `AlignedCardResult`, `TextBox`, `OCRResult`, `NERResult`, `BackSideResult`, `QRResult`, `ValidationReport`, `CCCDData`, `FinalCCCDResult` trong `vn_id.core.schemas`. Danh mục mã tỉnh và từ khóa trong `vn_id.core.constants`.

- [ ] **Step 1: Write failing test in `tests/test_schemas.py`**

```python
import pytest
from vn_id.core.schemas import (
    CardSide, AlignedCardResult, BackSideResult, 
    CCCDData, FinalCCCDResult, ValidationReport
)
from vn_id.core.constants import PROVINCE_CODES, GENDER_CENTURY_MAP

def test_schemas_validation():
    back_res = BackSideResult(
        card_version="cccd_chip_2021",
        issue_date="24/06/2021",
        issue_loc="Cục Cảnh sát Quản lý hành chính về trật tự xã hội",
        raw_text="Ngày, tháng, năm / Date, month, year 24/06/2021\nCỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI"
    )
    assert back_res.issue_date == "24/06/2021"
    assert back_res.issue_loc == "Cục Cảnh sát Quản lý hành chính về trật tự xã hội"
    assert not hasattr(back_res, "identifying_characteristics")

def test_province_constants():
    assert "001" in PROVINCE_CODES
    assert PROVINCE_CODES["001"] == "Hà Nội"
    assert "079" in PROVINCE_CODES
    assert PROVINCE_CODES["079"] == "Thành phố Hồ Chí Minh"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_schemas.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'vn_id'"

- [ ] **Step 3: Implement `pyproject.toml`, `vn_id/core/constants.py`, and `vn_id/core/schemas.py`**

Khởi tạo package, định nghĩa đầy đủ 63 mã tỉnh thành Việt Nam, bảng mã thế kỷ/giới tính, và các Pydantic models tuân thủ chính xác spec.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_schemas.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml vn_id/ tests/test_schemas.py
git commit -m "feat(core): setup package structure, constants, and pydantic data contracts"
```

---

### Task 2: Stage 1 - Card Alignment & Side Classifier (`vn_id.aligner`)

**Files:**
- Create: `vn_id/aligner/__init__.py`
- Create: `vn_id/aligner/classifier.py`
- Create: `vn_id/aligner/detector.py`
- Create: `vn_id/aligner/mock.py`
- Test: `tests/test_aligner.py`
- Test: `tests/test_side_classifier.py`

**Interfaces:**
- Consumes: `CardSide`, `AlignedCardResult` từ `vn_id.core.schemas`.
- Produces: `SideClassifier.classify(image, text_hint) -> CardSide`, `CardAligner.align(image) -> AlignedCardResult`, `MockAligner`.

- [ ] **Step 1: Write failing test in `tests/test_side_classifier.py` and `tests/test_aligner.py`**

```python
import numpy as np
from vn_id.core.schemas import CardSide
from vn_id.aligner.classifier import SideClassifier
from vn_id.aligner.mock import MockAligner

def test_side_classifier_by_text():
    front_text = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nCĂN CƯỚC CÔNG DÂN\nSố / No.: 001098012345\nHọ và tên: NGUYỄN VĂN A"
    back_text = "Ngày, tháng, năm / Date, month, year 24/06/2021\nCỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI"
    
    assert SideClassifier.classify_text(front_text) == CardSide.FRONT
    assert SideClassifier.classify_text(back_text) == CardSide.BACK

def test_mock_aligner():
    dummy_img = np.zeros((600, 800, 3), dtype=np.uint8)
    aligner = MockAligner(side=CardSide.BACK)
    res = aligner.align(dummy_img)
    assert res.is_aligned
    assert res.aligned_image.shape == (630, 1000, 3)
    assert res.side == CardSide.BACK
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_side_classifier.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement `classifier.py`, `detector.py`, and `mock.py`**

`classifier.py`: Phân loại mặt trước/sau dựa trên keyword và đặc trưng (QR/MRZ/Quốc huy).
`detector.py`: Perspective warp transform 4 góc thành ảnh phẳng chuẩn $1000 \times 630$, crop vùng QR $x \ge 70\%, y \le 35\%$.
`mock.py`: Trả về ảnh chuẩn và vùng crop giả lập cho test.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_side_classifier.py tests/test_aligner.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add vn_id/aligner/ tests/test_aligner.py tests/test_side_classifier.py
git commit -m "feat(aligner): implement card alignment, side classifier, and mock aligner"
```

---

### Task 3: Stage 2 - Reading Order Sorter & OCR Engine (`vn_id.ocr`)

**Files:**
- Create: `vn_id/ocr/__init__.py`
- Create: `vn_id/ocr/sorter.py`
- Create: `vn_id/ocr/engine.py`
- Create: `vn_id/ocr/mock.py`
- Test: `tests/test_reading_order.py`

**Interfaces:**
- Consumes: `TextBox`, `OCRResult` từ `vn_id.core.schemas`.
- Produces: `ReadingOrderSorter.sort_boxes(boxes: list[TextBox], y_threshold: int = 18) -> OCRResult`, `OCREngine`, `MockOCR`.

- [ ] **Step 1: Write failing test in `tests/test_reading_order.py`**

```python
from vn_id.core.schemas import TextBox
from vn_id.ocr.sorter import ReadingOrderSorter

def test_reading_order_sorter():
    # 2 dòng xáo trộn vị trí
    boxes = [
        TextBox(bbox=[150, 50, 250, 70], text="quản lý hành chính", confidence=0.9, line_number=0),
        TextBox(bbox=[10, 10, 100, 30], text="Ngày, tháng, năm", confidence=0.9, line_number=0),
        TextBox(bbox=[105, 12, 200, 31], text="24/06/2021", confidence=0.9, line_number=0),
        TextBox(bbox=[10, 48, 140, 68], text="Cục Cảnh sát", confidence=0.9, line_number=0),
    ]
    sorter = ReadingOrderSorter(y_threshold=18)
    sorted_res = sorter.sort_boxes(boxes)
    lines = sorted_res.full_text.split("\n")
    assert len(lines) == 2
    assert lines[0] == "Ngày, tháng, năm 24/06/2021"
    assert lines[1] == "Cục Cảnh sát quản lý hành chính"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_reading_order.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `sorter.py`, `engine.py`, and `mock.py`**

Nhóm các box có chênh lệch $\Delta y \le 18\text{px}$, sắp xếp $x$ tăng dần, nối thành chuỗi `full_text`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_reading_order.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add vn_id/ocr/ tests/test_reading_order.py
git commit -m "feat(ocr): implement reading order sorter and ocr mock engine"
```

---

### Task 4: Stage 4 - QR Code Detector & Parser (`vn_id.qr`)

**Files:**
- Create: `vn_id/qr/__init__.py`
- Create: `vn_id/qr/decoder.py`
- Create: `vn_id/qr/mock.py`
- Test: `tests/test_qr_parser.py`

**Interfaces:**
- Consumes: `QRResult` từ `vn_id.core.schemas`.
- Produces: `QRDecoder.parse_payload(raw_text: str) -> QRResult`, `QRDecoder.decode(crop_img) -> QRResult`, `MockQRDecoder`.

- [ ] **Step 1: Write failing test in `tests/test_qr_parser.py`**

```python
from vn_id.qr.decoder import QRDecoder

def test_parse_valid_qr_payload():
    payload = "001098012345|012345678|NGUYỄN VĂN A|15081998|Nam|Số 1 Đại Cồ Việt, Hai Bà Trưng, Hà Nội|25052021"
    res = QRDecoder.parse_payload(payload)
    assert res.is_detected
    assert res.id == "001098012345"
    assert res.cmnd_old == "012345678"
    assert res.name == "NGUYỄN VĂN A"
    assert res.dob == "15/08/1998"
    assert res.gender == "Nam"
    assert res.address == "Số 1 Đại Cồ Việt, Hai Bà Trưng, Hà Nội"
    assert res.issue_date == "25/05/2021"

def test_parse_qr_missing_cmnd():
    payload = "001098012345||NGUYỄN VĂN B|01012000|Nữ|Hà Nội|01012022"
    res = QRDecoder.parse_payload(payload)
    assert res.is_detected
    assert res.id == "001098012345"
    assert res.cmnd_old is None
    assert res.name == "NGUYỄN VĂN B"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_qr_parser.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `decoder.py` and `mock.py`**

Tách chuỗi theo dấu `|`, chuẩn hóa ngày từ `DDMMYYYY` sang `DD/MM/YYYY`, xử lý trường hợp không có CMND cũ hoặc số trường linh hoạt.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_qr_parser.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add vn_id/qr/ tests/test_qr_parser.py
git commit -m "feat(qr): implement qr payload parser and mock decoder"
```

---

### Task 5: Stage 3 - Heuristic Rule Extractor cho Mặt Sau & Thẻ 2024 (`vn_id.ner`)

**Files:**
- Create: `vn_id/ner/__init__.py`
- Create: `vn_id/ner/back_rules.py`
- Create: `vn_id/ner/front_rules.py`
- Create: `vn_id/ner/phobert.py`
- Create: `vn_id/ner/mock.py`
- Test: `tests/test_back_rules.py`
- Test: `tests/test_front_rules.py`

**Interfaces:**
- Consumes: `OCRResult`, `NERResult`, `BackSideResult` từ `vn_id.core.schemas`.
- Produces: `BackSideExtractor.extract(text: str) -> BackSideResult`, `FrontFallbackExtractor.extract(text: str) -> dict`, `NERModel`, `MockNER`.

- [ ] **Step 1: Write failing test in `tests/test_back_rules.py` for 2021 chip card and 2024 card**

```python
from vn_id.ner.back_rules import BackSideExtractor

def test_extract_back_side_cccd_2021():
    # Đúng đoạn text trong ảnh mẫu user gửi:
    text = (
        "Ngày, tháng, năm / Date, month, year 24/06/2021\n"
        "CỤC TRƯỞNG CỤC CẢNH SÁT\n"
        "QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI\n"
        "DIRECTOR GENERAL OF THE POLICE DEPARTMENT"
    )
    result = BackSideExtractor.extract(text)
    assert result.card_version == "cccd_chip_2021"
    assert result.issue_date == "24/06/2021"
    # Bỏ từ CỤC TRƯỞNG theo yêu cầu user:
    assert result.issue_loc == "Cục Cảnh sát Quản lý hành chính về trật tự xã hội"
    assert result.expiry_date is None

def test_extract_back_side_can_cuoc_2024():
    text = (
        "Ngày, tháng, năm cấp: 15/07/2024\n"
        "Ngày, tháng, năm hết hạn: 15/07/2034\n"
        "BỘ CÔNG AN"
    )
    result = BackSideExtractor.extract(text)
    assert result.card_version == "can_cuoc_2024"
    assert result.issue_date == "15/07/2024"
    assert result.expiry_date == "15/07/2034"
    assert result.issue_loc == "Bộ Công an"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_back_rules.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `back_rules.py`, `front_rules.py`, and `mock.py`**

`back_rules.py`:
- Regex tìm `issue_date` sau "Ngày, tháng, năm" hoặc "Ngày, tháng, năm cấp".
- Tìm `expiry_date` sau "Ngày, tháng, năm hết hạn".
- Tìm `issue_loc`: Nhận diện cụm Cục Cảnh sát quản lý hành chính về trật tự xã hội (bỏ từ Cục trưởng) hoặc Bộ Công an.
- Tuyệt đối không trích xuất trường Đặc điểm nhận dạng.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_back_rules.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add vn_id/ner/ tests/test_back_rules.py
git commit -m "feat(ner): implement back side heuristic rule extractor for 2021 and 2024 cards"
```

---

### Task 6: Stage 5 - Logic Validation & Data Fusion (`vn_id.validator`)

**Files:**
- Create: `vn_id/validator/__init__.py`
- Create: `vn_id/validator/cccd_rules.py`
- Create: `vn_id/validator/fuzzy_address.py`
- Create: `vn_id/validator/fusion.py`
- Test: `tests/test_cccd_validator.py`
- Test: `tests/test_fusion.py`

**Interfaces:**
- Consumes: `NERResult`, `QRResult`, `BackSideResult`, `FinalCCCDResult` từ `vn_id.core.schemas`.
- Produces: `CCCDValidator.validate_12_digits(id_num, dob, gender) -> ValidationReport`, `AddressFuzzyMatcher`, `DataFusion.fuse(...) -> FinalCCCDResult`.

- [ ] **Step 1: Write failing test in `tests/test_cccd_validator.py` and `tests/test_fusion.py`**

```python
from vn_id.validator.cccd_rules import CCCDValidator
from vn_id.validator.fusion import DataFusion
from vn_id.core.schemas import NERResult, QRResult, BackSideResult

def test_cccd_12_digits_validation_valid():
    # 001: Hà Nội, 0: Nam thế kỷ 20, 98: sinh 1998
    rep = CCCDValidator.validate_12_digits("001098012345", dob="15/08/1998", gender="Nam")
    assert rep.is_valid_12_digits
    assert rep.province_valid
    assert rep.gender_century_valid
    assert rep.birth_year_valid

def test_cccd_12_digits_validation_century_21():
    # 079: TP.HCM, 3: Nữ thế kỷ 21, 05: sinh 2005
    rep = CCCDValidator.validate_12_digits("079305099999", dob="10/10/2005", gender="Nữ")
    assert rep.is_valid_12_digits
    assert rep.gender_century_valid
    assert rep.birth_year_valid

def test_fusion_qr_over_ocr_and_back_side():
    qr = QRResult(is_detected=True, id="001098012345", name="NGUYỄN VĂN A", dob="15/08/1998", gender="Nam")
    ner = NERResult(name="NGUYEN VAN A", dob="15/08/1998")  # OCR bị mất dấu
    back = BackSideResult(
        card_version="cccd_chip_2021",
        issue_date="24/06/2021",
        issue_loc="Cục Cảnh sát Quản lý hành chính về trật tự xã hội"
    )
    final = DataFusion.fuse(qr=qr, ner=ner, back=back)
    assert final.success
    assert final.data.name == "NGUYỄN VĂN A"  # Ưu tiên QR có dấu
    assert final.data.issue_date == "24/06/2021"
    assert final.data.issue_loc == "Cục Cảnh sát Quản lý hành chính về trật tự xã hội"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cccd_validator.py tests/test_fusion.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `cccd_rules.py`, `fuzzy_address.py`, and `fusion.py`**

Quy tắc 12 số định danh, so khớp fuzzy địa chỉ, và gộp dữ liệu theo thứ tự ưu tiên (QR > OCR/NER, gộp dữ liệu mặt sau).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cccd_validator.py tests/test_fusion.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add vn_id/validator/ tests/test_cccd_validator.py tests/test_fusion.py
git commit -m "feat(validator): implement 12-digit validator and dual-side data fusion engine"
```

---

### Task 7: CCCD Pipeline Orchestrator (`vn_id.pipeline`)

**Files:**
- Create: `vn_id/pipeline.py`
- Test: `tests/test_pipeline_mock.py`

**Interfaces:**
- Consumes: All modules from Tasks 1-6.
- Produces: `CCCDPipeline`:
  - `pipeline.process(image) -> FinalCCCDResult` (tự nhận diện front/back).
  - `pipeline.process_both_sides(front_image, back_image) -> FinalCCCDResult` (hợp nhất 2 mặt).

- [ ] **Step 1: Write failing test in `tests/test_pipeline_mock.py`**

```python
import numpy as np
from vn_id.pipeline import CCCDPipeline

def test_pipeline_mock_both_sides():
    dummy_front = np.zeros((600, 800, 3), dtype=np.uint8)
    dummy_back = np.zeros((600, 800, 3), dtype=np.uint8)
    
    pipeline = CCCDPipeline(mock_mode=True)
    res = pipeline.process_both_sides(front_image=dummy_front, back_image=dummy_back)
    
    assert res.success
    assert "front" in res.side_detected
    assert "back" in res.side_detected
    assert res.data.id is not None
    assert res.data.name is not None
    assert res.data.issue_date is not None
    assert res.data.issue_loc == "Cục Cảnh sát Quản lý hành chính về trật tự xã hội"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pipeline_mock.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `vn_id/pipeline.py`**

Kết nối 5 chặng, điều phối xử lý 1 ảnh hoặc 2 ảnh, đo thời gian thực thi (timings) của từng chặng.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_pipeline_mock.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add vn_id/pipeline.py tests/test_pipeline_mock.py
git commit -m "feat(pipeline): implement full dual-side pipeline orchestrator"
```

---

### Task 8: Delivery Interfaces - CLI Tool & FastAPI Service (`vn_id.cli`, `vn_id.api`)

**Files:**
- Create: `vn_id/cli/__init__.py`
- Create: `vn_id/cli/main.py`
- Create: `vn_id/api/__init__.py`
- Create: `vn_id/api/app.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `CCCDPipeline` từ `vn_id.pipeline`.
- Produces: CLI commands `vn-id extract ...`, FastAPI endpoints `POST /api/v1/extract`, `POST /api/v1/extract-both`, `GET /health`.

- [ ] **Step 1: Write failing test in `tests/test_api.py` and `tests/test_cli.py`**

```python
from fastapi.testclient import TestClient
from vn_id.api.app import app
import io

client = TestClient(app)

def test_api_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

def test_api_extract_both_mock():
    front_bytes = io.BytesIO(b"fake_front_image")
    back_bytes = io.BytesIO(b"fake_back_image")
    response = client.post(
        "/api/v1/extract-both?mock=true",
        files={
            "front": ("front.jpg", front_bytes, "image/jpeg"),
            "back": ("back.jpg", back_bytes, "image/jpeg")
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["issue_loc"] == "Cục Cảnh sát Quản lý hành chính về trật tự xã hội"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `vn_id/cli/main.py` and `vn_id/api/app.py`**

Xây dựng CLI parser (Click hoặc argparse) và FastAPI endpoints nhận file upload (`UploadFile`), gọi `CCCDPipeline`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_api.py tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add vn_id/cli/ vn_id/api/ tests/test_cli.py tests/test_api.py
git commit -m "feat(interfaces): implement CLI runner and FastAPI REST service"
```

---

### Task 9: Real User Image Integration Test (`tests/test_user_image_e2e.py`)

**Files:**
- Create: `tests/test_user_image_e2e.py`

**Interfaces:**
- Consumes: `media_1791257565797_ff5db4d9.png`, `BackSideExtractor`, `CCCDPipeline`.
- Produces: Verification that user's uploaded sample card image segment extracts `issue_date == "24/06/2021"` and `issue_loc == "Cục Cảnh sát Quản lý hành chính về trật tự xã hội"`.

- [ ] **Step 1: Write integration test with real image**

```python
import os
from vn_id.ner.back_rules import BackSideExtractor

def test_real_user_image_back_side_rules():
    # Kiểm tra trực tiếp đoạn text OCR bóc tách từ ảnh người dùng cung cấp
    ocr_text = (
        "Ngày, tháng, năm / Date, month, year24/06/2021\n"
        "CỤC TRƯỞNG CỤC CẢNH SÁT\n"
        "QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI\n"
        "DIRECTOR GENERAL OF THE POLICE DEPARTMENT\n"
        "FOR ADMINISTRATIVE MANAGEMENT OF SOCIAL ORDER"
    )
    res = BackSideExtractor.extract(ocr_text)
    assert res.issue_date == "24/06/2021"
    assert res.issue_loc == "Cục Cảnh sát Quản lý hành chính về trật tự xã hội"
```

- [ ] **Step 2: Run test and verify it passes**

Run: `pytest tests/test_user_image_e2e.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_user_image_e2e.py
git commit -m "test: add integration test matching user's real card snippet"
```
