import numpy as np
import pytest
from vn_id.pipeline import CCCDPipeline
from vn_id.core.schemas import CardSide

def test_pipeline_mock_both_sides():
    dummy_front = np.zeros((600, 800, 3), dtype=np.uint8)
    dummy_back = np.zeros((600, 800, 3), dtype=np.uint8)
    
    pipeline = CCCDPipeline(mock_mode=True)
    res = pipeline.process_both_sides(front_image=dummy_front, back_image=dummy_back)
    
    assert res.success
    assert "front" in res.side_detected
    assert "back" in res.side_detected
    assert res.data.id == "001098012345"
    assert res.data.name == "NGUYỄN VĂN A"
    assert res.data.issue_date == "24/06/2021"
    assert res.data.issue_loc == "Cục Cảnh sát Quản lý hành chính về trật tự xã hội"
    assert res.validation.is_valid_12_digits
    # Check detailed OCR breakdown timings
    assert "front_ocr_det_ms" in res.timings
    assert "front_ocr_rec_ms" in res.timings
    assert "front_ocr_sort_ms" in res.timings
    assert "back_ocr_det_ms" in res.timings
    assert "back_ocr_rec_ms" in res.timings
    assert "back_ocr_sort_ms" in res.timings
    assert "total_ms" in res.timings

def test_pipeline_mock_single_front():
    dummy_front = np.zeros((600, 800, 3), dtype=np.uint8)
    pipeline = CCCDPipeline(mock_mode=True)
    res = pipeline.process(dummy_front, force_side=CardSide.FRONT)
    assert res.success
    assert "front" in res.side_detected
    assert res.data.name == "NGUYỄN VĂN A"
    assert "ocr_det_ms" in res.timings
    assert "ocr_rec_ms" in res.timings
    assert "ocr_sort_ms" in res.timings

def test_pipeline_mock_single_back():
    dummy_back = np.zeros((600, 800, 3), dtype=np.uint8)
    pipeline = CCCDPipeline(mock_mode=True)
    res = pipeline.process(dummy_back, force_side=CardSide.BACK)
    assert res.success
    assert "back" in res.side_detected
    assert res.data.issue_date == "24/06/2021"
    assert res.data.issue_loc == "Cục Cảnh sát Quản lý hành chính về trật tự xã hội"
    assert "ocr_det_ms" in res.timings
    assert "ocr_rec_ms" in res.timings
    assert "ocr_sort_ms" in res.timings

