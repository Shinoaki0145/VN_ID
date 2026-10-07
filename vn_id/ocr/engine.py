"""OCR Engine with DBNet detector and VietOCR recognizer."""
import os
import time
import unicodedata
from typing import Any
import cv2
import numpy as np
from PIL import Image

from vn_id.core.config import (
    EASYOCR_STORAGE_DIR,
    EASYOCR_USER_NETWORK_DIR,
    VIETOCR_CFG_PATH,
    VIETOCR_WEIGHTS_PATH,
)
from vn_id.core.schemas import OCRResult, TextBox
from vn_id.ocr.sorter import ReadingOrderSorter
from vn_id.ocr.mock import MockOCREngine


class OCREngine:
    """OCR Engine managing text detection (DBNet) and recognition (VietOCR)."""

    def __init__(self, use_mock: bool = False, device: str = "cpu"):
        self.use_mock = use_mock
        self.device = device
        self.sorter = ReadingOrderSorter()
        self.mock_engine = MockOCREngine()
        self._detector = None
        self._recognizer = None

    def _get_detector(self):
        if self._detector is None:
            import easyocr

            EASYOCR_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
            EASYOCR_USER_NETWORK_DIR.mkdir(parents=True, exist_ok=True)

            use_gpu = self.device == "cuda"
            self._detector = easyocr.Reader(
                ["vi"],
                gpu=use_gpu,
                detect_network="dbnet18",
                recognizer=False,
                model_storage_directory=str(EASYOCR_STORAGE_DIR),
                user_network_directory=str(EASYOCR_USER_NETWORK_DIR),
                verbose=False,
            )
        return self._detector

    def _get_recognizer(self):
        if self._recognizer is None:
            from vietocr.tool.config import Cfg
            from vietocr.tool.predictor import Predictor

            if VIETOCR_CFG_PATH.is_file():
                config = Cfg.load_config_from_file(str(VIETOCR_CFG_PATH))
            else:
                config = Cfg.load_config_from_name("vgg_seq2seq")

            # Configure weights path and device
            if VIETOCR_WEIGHTS_PATH.is_file():
                config["weights"] = str(VIETOCR_WEIGHTS_PATH)

            config["device"] = "cuda" if self.device == "cuda" else "cpu"
            self._recognizer = Predictor(config)
        return self._recognizer

    def recognize(self, image: np.ndarray, is_front: bool = True) -> OCRResult:
        """Run OCR on image using DBNet (detection) + VietOCR (recognition) + ReadingOrderSorter."""
        if self.use_mock:
            return self.mock_engine.recognize(image, is_front=is_front)

        if image is None or not isinstance(image, np.ndarray) or image.size == 0:
            return OCRResult(boxes=[], full_text="", time_taken_ms=0.0)

        t0 = time.time()
        try:
            detector = self._get_detector()
            recognizer = self._get_recognizer()

            t_det_start = time.time()
            h_list, f_list = detector.detect(image)
            det_time_ms = (time.time() - t_det_start) * 1000.0

            boxes: list[TextBox] = []
            h, w = image.shape[:2]

            # 1. Process horizontal detection boxes from DBNet with VietOCR
            t_rec_start = time.time()
            if h_list and h_list[0]:
                for b in h_list[0]:
                    xmin, xmax, ymin, ymax = int(b[0]), int(b[1]), int(b[2]), int(b[3])
                    # Filter out tiny noise boxes
                    box_w = xmax - xmin
                    box_h = ymax - ymin
                    if box_w < 8 or box_h < 6:
                        continue

                    pad_y = 4
                    pad_x = 2
                    y1, y2 = max(0, ymin - pad_y), min(h, ymax + pad_y)
                    x1, x2 = max(0, xmin - pad_x), min(w, xmax + pad_x)
                    crop = image[y1:y2, x1:x2]
                    if crop.size == 0:
                        continue

                    pil_crop = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
                    try:
                        text, prob = recognizer.predict(pil_crop, return_prob=True)
                        clean_text = unicodedata.normalize("NFC", text.strip())
                        if clean_text and prob >= 0.35:
                            boxes.append(
                                TextBox(
                                    bbox=[xmin, ymin, xmax, ymax],
                                    text=clean_text,
                                    confidence=float(prob),
                                )
                            )
                    except Exception:
                        pass
            rec_time_ms = (time.time() - t_rec_start) * 1000.0

            if not boxes:
                duration_ms = (time.time() - t0) * 1000.0
                return OCRResult(
                    boxes=[],
                    full_text="",
                    time_taken_ms=duration_ms,
                    det_time_ms=det_time_ms,
                    rec_time_ms=rec_time_ms,
                    sort_time_ms=0.0,
                )

            t_sort_start = time.time()
            sorted_ocr = self.sorter.sort_boxes(boxes)
            sort_time_ms = (time.time() - t_sort_start) * 1000.0

            sorted_ocr.time_taken_ms = (time.time() - t0) * 1000.0
            sorted_ocr.det_time_ms = det_time_ms
            sorted_ocr.rec_time_ms = rec_time_ms
            sorted_ocr.sort_time_ms = sort_time_ms
            return sorted_ocr

        except Exception:
            duration_ms = (time.time() - t0) * 1000.0
            return OCRResult(boxes=[], full_text="", time_taken_ms=duration_ms)
