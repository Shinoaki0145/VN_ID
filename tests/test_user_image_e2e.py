import os
from pathlib import Path
from types import SimpleNamespace
import cv2
import pytest
from vn_id.parser import BackRuleExtractor as BackSideExtractor, FrontRuleExtractor
from vn_id.pipeline import CCCDPipeline
from vn_id.validator.fusion import DataFusion
from vn_id.core.schemas import CardSide
from vn_id.core.config import EASYOCR_STORAGE_DIR, QR_WEIGHTS_DIR, VIETOCR_WEIGHTS_PATH
from vn_id.ocr import OCREngine
from vn_id.aligner.detector import CardAligner

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


@pytest.fixture
def ocr_only_engine():
    torch = pytest.importorskip("torch")
    pytest.importorskip("easyocr")
    pytest.importorskip("vietocr")
    for weight in (EASYOCR_STORAGE_DIR / "pretrained_ic15_res18.pt", VIETOCR_WEIGHTS_PATH):
        if not weight.is_file():
            pytest.skip(f"Real OCR weights missing: {weight.name}")
    original_threads = torch.get_num_threads()
    torch.set_num_threads(min(original_threads, 4))
    try:
        yield OCREngine(device="cpu", qr_decoder=SimpleNamespace(mask_qr_regions=lambda image: image))
    finally:
        torch.set_num_threads(original_threads)


def test_front_cu_5_ocr_reads_both_addresses(ocr_only_engine):
    image = CCCDPipeline.load_image(real_image_path("front_cu_5.jpg"))
    aligned = CardAligner().align(image).aligned_image
    ocr = ocr_only_engine.recognize(aligned, is_front=True)
    front = FrontRuleExtractor.extract(ocr.full_text)

    assert front.origin == "Bình Hưng Hòa A, Bình Tân, TP. Hồ Chí Minh"
    assert front.residence == "24/12/29 LK 2-10, Kp 18, Bình Hưng Hòa A, Bình Tân, TP.HCM"
    assert front.expiry_date == "28/05/2034"
    assert front.extraction_source == "front_rules"


@pytest.mark.parametrize("name,origin,residence,expiry", [
    ("front_cu.jpg", "Hòa Hiệp Bắc, Thị xã Đông Hòa, Phú Yên",
     "234 Tân Trào, Bình Kiến, Thành phố Tuy Hoà, Phú Yên", "10/04/2030"),
    ("front_cu_4.jpg", "Thị trấn Hiệp Phước, Nhơn Trạch, Đồng Nai",
     "Kp Phước Hiệp, Thị trấn Hiệp Phước, Nhơn Trạch, Đồng Nai", "29/03/2037"),
    ("front_cu_6.jpg", "Đông Phú, Lục Nam, Bắc Giang",
     "Thôn Trong, Đông Phú, Lục Nam, Bắc Giang", "24/01/2029"),
])
def test_front_address_recovery_preserves_clean_cards(ocr_only_engine, name, origin, residence, expiry):
    image = CCCDPipeline.load_image(real_image_path(name))
    aligned = CardAligner().align(image).aligned_image
    front = FrontRuleExtractor.extract(ocr_only_engine.recognize(aligned, is_front=True).full_text)
    assert front.origin == origin
    if residence is not None:
        assert front.residence == residence
    assert front.expiry_date == expiry


def test_front_cu_7_recovers_residence_from_ocr_only(ocr_only_engine):
    image = CCCDPipeline.load_image(real_image_path("front_cu_7.jpg"))
    aligned = CardAligner().align(image).aligned_image
    front = FrontRuleExtractor.extract(ocr_only_engine.recognize(aligned, is_front=True).full_text)

    assert front.origin == "Minh Tâm, Nguyên Bình, Cao Bằng"
    assert front.residence == "Tổ 11, Sông Bằng, Thành phố Cao Bằng, Cao Bằng"
    assert front.expiry_date == "13/12/2023"


def test_front_cu_1_crop_reads_both_addresses_from_ocr_only(ocr_only_engine):
    image = CCCDPipeline.load_image(real_image_path("front_cu_1_crop.jpg"))
    aligned = CardAligner().align(image).aligned_image
    front = FrontRuleExtractor.extract(ocr_only_engine.recognize(aligned, is_front=True).full_text)

    assert front.id == "040098020586"
    assert front.name == "LÊ VĂN HOÀNG"
    assert front.dob == "19/03/1998"
    assert front.origin == "Xuân Thành, Yên Thành, Nghệ An"
    assert front.residence == "Bắc Phượng Sơn, Xuân Thành, Yên Thành, Nghệ An"
    assert front.expiry_date == "19/03/2038"
    assert front.extraction_source == "front_rules"


@pytest.mark.parametrize("name,expiry", [
    ("front_cu_5.jpg", "28/05/2034"),
    ("front_cu_6.jpg", "24/01/2029"),
])
def test_old_front_expiry_is_read_from_ocr_only(ocr_only_engine, name, expiry):
    image = CCCDPipeline.load_image(real_image_path(name))
    aligned = CardAligner().align(image).aligned_image
    front = FrontRuleExtractor.extract(ocr_only_engine.recognize(aligned, is_front=True).full_text)

    assert front.expiry_date == expiry


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
    result = BackSideExtractor.extract(ocr.full_text, mrz_text=ocr.mrz_text)

    assert result.card_version == "cccd_chip_2021"
    assert result.issue_loc == "Cục Cảnh sát Quản lý hành chính về trật tự xã hội"
    assert result.expiry_date == "01/01/2033"


def test_cccd_front_ocr_preserves_origin_comma(real_pipeline):
    image = CCCDPipeline.load_image(real_image_path("front_cu_4.jpg"))
    aligned = real_pipeline.aligner.align(image).aligned_image
    ocr = real_pipeline.ocr_engine.recognize(aligned, is_front=True)
    front = FrontRuleExtractor.extract(ocr.full_text)
    assert front.origin == "Thị trấn Hiệp Phước, Nhơn Trạch, Đồng Nai"
    assert front.id == "075097023463"
    assert front.dob == "29/03/1997"
    result = DataFusion.fuse(front=front)
    assert result.data.origin == front.origin


def test_front_cu_original_reads_identity_and_expiry_without_qr(real_pipeline, monkeypatch):
    monkeypatch.setattr(
        real_pipeline.ocr_engine, "qr_decoder",
        SimpleNamespace(mask_qr_regions=lambda image: image),
    )
    image = CCCDPipeline.load_image(real_image_path("front_cu.jpg"))
    aligned = real_pipeline.aligner.align(image).aligned_image
    ocr = real_pipeline.ocr_engine.recognize(aligned, is_front=True)
    front = FrontRuleExtractor.extract(ocr.full_text)
    assert front.id == "054205010560"
    assert front.dob == "10/04/2005"
    assert front.origin == "Hòa Hiệp Bắc, Thị xã Đông Hòa, Phú Yên"
    assert front.residence.startswith("234 Tân Trào,")
    assert front.expiry_date == "10/04/2030"
    result = DataFusion.fuse(front=front)
    assert result.data.id == "054205010560"
    assert result.field_sources["id"] == "front_rules"
    assert result.field_sources["expiry_date"] == "front_rules"


@pytest.mark.parametrize("image_name,id_num,dob,issue_date,expiry_date", [
    ("back_cu_8.jpg", "046069005251", "28/04/1969", "15/08/2021", "28/04/2029"),
    ("back_cu_14.jpg", "052206009281", "25/04/2006", "08/05/2022", "25/04/2031"),
    ("back_cu_16.jpg", "038068030449", "13/12/1968", "30/06/2022", "13/12/2028"),
    ("back_cu_18.jpg", "024091011267", "16/08/1991", "15/05/2022", "16/08/2031"),
])
def test_cccd_back_group_8_to_11_fills_identity_and_dates(
    real_pipeline, image_name, id_num, dob, issue_date, expiry_date,
):
    result = real_pipeline.process(real_image_path(image_name), force_side=CardSide.BACK)
    assert result.data.id == id_num
    assert result.data.dob == dob
    assert result.data.gender == "Nam"
    assert result.data.issue_date == issue_date
    assert result.data.expiry_date == expiry_date
    assert result.data.issue_loc == "Cục Cảnh sát Quản lý hành chính về trật tự xã hội"
    assert result.field_sources["id"] == "mrz"
    assert result.field_sources["expiry_date"] == "mrz"


def test_redacted_cccd_back_reads_gender_without_guessing_birth_century(real_pipeline):
    result = real_pipeline.process(real_image_path("back_cu_3.png"), force_side=CardSide.BACK)
    assert result.data.id is None
    assert result.data.dob is None
    assert result.data.gender == "Nam"
    assert result.field_sources["gender"] == "mrz"
    assert result.data.issue_date == "24/06/2021"
    assert result.data.expiry_date == "01/06/2033"
    assert result.data.issue_loc == "Cục Cảnh sát Quản lý hành chính về trật tự xã hội"


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
