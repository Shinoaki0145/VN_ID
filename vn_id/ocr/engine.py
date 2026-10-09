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
from vn_id.core.utils import remove_accents
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
                config["cnn"]["pretrained"] = False

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

    @staticmethod
    def _preserves_fragments(parts: list[str], candidate: str) -> bool:
        """Keep every recognized fragment, including its punctuation, in order."""
        offset = 0
        for part in parts:
            found = candidate.find(part, offset)
            if found < 0:
                return False
            offset = found + len(part)
        return candidate != " ".join(parts)

    def _recover_front_address_lines(self, image: np.ndarray, boxes: list[TextBox], recognizer) -> None:
        """Re-read address rows when DBNet split characters between adjacent boxes."""
        h, w = image.shape[:2]
        lines = self.sorter._group_and_sort_lines([b for b in boxes if b.bbox[0] >= 0.26 * w])

        def read(x1: int, y1: int, x2: int, y2: int) -> tuple[str, float]:
            crop = image[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
            if crop.size == 0:
                return "", 0.0
            value, prob = recognizer.predict(
                Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)), return_prob=True,
            )
            return unicodedata.normalize("NFC", value.strip()), float(prob)

        for previous, line in zip(lines, lines[1:]):
            header = remove_accents(" ".join(box.text for box in previous)).upper()
            if not any(anchor in header for anchor in ("QUE QUAN", "NOI THUONG TRU", "NOI CU TRU")):
                continue
            if len(line) == 1 and "QUE QUAN" in header:
                box = line[0]
                x1, y1, x2, y2 = box.bbox
                if "," in box.text and y2 - y1 >= 15:
                    rereads = [read(x1, y1 + top_trim, x2, y2 - 3) for top_trim in (4, 6)]
                    candidate = rereads[0][0]
                    if (candidate != box.text and all(
                        value == candidate and prob >= max(0.85, box.confidence - 0.02)
                        for value, prob in rereads
                    ) and remove_accents(candidate) == remove_accents(box.text)):
                        box.text = candidate
                        box.confidence = min(prob for _, prob in rereads)
                continue
            if len(line) < 2:
                continue
            line = sorted(line, key=lambda box: box.bbox[0])
            x1 = min(box.bbox[0] for box in line)
            x2 = max(box.bbox[2] for box in line)
            y1 = min(box.bbox[1] for box in line)
            y2 = max(box.bbox[3] for box in line)
            for top_pad in (2, 3):
                candidate, prob = read(x1, y1 - top_pad, x2, y2 + 3)
                if prob >= 0.8 and self._preserves_fragments([box.text for box in line], candidate):
                    boxes[:] = [box for box in boxes if box not in line]
                    boxes.append(TextBox(bbox=[x1, y1, x2, y2], text=candidate, confidence=prob))
                    break
            else:
                left, right = line[:2]
                gap_end = right.bbox[0] + round(0.12 * max(y2 - y1, 1))
                candidate, prob = read(left.bbox[0], y1 - 3, gap_end, y2 + 1)
                if prob >= 0.8 and self._preserves_fragments([left.text], candidate):
                    left.text = candidate
                    left.confidence = prob
                    left.bbox[2] = gap_end

        for line in lines:
            header = remove_accents(" ".join(box.text for box in line)).upper()
            if not any(anchor in header for anchor in ("NOI THUONG TRU", "NOI CU TRU")):
                continue
            for previous, box in zip(line, line[1:]):
                if not box.text.isdigit() or box.bbox[0] - previous.bbox[2] > 0.12 * w:
                    continue
                candidate, prob = read(
                    previous.bbox[2] - 4, min(previous.bbox[1], box.bbox[1]) - 3,
                    box.bbox[2] + 24, max(previous.bbox[3], box.bbox[3]) + 9,
                )
                if prob >= 0.8 and self._preserves_fragments([box.text], candidate):
                    box.text = candidate
                    box.confidence = prob
                    box.bbox[0] = previous.bbox[2]

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
            rejected_address_boxes: list[tuple[int, int, int, int]] = []
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
                        elif is_front and prob < 0.35 and ymin >= 0.8 * h and xmax >= 0.8 * w and box_h >= 0.07 * h:
                            rejected_address_boxes.append((xmin, xmax, ymin, ymax))
                    except Exception as error:
                        logger.warning("Text recognition unavailable: %s", str(error))

            if is_front and rejected_address_boxes:
                text_so_far = remove_accents(" ".join(box.text for box in boxes)).upper()
                if "QUE QUAN" in text_so_far and "NOI THUONG TRU" not in text_so_far:
                    try:
                        retry_start = time.time()
                        retry_h, _ = detector.detect(image, width_ths=0.3, canvas_size=1600)
                        det_time_ms += (time.time() - retry_start) * 1000.0
                        retry_boxes = []
                        for raw in (retry_h[0] if retry_h else []):
                            xmin, xmax, ymin, ymax = map(int, raw)
                            if xmin < 0.27 * w or not any(
                                bad_y <= ymin < bad_y + 0.4 * (bad_bottom - bad_y)
                                for _, _, bad_y, bad_bottom in rejected_address_boxes
                            ):
                                continue
                            crop = image[max(0, ymin - 4):min(h, ymax + 4), max(0, xmin - 2):min(w, xmax + 2)]
                            if crop.size == 0:
                                continue
                            value, prob = recognizer.predict(
                                Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)), return_prob=True,
                            )
                            if value.strip() and prob >= 0.35:
                                retry_boxes.append(TextBox(
                                    bbox=[xmin, ymin, xmax, ymax],
                                    text=unicodedata.normalize("NFC", value.strip()), confidence=float(prob),
                                ))
                        boxes.extend(retry_boxes)
                    except Exception as error:
                        logger.warning("Address retry unavailable; keeping ordinary OCR: %s", error)

            if is_front and boxes:
                original_boxes = [box.model_copy(deep=True) for box in boxes]
                try:
                    self._recover_front_address_lines(image, boxes, recognizer)
                except Exception as error:
                    boxes = original_boxes
                    logger.warning("Address line recovery unavailable; keeping ordinary OCR: %s", error)
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
