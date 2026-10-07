"""Card side classification module (FRONT vs BACK)."""
import re
from vn_id.core.schemas import CardSide
from vn_id.core.utils import remove_accents


class SideClassifier:
    """Classifies whether a card image/text belongs to the FRONT or BACK side."""

    # 5 dấu hiệu cốt lõi mặt trước (hỗ trợ cả CCCD 2021 & Căn cước 2024)
    FRONT_PATTERNS = [
        r"CAN\s+CUOC",                # "Căn cước" / "Căn cước công dân"
        r"HO.*TEN",                   # "Họ và tên" / "Họ, chữ đệm và tên khai sinh"
        r"NGAY.*SINH",                # "Ngày sinh" / "Ngày, tháng, năm sinh"
        r"GIOI\s+TINH",               # "Giới tính"
        r"QUOC\s+TICH",               # "Quốc tịch"
    ]

    # 4 dấu hiệu cốt lõi mặt sau
    BACK_PATTERNS = [
        r"NGAY.*THANG.*NAM",          # "Ngày, tháng, năm" (ngày cấp / hết hạn)
        r"BO\s+CONG\s+AN",            # Nơi cấp thẻ Căn cước 2024
        r"CUC\s+(TRUONG|CANH\s+SAT)", # Nơi cấp thẻ CCCD 2021
        r"IDVNM",                     # Mã MRZ ở đáy mặt sau CCCD gắn chip
    ]

    @classmethod
    def classify_text(cls, text: str) -> CardSide:
        """Classify side from OCR text using accent-insensitive regex."""
        if not text:
            return CardSide.UNKNOWN

        clean_text = remove_accents(text).upper()

        front_score = sum(
            1 for pattern in cls.FRONT_PATTERNS if re.search(pattern, clean_text)
        )
        back_score = sum(
            1 for pattern in cls.BACK_PATTERNS if re.search(pattern, clean_text)
        )

        if front_score == 0 and back_score == 0:
            return CardSide.UNKNOWN

        if front_score >= back_score:
            return CardSide.FRONT
        else:
            return CardSide.BACK
