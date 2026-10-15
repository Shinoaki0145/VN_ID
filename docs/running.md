# Cài đặt và vận hành

## Môi trường

Chạy từ thư mục gốc dự án. Yêu cầu **Python 3.12** để dùng môi trường VietOCR đã được kiểm tra, đồng nhất với Docker. `.python-version` chọn Python 3.12 cho `uv`; `pyproject.toml` giới hạn package ở nhánh 3.12.x. `uv` là cách cài được khóa phiên bản; `pip` vẫn dùng được nhưng giải quyết phiên bản theo thời điểm cài.

```bash
uv sync --locked                 # cài pipeline, API, CLI, EasyOCR, VietOCR, QReader và PyTorch
```

Nếu dùng pip, tạo môi trường bằng Python 3.12:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

File này cài project ở chế độ editable và lấy dependency từ `pyproject.toml`; pip không dùng `uv.lock`. Sau đó chạy trực tiếp `vn-id` hoặc `uvicorn` thay cho `uv run vn-id` và `uv run uvicorn` trong các ví dụ bên dưới.

Trên Linux, PyTorch có thể kéo các gói CUDA dung lượng lớn kể cả khi dùng CPU. Cần đủ ổ đĩa và kết nối mạng cho lần cài/tải model đầu. Với bản cài editable trong repo, model được lưu dưới `.easyocr_models/` và `.models/` (đều bị `.gitignore` bỏ qua). Bản cài từ wheel dùng `~/.cache/vn_id/`. Không xóa cache nếu muốn chạy ngoại tuyến.

QReader/pyzbar cần thư viện hệ thống ZBar để đọc QR. Trên Ubuntu 26.04:

```bash
sudo apt-get install libzbar0t64
```

Ubuntu bản cũ có thể dùng tên gói `libzbar0`. Nếu thiếu thư viện này,
QReader báo `Unable to find zbar shared library`; OCR vẫn có thể chạy nhưng
phần đọc QR không hoạt động.

## Chạy một hoặc hai mặt

### EasyOCR DBNet trên CUDA với PyTorch mới

Nếu biên dịch `deform_conv_cuda`/`deform_pool_cuda` báo lỗi chuyển đổi
`at::DeprecatedTypeProperties` sang `c10::ScalarType`, chạy bản vá trong repo:

```bash
uv run python scripts/patch_easyocr_cuda.py
```

Script chỉ đổi `tensor.type()` thành `tensor.scalar_type()` tại các macro dispatch
CUDA của EasyOCR đã cài. Có thể chạy nhiều lần; chạy lại sau khi tạo mới `.venv`
hoặc cài lại EasyOCR. CUDA Toolkit và `CUDA_HOME` vẫn cần được cấu hình trước.
Khởi động lại Uvicorn/CLI để PyTorch biên dịch lại extension từ source đã sửa.

### Trích xuất ảnh

```bash
uv run vn-id extract --front image/front_moi_1.jpg
uv run vn-id extract --back image/back_cu_7.jpg
uv run vn-id extract --front image/front_moi_1.jpg --back image/back_moi_1.jpg -o result.json
```

Với ảnh đơn dạng positional (`vn-id extract image/ten_anh.jpg`), pipeline dùng OCR sơ bộ để phân loại mặt. Nếu không tìm được dấu hiệu, mặc định chọn mặt trước. Với ảnh mặt sau, dùng `--back` để tránh suy đoán này. `--front` và `--back` cùng lúc nghĩa là một cặp ảnh; không trộn ảnh của hai người hoặc hai thẻ khác nhau.

`-o` ghi JSON UTF-8 vào file; nếu bỏ qua, JSON được in ra stdout. File đầu vào phải tồn tại và là ảnh OpenCV đọc được. Thư mục cha của file đầu ra phải được tạo trước, ví dụ `mkdir -p output`.

Script mẫu cũng dùng cùng pipeline: `uv run python test_run.py` chạy cặp ảnh `front_moi_1.jpg` và `back_moi_1.jpg`; dùng `--front`, `--back`, `--device`, `--output` để chọn dữ liệu và chế độ khác.

## Chạy API

```bash
uv run uvicorn vn_id.api.app:app --host 127.0.0.1 --port 8000
curl -F "file=@image/front_moi_1.jpg" http://127.0.0.1:8000/api/v1/extract
curl -F "front=@image/front_moi_1.jpg" -F "back=@image/back_moi_1.jpg" http://127.0.0.1:8000/api/v1/extract-both
```

API mặc định không xác thực, nên ví dụ chỉ bind localhost. `GET /health` chỉ kiểm tra process và thiết bị chọn, chưa thử OCR. Upload hỏng trả 400. OCR/QR dùng model thật sẽ tải khi request đầu tới, khiến request đầu chậm hơn các request sau. Nếu đặt sau reverse proxy, cấu hình giới hạn kích thước upload và timeout ở proxy.

## Dùng từ Python

```python
from vn_id import CCCDPipeline, CardSide

p = CCCDPipeline(device="cpu")
one = p.process("image/back_cu_7.jpg", force_side=CardSide.BACK)
both = p.process_both_sides("image/front_moi_1.jpg", "image/back_moi_1.jpg")
print(one.model_dump_json(indent=2))
print(both.validation.warnings)
```

`device="auto"` chọn CUDA nếu PyTorch báo sẵn sàng.

## Kiểm thử

```bash
uv run --with pytest pytest -q
uv lock --check
```

Bộ test có test logic, test API/CLI và test ảnh thật. Test ảnh thật sẽ `skip` nếu thiếu trọng số. Một lần `pytest` xanh với nhiều bài `skip` không chứng minh OCR thực tế hoạt động trên mọi ảnh. Muốn đánh giá chất lượng, dùng bộ ảnh có kết quả chuẩn và theo dõi tỷ lệ đúng từng trường.

## Khi chạy thật gặp lỗi

1. **Kết quả rỗng:** kiểm tra log warning của `vn_id.ocr.engine`; lỗi tải model hoặc OOM hiện có thể khiến OCR trả chuỗi rỗng. Chạy `uv sync --locked`, kiểm tra dung lượng đĩa và thử `--device cpu`.
2. **QR không được đọc:** hệ thống thử vùng QR đã cắt rồi toàn ảnh. Ảnh mờ, chói hoặc QR hỏng có thể khiến parser phải dựa vào OCR/MRZ.
3. **Sai mặt:** dùng `--front` hoặc `--back`; tự phân loại dựa trên chữ OCR và mặc định mặt trước khi không chắc.
4. **Kết quả xung đột:** xem `field_sources`, `validation.mrz_checks`, `validation.mrz_checksums` và `warnings`; không tự coi `success` là xác thực danh tính.
