"""Contracts for independently selectable card strategies and legacy facades."""
import json

import pytest
from pydantic import ValidationError

from vn_id.core import schemas
from vn_id import parser
from vn_id.parser import BackRuleExtractor, FrontRuleExtractor


def test_card_versions_are_typed_without_changing_json_values():
    assert hasattr(schemas, 'CardVersion'), 'CardVersion enum is missing'
    version = schemas.CardVersion.CAN_CUOC_2024
    for model in (schemas.FrontSideResult, schemas.BackSideResult, schemas.FinalCCCDResult):
        result = model(card_version='can_cuoc_2024')
        assert result.card_version is version
        assert json.loads(result.model_dump_json())['card_version'] == 'can_cuoc_2024'
        with pytest.raises(ValidationError):
            model(card_version='unsupported')


@pytest.mark.parametrize('text, side, version', [
    ('CĂN CƯỚC CÔNG DÂN\nSố: 001098012345', 'front', 'can_cuoc_cong_dan_2021'),
    ('CĂN CƯỚC\nSố: 001098012345', 'front', 'can_cuoc_2024'),
    ('CỤC CẢNH SÁT\n24/06/2021', 'back', 'can_cuoc_cong_dan_2021'),
    ('BỘ CÔNG AN\nNgày, tháng, năm cấp: 18/11/2024', 'back', 'can_cuoc_2024'),
    ('Số: 001098012345', 'front', 'unknown'),
    ('24/06/2021', 'back', 'unknown'),
    ('', 'back', 'unknown'),
])
def test_factory_preserves_detection_and_legacy_results(text, side, version):
    assert hasattr(parser, 'CardParserFactory'), 'Parser factory is missing'
    factory = parser.CardParserFactory()
    detected = factory.detect_version(text, schemas.CardSide(side))
    assert detected == version
    strategy = factory.detect_and_get(text, schemas.CardSide(side))
    assert strategy.version == version
    if side == 'front':
        result = strategy.parse_front(text)
        assert result == FrontRuleExtractor.extract(text)
        assert result.id == ('001098012345' if '001098012345' in text else None)
    else:
        result = strategy.parse_back(text)
        assert result == BackRuleExtractor.extract(text)
        assert result.issue_date == ('18/11/2024' if version == 'can_cuoc_2024' else '24/06/2021' if text else None)
    assert result.card_version == version


def test_explicit_strategies_isolate_back_layouts_and_accept_parsed_mrz():
    assert hasattr(parser, 'CardParserFactory'), 'Parser factory is missing'
    factory = parser.CardParserFactory()
    mrz = schemas.MRZResult(raw_text='checked MRZ', expiry_date='01/01/2033')
    old = factory.get_parser('can_cuoc_cong_dan_2021').parse_back('24/06/2021', mrz=mrz)
    new = factory.get_parser('can_cuoc_2024').parse_back(
        'BỘ CÔNG AN\nNgày, tháng, năm cấp: 18/11/2024\nNgày, tháng, năm hết hạn: 14/09/2043', mrz=mrz,
    )
    assert old.card_version == 'can_cuoc_cong_dan_2021'
    assert old.issue_date == '24/06/2021'
    assert old.expiry_date == '01/01/2033'
    assert old.mrz_raw == 'checked MRZ'
    assert new.card_version == 'can_cuoc_2024'
    assert new.issue_loc == 'Bộ Công an'
    assert new.issue_date == '18/11/2024'
    assert new.expiry_date == '14/09/2043'
    assert new.mrz == mrz


def test_pipeline_uses_injected_strategies_for_single_and_both_sides(monkeypatch):
    """Catch bypasses of injected factory or fusion in any pipeline path."""
    from vn_id.pipeline import CCCDPipeline
    from vn_id.validator import DataFusion
    import numpy as np

    assert hasattr(parser, 'CardParserFactory'), 'Parser factory is missing'

    class Custom2024(parser.CanCuoc2024Parser):
        def parse_front(self, text):
            result = super().parse_front(text)
            result.name = 'Injected Name'
            return result

        def parse_back(self, text, mrz=None, *, mrz_text=None):
            result = super().parse_back(text, mrz, mrz_text=mrz_text)
            result.issue_loc = 'Injected Issuer'
            result.mrz_raw = mrz_text
            return result

    class CustomFusion(DataFusion):
        def merge(self, **kwargs):
            result = super().merge(**kwargs)
            result.data.nationality = 'Injected Nationality'
            return result

    factory = parser.CardParserFactory({schemas.CardVersion.CAN_CUOC_2024: Custom2024()})
    pipeline = CCCDPipeline(device='cpu', parser_factory=factory, fusion=CustomFusion())
    image = np.zeros((10, 10, 3), dtype=np.uint8)
    # Only image/ML stages are replaced: exercise real parser/fusion/orchestration.
    monkeypatch.setattr(pipeline.aligner, 'align', lambda img: schemas.AlignedCardResult(aligned_image=img))
    monkeypatch.setattr(pipeline.qr_decoder, 'decode', lambda img: schemas.QRResult())
    monkeypatch.setattr(
        pipeline.ocr_engine, 'recognize',
        lambda img, is_front: schemas.OCRResult(
            full_text='CĂN CƯỚC\nSố: 001098012345' if is_front else 'BỘ CÔNG AN\nNgày, tháng, năm cấp: 18/11/2024',
            mrz_text='separate MRZ crop' if not is_front else None,
        ),
    )
    front = pipeline.process(image, force_side=schemas.CardSide.FRONT)
    back = pipeline.process(image, force_side=schemas.CardSide.BACK)
    both = pipeline.process_both_sides(image, image)
    for result in (front, back, both):
        assert result.data.nationality == 'Injected Nationality'
        assert result.card_version == 'can_cuoc_2024'
    assert front.data.name == both.data.name == 'INJECTED NAME'
    assert back.data.issue_loc == both.data.issue_loc == 'Injected Issuer'
    assert factory.parse_back('BỘ CÔNG AN', mrz_text='separate MRZ crop').mrz_raw == 'separate MRZ crop'


def test_factory_registry_is_not_shared_between_instances():
    class Custom2024(parser.CanCuoc2024Parser):
        def parse_front(self, text):
            result = super().parse_front(text)
            result.name = 'Custom Name'
            return result

    custom = parser.CardParserFactory({schemas.CardVersion.CAN_CUOC_2024: Custom2024()})
    ordinary = parser.CardParserFactory()
    assert custom.parse_front('CĂN CƯỚC').name == 'Custom Name'
    assert ordinary.parse_front('CĂN CƯỚC').name is None
    assert FrontRuleExtractor.extract('CĂN CƯỚC').name is None


def test_instance_fusion_preserves_conflicts_and_source_priorities():
    from vn_id.validator import DataFusion

    assert hasattr(DataFusion(), 'merge'), 'Instance fusion entrypoint is missing'
    front = schemas.FrontSideResult(card_version='can_cuoc_cong_dan_2021', id='001098012345', expiry_date='01/01/2033')
    back = schemas.BackSideResult(card_version='can_cuoc_2024', expiry_date='14/09/2043')
    qr = schemas.QRResult(is_detected=True, id='079183034888')
    result = DataFusion().merge(front=front, back=back, qr=qr)
    assert result.card_version == schemas.CardVersion.UNKNOWN
    assert result.data.id == '079183034888'
    assert result.field_sources['id'] == 'qr'
    assert result.data.expiry_date == '01/01/2033'
    assert result.field_sources['expiry_date'] == 'front_rules'
    assert any('card_version' in warning for warning in result.validation.warnings)
    assert result == DataFusion.fuse(front=front, back=back, qr=qr)


def test_front_tolerance_does_not_change_back_address_parsing():
    from vn_id.parser.strategies.can_cuoc_2024 import CanCuoc2024Parser
    parser = CanCuoc2024Parser()
    result = parser.parse_back('Nơi cư trú Phace no\nNgày, tháng, năm hết hạn: 22/11/2033')
    assert result.residence == 'Phace no'
    assert parser.parse_back('Quố quân I Place d Vonym').origin is None
