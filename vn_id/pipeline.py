"""CCCD extraction pipeline orchestrator connecting all 5 stages."""
import time
from typing import Any
import cv2
import numpy as np

from vn_id.core.schemas import (
    CardSide,
    FinalCCCDResult,
    AlignedCardResult,
    QRResult,
    NERResult,
    BackSideResult,
)
from vn_id.aligner import CardAligner, MockAligner, SideClassifier
from vn_id.ocr import OCREngine, MockOCREngine
from vn_id.parser import FrontRuleExtractor, BackRuleExtractor, MockRuleExtractor
from vn_id.qr import QRDecoder, MockQRDecoder
from vn_id.validator import DataFusion


class CCCDPipeline:
    """End-to-end pipeline orchestrator for Vietnamese CCCD / ID card extraction."""

    def __init__(self, device: str = "auto", mock_mode: bool = False):
        self.device = self._resolve_device(device)
        self.mock_mode = mock_mode

        if self.mock_mode:
            self.aligner = MockAligner()
            self.ocr_engine = MockOCREngine()
            self.front_extractor = MockRuleExtractor()
            self.qr_decoder = MockQRDecoder()
        else:
            self.aligner = CardAligner()
            self.qr_decoder = QRDecoder(device=self.device)
            self.ocr_engine = OCREngine(use_mock=False, device=self.device, qr_decoder=self.qr_decoder)
            self.front_extractor = FrontRuleExtractor

    @staticmethod
    def _resolve_device(device: str) -> str:
        if device == "auto":
            try:
                import torch
                return "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                return "cpu"
        return device

    @staticmethod
    def load_image(image_input: str | bytes | np.ndarray) -> np.ndarray:
        """Loads image from file path, raw bytes, or numpy array."""
        if isinstance(image_input, np.ndarray):
            return image_input
        elif isinstance(image_input, bytes):
            nparr = np.frombuffer(image_input, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Could not decode image from provided bytes.")
            return img
        elif isinstance(image_input, str):
            img = cv2.imread(image_input)
            if img is None:
                raise ValueError(f"Could not read image from path: {image_input}")
            return img
        else:
            raise TypeError(f"Unsupported image input type: {type(image_input)}")

    def process(
        self,
        image: str | bytes | np.ndarray,
        force_side: CardSide | None = None,
    ) -> FinalCCCDResult:
        """Processes a single card image (auto-detects or enforces front/back)."""
        timings: dict[str, float] = {}
        t_start = time.time()

        img = self.load_image(image)

        # 1. Aligner
        t0 = time.time()
        align_res = self.aligner.align(img)
        timings["align_ms"] = (time.time() - t0) * 1000.0

        # Determine side
        side = force_side
        if not side or side == CardSide.UNKNOWN:
            # Run quick OCR to detect side
            ocr_pre = self.ocr_engine.recognize(align_res.aligned_image, is_front=True)
            side = SideClassifier.classify_text(ocr_pre.full_text)
            if side == CardSide.UNKNOWN:
                side = CardSide.FRONT  # default front

        if side == CardSide.FRONT:
            # Front Side Workflow
            t_qr = time.time()
            qr_res = self.qr_decoder.decode(align_res.qr_crop_image)
            if not qr_res.is_detected:
                qr_res = self.qr_decoder.decode(img)
            timings["qr_ms"] = (time.time() - t_qr) * 1000.0

            t_ocr = time.time()
            ocr_res = self.ocr_engine.recognize(align_res.aligned_image, is_front=True)
            timings["ocr_det_ms"] = ocr_res.det_time_ms
            timings["ocr_rec_ms"] = ocr_res.rec_time_ms
            timings["ocr_sort_ms"] = ocr_res.sort_time_ms
            timings["ocr_ms"] = (time.time() - t_ocr) * 1000.0

            t_front = time.time()
            front_res = self.front_extractor.extract(ocr_res.full_text)
            timings["front_rules_ms"] = (time.time() - t_front) * 1000.0

            fused_result = DataFusion.fuse(
                qr=qr_res,
                front=front_res,
                back=None,
                side_detected=["front"],
                timings=timings,
            )
            total_ms = (time.time() - t_start) * 1000.0
            timings["total_ms"] = total_ms
            fused_result.timings["total_ms"] = total_ms
            return fused_result
        else:
            # Back Side Workflow (Check QR on back side e.g. for 2024 card)
            t_qr = time.time()
            qr_res = self.qr_decoder.decode(align_res.qr_crop_image)
            if not qr_res.is_detected:
                qr_res = self.qr_decoder.decode(img)
            timings["qr_ms"] = (time.time() - t_qr) * 1000.0

            t_ocr = time.time()
            ocr_res = self.ocr_engine.recognize(align_res.aligned_image, is_front=False)
            timings["ocr_det_ms"] = ocr_res.det_time_ms
            timings["ocr_rec_ms"] = ocr_res.rec_time_ms
            timings["ocr_sort_ms"] = ocr_res.sort_time_ms
            timings["ocr_ms"] = (time.time() - t_ocr) * 1000.0

            t_back = time.time()
            back_res = BackRuleExtractor.extract(ocr_res.full_text)
            timings["back_rules_ms"] = (time.time() - t_back) * 1000.0

            fused_result = DataFusion.fuse(
                qr=qr_res,
                front=None,
                back=back_res,
                side_detected=["back"],
                timings=timings,
            )
            total_ms = (time.time() - t_start) * 1000.0
            timings["total_ms"] = total_ms
            fused_result.timings["total_ms"] = total_ms
            return fused_result

    def process_both_sides(
        self,
        front_image: str | bytes | np.ndarray,
        back_image: str | bytes | np.ndarray,
    ) -> FinalCCCDResult:
        """Processes front and back card images together and merges them into one complete profile."""
        timings: dict[str, float] = {}
        t_start = time.time()

        # Process front
        img_front = self.load_image(front_image)
        t_align_front = time.time()
        align_front = self.aligner.align(img_front)
        timings["front_align_ms"] = (time.time() - t_align_front) * 1000.0

        t_qr = time.time()
        qr_res = self.qr_decoder.decode(align_front.qr_crop_image)
        if not qr_res.is_detected:
            qr_res = self.qr_decoder.decode(img_front)
        timings["qr_ms"] = (time.time() - t_qr) * 1000.0

        t_ocr_front = time.time()
        ocr_front = self.ocr_engine.recognize(align_front.aligned_image, is_front=True)
        timings["front_ocr_det_ms"] = ocr_front.det_time_ms
        timings["front_ocr_rec_ms"] = ocr_front.rec_time_ms
        timings["front_ocr_sort_ms"] = ocr_front.sort_time_ms
        timings["front_ocr_ms"] = (time.time() - t_ocr_front) * 1000.0

        t_front = time.time()
        front_res = self.front_extractor.extract(ocr_front.full_text)
        timings["front_rules_ms"] = (time.time() - t_front) * 1000.0

        # Process back
        img_back = self.load_image(back_image)
        t_align_back = time.time()
        align_back = self.aligner.align(img_back)
        timings["back_align_ms"] = (time.time() - t_align_back) * 1000.0

        # If QR not found on front (e.g. 2024 card where QR is on the back), decode on back
        if not qr_res or not qr_res.is_detected:
            t_qr_back = time.time()
            qr_res = self.qr_decoder.decode(align_back.qr_crop_image)
            if not qr_res.is_detected:
                qr_res = self.qr_decoder.decode(img_back)
            timings["qr_ms"] += (time.time() - t_qr_back) * 1000.0

        t_ocr_back = time.time()
        ocr_back = self.ocr_engine.recognize(align_back.aligned_image, is_front=False)
        timings["back_ocr_det_ms"] = ocr_back.det_time_ms
        timings["back_ocr_rec_ms"] = ocr_back.rec_time_ms
        timings["back_ocr_sort_ms"] = ocr_back.sort_time_ms
        timings["back_ocr_ms"] = (time.time() - t_ocr_back) * 1000.0

        t_back_rules = time.time()
        back_res = BackRuleExtractor.extract(ocr_back.full_text)
        timings["back_rules_ms"] = (time.time() - t_back_rules) * 1000.0

        fused_result = DataFusion.fuse(
            qr=qr_res,
            front=front_res,
            back=back_res,
            side_detected=["front", "back"],
            timings=timings,
        )
        total_ms = (time.time() - t_start) * 1000.0
        timings["total_ms"] = total_ms
        fused_result.timings["total_ms"] = total_ms
        return fused_result
