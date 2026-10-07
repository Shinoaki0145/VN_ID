"""Mock aligner implementation for fast independent testing."""
import numpy as np
from vn_id.core.schemas import AlignedCardResult, CardSide


class MockAligner:
    """Mock aligner returning synthetic standard ID-1 (1000x630) images."""

    def __init__(self, side: CardSide = CardSide.FRONT):
        self.side = side

    def align(self, image: np.ndarray, corners: list[tuple[int, int]] | None = None) -> AlignedCardResult:
        aligned_image = np.zeros((630, 1000, 3), dtype=np.uint8)
        # 35% height = 220px, 30% width = 300px
        qr_crop = np.zeros((220, 300, 3), dtype=np.uint8) if self.side == CardSide.FRONT else None

        return AlignedCardResult(
            aligned_image=aligned_image,
            qr_crop_image=qr_crop,
            side=self.side,
            corners=[(0, 0), (1000, 0), (1000, 630), (0, 630)],
            is_aligned=True,
            confidence=0.99,
        )

