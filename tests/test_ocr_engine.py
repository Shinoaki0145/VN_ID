from types import SimpleNamespace

import numpy as np
import pytest

from vn_id.ocr import OCREngine
from vn_id.pipeline import CCCDPipeline
from vn_id.qr import QRDecoder


def test_ocr_masks_qr_before_detection_and_recognition():
    image = np.full((64, 64, 3), 17, dtype=np.uint8)
    decoder = QRDecoder()
    decoder._qreader = SimpleNamespace(detect=lambda **kwargs: ({
        "quad_xy": np.array([[20, 20], [40, 20], [40, 40], [20, 40]], dtype=float),
    },))
    seen = {}

    def detect(image, **kwargs):
        seen["detector_image"] = image.copy()
        return [[[20, 40, 20, 40]]], [[]]

    def predict(crop, **kwargs):
        seen["recognizer_image"] = np.array(crop)
        return "Địa chỉ", 0.9

    engine = OCREngine(qr_decoder=decoder)
    engine._detector = SimpleNamespace(detect=detect)
    engine._recognizer = SimpleNamespace(predict=predict)

    result = engine.recognize(image)

    assert result.full_text == "Địa chỉ"
    assert np.all(seen["detector_image"][20:41, 20:41] == 255)
    assert np.all(seen["recognizer_image"][4:24, 2:22] == 255)
    assert np.all(image == 17)


def test_pipeline_shares_qr_decoder_with_ocr():
    pipeline = CCCDPipeline(device="cpu")
    assert pipeline.ocr_engine.qr_decoder is pipeline.qr_decoder


@pytest.mark.parametrize("is_front, second_x, has_qr", [
    (True, 120, False), (False, 150, True), (False, 120, False),
])
def test_ocr_keeps_distinct_fields(is_front, second_x, has_qr):
    easyocr = pytest.importorskip("easyocr")
    decoder = QRDecoder()
    detections = ({"quad_xy": np.array([[250, 40], [270, 40], [270, 60], [250, 60]])},) if has_qr else ()
    decoder._qreader = SimpleNamespace(detect=lambda **kwargs: detections)
    engine = OCREngine(qr_decoder=decoder)
    polygons = [
        [10, 10, 90, 10, 90, 30, 10, 30],
        [second_x, 10, second_x + 80, 10, second_x + 80, 30, second_x, 30],
    ]

    def detect(image, **kwargs):
        horizontal, free = easyocr.utils.group_text_box(
            polygons, width_ths=kwargs.get("width_ths", 0.5), add_margin=0,
        )
        return [horizontal], [free]

    engine._detector = SimpleNamespace(detect=detect)
    engine._recognizer = SimpleNamespace(predict=lambda *args, **kwargs: ("Giá trị", 0.9))

    result = engine.recognize(np.zeros((64, 300, 3), dtype=np.uint8), is_front=is_front)

    assert len(result.boxes) == 2
    assert sorted(box.bbox for box in result.boxes) == [
        [10, 10, 90, 30], [second_x, 10, second_x + 80, 30],
    ]
