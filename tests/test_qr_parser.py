from pathlib import Path
from types import SimpleNamespace
import sys

import cv2
import numpy as np
import pytest
from vn_id.qr.decoder import QRDecoder
from vn_id.qr.mock import MockQRDecoder


@pytest.mark.parametrize("fails", [False, True])
def test_decode_uses_only_qreader(monkeypatch, fails):
    payload = "001098012345||NGUYỄN VĂN A|15081998|Nam|Hà Nội|25052021"
    monkeypatch.setitem(sys.modules, "zxingcpp", SimpleNamespace(
        read_barcodes=lambda image: [SimpleNamespace(text=payload)],
    ))

    def detect_and_decode(**kwargs):
        if fails:
            raise RuntimeError("QReader unavailable")
        return ()

    decoder = QRDecoder()
    decoder._qreader = SimpleNamespace(detect_and_decode=detect_and_decode)

    assert not decoder.decode(np.zeros((32, 32, 3), dtype=np.uint8)).is_detected


@pytest.mark.parametrize("shape", [(64, 64), (64, 64, 3), (64, 64, 4)])
def test_mask_qr_regions_preserves_input_and_text(shape):
    image = np.full(shape, 17, dtype=np.uint8)
    original = image.copy()
    decoder = QRDecoder()
    decoder._qreader = SimpleNamespace(detect=lambda **kwargs: ({
        "quad_xy": np.array([[20, 20], [40, 20], [40, 40], [20, 40]], dtype=float),
    },))

    masked = decoder.mask_qr_regions(image)

    expected = original.copy()
    expected[20:41, 20:41] = 255
    np.testing.assert_array_equal(masked, expected)
    np.testing.assert_array_equal(image, original)
    assert masked.shape == image.shape
    assert masked.dtype == image.dtype
    assert not np.shares_memory(masked, image)


@pytest.mark.parametrize("fails", [False, True])
def test_mask_qr_regions_without_detection_or_on_failure(fails):
    def detect(**kwargs):
        if fails:
            raise RuntimeError("QR detector unavailable")
        return ()

    image = np.full((64, 64, 3), 17, dtype=np.uint8)
    decoder = QRDecoder()
    decoder._qreader = SimpleNamespace(detect=detect)

    masked = decoder.mask_qr_regions(image)

    np.testing.assert_array_equal(masked, image)
    assert not np.shares_memory(masked, image)


def test_mask_qr_regions_clips_rotated_polygon():
    image = np.zeros((64, 64, 3), dtype=np.uint8)
    decoder = QRDecoder()
    decoder._qreader = SimpleNamespace(detect=lambda **kwargs: ({
        "quad_xy": np.array([[-4, 10], [10, -4], [24, 10], [10, 24]], dtype=float),
    },))

    masked = decoder.mask_qr_regions(image)

    assert np.all(masked[10, 10] == 255)
    assert np.all(masked[8, 0] == 255)
    assert np.all(masked[0, 8] == 255)
    assert np.all(masked[0, 0] == 0)  # Outside the rotated QR, inside its rectangle.
    assert np.all(masked[40, 40] == 0)
    assert not image.any()


@pytest.mark.parametrize("decoded_name, expected_name", [
    ("B羅i Xu璽n Thu廕要", "Bùi Xuân Thuận"),
    ("Bﾃｹi Huy Tuy盻ハ", "Bùi Huy Tuyển"),
    ("N繫ng Tr廕吵 Huy", "Nông Trần Huy"),
    ("Huỳnh Thị Thanh Hiền", "Huỳnh Thị Thanh Hiền"),
])
def test_qreader_restores_vietnamese_payload(monkeypatch, decoded_name, expected_name):
    pytest.importorskip("qreader")
    decoder = QRDecoder()
    reader = decoder._get_qreader()
    payload = f"001098012345||{decoded_name}|15081998|Nam|Hà Nội|25052021"
    # Keep QReader's real text decoding; stub image detection and zbar's byte output.
    monkeypatch.setattr(reader, "detect", lambda **kwargs: ({},))
    monkeypatch.setattr(reader, "_decode_qr_zbar", lambda **kwargs: [
        SimpleNamespace(result=SimpleNamespace(data=payload.encode("utf-8")))
    ])

    result = decoder.decode(np.zeros((32, 32, 3), dtype=np.uint8))

    assert result.is_detected
    assert result.name == expected_name
    assert result.address == "Hà Nội"


@pytest.mark.parametrize("image_name, expected_name, expected_address", [
    ("front_cu_4.jpg", "Bùi Xuân Thuận", "Tổ 10, Kp Phước Hiệp, Hiệp Phước, Nhơn Trạch, Đồng Nai"),
    ("front_cu_6.jpg", "Bùi Huy Tuyển", "Thôn Trong, Đông Phú, Lục Nam, Bắc Giang"),
    ("front_cu_7.jpg", "Nông Trần Huy", "Tổ 11, Sông Bằng, Thành phố Cao Bằng, Cao Bằng"),
])
def test_qr_decoder_vietnamese_images(image_name, expected_name, expected_address):
    pytest.importorskip("qreader")
    path = Path(__file__).resolve().parents[1] / "image" / image_name
    if not path.exists():
        pytest.skip(f"Image fixture missing: {image_name}")

    result = QRDecoder().decode(cv2.imread(str(path)))

    assert result.is_detected
    assert result.name == expected_name
    assert result.address == expected_address

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
