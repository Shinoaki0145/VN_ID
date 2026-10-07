import pytest
from vn_id.parser import FrontRuleExtractor

def test_front_fallback_2024_keywords():
    text = (
        "CĂN CƯỚC\n"
        "Số định danh cá nhân: 001098012345\n"
        "Họ, chữ đệm và tên: NGUYỄN VĂN A\n"
        "Ngày sinh: 15/08/1998\n"
        "Giới tính: Nam\n"
        "Nơi cư trú: Số 1 Đại Cồ Việt, Hai Bà Trưng, Hà Nội\n"
        "Nơi đăng ký khai sinh: Kim Liên, Nam Đàn, Nghệ An"
    )
    res = FrontRuleExtractor.extract_raw(text)
    assert res.get("residence") == "Số 1 Đại Cồ Việt, Hai Bà Trưng, Hà Nội"
    assert res.get("origin") == "Kim Liên, Nam Đàn, Nghệ An"

