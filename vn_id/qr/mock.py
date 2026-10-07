"""Mock QR Decoder for fast independent testing."""
from typing import Any
from vn_id.core.schemas import QRResult


class MockQRDecoder:
    """Mock QR Decoder returning predefined valid or unreadable QR result."""

    def __init__(self, is_detected: bool = True):
        self.is_detected = is_detected

    def decode(self, image: Any = None) -> QRResult:
        if not self.is_detected:
            return QRResult(is_detected=False)

        return QRResult(
            is_detected=True,
            raw_payload="001098012345|012345678|NGUYỄN VĂN A|15081998|Nam|Số 1 Đại Cồ Việt, Hai Bà Trưng, Hà Nội|25052021",
            id="001098012345",
            cmnd_old="012345678",
            name="NGUYỄN VĂN A",
            dob="15/08/1998",
            gender="Nam",
            address="Số 1 Đại Cồ Việt, Hai Bà Trưng, Hà Nội",
            issue_date="25/05/2021",
        )

