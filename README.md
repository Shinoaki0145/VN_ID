# VN_ID — OCR CCCD và Căn cước Việt Nam

Trích xuất thông tin từ ảnh CCCD gắn chip mẫu 2021 và thẻ Căn cước mẫu 2024.
Hệ thống căn chỉnh ảnh, đọc QR, phát hiện chữ bằng EasyOCR/DBNet, nhận dạng
bằng VietOCR, phân tích MRZ rồi hợp nhất và đối chiếu dữ liệu. Có REST API,
CLI và giao diện Python; hỗ trợ CPU hoặc GPU NVIDIA.

> `success: true` nghĩa là đã đọc được ít nhất một trường nhận dạng hoặc cấp
> thẻ. Nó không xác nhận thẻ thật, mọi trường đều chính xác hay hai ảnh thuộc
> cùng một thẻ. Luôn xem `field_sources` và `validation.warnings`.

## Chạy bằng Docker GPU

Thực hiện các lệnh tại thư mục gốc repo trên **máy chạy service**.
Không cần cài môi trường Python local để dùng Docker.

### Yêu cầu

- GPU NVIDIA và driver tương thích với CUDA trong PyTorch. Đã kiểm tra DBNet
  và VietOCR trong container trên RTX 5060 với PyTorch 2.14.1, CUDA 13.0.
- Docker Engine, Docker Compose hỗ trợ `gpus: all` và NVIDIA Container Toolkit.
- Với Ubuntu trong WSL2: bật systemd và cài driver NVIDIA trên Windows;
  không cài thêm driver GPU Linux vào WSL.
- Có mạng và đủ dung lượng cho image/dependency nhiều GB. Model được tải
  riêng khi sử dụng lần đầu.

### Lần đầu: Ubuntu/WSL2 chưa có Docker

```bash
bash scripts/setup_docker_gpu.sh
```

Nhập mật khẩu `sudo` trong terminal khi được yêu cầu. Script cài Docker
Engine, Buildx, Compose và NVIDIA Container Toolkit từ repository chính thức
nếu chưa có; cấu hình NVIDIA runtime và khởi động lại Docker. Sau đó build
image `vn-id:0.1.0-gpu`, kiểm tra phép tính CUDA và khởi động API.

Script dành cho Docker Engine trên Ubuntu có systemd. Nếu dùng Docker Desktop
trên Windows, bật WSL integration và cấu hình GPU của Desktop trước, rồi dùng
các lệnh build bên dưới; không dùng script cài Engine vào cùng môi trường đó.

### Máy đã có Docker và NVIDIA runtime

```bash
sudo docker compose up -d --build --wait --wait-timeout 120
sudo docker compose ps
```

Image dùng Python 3.12 và dependency theo `uv.lock`; build kiểm tra PyTorch
có hỗ trợ CUDA. Compose cấp GPU và kiểm tra CUDA trước khi khởi động API:
nếu không thấy GPU, service dừng thay vì tự chuyển sang CPU.

Các ví dụ dùng `sudo` vì script không thêm user vào nhóm `docker`. Nếu tài
khoản đã có quyền Docker thì có thể bỏ `sudo`.

### Những lần sử dụng tiếp theo

```bash
# Khởi động service đã build
sudo docker compose up -d

# Xem trạng thái và theo dõi log
sudo docker compose ps
sudo docker compose logs --tail 100 -f vn-id

# Dừng service, giữ container và cache
sudo docker compose stop
```

Không cần chạy lại script cài đặt mỗi lần mở máy. Sau khi sửa source hoặc
dependency, chạy `sudo docker compose up -d --build` để cập nhật container;
`up -d` đơn thuần không build lại source.

`Ctrl+C` khi đang xem `logs -f` chỉ dừng theo dõi log, không dừng service.

### Truy cập trên cùng máy

- Swagger để chọn ảnh và gọi API: **http://127.0.0.1:8000/docs**.
- Trạng thái service: **http://127.0.0.1:8000/health**.

```bash
curl --fail-with-body http://127.0.0.1:8000/health
```

Kết quả mong đợi có `"status":"ok"` và `"device":"cuda"`. Health không tải
hay kiểm tra inference của model. Route `/` không có giao diện nên trả 404;
hãy mở `/docs`.

### Truy cập từ máy khác qua SSH/VS Code

Docker chỉ công bố API tại `127.0.0.1:8000` của máy chạy service. Trình duyệt
trên máy cá nhân cần chuyển tiếp cổng SSH để truy cập địa chỉ này.

Trong cửa sổ VS Code đang kết nối Remote SSH:

1. Mở tab **Ports** cạnh Terminal, chọn **Add Port**, nhập **`8000`**.
2. Nhấp phải dòng vừa tạo → **Change Local Address Port** → nhập **`18000`**.
3. Kiểm tra bảng có đúng hai cột sau:

| Port — trên máy SSH | Forwarded Address — trên máy cá nhân |
|---|---|
| `8000` | `localhost:18000` |

Mở **http://127.0.0.1:18000/docs** bằng trình duyệt trên máy cá nhân.
Giữ kết nối VS Code/SSH trong lúc dùng service.

```text
Trình duyệt máy cá nhân       Máy SSH                Container
127.0.0.1:18000 ─── SSH ───▶ 127.0.0.1:8000 ──────▶ API :8000
```

**Giữ cột Port là `8000`.** Nếu đổi cột này thành `18000`, tunnel sẽ trỏ tới
cổng không có service trên máy SSH. Cổng local `18000` là lựa chọn tránh trùng
cổng; có thể dùng local `8000` nếu cổng đó trống.

Cách khác: chạy trên **máy cá nhân**, thay `USER` và `IP_MAY_CHAY_SERVICE`
bằng thông tin SSH thực tế:

```bash
ssh -N -L 18000:127.0.0.1:8000 USER@IP_MAY_CHAY_SERVICE
```

Giữ terminal này mở rồi vào `http://127.0.0.1:18000/docs`. Tên host trong
VS Code chỉ dùng được với lệnh `ssh` nếu nó cũng được cấu hình trong SSH
config của máy đang chạy lệnh.

### Kiểm tra GPU bên trong container

Chạy khi không có request OCR đang xử lý vì script tải thêm model vào một
process riêng, cần thêm bộ nhớ GPU:

```bash
sudo docker compose exec -T vn-id python < scripts/check_docker_gpu.py
```

Script in phiên bản thư viện, checksum source, tên GPU; kiểm tra phép tính
CUDA, model DBNet/VietOCR nằm trên GPU và inference bằng ảnh trắng. Khi đạt:

```text
PASS: torchvision CUDA convolution
PASS: DBNet CUDA inference
PASS: VietOCR CUDA inference
```

Kiểm tra này không thay thế đánh giá độ chính xác trên ảnh thật.

### Model và dữ liệu trong Docker

- Container chạy bằng user `app`, không phải root.
- Volume `model-cache` giữ model/cache tại `/home/app/.cache` qua các lần
  dừng, khởi động hoặc tạo lại container.
- Image không chứa ảnh CCCD, kết quả, `.venv` hay model local của repo.
- Request OCR đầu có thể lâu do tải trọng số. Image mới chưa chạy ngoại
  tuyến được nếu chưa chuẩn bị đủ model.
- `sudo docker compose down` giữ volume; **`down -v` xóa volume model-cache**.

Xem [hướng dẫn Docker chi tiết](docs/docker.md) để sao chép model local vào
volume hoặc chạy kiểm tra bằng CPU.

## Gọi API OCR

Trong Swagger `/docs`, chọn endpoint → **Try it out** → chọn ảnh → **Execute**.

| Phương thức | Endpoint | Dữ liệu gửi |
|---|---|---|
| GET | `/health` | Không có |
| POST | `/api/v1/extract` | File ảnh ở trường `file` |
| POST | `/api/v1/extract-both` | Hai file ở trường `front` và `back` |

Ví dụ chạy trực tiếp trên máy service:

```bash
# Một mặt
curl --fail-with-body \
  -F 'file=@image/front_cu_10.png' \
  http://127.0.0.1:8000/api/v1/extract

# Hai mặt cùng một thẻ
curl --fail-with-body \
  -F 'front=@image/front_moi_1.jpg' \
  -F 'back=@image/back_moi_1.jpg' \
  http://127.0.0.1:8000/api/v1/extract-both
```

Nếu gọi từ máy cá nhân qua tunnel ở trên, đổi địa chỉ thành
`http://127.0.0.1:18000` và dùng đường dẫn ảnh có trên máy cá nhân đó.
Ảnh không giải mã được trả HTTP 400. API chưa có xác thực; Compose giới hạn
cổng ở localhost, dùng SSH để truy cập từ xa.

### Đọc kết quả

| Trường | Ý nghĩa |
|---|---|
| `success` | Đã đọc được ít nhất một trường ID, tên, ngày cấp hoặc nơi cấp |
| `card_version` | `can_cuoc_cong_dan_2021`, `can_cuoc_2024` hoặc `unknown` |
| `side_detected` | Các mặt đã xử lý |
| `data` | Dữ liệu hợp nhất; trường không đọc được là `null` |
| `field_sources` | Nguồn từng trường: `qr`, `front_rules`, `back_rules`, `mrz`, `id_deduced`, `default` |
| `validation` | Kiểm tra cấu trúc ID, đối chiếu MRZ và cảnh báo |
| `timings` | Thời gian từng bước, đơn vị mili giây |

HTTP 200 chỉ xác nhận API trả phản hồi, không bảo đảm OCR thành công.
`mrz_checks: false` nghĩa là dữ liệu MRZ khác dữ liệu từ nguồn được ưu tiên;
khác với `mrz_checksums`, là kiểm tra chữ số kiểm tra trong MRZ.

**Chỉ gửi hai mặt của cùng một thẻ.** Các file có cùng số thứ tự chưa chắc
là một cặp: `front_cu_8.jpg` và `back_cu_8.jpg` thuộc hai thẻ khác nhau.
Pipeline hiện vẫn có thể trả `success: true` và ghép thông tin từ cả hai mặt;
phải đọc cảnh báo đối chiếu trước khi dùng kết quả.

## Chạy trực tiếp bằng Python

Yêu cầu **Python 3.12** cho cả local và Docker để dùng môi trường VietOCR
đã được kiểm tra của dự án. Chạy từ thư mục gốc repo.

### Cài dependency

Khuyến nghị dùng `uv` để cài theo lockfile:

```bash
uv sync --locked
```

Hoặc dùng pip:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Pip cài package editable từ `pyproject.toml` và không dùng `uv.lock`.
Dependency CUDA có thể chiếm nhiều GB kể cả khi chỉ định chạy CPU.
Lần đầu chạy cần mạng để tải model.

### CLI

```bash
# Tự chọn CUDA nếu có GPU, nếu không thì CPU
uv run vn-id extract image/front_moi_1.jpg -o result.json

# Chỉ định GPU và mặt ảnh
uv run vn-id extract --front image/front_moi_1.jpg --device cuda -o result.json

# Hai mặt cùng một thẻ
uv run vn-id extract \
  --front image/front_moi_1.jpg --back image/back_moi_1.jpg \
  --device cuda -o result.json

# Ép chạy CPU
uv run vn-id extract image/front_moi_1.jpg --device cpu
```

Thư mục cha của file `-o` phải tồn tại. Tham số mặc định `--device auto`
chọn thiết bị theo khả năng CUDA của PyTorch.

### Python API

```python
from vn_id import CCCDPipeline, CardSide

pipeline = CCCDPipeline(device="cuda")  # "auto" hoặc "cpu" nếu cần
result = pipeline.process_both_sides(
    "image/front_moi_1.jpg", "image/back_moi_1.jpg"
)
print(result.model_dump_json(indent=2))

single = pipeline.process("image/front_moi_1.jpg", force_side=CardSide.FRONT)
print(single.validation.warnings)
```

`process()` nhận đường dẫn, bytes hoặc mảng NumPy. `process_both_sides()`
nhận ảnh mặt trước và mặt sau theo đúng thứ tự.

### REST API local, không dùng Docker

```bash
uv run uvicorn vn_id.api.app:app --host 127.0.0.1 --port 8000
```

Mở `/docs` và gọi các endpoint như bản Docker. Pipeline tự chọn CUDA nếu có.
Dừng service Docker trước nếu muốn dùng cùng cổng `8000`:

```bash
sudo docker compose stop
```

### Parser độc lập

```python
from vn_id import CardVersion, CCCDPipeline
from vn_id.parser import CardParserFactory
from vn_id.validator import DataFusion

factory = CardParserFactory()
parser = factory.get_parser(CardVersion.CAN_CUOC_2024)
back = parser.parse_back("BỘ CÔNG AN\nNgày, tháng, năm cấp: 18/11/2024")
pipeline = CCCDPipeline(
    device="auto", parser_factory=factory, fusion=DataFusion()
)
```

Factory chọn parser theo bố cục thẻ; không đủ dấu hiệu thì trả `unknown`.
Có thể truyền mapping `CardVersion → BaseCardParser` vào factory để thay
strategy. `DataFusion.fuse()`, `FrontRuleExtractor.extract()` và
`BackRuleExtractor.extract(text, mrz_text)` vẫn được giữ để tương thích.

## Xử lý lỗi thường gặp

| Hiện tượng | Kiểm tra / xử lý |
|---|---|
| `NetworkError` / `Failed to fetch` trong Swagger | Kiểm tra tunnel SSH và đúng cột Port remote `8000`; gọi API bằng curl trên máy service để tách lỗi kết nối khỏi inference |
| `/` hoặc `/favicon.ico` trả 404 | Mở `/docs`; ứng dụng không có trang chủ hay favicon |
| Lần đầu OCR chậm, có `Downloading...` | Model đang được tải; theo dõi log và giữ volume cache |
| `Failed...deform_conv_cpu`, `deform_pool_cpu`, thiếu `c++` hoặc `CUDA_HOME` | EasyOCR thử biên dịch extension cũ khi import; repo dùng toán tử `torchvision` thay thế. Chạy script kiểm tra GPU để xác nhận DBNet/VietOCR thực sự đạt |
| Có chữ `cpu` trong log biên dịch | EasyOCR thử nạp extension CPU ngay cả khi dùng GPU; dòng đó không xác định thiết bị inference |
| `success: false` hoặc dữ liệu rỗng | Xem log `OCR unavailable`, lỗi tải model hoặc hết bộ nhớ GPU; HTTP 200 không loại trừ lỗi OCR |
| `mrz_checks` trả `false` | Đối chiếu dữ liệu hai mặt, kiểm tra có gửi đúng hai mặt của cùng một thẻ không |
| Sửa source nhưng container vẫn chạy bản cũ | Chạy `sudo docker compose up -d --build` |
| Docker báo `permission denied` | Dùng `sudo docker ...` nếu user chưa có quyền truy cập Docker |

Không cần chạy `scripts/patch_easyocr_cuda.py` cho Docker hiện tại: pipeline
dùng lớp tương thích [`dbnet_compat.py`](vn_id/ocr/dbnet_compat.py). Script
patch dành cho trường hợp cần biên dịch extension CUDA cũ, không phải bước
cài đặt thông thường của image.

## Kiểm thử và cấu hình

```bash
uv run --with pytest pytest -q
```

Test ảnh thật có thể bỏ qua khi thiếu ảnh hoặc trọng số model; xem điều kiện
trong test và [hướng dẫn chạy](docs/running.md). Script mẫu:

```bash
uv run python test_run.py
```

`test_run.py` mặc định đọc `front_moi_1.jpg` và `back_moi_1.jpg`, có tham số
`--front`, `--back`, `--device`, `--output`.

- [`pyproject.toml`](pyproject.toml): khai báo package và dependency.
- [`uv.lock`](uv.lock): khóa phiên bản dùng cho local với uv và Docker.
- [`compose.yaml`](compose.yaml): GPU, cổng API và volume model.
- [`vn_id/ocr/vgg_seq2seq.yml`](vn_id/ocr/vgg_seq2seq.yml): cấu hình VietOCR;
  thiết bị được ghi đè khi chạy. Local ưu tiên trọng số
  `.easyocr_models/model/vgg_seq2seq.pth` nếu file tồn tại.

## Tài liệu chi tiết

- [Docker, model cache và các kiểm tra đã ghi nhận](docs/docker.md)
- [Cài đặt, chạy và kiểm thử local](docs/running.md)
- [Kiến trúc, luồng dữ liệu và quy tắc hợp nhất](docs/architecture.md)
- [Kết quả rà soát, rủi ro và lộ trình](docs/audit-and-roadmap.md)
