import pytest
from vn_id.core.schemas import TextBox
from vn_id.ocr.sorter import ReadingOrderSorter
from vn_id.ocr.mock import MockOCREngine

def test_reading_order_sorter():
    # 2 dòng với các boxes bị đảo lộn
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
    assert len(sorted_res.boxes) == 4
    assert sorted_res.boxes[0].line_number == 1
    assert sorted_res.boxes[1].line_number == 1
    assert sorted_res.boxes[2].line_number == 2
    assert sorted_res.boxes[3].line_number == 2

def test_mock_ocr_engine():
    mock_ocr = MockOCREngine()
    res = mock_ocr.recognize(image=None, is_front=True)
    assert len(res.boxes) > 0
    assert "CĂN CƯỚC" in res.full_text or "Họ và tên" in res.full_text

    back_res = mock_ocr.recognize(image=None, is_front=False)
    assert "Ngày, tháng, năm" in back_res.full_text
    assert "CỤC TRƯỞNG CỤC CẢNH SÁT" in back_res.full_text
    assert "QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" in back_res.full_text
