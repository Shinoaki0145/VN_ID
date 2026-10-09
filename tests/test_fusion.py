import pytest
from vn_id.core.schemas import FrontSideResult, QRResult, BackSideResult
from vn_id.validator.fusion import DataFusion

def test_fusion_qr_priority_over_ocr():
    qr = QRResult(
        is_detected=True,
        id="001098012345",
        name="NGUYỄN VĂN A",
        dob="15/08/1998",
        gender="Nam",
        address="Số 1 Đại Cồ Việt, Hai Bà Trưng, Hà Nội"
    )
    front = FrontSideResult(
        id="001098012345",
        name="NGUYEN VAN A",  # OCR typo/no accents
        dob="15/08/1998",
        gender="Nam",
        origin="Kim Liên, Nam Đàn, Nghệ An",
        residence="Số 1 Đại Cồ Việt, Hai Bà Trưng, Hà Nội"
    )
    back = BackSideResult(
        card_version="cccd_chip_2021",
        issue_date="24/06/2021",
        issue_loc="Cục Cảnh sát Quản lý hành chính về trật tự xã hội"
    )

    final = DataFusion.fuse(qr=qr, front=front, back=back)
    assert final.success
    # QR has priority for Name
    assert final.data.name == "NGUYỄN VĂN A"
    assert final.field_sources["name"] == "qr"
    # Origin from front rules since QR does not have origin
    assert final.data.origin == "Kim Liên, Nam Đàn, Nghệ An"
    assert final.field_sources["origin"] == "front_rules"
    # Back side data
    assert final.data.issue_date == "24/06/2021"
    assert final.data.issue_loc == "Cục Cảnh sát Quản lý hành chính về trật tự xã hội"
    assert final.field_sources["issue_date"] == "back_rules"
    assert final.validation.is_valid_12_digits

def test_fusion_no_qr_uses_front_rules():
    qr = QRResult(is_detected=False)
    front = FrontSideResult(
        id="001098012345",
        name="NGUYỄN VĂN B",
        dob="15/08/1998",
        gender="Nam",
        origin="Hà Nội",
        residence="Hà Nội"
    )
    final = DataFusion.fuse(qr=qr, front=front, back=None)
    assert final.data.name == "NGUYỄN VĂN B"
    assert final.field_sources["name"] == "front_rules"
    assert final.data.issue_date is None

def test_fusion_2024_card_back_address_and_qr():
    # 2024 card where front has basic info, and back has QR, residence & origin
    qr_back = QRResult(
        is_detected=True,
        id="054200009740",
        cmnd_old="221472077",
        name="Nguyễn Trần Phương Duy",
        dob="20/10/2000",
        gender="Nam",
        address="Khu Phố An Thạnh, Xuân Đài, Sông Cầu, Phú Yên",
        issue_date="09/05/2025"
    )
    front = FrontSideResult(
        id="054200009740",
        name="NGUYỄN TRẦN PHƯƠNG DUY",
        dob="20/10/2000",
        gender="Nam"
    )
    back_rules = BackSideResult(
        card_version="can_cuoc_2024",
        origin="Xuân Đài, Sông Cầu, Phú Yên",
        residence="Khu Phố An Thạnh, Xuân Đài, Sông Cầu, Phú Yên",
        issue_date="09/05/2025",
        expiry_date="20/10/2040",
        issue_loc="Bộ Công an"
    )

    final = DataFusion.fuse(qr=qr_back, front=front, back=back_rules)
    assert final.success
    assert final.data.id == "054200009740"
    assert final.data.cmnd_old == "221472077"
    assert final.data.name == "Nguyễn Trần Phương Duy"
    assert final.data.residence == "Khu Phố An Thạnh, Xuân Đài, Sông Cầu, Phú Yên"
    assert final.data.origin == "Xuân Đài, Sông Cầu, Phú Yên"
    assert final.field_sources["origin"] == "back_rules"
    assert final.data.expiry_date == "20/10/2040"
    assert final.data.issue_loc == "Bộ Công an"


def test_fusion_gender_deduction_from_id():
    # When front does not have gender, deduce from 4th digit (even = Nam, odd = Nu)
    front = FrontSideResult(
        id="001098012345",  # 4th digit is '0' (Nam born in 1900s)
        name="NGUYỄN VĂN A",
        gender=None,
    )
    final = DataFusion.fuse(front=front)
    assert final.data.gender == "Nam"
    assert final.field_sources["gender"] == "id_deduced"


def test_fusion_back_side_only_does_not_inject_front():
    # Processing only back side image should retain side_detected=["back"]
    back = BackSideResult(
        card_version="can_cuoc_2024",
        issue_date="09/05/2025",
        issue_loc="Bộ Công an",
    )
    final = DataFusion.fuse(back=back, side_detected=["back"])
    assert final.side_detected == ["back"]


@pytest.mark.parametrize("origin,residence", [
    ("Thị trấn Hiệp Phước Nhơn Trạch, Đồng Nai", "Hiệp Phước, Nhơn Trạch, Đồng Nai"),
    ("Hòa Hiệp Bắc Thị xã Đông Hòa, Phú Yên", "Bình Kiến, Tuy Hòa, Phú Yên"),
])
def test_fusion_does_not_invent_origin_commas_from_residence(origin, residence):
    final = DataFusion.fuse(
        front=FrontSideResult(origin=origin),
        qr=QRResult(is_detected=True, address=residence),
    )
    assert final.data.origin == origin
    assert final.data.residence == residence
