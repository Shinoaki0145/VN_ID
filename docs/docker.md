# Docker với GPU NVIDIA

Image cài Python 3.12 và dependency đúng `uv.lock`, bao gồm PyTorch/CUDA. Build
không cần GPU. Chạy GPU cần máy có NVIDIA driver tương thích với CUDA của
PyTorch và Docker Engine đã cấu hình NVIDIA Container Toolkit. Docker Desktop
trên Linux không hỗ trợ GPU passthrough; dùng Docker Engine trên máy GPU.

DBNet dùng toán tử deformable convolution của `torchvision` thông qua lớp tương
thích trong repo. Không cần sửa EasyOCR trong `site-packages` hoặc cài compiler
để inference. Image GPU khá lớn do giữ nguyên bộ dependency CUDA đã khóa.

Tham khảo [GPU trong Docker Engine](https://docs.docker.com/engine/containers/gpu/)
và [GPU trong Docker Desktop](https://docs.docker.com/desktop/features/gpu/).

## Build và chạy

```bash
docker build -t vn-id:0.1.0-gpu .
docker compose up -d
docker compose logs -f vn-id
```

Compose cấp tất cả GPU và kiểm tra CUDA lúc khởi động. Nếu không thấy GPU,
service dừng thay vì âm thầm chạy CPU. API dùng một worker, bind cổng máy chủ
ở `127.0.0.1:8000`. Kiểm tra GPU trước khi gửi ảnh:

```bash
docker compose exec vn-id python -c 'import torch; assert torch.cuda.is_available(); print(torch.__version__, torch.version.cuda, torch.cuda.get_device_name(0))'
curl --fail http://127.0.0.1:8000/health
curl --fail -F "file=@image/front_cu_10.png" http://127.0.0.1:8000/api/v1/extract
```

`/health` cần trả `device: cuda` trên máy GPU, nhưng chưa xác nhận model đã tải.
Kiểm tra kết quả trích xuất và log sau request ảnh thật; model lỗi hiện có thể
trả dữ liệu rỗng. Một worker vẫn có thể xử lý nhiều request đồng thời; chưa có
giới hạn inference hoặc đảm bảo an toàn tải đồng thời của model trong ứng dụng.

## Trọng số và dữ liệu

Image chạy bằng user không phải root. Volume `model-cache` lưu cache tại
`/home/app/.cache`, gồm model OCR/QR, cache PyTorch và trọng số VietOCR tải qua
thư mục tạm. Request đầu tiên cần mạng và có thể chậm do tải model.

`.dockerignore` chỉ cho phép source package và metadata cài đặt vào build:
ảnh CCCD, JSON kết quả, notebook, `.venv` và model local không nằm trong image.
Image không bao gồm trọng số, nên chưa phải bản chạy ngoại tuyến ngay sau build.

Nếu muốn dùng trọng số local đang có trong repo, sau khi service khởi động và
trước request đầu:

```bash
docker compose cp .easyocr_models/model/. vn-id:/home/app/.cache/vn_id/.easyocr_models/model/
docker compose cp .models/qrdet/. vn-id:/home/app/.cache/vn_id/.models/qrdet/
docker compose exec --user root vn-id chown -R app:app /home/app/.cache
```

Trọng số được tải ngoài lockfile, chưa có manifest checksum riêng. Giữ volume
để tái sử dụng; `docker compose down` giữ volume, `down -v` xóa cache.

## Kiểm tra container bằng CPU

Cùng image có thể kiểm tra bằng CPU trên máy không có GPU. Lệnh này bỏ qua
Compose vì Compose yêu cầu NVIDIA GPU:

```bash
docker run --rm -p 127.0.0.1:8000:8000 \
  -v vn-id-model-cache:/home/app/.cache vn-id:0.1.0-gpu
```

CPU smoke test không thay thế kiểm thử inference CUDA. Các vấn đề OCR mặt
trước đã ghi nhận trong review vẫn cần kiểm thử thêm với ảnh biến thể.

## Kết quả kiểm tra ngày 13/10/2026

- `uv lock --check` đạt; môi trường local đã đồng bộ dependency theo lock.
- Toàn bộ test sau bổ sung lớp tương thích DBNet: **194 passed, 3 skipped,
  1 xfailed**. Skip do thiếu `front_cu.jpg` (hai test) và
  `front_cu_1_crop.jpg` (một test). Xfail là dấu địa chỉ mẫu 9 chưa đọc chính xác.
- Build `vn-id:0.1.0-gpu` thành công trên linux/amd64; khoảng 10.2 GB theo
  Docker image inspect. PyTorch `2.14.1+cu130`, CUDA bundle `13.0`.
- Container sạch chạy bằng user `app`, không có compiler: health đạt, upload
  hỏng trả 400, API đọc đúng sáu trường ID/tên/DOB/quê quán/nơi thường trú/
  hết hạn của `front_cu_10.png` và `front_cu_11.png`.
- API hai mặt mẫu 2024 đạt ID, quê quán, ngày cấp và ngày hết hạn. OCR-only
  mẫu 10, tắt QR, cũng đạt đủ sáu trường trên.
- Model local được đưa vào volume để kiểm tra; chưa nghiệm thu tải toàn bộ
  trọng số từ cache rỗng hoặc chạy ngoại tuyến từ image mới.
- Chưa nghiệm thu GPU: máy kiểm tra không có NVIDIA GPU/runtime khả dụng.
  Cần chạy các lệnh kiểm tra CUDA và request ảnh thật ở máy đích.

EasyOCR vẫn có thể in cảnh báo về extension C++ cũ lúc import. DBNet trong
pipeline sử dụng toán tử `torchvision` sau bước khởi tạo; các phép kiểm tra
ảnh thật ở trên xác nhận đường này hoạt động dù extension custom không có.

### Bổ sung nhận diện phiên bản mặt trước

Đã hỗ trợ tiêu đề OCR bị cắt còn `CĂN CƯỚC CÔNG` khi đi kèm dấu hiệu bố cục
2021 (`Quê quán`, `Nơi thường trú` hoặc `Có giá trị đến`). Không có bằng chứng
bố cục thì vẫn trả `unknown`. Kiểm thử sau sửa: **200 passed, 3 skipped,
1 xfailed**; kiểm tra API trong image mới xác nhận `front_cu_10.png` và
`front_cu_11.png` trả `card_version: can_cuoc_cong_dan_2021` và giữ đúng sáu
trường dữ liệu đã kiểm tra.
