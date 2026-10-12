"""Backward-compatible front extraction facade."""
from vn_id.core.schemas import CardSide, CardVersion, FrontSideResult
from vn_id.parser.common import extract_front_raw
from vn_id.parser.factory import CardParserFactory


class FrontRuleExtractor:
    @staticmethod
    def detect_card_version(text: str) -> CardVersion:
        return CardParserFactory.detect_version(text, CardSide.FRONT)

    @classmethod
    def extract_raw(cls, text: str) -> dict[str, str]:
        return extract_front_raw(text)

    @classmethod
    def extract(cls, text: str) -> FrontSideResult:
        return CardParserFactory().parse_front(text)
