# Kế hoạch & Ý tưởng Triển khai: Pipeline Trích xuất CCCD Đa Định dạng

## 1. Ý tưởng Cốt lõi (Core Concept)

Thay vì đi theo lối mòn **Top-down (YOLO crop từng ô thông tin)** vốn rất dễ gãy khi nhà nước đổi mẫu thẻ, hệ thống chuyển sang kiến trúc **Bottom-up Hybrid**:

* **Thị giác (Vision):** Chỉ làm nhiệm vụ cơ bản là nắn phẳng thẻ và gom toàn bộ chữ có trên mặt thẻ mà không cần quan tâm chữ đó nằm ở đâu hay thuộc trường nào.
* **Ngôn ngữ (NLP):** Đọc hiểu ngữ nghĩa chuỗi text thu được để tự phân loại xem đâu là Họ tên, đâu là Địa chỉ, Ngày sinh.
* **Vật lý (QR Decoding):** Tận dụng mã QR có sẵn trên thẻ làm chốt chặn kiểm tra chéo (Ground Truth). Nếu đọc được QR, toàn bộ lỗi sai dấu hay nhầm chữ số của OCR đều bị triệt tiêu hoàn toàn.

---

## 2. Thiết kế Kiến trúc Pipeline (5 Chặng)

```text
[Ảnh CCCD đầu vào]
        │
        ▼
[Chặng 1: Nắn phẳng] ────────► YOLOv8 Detect 4 góc + Perspective Transform
        │
        ├────────────────────────────────────┐
        ▼                                    ▼
[Chặng 2: Gom chữ toàn bộ]           [Chặng 4: Đọc mã QR]
  • DBNet: Quét tìm tất cả các box     • QReader: Giải mã trực tiếp chuỗi
  • Sắp xếp toạ độ: Trái->Phải,        • Tách các trường qua delimiter "|"
    Trên->Dưới
  • VietOCR: Đọc text có dấu
        │                                    │
        ▼                                    │
[Chặng 3: Hiểu ngữ nghĩa]                    │
  • PhoBERT-NER: Bóc tách thực thể           │
  • Rule bổ trợ: Bắt từ khóa mới             │
    ("Nơi cư trú", "Khai sinh")              │
        │                                    │
        └─────────────────┬──────────────────┘
                          ▼
[Chặng 5: Hợp nhất & Đối soát]
  • Ưu tiên dữ liệu QR > Dữ liệu OCR/NER
  • Kiểm tra logic 12 số CCCD (Mã tỉnh, Giới tính, Năm sinh)
  • Fuzzy match chuẩn hóa địa chỉ hành chính
        │
        ▼
[JSON Kết quả cuối cùng]

```

---

## 3. Các Bước Triển khai Chi tiết

### Chặng 1: Chuẩn hóa Góc nhìn (Card Alignment)

* **Mục tiêu:** Đưa ảnh thẻ chụp nghiêng, méo, lóa nền về một tấm ảnh chữ nhật phẳng, chuẩn kích thước tỷ lệ ID-1 ($1000 \times 630\text{ px}$).
* **Cách làm:**
* Dùng **YOLOv8-pose** hoặc **YOLOv8-detect** (pretrained weights) tìm 4 điểm góc của thẻ (`top-left`, `top-right`, `bottom-right`, `bottom-left`).
* Áp dụng `cv2.getPerspectiveTransform` và `cv2.warpPerspective` để nắn thẳng ảnh thẻ.
* Tách riêng 1 bản crop nhỏ góc trên bên phải ($x \ge 70\%$, $y \le 35\%$) để phục vụ riêng cho việc quét QR.



### Chặng 2: Trích xuất Chữ & Xử lý Toạ độ (OCR Engine)

* **Bước 2.1: Quét vùng chữ (DBNet):**
* Quét toàn bộ bề mặt thẻ để lấy danh sách bounding box chứa chữ.
* *Mẹo xử lý:* Padding mở rộng mỗi box thêm khoảng $8-10\%$ theo trục dọc để tránh cắt mất dấu hỏi, ngã, nặng của tiếng Việt.


* **Bước 2.2: Sắp xếp thứ tự đọc (Reading Order Sort):**
* DBNet trả về danh sách box không theo thứ tự đọc tự nhiên.
* Chia nhóm dòng theo toạ độ $y$ (các box có khoảng cách $y$ chênh lệch nhau dưới 15-20px thì coi là cùng 1 dòng), sau đó sort theo $x$ tăng dần.
* Ghép các box lại theo đúng thứ tự từ trên xuống dưới, từ trái sang phải.


* **Bước 2.3: Đọc text (VietOCR):**
* Cắt ảnh theo từng box đã sort, gom thành 1 batch và đẩy vào VietOCR (`vgg_transformer` hoặc `mobilenet_v3`).
* Kết quả thu được là một đoạn văn bản thô hoàn chỉnh của toàn bộ thẻ.



### Chặng 3: Bóc tách Thực thể (KIE / Semantic Mapping)

* **Xử lý bằng `ngocthanhdoan/phobert-cccd-ner`:**
* Đưa đoạn text đã ghép vào model NER để nhận diện các nhãn: `ID`, `NAME`, `DOB`, `GENDER`, `QUE_QUAN`, `NOI_THUONG_TRU`.


* **Xử lý Fallback cho Thẻ Căn cước mới (Luật 2024):**
* Thẻ mới đổi *"Quê quán"* $\rightarrow$ *"Nơi đăng ký khai sinh"*, *"Nơi thường trú"* $\rightarrow$ *"Nơi cư trú"*.
* Viết một lớp rule đơn giản: Nếu PhoBERT trả về rỗng ở trường địa chỉ, quét chuỗi tìm từ khóa neo `"Nơi cư trú"` hoặc `"Nơi đăng ký khai sinh"`, lấy toàn bộ phần text nằm phía sau làm giá trị.



### Chặng 4: Đọc mã QR (QReader / Ground Truth)

* **Cách làm:**
* Đưa vùng ảnh góc trên bên phải vào `QReader`.
* Tăng độ tương phản (Contrast/CLAHE) nếu ảnh bị bóng mờ do lớp nhựa thẻ.
* Chuỗi QR CCCD gắn chip trả về có dạng:

$$\text{Số CCCD} \mid \text{Số CMND cũ} \mid \text{Họ tên} \mid \text{Ngày sinh} \mid \text{Giới tính} \mid \text{Địa chỉ} \mid \text{Ngày cấp}$$


* Tách chuỗi theo ký tự `|` để lấy thông tin dạng số hóa tuyệt đối chính xác.



### Chặng 5: Hợp nhất Dữ liệu & Kiểm tra Logic (Validation)

* **Quy tắc ưu tiên (Priority Rule):**
* Nếu QR decode thành công $\rightarrow$ Ghi đè các trường `ID`, `Họ tên`, `Ngày sinh`, `Giới tính`, `Địa chỉ` từ QR vào kết quả cuối.
* Nếu QR bị xước/mờ/không đọc được $\rightarrow$ Lấy kết quả từ chặng OCR + PhoBERT-NER.


* **Đối soát chéo 12 số CCCD:**
* 3 số đầu: Đối chiếu mã tỉnh thành.
* Số thứ 4: So khớp thế kỷ và giới tính với trường Giới tính.
* 2 số tiếp theo: So khớp 2 số cuối năm sinh với trường Ngày sinh.


* **Chuẩn hóa địa chỉ:**
* Sử dụng thuật toán so khớp mờ (Fuzzy matching) đối chiếu chuỗi địa chỉ đọc được với danh mục hành chính (Tỉnh/Thành, Quận/Huyện, Xã/Phường) để tự động sửa các lỗi nhầm dấu.



---

## 4. Ưu điểm Cốt lõi của Hướng Triển khai Này

1. **Không phụ thuộc toạ độ:** Bất kể CMND cũ, CCCD 2021 hay thẻ Căn cước mới thay đổi vị trí các dòng chữ, pipeline vẫn bắt được toàn bộ text và phân loại bằng ngữ nghĩa.
2. **Không cần huấn luyện lại từ đầu:** Cả 4 thành phần (YOLOv8, DBNet, VietOCR, PhoBERT-NER) đều tận dụng checkpoint mã nguồn mở sẵn có.
3. **Độ tin cậy tối đa:** Nhờ có bước giải mã QR làm ground-truth, các trường quan trọng nhất (Số định danh, Họ tên, Ngày sinh) đạt độ chính xác gần như $100\%$ khi chất lượng ảnh ở mức cơ bản.