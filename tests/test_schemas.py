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
    assert len(PROVINCE_CODES) == 63

def test_gender_century_map():
    # 20th century (1900-1999)
    assert GENDER_CENTURY_MAP[1900]["Nam"] == 0
    assert GENDER_CENTURY_MAP[1900]["Nữ"] == 1
    # 21st century (2000-2099)
    assert GENDER_CENTURY_MAP[2000]["Nam"] == 2
    assert GENDER_CENTURY_MAP[2000]["Nữ"] == 3

