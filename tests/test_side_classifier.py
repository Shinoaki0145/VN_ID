import pytest
from vn_id.core.schemas import CardSide
from vn_id.aligner.classifier import SideClassifier

def test_side_classifier_by_text():
    front_text = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nCĂN CƯỚC CÔNG DÂN\nSố / No.: 001098012345\nHọ và tên: NGUYỄN VĂN A"
    back_text = "Ngày, tháng, năm / Date, month, year 24/06/2021\nCỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI"
    can_cuoc_2024_front = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nCĂN CƯỚC\nSố định danh cá nhân: 001098012345\nNơi cư trú: Hà Nội"
    can_cuoc_2024_back = "Ngày, tháng, năm cấp: 10/07/2024\nNgày, tháng, năm hết hạn: 10/07/2034\nBỘ CÔNG AN"

    assert SideClassifier.classify_text(front_text) == CardSide.FRONT
    assert SideClassifier.classify_text(back_text) == CardSide.BACK
    assert SideClassifier.classify_text(can_cuoc_2024_front) == CardSide.FRONT
    assert SideClassifier.classify_text(can_cuoc_2024_back) == CardSide.BACK

def test_side_classifier_unknown():
    assert SideClassifier.classify_text("Phong cảnh thiên nhiên Việt Nam") == CardSide.UNKNOWN

