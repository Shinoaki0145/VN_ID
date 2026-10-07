"""Card perspective alignment and QR region cropping."""
from typing import Any
import cv2
import numpy as np
from vn_id.core.config import STANDARD_CARD_WIDTH, STANDARD_CARD_HEIGHT
from vn_id.core.schemas import AlignedCardResult, CardSide


class CardAligner:
    """Card perspective transformation and region crop engine."""

    TARGET_WIDTH = STANDARD_CARD_WIDTH
    TARGET_HEIGHT = STANDARD_CARD_HEIGHT

    def __init__(self, target_width: int = STANDARD_CARD_WIDTH, target_height: int = STANDARD_CARD_HEIGHT):
        self.target_width = target_width
        self.target_height = target_height

    def warp_perspective(
        self, image: np.ndarray, corners: list[tuple[int, int]] | np.ndarray
    ) -> np.ndarray:
        """Warp card using 4 corner points [TL, TR, BR, BL] to standard ID-1 ratio."""
        pts_src = np.array(corners, dtype=np.float32)
        pts_dst = np.array(
            [
                [0, 0],
                [self.target_width - 1, 0],
                [self.target_width - 1, self.target_height - 1],
                [0, self.target_height - 1],
            ],
            dtype=np.float32,
        )

        matrix = cv2.getPerspectiveTransform(pts_src, pts_dst)
        warped = cv2.warpPerspective(
            image, matrix, (self.target_width, self.target_height)
        )
        return warped

    def crop_qr_region(self, aligned_image: np.ndarray) -> np.ndarray:
        """Crop top-right region for QR detection.
        
        - CCCD 2021 (front): smaller QR (y <= 28%, x >= 77%)
        - Can cuoc 2024 (back): larger QR (y <= 42%, x >= 70%)
        Taking x >= 65% and y <= 45% captures both formats reliably.
        """
        h, w = aligned_image.shape[:2]
        y_max = int(h * 0.45)
        x_min = int(w * 0.65)
        return aligned_image[0:y_max, x_min:w].copy()

    def align(self, image: np.ndarray, corners: list[tuple[int, int]] | None = None) -> AlignedCardResult:
        """Align input card image. If corners are given, performs warp; otherwise resizes to standard size."""
        if corners and len(corners) == 4:
            aligned = self.warp_perspective(image, corners)
            is_aligned = True
            conf = 0.95
        else:
            # Fallback resize
            aligned = cv2.resize(image, (self.target_width, self.target_height))
            corners = [
                (0, 0),
                (self.target_width, 0),
                (self.target_width, self.target_height),
                (0, self.target_height),
            ]
            is_aligned = False
            conf = 0.50

        qr_crop = self.crop_qr_region(aligned)
        return AlignedCardResult(
            aligned_image=aligned,
            qr_crop_image=qr_crop,
            side=CardSide.UNKNOWN,
            corners=corners,
            is_aligned=is_aligned,
            confidence=conf,
        )

