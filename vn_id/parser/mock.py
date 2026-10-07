"""Mock rule-based extractor for fast offline testing."""
from vn_id.core.schemas import FrontSideResult


class MockRuleExtractor:
    """Mock extractor returning realistic synthetic CCCD front entities."""

    def extract(self, text: str) -> FrontSideResult:
        return FrontSideResult(
            id="001098012345",
            name="NGUYỄN VĂN A",
            dob="15/08/1998",
            gender="Nam",
            nationality="Việt Nam",
            origin="Kim Liên, Nam Đàn, Nghệ An",
            residence="Dịch Vọng Hậu, Cầu Giấy, Hà Nội",
            expiry_date="15/08/2038",
            extraction_source="mock_rule",
            confidence_scores={
                "id": 1.0,
                "name": 1.0,
                "dob": 1.0,
            },
        )

