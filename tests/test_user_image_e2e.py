import os
import cv2
import pytest
from vn_id.parser import BackRuleExtractor as BackSideExtractor
from vn_id.pipeline import CCCDPipeline
from vn_id.validator.fusion import DataFusion
from vn_id.core.schemas import CardSide

USER_FIXTURE_PATH = "tests/fixtures/user_sample_back.png"


def test_user_fixture_exists_and_loads():
    assert os.path.exists(USER_FIXTURE_PATH)
    img = CCCDPipeline.load_image(USER_FIXTURE_PATH)
    assert img is not None
    assert img.shape[0] > 0 and img.shape[1] > 0


def test_real_user_image_back_side_rules():
    # Đoạn text chính xác từ hình ảnh người dùng đã gửi:
    ocr_text = (
        "Ngày, tháng, năm / Date, month, year24/06/2021\n"
        "CỤC TRƯỞNG CỤC CẢNH SÁT\n"
        "QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI\n"
        "DIRECTOR GENERAL OF THE POLICE DEPARTMENT\n"
        "FOR ADMINISTRATIVE MANAGEMENT OF SOCIAL ORDER"
    )
    res = BackSideExtractor.extract(ocr_text)
    
    # 1. Ngày cấp chính xác 24/06/2021
    assert res.issue_date == "24/06/2021"
    
    # 2. Nơi cấp đã lược bỏ "CỤC TRƯỞNG"
    assert res.issue_loc == "Cục Cảnh sát Quản lý hành chính về trật tự xã hội"
    assert "Cục trưởng" not in res.issue_loc
    assert "CỤC TRƯỞNG" not in res.issue_loc
    
    # 3. Không có trường Đặc điểm nhận dạng
    assert not hasattr(res, "identifying_characteristics")


def test_real_user_back_side_data_fusion():
    ocr_text = (
        "Ngày, tháng, năm / Date, month, year24/06/2021\n"
        "CỤC TRƯỞNG CỤC CẢNH SÁT\n"
        "QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI"
    )
    back_res = BackSideExtractor.extract(ocr_text)
    final = DataFusion.fuse(back=back_res)

    assert final.success is True
    assert final.data.issue_date == "24/06/2021"
    assert final.data.issue_loc == "Cục Cảnh sát Quản lý hành chính về trật tự xã hội"
    assert "back" in final.side_detected

