import pytest
from vn_id.validator.cccd_rules import CCCDValidator

def test_cccd_12_digits_validation_valid():
    # 001: Hà Nội, 0: Nam 1900-1999, 98: 1998
    rep = CCCDValidator.validate_12_digits("001098012345", dob="15/08/1998", gender="Nam")
    assert rep.is_valid_12_digits
    assert rep.province_valid
    assert rep.gender_century_valid
    assert rep.birth_year_valid
    assert len(rep.warnings) == 0

def test_cccd_12_digits_validation_century_21():
    # 079: TP.HCM, 3: Nữ 2000-2099, 05: 2005
    rep = CCCDValidator.validate_12_digits("079305099999", dob="10/10/2005", gender="Nữ")
    assert rep.is_valid_12_digits
    assert rep.province_valid
    assert rep.gender_century_valid
    assert rep.birth_year_valid

def test_cccd_12_digits_invalid_length_or_digits():
    rep = CCCDValidator.validate_12_digits("00109801234")  # 11 digits
    assert not rep.is_valid_12_digits
    assert "Độ dài số CCCD không hợp lệ" in rep.warnings[0]

def test_cccd_12_digits_invalid_province():
    rep = CCCDValidator.validate_12_digits("999098012345")  # 999 is not a valid province
    assert rep.is_valid_12_digits
    assert not rep.province_valid
    assert any("Mã tỉnh" in w for w in rep.warnings)

def test_cccd_12_digits_mismatched_birth_year():
    rep = CCCDValidator.validate_12_digits("001098012345", dob="15/08/1999", gender="Nam")
    assert not rep.birth_year_valid
    assert any("năm sinh" in w for w in rep.warnings)

