"""QR Code detector and CCCD payload parser."""
import re
import unicodedata
from typing import Any
import cv2
import numpy as np
from vn_id.core.config import QR_WEIGHTS_DIR
from vn_id.core.schemas import QRResult
from vn_id.core.utils import normalize_date


class QRDecoder:
    """Decodes QR codes from CCCD card images using QReader with zxing-cpp fallback."""

    def __init__(self, device: str = "cpu"):
        self.device = str(device).lower()
        self._qreader = None

    # def _get_qreader(self):
    #     if self._qreader is None:
    #         import os
    #         import logging
    #         import warnings
    #         if "YOLO_CONFIG_DIR" not in os.environ:
    #             os.environ["YOLO_CONFIG_DIR"] = "/tmp/Ultralytics"
    #         try:
    #             from ultralytics.utils import LOGGER
    #             LOGGER.setLevel(logging.ERROR)
    #         except Exception:
    #             pass
    #         from qreader import QReader

    #         weights_arg = str(QR_WEIGHTS_DIR) if QR_WEIGHTS_DIR.is_dir() else None

    #         with warnings.catch_warnings():
    #             warnings.filterwarnings("ignore")
    #             self._qreader = QReader(weights_folder=weights_arg, reencode_to=None)
    #             if self.device == "cuda":
    #                 try:
    #                     import torch
    #                     if torch.cuda.is_available():
    #                         self._qreader.detector.model.to("cuda")
    #                 except Exception:
    #                     pass
    #     return self._qreader

    def _get_qreader(self):
        if self._qreader is None:
            import os
            import logging
            import warnings

            if "YOLO_CONFIG_DIR" not in os.environ:
                os.environ["YOLO_CONFIG_DIR"] = "/tmp/Ultralytics"

            try:
                from ultralytics.utils import LOGGER
                LOGGER.setLevel(logging.ERROR)
            except Exception:
                pass

            from qreader import QReader

            weights_arg = (
                str(QR_WEIGHTS_DIR)
                if QR_WEIGHTS_DIR.is_dir()
                else None
            )

            with warnings.catch_warnings():
                warnings.filterwarnings("ignore")

                self._qreader = QReader(
                    weights_folder=weights_arg,
                    reencode_to="cp65001",
                )

            if str(self.device).startswith("cuda"):
                import torch

                if not torch.cuda.is_available():
                    raise RuntimeError(
                        "QRDecoder được cấu hình CUDA nhưng "
                        "torch.cuda.is_available() = False"
                    )

                detector = self._qreader.detector
                detector.model.to(self.device)
                original_predict = detector.model.predict

                def predict_on_cuda(*args, **kwargs):
                    if kwargs.get("device") is None:
                        kwargs["device"] = 0
                    return original_predict(*args, **kwargs)

                detector.model.predict = predict_on_cuda

        return self._qreader

    @staticmethod
    def _normalize_date(date_str: str | None) -> str | None:
        """Normalizes date string to DD/MM/YYYY format (wraps central normalize_date)."""
        return normalize_date(date_str)

    @classmethod
    def parse_payload(cls, raw_text: str | None) -> QRResult:
        """Parses pipe-delimited CCCD QR payload."""
        if not raw_text or "|" not in raw_text:
            return QRResult(is_detected=False, raw_payload=raw_text)

        raw_text = unicodedata.normalize("NFC", raw_text)
        parts = raw_text.split("|")
        # Standard CCCD has 6 or 7 parts:
        # [0]: ID (12 digits)
        # [1]: CMND_OLD (9 digits, optional)
        # [2]: Name
        # [3]: DOB (DDMMYYYY)
        # [4]: Gender
        # [5]: Address
        # [6]: Issue date (DDMMYYYY, optional)
        if len(parts) < 5:
            return QRResult(is_detected=False, raw_payload=raw_text)

        cccd_id = parts[0].strip() if len(parts[0].strip()) == 12 and parts[0].strip().isdigit() else None
        if not cccd_id:
            return QRResult(is_detected=False, raw_payload=raw_text)

        cmnd_old = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
        name = parts[2].strip() if len(parts) > 2 and parts[2].strip() else None
        dob = cls._normalize_date(parts[3]) if len(parts) > 3 and parts[3].strip() else None
        gender = parts[4].strip() if len(parts) > 4 and parts[4].strip() else None
        address = parts[5].strip() if len(parts) > 5 and parts[5].strip() else None
        issue_date = cls._normalize_date(parts[6]) if len(parts) > 6 and parts[6].strip() else None
        father_name = parts[8].strip() if len(parts) > 8 and parts[8].strip() else None
        mother_name = parts[9].strip() if len(parts) > 9 and parts[9].strip() else None

        return QRResult(
            is_detected=True,
            raw_payload=raw_text,
            id=cccd_id,
            cmnd_old=cmnd_old,
            name=name,
            dob=dob,
            gender=gender,
            address=address,
            issue_date=issue_date,
            father_name=father_name,
            mother_name=mother_name,
        )

    def decode(self, image: np.ndarray | None) -> QRResult:
        """Detect and decode QR code using QReader with zxing-cpp fallback."""
        if image is None or image.size == 0:
            return QRResult(is_detected=False)

        # 1. Primary: QReader (YOLOv8 QR detector + multi-step pyzbar decoder)
        try:
            if len(image.shape) == 2:
                rgb_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            elif image.shape[2] == 4:
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
            else:
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            qreader = self._get_qreader()
            decoded_texts = qreader.detect_and_decode(image=rgb_image)
            for text in decoded_texts:
                if text and "|" in text:
                    parsed = self.parse_payload(text)
                    if parsed.is_detected:
                        return parsed
        except Exception:
            pass

        # 2. Fallback: zxing-cpp
        try:
            import zxingcpp
            results = zxingcpp.read_barcodes(image)
            for r in results:
                if r.text and "|" in r.text:
                    parsed = self.parse_payload(r.text)
                    if parsed.is_detected:
                        return parsed
        except Exception:
            pass
        
        return QRResult(is_detected=False)

