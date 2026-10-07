import pytest
from vn_id.qr.decoder import QRDecoder
from vn_id.qr.mock import MockQRDecoder

def test_parse_valid_qr_payload():
    # Chuỗi QR chuẩn: Số CCCD | CMND cũ | Họ tên | Ngày sinh | Giới tính | Địa chỉ | Ngày cấp
    payload = "001098012345|012345678|NGUYỄN VĂN A|15081998|Nam|Số 1 Đại Cồ Việt, Hai Bà Trưng, Hà Nội|25052021"
    res = QRDecoder.parse_payload(payload)
    assert res.is_detected
    assert res.id == "001098012345"
    assert res.cmnd_old == "012345678"
    assert res.name == "NGUYỄN VĂN A"
    assert res.dob == "15/08/1998"
    assert res.gender == "Nam"
    assert res.address == "Số 1 Đại Cồ Việt, Hai Bà Trưng, Hà Nội"
    assert res.issue_date == "25/05/2021"

def test_parse_qr_missing_cmnd():
    payload = "001098012345||NGUYỄN VĂN B|01012000|Nữ|Hà Nội|01012022"
    res = QRDecoder.parse_payload(payload)
    assert res.is_detected
    assert res.id == "001098012345"
    assert res.cmnd_old is None
    assert res.name == "NGUYỄN VĂN B"
    assert res.dob == "01/01/2000"

def test_parse_invalid_qr_payload():
    res = QRDecoder.parse_payload("https://example.com/not-cccd-qr")
    assert not res.is_detected
    assert res.id is None

def test_mock_qr_decoder():
    decoder = MockQRDecoder(is_detected=True)
    res = decoder.decode(None)
    assert res.is_detected
    assert res.id == "001098012345"
    assert res.name == "NGUYỄN VĂN A"

def test_qr_decoder_real_image():
    import os
    import cv2
    img_path = "image/front_cu.jpg"
    if os.path.exists(img_path):
        img = cv2.imread(img_path)
        decoder = QRDecoder()
        res = decoder.decode(img)
        assert res.is_detected
        assert res.id == "054205010560"
        assert "Thiện Nhân" in res.name


