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


def test_missing_residence_does_not_guess_hoa_binh_from_origin():
    text = "Quê quán I Place of origin:\nBình Hưng Hòa Bình Tân"
    assert FrontRuleExtractor.extract_raw(text).get("residence") is None


@pytest.mark.parametrize("label,first_line,second_line,expected", [
    ("Place residence", "Kp Phước Hiệp", "Thị trấn Hiệp Phước, Nhơn Trạch, Đồng Nai",
     "Kp Phước Hiệp, Thị trấn Hiệp Phước, Nhơn Trạch, Đồng Nai"),
    ("I Place ofresidence", "Thôn Trong", "Đông Phú, Lục Nam, Bắc Giang",
     "Thôn Trong, Đông Phú, Lục Nam, Bắc Giang"),
    ("I Place ofresidence:", "Tổ 11", "Sông Bằng, Thành phố Cao Bằng, Cao Bằng",
     "Tổ 11, Sông Bằng, Thành phố Cao Bằng, Cao Bằng"),
])
def test_residence_keeps_value_after_noisy_english_label(label, first_line, second_line, expected):
    text = f"Nơi thường trú {label} {first_line}\n{second_line}\nCó giá trị đến: 01/01/2030"
    assert FrontRuleExtractor.extract_raw(text).get("residence") == expected


def test_residence_normalizes_unambiguous_province_accent_in_final_component():
    text = (
        "Nơi thường trú I Place ofresidence: Tổ 11\n"
        "Sông Bằng, Thành phố Cao Bằng, Cảo Bằng"
    )
    assert FrontRuleExtractor.extract_raw(text).get("residence") == (
        "Tổ 11, Sông Bằng, Thành phố Cao Bằng, Cao Bằng"
    )
