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


@pytest.mark.parametrize('header,name', [
    ('SOCULISTREPULLIC TIET NAM', 'PHÙNG THÀNH LUÂN'),
    ('SOCIALIST REPUBLIC OF MET NAM', 'NGUYỄN ANH THƯ'),
])
@pytest.mark.parametrize('separator', ['\n', ' '])
def test_front_name_prefers_full_name_anchor_over_noisy_country_header(header, name, separator):
    text = f'{header}\nHọ và tên I Full name:{separator}{name}\nNgày sinh: 22/11/2008'
    assert FrontRuleExtractor.extract_raw(text).get('name') == name


def test_front_name_does_not_accept_country_header_without_identity():
    assert FrontRuleExtractor.extract_raw('SOCIALIST REPUBLIC OF MET NAM').get('name') is None


def test_origin_uses_value_after_misspelled_english_label():
    text = 'Quê quản / Place of orggin\nSơn Kim 2, Hương Sơn, Hà Tĩnh\nNơi thường trú: Tổ 15'
    assert FrontRuleExtractor.extract_raw(text).get('origin') == 'Sơn Kim 2, Hương Sơn, Hà Tĩnh'


def test_origin_retains_full_address_after_noisy_vietnamese_label():
    text = 'Quố quân I Place d Vonym\nBình Phú Tháng Bịnh, Quảng Nam\nNơi thường trú: La Ngà, Đồng Nai'
    assert FrontRuleExtractor.extract_raw(text).get('origin') == 'Bình Phú Tháng Bịnh, Quảng Nam'


def test_residence_removes_corrupted_english_label_without_removing_value():
    text = 'Nơi thường trú Phace no Tổ 11, Pp 11\nLa Ngà, Định Quán, Đồng Nai'
    assert FrontRuleExtractor.extract_raw(text).get('residence') == 'Tổ 11, Pp 11, La Ngà, Định Quán, Đồng Nai'


def test_origin_empty_label_does_not_use_next_field_as_value():
    text = 'Quê quán / Place of orggin\nNơi thường trú: Tổ 15, Hà Nội'
    assert FrontRuleExtractor.extract_raw(text).get('origin') is None


def test_name_empty_label_does_not_use_birth_header_as_name():
    text = 'Họ và tên / Full name:\nNGÀY SINH: 22/11/2008'
    assert FrontRuleExtractor.extract_raw(text).get('name') is None


def test_address_cleanup_preserves_real_place_names():
    text = 'Quê quán: Bình Phú, Thăng Bình, Quảng Nam\nNơi thường trú: Thôn Bình Phú, Quảng Nam'
    assert FrontRuleExtractor.extract_raw(text).get('origin') == 'Bình Phú, Thăng Bình, Quảng Nam'
    assert FrontRuleExtractor.extract_raw(text).get('residence') == 'Thôn Bình Phú, Quảng Nam'


@pytest.mark.parametrize('text', [
    'Họ và tên\nFull name:\nNGUYỄN ANH THƯ\nNgày sinh: 22/11/2008',
    'Họ và tên / Full name: NGUYỄN ANH THƯ Date of birth: 22/11/2008',
])
def test_name_handles_split_labels_and_stops_at_next_inline_field(text):
    assert FrontRuleExtractor.extract_raw(text).get('name') == 'NGUYỄN ANH THƯ'


@pytest.mark.parametrize('text,field', [
    ('Quố quân I Place d Vonym', 'origin'),
    ('Quê quán / Place of orggin\nCó giá trị đến: 22/11/2033', 'origin'),
    ('Nơi thường trú Phace no\nCó giá trị đến: 22/11/2033', 'residence'),
])
def test_empty_noisy_address_label_does_not_take_other_field(text, field):
    assert FrontRuleExtractor.extract_raw(text).get(field) is None
