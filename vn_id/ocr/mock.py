"""Mock OCR Engine for testing and development."""
from typing import Any
from vn_id.core.schemas import TextBox, OCRResult
from vn_id.ocr.sorter import ReadingOrderSorter


class MockOCREngine:
    """Mock OCR Engine producing realistic CCCD text boxes for front and back sides."""

    def __init__(self):
        self.sorter = ReadingOrderSorter()

    def recognize(self, image: Any = None, is_front: bool = True) -> OCRResult:
        if is_front:
            boxes = [
                TextBox(bbox=[100, 50, 900, 80], text="CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", confidence=0.99),
                TextBox(bbox=[250, 90, 750, 120], text="Độc lập - Tự do - Hạnh phúc", confidence=0.99),
                TextBox(bbox=[300, 140, 700, 180], text="CĂN CƯỚC CÔNG DÂN", confidence=0.98),
                TextBox(bbox=[350, 190, 650, 220], text="Số / No.: 001098012345", confidence=0.99),
                TextBox(bbox=[150, 240, 300, 265], text="Họ và tên:", confidence=0.98),
                TextBox(bbox=[310, 240, 650, 265], text="NGUYỄN VĂN A", confidence=0.97),
                TextBox(bbox=[150, 280, 280, 305], text="Ngày sinh:", confidence=0.98),
                TextBox(bbox=[290, 280, 450, 305], text="15/08/1998", confidence=0.99),
                TextBox(bbox=[500, 280, 600, 305], text="Giới tính:", confidence=0.98),
                TextBox(bbox=[610, 280, 700, 305], text="Nam", confidence=0.99),
                TextBox(bbox=[150, 320, 280, 345], text="Quốc tịch:", confidence=0.98),
                TextBox(bbox=[290, 320, 420, 345], text="Việt Nam", confidence=0.99),
                TextBox(bbox=[150, 360, 300, 385], text="Quê quán:", confidence=0.98),
                TextBox(bbox=[310, 360, 850, 385], text="Kim Liên, Nam Đàn, Nghệ An", confidence=0.96),
                TextBox(bbox=[150, 400, 330, 425], text="Nơi thường trú:", confidence=0.98),
                TextBox(bbox=[340, 400, 900, 425], text="Số 1 Đại Cồ Việt, Bách Khoa, Hai Bà Trưng, Hà Nội", confidence=0.96),
                TextBox(bbox=[150, 450, 350, 475], text="Có giá trị đến:", confidence=0.98),
                TextBox(bbox=[360, 450, 520, 475], text="15/08/2038", confidence=0.99),
            ]
        else:
            boxes = [
                TextBox(bbox=[50, 100, 500, 130], text="Ngày, tháng, năm / Date, month, year", confidence=0.98),
                TextBox(bbox=[510, 100, 700, 130], text="24/06/2021", confidence=0.99),
                TextBox(bbox=[150, 150, 750, 185], text="CỤC TRƯỞNG CỤC CẢNH SÁT", confidence=0.98),
                TextBox(bbox=[100, 195, 800, 230], text="QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI", confidence=0.98),
                TextBox(bbox=[100, 240, 800, 265], text="DIRECTOR GENERAL OF THE POLICE DEPARTMENT", confidence=0.95),
            ]

        res = self.sorter.sort_boxes(boxes)
        res.det_time_ms = 4.0
        res.rec_time_ms = 8.0
        res.sort_time_ms = 1.0
        res.time_taken_ms = 13.0
        return res

