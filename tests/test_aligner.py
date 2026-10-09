import numpy as np
import cv2
import pytest
from pathlib import Path
from vn_id.core.schemas import CardSide
from vn_id.aligner.mock import MockAligner
from vn_id.aligner.detector import CardAligner

def test_mock_aligner():
    dummy_img = np.zeros((600, 800, 3), dtype=np.uint8)
    aligner = MockAligner(side=CardSide.BACK)
    res = aligner.align(dummy_img)
    assert res.is_aligned
    assert res.aligned_image.shape == (630, 1000, 3)
    assert res.side == CardSide.BACK

def test_mock_aligner_front_has_qr_crop():
    dummy_img = np.zeros((600, 800, 3), dtype=np.uint8)
    aligner = MockAligner(side=CardSide.FRONT)
    res = aligner.align(dummy_img)
    assert res.is_aligned
    assert res.side == CardSide.FRONT
    assert res.qr_crop_image is not None
    # QR crop occupies roughly x >= 70% and y <= 35% of 1000x630
    # y: 0 to ~220, x: 700 to 1000
    h, w, _ = res.qr_crop_image.shape
    assert h > 0 and w > 0

def test_card_aligner_fallback_on_unaligned():
    dummy_img = np.zeros((630, 1000, 3), dtype=np.uint8)
    aligner = CardAligner()
    # Test warp with explicit corners
    corners = [(0, 0), (1000, 0), (1000, 630), (0, 630)]
    aligned = aligner.warp_perspective(dummy_img, corners)
    assert aligned.shape == (630, 1000, 3)
    
    qr_crop = aligner.crop_qr_region(aligned)
    assert qr_crop.shape[0] == int(630 * 0.45)
    assert qr_crop.shape[1] == int(1000 * 0.35)


def test_card_aligner_finds_card_inside_portrait_photo():
    image = np.full((1100, 750, 3), 35, dtype=np.uint8)
    corners = np.array([[90, 380], [650, 345], [675, 690], [75, 730]])
    cv2.fillConvexPoly(image, corners, (185, 205, 160))
    result = CardAligner().align(image)
    assert result.is_aligned
    assert np.allclose(result.corners, corners, atol=12)
    assert np.linalg.norm(result.aligned_image[315, 500].astype(float) - [185, 205, 160]) < 3


def test_card_aligner_blank_image_keeps_resize_fallback():
    result = CardAligner().align(np.zeros((1100, 750, 3), dtype=np.uint8))
    assert not result.is_aligned
    assert result.aligned_image.shape == (630, 1000, 3)


@pytest.mark.parametrize("name,date_point", [
    ("back_cu_15.jpg", (350, 75)), ("back_cu_17.jpg", (500, 205)),
])
def test_card_aligner_does_not_crop_issue_date_from_incomplete_security_background(name, date_point):
    path = Path(__file__).resolve().parents[1] / "image" / name
    if not path.is_file():
        pytest.skip(f"Real image fixture missing: {name}")
    result = CardAligner().align(cv2.imread(str(path)))
    if result.is_aligned:
        assert cv2.pointPolygonTest(np.array(result.corners, dtype=np.float32), date_point, False) >= 0
