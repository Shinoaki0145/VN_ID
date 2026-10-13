import pytest

from vn_id.core.schemas import BackSideResult
from vn_id.parser import FrontRuleExtractor
from vn_id.validator import DataFusion


@pytest.mark.parametrize(
    "text, expected",
    [
        ("CĂN CƯỚC CÔNG DÂN\nSố: 001098012345", "can_cuoc_cong_dan_2021"),
        ("CĂN CƯỚC\nSố định danh: 001098012345", "can_cuoc_2024"),
        ("CĂN CƯỚC\nCÔNG DÂN\nSố: 001098012345", "can_cuoc_cong_dan_2021"),
        ("Số: 001098012345\nNơi cư trú: Hà Nội", "unknown"),
        ("Số căn cước: 001098012345", "unknown"),
        ("CĂN CƯỚC\nSố: 001098012345\nNơi thường trú: Hà Nội", "unknown"),
        ("CĂN CƯỚC CÔNG\nQuê quán: Hà Nội", "can_cuoc_cong_dan_2021"),
        ("CĂN CƯỚC CÔNG\nNơi thường trú: Hà Nội", "can_cuoc_cong_dan_2021"),
        ("CĂN CƯỚC CÔNG\nCó giá trị đến: 01/01/2030", "can_cuoc_cong_dan_2021"),
        ("CĂN CƯỚC CÔNG\nSố: 001098012345", "unknown"),
        ("CĂN CƯỚC CÔNG\nNơi cư trú: Hà Nội", "unknown"),
        ("Số căn cước công: 001098012345\nQuê quán: Hà Nội", "unknown"),
    ],
)
def test_front_card_version_from_title(text, expected):
    front = FrontRuleExtractor.extract(text)
    assert front.card_version == expected
    assert DataFusion.fuse(front=front, side_detected=["front"]).card_version == expected


def test_back_version_fills_missing_front_version():
    front = FrontRuleExtractor.extract("Số: 001098012345")
    back = BackSideResult(card_version="can_cuoc_2024")
    assert DataFusion.fuse(front=front, back=back).card_version == "can_cuoc_2024"


def test_conflicting_front_and_back_versions_remain_unknown():
    front = FrontRuleExtractor.extract("CĂN CƯỚC\nSố: 001098012345")
    back = BackSideResult(card_version="can_cuoc_cong_dan_2021")
    result = DataFusion.fuse(front=front, back=back)
    assert result.card_version == "unknown"
    assert any("card_version" in warning for warning in result.validation.warnings)
