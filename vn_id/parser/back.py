"""Backward-compatible back extraction facade."""
from vn_id.core.schemas import BackSideResult
from vn_id.parser.factory import CardParserFactory


class BackRuleExtractor:
    @classmethod
    def extract(cls, text: str, mrz_text: str | None = None) -> BackSideResult:
        return CardParserFactory().parse_back(text, mrz_text)
