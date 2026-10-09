from types import SimpleNamespace

import numpy as np
import pytest

from vn_id.ocr import OCREngine
from vn_id.pipeline import CCCDPipeline
from vn_id.qr import QRDecoder
from vn_id.core.config import EASYOCR_STORAGE_DIR
from vn_id.core.schemas import TextBox


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


@pytest.mark.parametrize("failure", ["detector_error", "ambiguous", "no_id"])
def test_id_region_refinement_preserves_ordinary_ocr_when_unreliable(failure):
    engine = OCREngine()
    engine.qr_decoder._qreader = SimpleNamespace(detect=lambda **kwargs: ())
    original = "Số 10044205010560"
    predictions = iter([
        original,
        "054205010560" if failure == "ambiguous" else "Số",
        "075097023463" if failure == "ambiguous" else "No.",
    ])

    def detect(image, **kwargs):
        if kwargs.get("canvas_size") == 128:
            if failure == "detector_error":
                raise RuntimeError("ID detector unavailable")
            return [[[10, 100, 5, 30], [110, 200, 5, 30]]], [[]]
        return [[[10, 290, 10, 45]]], [[]]

    engine._detector = SimpleNamespace(detect=detect)
    engine._recognizer = SimpleNamespace(predict=lambda *args, **kwargs: (next(predictions), 0.9))
    result = engine.recognize(np.zeros((100, 300, 3), dtype=np.uint8))
    assert result.full_text == original
    assert len(result.boxes) == 1


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


def test_failed_address_retry_keeps_primary_ocr():
    engine = OCREngine(qr_decoder=SimpleNamespace(mask_qr_regions=lambda image: image))
    calls = []

    def detect(image, **kwargs):
        calls.append(kwargs["width_ths"])
        if kwargs["width_ths"] == 0.3:
            raise RuntimeError("retry detector unavailable")
        return [[[273, 560, 487, 515], [279, 963, 509, 550], [95, 935, 543, 598]]], [[]]

    predictions = iter([("Quê quán", 0.9), ("Bình Tân", 0.9), ("noise", 0.2)])
    engine._detector = SimpleNamespace(detect=detect)
    engine._recognizer = SimpleNamespace(predict=lambda *args, **kwargs: next(predictions))

    result = engine.recognize(np.zeros((630, 1000, 3), dtype=np.uint8), is_front=True)

    assert calls == [0.75, 0.3]
    assert "Quê quán" in result.full_text
    assert "Bình Tân" in result.full_text


def test_local_vietocr_checkpoint_does_not_download_backbone(tmp_path, monkeypatch):
    from vietocr.tool.config import Cfg
    from vietocr.tool import predictor

    checkpoint = tmp_path / "vgg_seq2seq.pth"
    checkpoint.touch()
    monkeypatch.setattr("vn_id.ocr.engine.VIETOCR_WEIGHTS_PATH", checkpoint)
    monkeypatch.setattr(Cfg, "load_config_from_file", lambda path: {"cnn": {}})
    seen = {}
    monkeypatch.setattr(predictor, "Predictor", lambda config: seen.update(config))

    OCREngine()._get_recognizer()

    assert seen["cnn"].get("pretrained") is False


def test_address_retry_recovers_separate_residence_boxes():
    engine = OCREngine(qr_decoder=SimpleNamespace(mask_qr_regions=lambda image: image))
    calls = []

    def detect(image, **kwargs):
        calls.append(kwargs["width_ths"])
        if kwargs["width_ths"] == 0.3:
            return [[[273, 451, 546, 577], [458, 934, 544, 589]]], [[]]
        return [[[273, 560, 487, 515], [279, 963, 509, 550], [95, 935, 543, 598]]], [[]]

    predictions = iter([
        ("Quê quán", 0.9), ("Bình Tân", 0.9), ("noise", 0.2),
        ("Nơi thường trú", 0.9), ("Place of residence: 24/12/29 LK 2-10", 0.9),
    ])
    engine._detector = SimpleNamespace(detect=detect)
    engine._recognizer = SimpleNamespace(predict=lambda *args, **kwargs: next(predictions))

    result = engine.recognize(np.zeros((630, 1000, 3), dtype=np.uint8), is_front=True)

    assert calls == [0.75, 0.3]
    assert "Nơi thường trú Place of residence: 24/12/29 LK 2-10" in result.full_text
    assert result.full_text.count("Bình Tân") == 1


def test_address_gap_recovery_keeps_spelling_from_original_box():
    engine = OCREngine()
    boxes = [
        TextBox(bbox=[273, 487, 560, 515], text="Quê quán"),
        TextBox(bbox=[279, 509, 512, 548], text="Bình Hưng Hòa"),
        TextBox(bbox=[549, 507, 963, 550], text="Bình Tân"),
    ]
    predictions = iter([
        ("Bình Hưng Hòa A, Bình Tần", 0.9),
        ("Bình Hưng Hòa A, Bình Tần", 0.9),
        ("Bình Hưng Hòa A,", 0.9),
    ])
    recognizer = SimpleNamespace(predict=lambda *args, **kwargs: next(predictions))

    engine._recover_front_address_lines(np.zeros((630, 1000, 3), dtype=np.uint8), boxes, recognizer)

    assert "Bình Hưng Hòa A, Bình Tân" == " ".join(box.text for box in boxes[1:])


def test_address_reread_cannot_change_existing_number_separators():
    engine = OCREngine()
    boxes = [
        TextBox(bbox=[273, 546, 451, 577], text="Nơi thường trú"),
        TextBox(bbox=[274, 574, 615, 622], text="24/12/29 LK 2-10"),
        TextBox(bbox=[649, 577, 963, 627], text="Bình Tân, TP.HCM"),
    ]
    candidate = "24-12-29 LK 2/10, Bình Tân, TP.HCM"
    recognizer = SimpleNamespace(predict=lambda *args, **kwargs: (candidate, 0.9))

    engine._recover_front_address_lines(np.zeros((630, 1000, 3), dtype=np.uint8), boxes, recognizer)

    assert [box.text for box in boxes] == [
        "Nơi thường trú", "24/12/29 LK 2-10", "Bình Tân, TP.HCM",
    ]


def test_residence_number_reread_recovers_word_before_detected_digits():
    engine = OCREngine()
    boxes = [
        TextBox(bbox=[282, 538, 477, 571], text="Nơi thường trú I"),
        TextBox(bbox=[474, 536, 683, 579], text="Place ofresidence:"),
        TextBox(bbox=[735, 559, 756, 575], text="11"),
        TextBox(bbox=[280, 575, 945, 632], text="Sông Bằng, Thành phố Cao Bằng, Cảo Bằng"),
    ]
    recognizer = SimpleNamespace(predict=lambda *args, **kwargs: ("Tổ 11", 0.89))

    engine._recover_front_address_lines(np.zeros((630, 1000, 3), dtype=np.uint8), boxes, recognizer)

    assert boxes[2].text == "Tổ 11"


@pytest.mark.parametrize("original,rereads,expected", [
    ("Minh Tâm, Nguyễn Bình, Cao Bằng", ["Minh Tâm, Nguyên Bình, Cao Bằng"] * 2,
     "Minh Tâm, Nguyên Bình, Cao Bằng"),
    ("Minh Tâm, Nguyễn Bình, Cao Bằng",
     ["Minh Tâm, Nguyên Bình, Cao Bằng", "Minh Tâm, Nguyễn Bình, Cao Bằng"],
     "Minh Tâm, Nguyễn Bình, Cao Bằng"),
    ("Thị trấn Hiệp Phước, Nhơn Trạch, Đồng Nai",
     ["Thị trấn Hiệp Phước, Nhơn Trạch, Đang Nai"] * 2,
     "Thị trấn Hiệp Phước, Nhơn Trạch, Đồng Nai"),
])
def test_origin_tight_crop_only_accepts_repeatable_accent_change(original, rereads, expected):
    engine = OCREngine()
    boxes = [
        TextBox(bbox=[284, 474, 579, 507], text="Quê quán I Place of origin:"),
        TextBox(bbox=[283, 501, 813, 551], text=original, confidence=0.88),
    ]
    predictions = iter((value, 0.88) for value in rereads)
    recognizer = SimpleNamespace(predict=lambda *args, **kwargs: next(predictions))

    engine._recover_front_address_lines(np.zeros((630, 1000, 3), dtype=np.uint8), boxes, recognizer)

    assert boxes[1].text == expected
