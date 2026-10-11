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
    ("I Place Tresidence", "Bắc Phượng Sơn", "Xuân Thành, Yên Thành, Nghệ An",
     "Bắc Phượng Sơn, Xuân Thành, Yên Thành, Nghệ An"),
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


@pytest.mark.parametrize("expiry_line,expected", [
    ("Date prepoy 28/05/2034", "28/05/2034"),
    ("Có giá trịch Date of expiry 201/21/01/2029 24/01/2029", "24/01/2029"),
])
def test_front_expiry_uses_valid_date_after_residence_label(expiry_line, expected):
    text = f"Ngày sinh / Date of birth: 24/01/2004\nNơi thường trú: Bắc Giang\n{expiry_line}"
    assert FrontRuleExtractor.extract_raw(text).get("expiry_date") == expected


def test_front_expiry_does_not_reuse_birth_date_without_residence_anchor():
    text = "CĂN CƯỚC CÔNG DÂN\nNgày sinh / Date of birth: 24/01/2004"
    assert FrontRuleExtractor.extract_raw(text).get("expiry_date") is None


def test_front_expiry_does_not_use_unlabelled_or_malformed_date_after_residence():
    text = "Nơi thường trú: Bắc Giang\nHẻm 24/01/2029\nDate of expiry 201/21/01/2029"
    assert FrontRuleExtractor.extract_raw(text).get("expiry_date") is None
