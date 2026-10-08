import os
from pathlib import Path
import cv2
import pytest
from vn_id.parser import BackRuleExtractor as BackSideExtractor
from vn_id.pipeline import CCCDPipeline
from vn_id.validator.fusion import DataFusion
from vn_id.core.schemas import CardSide
from vn_id.core.config import EASYOCR_STORAGE_DIR, QR_WEIGHTS_DIR, VIETOCR_WEIGHTS_PATH

USER_FIXTURE_PATH = "tests/fixtures/user_sample_back.png"


@pytest.fixture(scope="module")
def real_pipeline():
    torch = pytest.importorskip("torch")
    pytest.importorskip("easyocr")
    pytest.importorskip("vietocr")
    pytest.importorskip("qreader")
    for weights in (
        EASYOCR_STORAGE_DIR / "pretrained_ic15_res18.pt",
        VIETOCR_WEIGHTS_PATH,
        QR_WEIGHTS_DIR / "qrdet-s.pt",
    ):
        if not weights.is_file():
            pytest.skip(f"Real OCR weights missing: {weights.name}")
    original_threads = torch.get_num_threads()
    torch.set_num_threads(min(original_threads, 4))
    try:
        yield CCCDPipeline(device="cpu")
    finally:
        torch.set_num_threads(original_threads)


def real_image_path(name):
    path = Path(__file__).resolve().parents[1] / "image" / name
    if not path.is_file():
        pytest.skip(f"Real image fixture missing: {name}")
    return str(path)


def test_can_cuoc_2024_origin_keeps_ward_and_district_numbers(real_pipeline):
    image = CCCDPipeline.load_image(real_image_path("back_moi_1.jpg"))
    aligned = real_pipeline.aligner.align(image).aligned_image

    ocr = real_pipeline.ocr_engine.recognize(aligned, is_front=False)
    result = BackSideExtractor.extract(ocr.full_text)

    assert result.origin == "Phường 7, Quận 8, TP. Hồ Chí Minh"
    assert result.issue_date == "18/11/2024"
    assert result.expiry_date == "14/09/2043"
    assert all(box.text != "ALLE" for box in ocr.boxes)


def test_can_cuoc_2024_both_sides_origin(real_pipeline):
    result = real_pipeline.process_both_sides(
        real_image_path("front_moi_1.jpg"), real_image_path("back_moi_1.jpg"),
    )

    assert result.data.origin == "Phường 7, Quận 8, TP. Hồ Chí Minh"
    assert result.field_sources["origin"] == "back_rules"
    assert result.data.id == "079183034888"
    assert result.data.name == "Huỳnh Thị Thanh Hiền"
    assert result.data.issue_date == "18/11/2024"
    assert result.data.expiry_date == "14/09/2043"


def test_cccd_2021_back_preserves_issuer(real_pipeline):
    image = CCCDPipeline.load_image(real_image_path("back_cu_7.jpg"))
    aligned = real_pipeline.aligner.align(image).aligned_image

    ocr = real_pipeline.ocr_engine.recognize(aligned, is_front=False)
    result = BackSideExtractor.extract(ocr.full_text)

    assert result.card_version == "cccd_chip_2021"
    assert result.issue_loc == "Cục Cảnh sát Quản lý hành chính về trật tự xã hội"
    assert result.expiry_date == "01/01/2033"


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
