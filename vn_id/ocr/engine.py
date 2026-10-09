"""OCR Engine with DBNet detector and VietOCR recognizer."""
import os
import logging
import re
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
from vn_id.qr.decoder import QRDecoder


logger = logging.getLogger(__name__)


class OCREngine:
    """OCR Engine managing text detection (DBNet) and recognition (VietOCR)."""

    def __init__(self, use_mock: bool = False, device: str = "cpu", qr_decoder: QRDecoder | None = None):
        self.use_mock = use_mock
        self.device = device
        self.qr_decoder = qr_decoder if qr_decoder is not None else QRDecoder(device=device)
        self.sorter = ReadingOrderSorter()
        self.mock_engine = MockOCREngine()
        self._detector = None
        self._recognizer = None
        self._mrz_reader = None

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

    def _get_mrz_reader(self):
        if self._mrz_reader is None:
            import easyocr

            # Fresh environments (including Colab) need the Latin weights too.
            self._mrz_reader = easyocr.Reader(
                ["vi", "en"], gpu=self.device == "cuda", detector=False,
                model_storage_directory=str(EASYOCR_STORAGE_DIR),
                user_network_directory=str(EASYOCR_USER_NETWORK_DIR),
                download_enabled=True, verbose=False,
            )
        return self._mrz_reader

    def _recognize_id_region(self, crop: np.ndarray, detector, recognizer) -> tuple[str, float] | None:
        """Separate a smaller ID label from larger digits and read the actual digit crop."""
        horizontal, _ = detector.detect(crop, height_ths=0.2, width_ths=0.5, canvas_size=128)
        candidates = []
        for xmin, xmax, ymin, ymax in (horizontal[0] if horizontal else []):
            digits = crop[
                max(0, int(ymin) - 2):min(crop.shape[0], int(ymax) + 2),
                max(0, int(xmin) - 2):min(crop.shape[1], int(xmax) + 2),
            ]
            if digits.size == 0:
                continue
            text, prob = recognizer.predict(
                Image.fromarray(cv2.cvtColor(digits, cv2.COLOR_BGR2RGB)), return_prob=True,
            )
            text = text.strip()
            if len(text) == 12 and text.isascii() and text.isdigit() and prob >= 0.35:
                candidates.append((text, float(prob)))
        return candidates[0] if len(candidates) == 1 else None

    def _recognize_mrz(self, image: np.ndarray) -> str:
        """Read complete MRZ lines instead of Vietnamese fragments/filler guesses."""
        roi = image[int(image.shape[0] * 0.6):]
        # DBNet treats canvas_size as the SHORT side. Its default 2560 would
        # inflate this narrow ROI to roughly 10176x2560, exhausting Colab VRAM.
        horizontal, free = self._get_detector().detect(roi, width_ths=2.0, canvas_size=640)
        boxes = [
            TextBox(bbox=[int(b[0]), int(b[2]), int(b[1]), int(b[3])], text="")
            for b in (horizontal[0] if horizontal else [])
        ]
        for polygon in (free[0] if free else []):
            x, y, width, height = cv2.boundingRect(np.asarray(polygon, dtype=np.float32))
            boxes.append(TextBox(bbox=[x, y, x + width, y + height], text=""))
        lines = self.sorter._group_and_sort_lines(boxes)
        bounds = [
            [min(b.bbox[0] for b in line), max(b.bbox[2] for b in line),
             min(b.bbox[1] for b in line), max(b.bbox[3] for b in line)]
            for line in lines
        ]
        if not bounds:
            return ""
        recognized = self._get_mrz_reader().recognize(
            cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), horizontal_list=bounds, free_list=[],
            allowlist="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ<", decoder="greedy", detail=1,
        )
        return "\n".join(text for _, text, _ in recognized)

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
            masked_image = self.qr_decoder.mask_qr_regions(image)
            # Back-side QR is the 2024 layout cue. Wider grouping keeps small
            # address digits, while other layouts retain their original boxes.
            has_back_qr = not is_front and not np.array_equal(image, masked_image)
            image = masked_image
            # Read front address fragments together so intervening commas stay
            # inside the VietOCR crop instead of being lost between boxes.
            width_ths = 0.75 if is_front else (2.0 if has_back_qr else 0.5)
            h_list, f_list = detector.detect(image, width_ths=width_ths, canvas_size=1600)
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

                    # Small expiry text under the portrait sits close to the
                    # next line; wider padding can corrupt its label.
                    pad_y = 2 if is_front and xmax <= 0.35 * w and ymin >= 0.45 * h else 4
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
                        if is_front and clean_text.casefold().startswith(("số", "so ", "no.")) and not re.search(r"\b\d{12}\b", clean_text):
                            try:
                                candidate = self._recognize_id_region(crop, detector, recognizer)
                                if candidate:
                                    clean_text, prob = candidate
                            except Exception as error:
                                logger.warning("ID region recognition unavailable; keeping ordinary OCR: %s", str(error))
                        if clean_text and prob >= 0.35:
                            boxes.append(
                                TextBox(
                                    bbox=[xmin, ymin, xmax, ymax],
                                    text=clean_text,
                                    confidence=float(prob),
                                )
                            )
                    except Exception as error:
                        logger.warning("Text recognition unavailable: %s", str(error))
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

            # This optional pass must never discard the ordinary OCR result.
            if not is_front and (
                "IDVNM" in re.sub(r"\s+", "", sorted_ocr.full_text.upper())
                or re.search(r"[\dOIL]{7}[MF<][\dOIL]{7}VNM", sorted_ocr.full_text.upper())
            ):
                t_mrz_start = time.time()
                try:
                    sorted_ocr.mrz_text = self._recognize_mrz(image) or None
                except Exception as error:
                    logger.warning("MRZ recognition unavailable; keeping ordinary OCR: %s", error)
                rec_time_ms += (time.time() - t_mrz_start) * 1000.0

            sorted_ocr.time_taken_ms = (time.time() - t0) * 1000.0
            sorted_ocr.det_time_ms = det_time_ms
            sorted_ocr.rec_time_ms = rec_time_ms
            sorted_ocr.sort_time_ms = sort_time_ms
            return sorted_ocr

        except Exception as error:
            logger.warning("OCR unavailable: %s", str(error))
            duration_ms = (time.time() - t0) * 1000.0
            return OCRResult(boxes=[], full_text="", time_taken_ms=duration_ms)
