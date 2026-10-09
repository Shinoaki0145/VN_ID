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

    def _detect_corners(self, image: np.ndarray) -> list[tuple[int, int]] | None:
        """Find a large card-shaped contour, including cards surrounded by scenery."""
        image_area = image.shape[0] * image.shape[1]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 40, 120)
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates = [
            cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)
            for contour in contours if cv2.contourArea(contour) > 0.12 * image_area
        ]

        # Pale cyan/green security background can locate edges that blend into
        # the photograph. A red stamp may split the mask into large components.
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, (50, 12, 60), (130, 255, 255))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
        colored, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        large = [contour for contour in colored if cv2.contourArea(contour) > 0.04 * image_area]
        if large:
            hull = cv2.convexHull(np.concatenate(large))
            candidates.append(cv2.approxPolyDP(hull, 0.025 * cv2.arcLength(hull, True), True))

        plausible = []
        for polygon in candidates:
            area = cv2.contourArea(polygon)
            if len(polygon) != 4 or not cv2.isContourConvex(polygon) or not 0.12 < area / image_area < 0.90:
                continue
            _, (width, height), _ = cv2.minAreaRect(polygon)
            if min(width, height) <= 0 or not 1.4 < max(width, height) / min(width, height) < 1.85:
                continue
            points = polygon.reshape(4, 2)
            sums = points.sum(axis=1)
            differences = np.diff(points, axis=1).ravel()
            ordered = points[[sums.argmin(), differences.argmin(), sums.argmax(), differences.argmax()]]
            if len(np.unique(ordered, axis=0)) == 4:
                lengths = np.linalg.norm(np.roll(ordered, -1, axis=0) - ordered, axis=1)
                # A fingerprint's white background can erase a color-mask
                # corner. Reject severely unequal opposing edges rather than
                # cropping through the issuer/date with an incomplete hull.
                if all(max(lengths[i], lengths[i + 2]) / min(lengths[i], lengths[i + 2]) < 1.5 for i in (0, 1)):
                    plausible.append((area, ordered))
        if not plausible:
            return None
        _, ordered = max(plausible, key=lambda candidate: candidate[0])
        return [(int(x), int(y)) for x, y in ordered]

    def align(self, image: np.ndarray, corners: list[tuple[int, int]] | None = None) -> AlignedCardResult:
        """Warp supplied/detected card corners; resize if no reliable contour exists."""
        if corners is None:
            corners = self._detect_corners(image)
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
