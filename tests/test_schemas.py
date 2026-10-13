import pytest
from vn_id.core.schemas import (
    CardSide, AlignedCardResult, BackSideResult, 
    CCCDData, FinalCCCDResult, ValidationReport
)
from vn_id.core import PROVINCE_CODES, CENTURY_GENDER_TO_INFO

def test_schemas_validation():
    back_res = BackSideResult(
        card_version="can_cuoc_cong_dan_2021",
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
    assert len(PROVINCE_CODES) == 63

def test_century_gender_to_info():
    # 20th century (1900-1999)
    assert CENTURY_GENDER_TO_INFO[0] == (1900, "Nam")
    assert CENTURY_GENDER_TO_INFO[1] == (1900, "Nữ")
    # 21st century (2000-2099)
    assert CENTURY_GENDER_TO_INFO[2] == (2000, "Nam")
    assert CENTURY_GENDER_TO_INFO[3] == (2000, "Nữ")

