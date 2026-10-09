from types import SimpleNamespace

import numpy as np
import pytest

from vn_id.ocr import OCREngine
from vn_id.pipeline import CCCDPipeline
from vn_id.qr import QRDecoder
from vn_id.core.config import EASYOCR_STORAGE_DIR


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


def test_mrz_recognition_merges_fragments_into_whole_lines():
    engine = OCREngine()
    seen = {}

    def recognize(gray, **kwargs):
        seen.update(kwargs)
        return [(None, "IDVNM0690052512046069005251", 0.9), (None, "6904281M2904283VNM", 0.9)]

    engine._detector = SimpleNamespace(detect=lambda *args, **kwargs: (
        [[[10, 120, 10, 30], [125, 280, 11, 31], [10, 280, 55, 75]]], [[]],
    ))
    engine._mrz_reader = SimpleNamespace(recognize=recognize)
    result = engine._recognize_mrz(np.zeros((200, 300, 3), dtype=np.uint8))
    assert result == "IDVNM0690052512046069005251\n6904281M2904283VNM"
    assert seen["horizontal_list"] == [[10, 280, 10, 31], [10, 280, 55, 75]]
    assert seen["allowlist"] == "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ<"


def test_optional_mrz_failure_preserves_ordinary_back_ocr(caplog):
    engine = OCREngine()
    engine.qr_decoder._qreader = SimpleNamespace(detect=lambda **kwargs: ())
    engine._detector = SimpleNamespace(detect=lambda *args, **kwargs: ([[[10, 290, 10, 35]]], [[]]))
    engine._recognizer = SimpleNamespace(predict=lambda *args, **kwargs: ("IDVNM0690052512046069005251", 0.9))

    attempted = []

    def unavailable(*args):
        attempted.append(True)
        raise RuntimeError("Optional Latin model unavailable")

    engine._recognize_mrz = unavailable
    result = engine.recognize(np.zeros((200, 300, 3), dtype=np.uint8), is_front=False)
    assert result.full_text == "IDVNM0690052512046069005251"
    assert result.mrz_text is None
    assert attempted
    assert "Optional Latin model unavailable" in caplog.text


def test_mrz_reader_downloads_missing_model_into_its_storage(tmp_path, monkeypatch):
    import shutil

    easyocr = pytest.importorskip("easyocr")
    torch = pytest.importorskip("torch")
    weights = EASYOCR_STORAGE_DIR / "latin_g2.pth"
    if not weights.is_file():
        pytest.skip("Local Latin weights required for an offline download-boundary test")

    def offline_download(url, filename, directory, verbose=True):
        shutil.copyfile(weights, tmp_path / filename)

    monkeypatch.setattr("vn_id.ocr.engine.EASYOCR_STORAGE_DIR", tmp_path)
    monkeypatch.setattr(easyocr.easyocr, "download_and_unzip", offline_download)
    original_threads = torch.get_num_threads()
    torch.set_num_threads(min(original_threads, 4))
    try:
        reader = OCREngine(device="cpu")._get_mrz_reader()
        assert (tmp_path / "latin_g2.pth").is_file()
        assert reader.model_lang == "latin"
    finally:
        torch.set_num_threads(original_threads)


def test_dbnet_bounds_card_and_mrz_detection_image_sizes():
    pytest.importorskip("easyocr")
    from easyocr.DBNet.DBNet import DBNet

    engine = OCREngine()
    engine.qr_decoder._qreader = SimpleNamespace(detect=lambda **kwargs: ())
    settings = SimpleNamespace(min_detection_size=736, max_detection_size=2048)
    sizes = []

    def detect(image, **kwargs):
        resized, _ = DBNet.resize_image(settings, image, kwargs.get("canvas_size", 2560))
        sizes.append(resized.shape[0] * resized.shape[1])
        return [[[10, 950, 10, 40]]], [[]]

    engine._detector = SimpleNamespace(detect=detect)
    engine._recognizer = SimpleNamespace(predict=lambda *args, **kwargs: ("IDVNM0690052512046069005251", 0.9))
    engine._mrz_reader = SimpleNamespace(recognize=lambda *args, **kwargs: [(None, "6904281M2904283VNM", 0.9)])
    result = engine.recognize(np.zeros((630, 1000, 3), dtype=np.uint8), is_front=False)
    assert result.mrz_text == "6904281M2904283VNM"
    assert len(sizes) == 2
    assert sizes[0] <= 4_200_000
    assert sizes[1] <= 2_000_000


@pytest.mark.parametrize("stage", ["detector", "recognizer", "mrz"])
def test_cuda_oom_keeps_device_without_cpu_retry(stage, caplog):
    torch = pytest.importorskip("torch")
    engine = OCREngine(device="cuda")
    engine.qr_decoder._qreader = SimpleNamespace(detect=lambda **kwargs: ())
    devices = []

    def detect(image, **kwargs):
        devices.append(engine.device)
        if stage == "detector":
            raise torch.cuda.OutOfMemoryError("CUDA out of memory in detector")
        return [[[10, 290, 10, 35]]], [[]]

    def predict(*args, **kwargs):
        devices.append(engine.device)
        if stage == "recognizer":
            raise torch.cuda.OutOfMemoryError("CUDA out of memory in recognizer")
        return "IDVNM0690052512046069005251", 0.9

    def mrz(image):
        devices.append(engine.device)
        raise torch.cuda.OutOfMemoryError("CUDA out of memory in MRZ")

    engine._get_detector = lambda: SimpleNamespace(detect=detect)
    engine._get_recognizer = lambda: SimpleNamespace(predict=predict)
    engine._recognize_mrz = mrz
    result = engine.recognize(np.zeros((200, 300, 3), dtype=np.uint8), is_front=False)

    assert engine.device == "cuda"
    assert devices and all(device == "cuda" for device in devices)
    assert result.mrz_text is None
    assert result.full_text == ("IDVNM0690052512046069005251" if stage == "mrz" else "")
    assert "out of memory" in caplog.text


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
