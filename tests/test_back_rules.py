import pytest
from vn_id.parser import BackRuleExtractor as BackSideExtractor

def test_extract_back_side_cccd_2021():
    # Exactly matching user's image snippet
    text = (
        "Ngày, tháng, năm / Date, month, year24/06/2021\n"
        "CỤC TRƯỞNG CỤC CẢNH SÁT\n"
        "QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI\n"
        "DIRECTOR GENERAL OF THE POLICE DEPARTMENT\n"
        "FOR ADMINISTRATIVE MANAGEMENT OF SOCIAL ORDER"
    )
    res = BackSideExtractor.extract(text)
    assert res.card_version == "cccd_chip_2021"
    assert res.issue_date == "24/06/2021"
    assert res.issue_loc == "Cục Cảnh sát Quản lý hành chính về trật tự xã hội"
    assert res.expiry_date is None
    assert not hasattr(res, "identifying_characteristics")

def test_extract_back_side_cccd_2021_with_spaces_and_dot():
    text = (
        "Ngày, tháng, năm / Date, month, year 05-09-2022.\n"
        "CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI"
    )
    res = BackSideExtractor.extract(text)
    assert res.card_version == "cccd_chip_2021"
    assert res.issue_date == "05/09/2022"
    assert res.issue_loc == "Cục Cảnh sát Quản lý hành chính về trật tự xã hội"

def test_extract_back_side_can_cuoc_2024():
    text = (
        "Nơi cư trú / Place of residence: Khu Phố An Thạnh, Xuân Đài, Sông Cầu, Phú Yên\n"
        "Nơi đăng ký khai sinh / Place of birth: Xuân Đài, Sông Cầu, Phú Yên\n"
        "Ngày, tháng, năm cấp: 15/07/2024\n"
        "Ngày, tháng, năm hết hạn: 15/07/2034\n"
        "BỘ CÔNG AN\n"
        "MINISTRY OF PUBLIC SECURITY"
    )
    res = BackSideExtractor.extract(text)
    assert res.card_version == "can_cuoc_2024"
    assert res.issue_date == "15/07/2024"
    assert res.expiry_date == "15/07/2034"
    assert res.issue_loc == "Bộ Công an"
    assert "Khu Phố An Thạnh" in res.residence
    assert "Xuân Đài" in res.origin


def test_extract_back_side_can_cuoc_2024_with_typos():
    text = (
        "Noi cutru Jplace Of residenco 234 Tân Trào\n"
        "Binh Kiến , Tuy Hòa, Phú Yên\n"
        "Nơi dáng ky khai sinh / Place o/ bỉrth\n"
        "Hòa Hiệp Bẳc, Đông Hòa, Phú Yên\n"
        "Ngày thang , nẵm cáp Date ol issue\n"
        "28/10/2024\n"
        "Ngày, tháng, nám hết hạn / Date of expiry:\n"
        "26/11/2036\n"
        "BỘ CÔNG AN /MINISTRY OF PUBLIC SECURITY\n"
    )
    res = BackSideExtractor.extract(text)
    assert res.card_version == "can_cuoc_2024"
    assert res.issue_date == "28/10/2024"
    assert res.expiry_date == "26/11/2036"
    assert res.issue_loc == "Bộ Công an"
    assert "Jplace" not in res.residence
    assert "residenco" not in res.residence
    assert "234 Tân Trào" in res.residence
    assert "Tuy Hòa" in res.residence
    assert "Place" not in res.origin
    assert "bỉrth" not in res.origin
    assert "Hòa Hiệp Bẳc" in res.origin


