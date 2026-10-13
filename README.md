# VN_ID

Pipeline đọc thông tin từ ảnh CCCD gắn chip (mẫu 2021) và thẻ Căn cước (mẫu 2024). Có giao diện Python, lệnh `vn-id` và REST API. Hệ thống căn ảnh, đọc QR/OCR, phân tích chữ in và MRZ, sau đó hợp nhất và đối chiếu các trường.

> `success=true` chỉ cho biết đã trích xuất được ít nhất một trường nhận dạng hoặc cấp thẻ. Nó không xác nhận thẻ thật, người sở hữu thẻ, hay độ chính xác của mọi trường. Hãy kiểm tra `field_sources` và `validation.warnings`.

## Cài đặt

Yêu cầu Python 3.10 trở lên. Chạy các lệnh từ thư mục gốc repo.

```bash
uv sync --locked
uv run vn-id extract image/front_moi_1.jpg -o result.json
uv run --with pytest pytest -q
```

Nếu dùng pip, tạo môi trường ảo rồi cài từ file yêu cầu:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

`requirements.txt` cài package ở chế độ editable và lấy dependency từ `pyproject.toml`; pip không dùng `uv.lock`. Cài thêm `pytest` nếu chạy test. Bộ dependency gồm EasyOCR, VietOCR, QReader và PyTorch, có thể chiếm nhiều GB. Lần đầu chạy cần mạng để tải model. `--device auto` dùng CUDA nếu PyTorch nhận GPU, nếu không thì CPU; dùng `--device cpu` để ép CPU.

## Sử dụng

### CLI

```bash
# Một ảnh, tự phân loại mặt bằng OCR
uv run vn-id extract image/front_moi_1.jpg -o result.json

# Ép mặt, tránh nhầm phân loại
uv run vn-id extract --front image/front_moi_1.jpg -o result.json
uv run vn-id extract --back image/back_cu_7.jpg -o result.json

# Hai mặt cùng một thẻ
uv run vn-id extract --front image/front_moi_1.jpg --back image/back_moi_1.jpg -o result.json
```

Thư mục cha của `-o` phải tồn tại. Chỉ ghép hai ảnh của cùng một thẻ.

### Python

```python
from vn_id import CCCDPipeline, CardSide

pipeline = CCCDPipeline(device="cpu")
result = pipeline.process_both_sides("image/front_moi_1.jpg", "image/back_moi_1.jpg")
print(result.model_dump_json(indent=2))
print(result.data.name, result.field_sources.get("name"))

back = pipeline.process("image/back_cu_7.jpg", force_side=CardSide.BACK)
print(back.validation.warnings)
```

`process` nhận đường dẫn, bytes hoặc mảng NumPy. `process_both_sides` nhận ảnh trước và sau đúng thứ tự.

### Parser OOP

Có thể dùng parser độc lập với OCR hoặc inject factory/fusion vào pipeline:

```python
from vn_id import CardVersion, CCCDPipeline
from vn_id.parser import CardParserFactory
from vn_id.validator import DataFusion

factory = CardParserFactory()
parser = factory.get_parser(CardVersion.CAN_CUOC_2024)
back = parser.parse_back("BỘ CÔNG AN\nNgày, tháng, năm cấp: 18/11/2024")
pipeline = CCCDPipeline(device="cpu", parser_factory=factory, fusion=DataFusion())
```

`CCCD2021Parser` và `CanCuoc2024Parser` tách rule mặt sau theo bố cục; rule mặt trước dùng chung để giữ khả năng phục hồi OCR hiện tại. Factory tự nhận diện từng mặt; OCR không đủ dấu hiệu trả `unknown`. Có thể truyền mapping `CardVersion → BaseCardParser` vào constructor của factory để thay strategy mà không đổi pipeline. `DataFusion.merge()` là API instance; `DataFusion.fuse()`, `FrontRuleExtractor.extract()` và `BackRuleExtractor.extract(text, mrz_text)` vẫn tương thích. `card_version` dùng enum với các giá trị chuỗi JSON như trước; giá trị ngoài enum bị từ chối khi tạo schema.

### API

```bash
uv run uvicorn vn_id.api.app:app --host 127.0.0.1 --port 8000
curl -F "file=@image/front_moi_1.jpg" http://127.0.0.1:8000/api/v1/extract
curl -F "front=@image/front_moi_1.jpg" -F "back=@image/back_moi_1.jpg" http://127.0.0.1:8000/api/v1/extract-both
```

Swagger UI: `http://127.0.0.1:8000/docs`; health check: `GET /health`. Ảnh không giải mã được trả HTTP 400. `/health` chỉ xác nhận ứng dụng khởi động, không kiểm tra model đã tải. API chưa có xác thực; ví dụ chỉ bind localhost.

### Docker với GPU NVIDIA

```bash
docker build -t vn-id:0.1.0-gpu .
docker compose up -d
```

Compose yêu cầu NVIDIA GPU và runtime phù hợp; model lưu trong volume riêng,
ảnh và kết quả không được đưa vào image. Xem [hướng dẫn Docker](docs/docker.md)
để kiểm tra CUDA, cache trọng số và chạy smoke test bằng CPU.

## Kết quả

| Trường | Ý nghĩa |
|---|---|
| `success` | Có ít nhất một trường nhận dạng/cấp thẻ được trích xuất |
| `card_version` | `can_cuoc_cong_dan_2021`, `can_cuoc_2024` hoặc `unknown`; suy ra từ tiêu đề mặt trước và dấu hiệu mặt sau |
| `side_detected` | Mặt đã xử lý theo lệnh gọi hoặc phân loại OCR |
| `data` | Thông tin hợp nhất; trường không đọc được là `null` |
| `field_sources` | Nguồn của từng trường: `qr`, `front_rules`, `back_rules`, `mrz`, `id_deduced`, `default` |
| `validation` | Kiểm tra cấu trúc ID, đối chiếu MRZ và cảnh báo |
| `timings` | Thời gian từng bước, đơn vị mili giây |

Thứ tự ưu tiên khác nhau theo từng trường; xem [luồng xử lý](docs/architecture.md). QR có thể sai hoặc bị thay đổi, nên vẫn cần đối chiếu.

## Cấu hình và kiểm thử

- [`pyproject.toml`](pyproject.toml) khai báo package và thư viện OCR/QR cần thiết. [`uv.lock`](uv.lock) khóa phiên bản để `uv sync --locked` cài lặp lại; pip không dùng lock này.
- [`vn_id/ocr/vgg_seq2seq.yml`](vn_id/ocr/vgg_seq2seq.yml) là cấu hình VietOCR. File `.easyocr_models/model/vgg_seq2seq.pth` được ưu tiên nếu có; nếu không, VietOCR tải từ URL trong YAML. `device` trong YAML được ghi đè lúc chạy.
- Kiểm thử: `uv run --with pytest pytest -q`. Test ảnh thật sẽ bỏ qua nếu thiếu trọng số model. Hướng dẫn chi tiết: [docs/running.md](docs/running.md).
- `test_run.py` chạy cặp ảnh mẫu hiện có (`front_moi_1.jpg` và `back_moi_1.jpg`), hoặc nhận `--front`/`--back`/`--output`: `uv run python test_run.py`.

## Tài liệu

- [Cài đặt, chạy, kiểm thử và xử lý lỗi](docs/running.md)
- [Kiến trúc, luồng dữ liệu và quy tắc hợp nhất](docs/architecture.md)
- [Kết quả rà soát, rủi ro còn lại và lộ trình](docs/audit-and-roadmap.md)
