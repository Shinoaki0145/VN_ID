import numpy as np
import pytest
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

