"""Instance-owned strategy registry and OCR version detection."""
import re
from collections.abc import Mapping

from vn_id.core.schemas import CardSide, CardVersion, FrontSideResult, BackSideResult
from vn_id.core.utils import remove_accents
from vn_id.parser.base import BaseCardParser
from vn_id.parser.strategies import CCCD2021Parser, CanCuoc2024Parser, UnknownCardParser


class CardParserFactory:
    def __init__(self, parsers: Mapping[CardVersion, BaseCardParser] | None = None):
        self._parsers = {
            CardVersion.CCCD_2021: CCCD2021Parser(),
            CardVersion.CAN_CUOC_2024: CanCuoc2024Parser(),
            CardVersion.UNKNOWN: UnknownCardParser(),
        }
        if parsers is not None:
            self._parsers.update(parsers)

    def get_parser(self, version: CardVersion | str) -> BaseCardParser:
        return self._parsers[CardVersion(version)]

    def detect_and_get(self, text: str, side: CardSide) -> BaseCardParser:
        return self.get_parser(self.detect_version(text, side))

    def parse_front(self, text: str) -> FrontSideResult:
        return self.detect_and_get(text, CardSide.FRONT).parse_front(text)

    def parse_back(self, text: str, mrz_text: str | None = None) -> BackSideResult:
        return self.detect_and_get(text, CardSide.BACK).parse_back(text, mrz_text=mrz_text)

    @staticmethod
    def detect_version(text: str, side: CardSide) -> CardVersion:
        side = CardSide(side)
        if side == CardSide.FRONT:
            return CardParserFactory._detect_front(text)
        if side == CardSide.BACK:
            return CardParserFactory._detect_back(text)
        return CardVersion.UNKNOWN

    @staticmethod
    def _detect_front(text: str) -> CardVersion:
        """Use the front title only; abstain if OCR did not read it clearly."""
        lines = [remove_accents(line).upper().strip() for line in text.splitlines() if line.strip()][:5]
        for index, line in enumerate(lines):
            if re.fullmatch(r"CAN\s+CUOC\s+CONG\s+DAN", line):
                return CardVersion.CCCD_2021
            if line == "CAN CUOC" and index + 1 < len(lines) and lines[index + 1] == "CONG DAN":
                return CardVersion.CCCD_2021
        old_layout = any(
            marker in remove_accents(text).upper()
            for marker in ("NOI THUONG TRU", "QUE QUAN", "CO GIA TRI DEN")
        )
        for index, line in enumerate(lines):
            if line == "CAN CUOC" and not old_layout and (
                index + 1 == len(lines) or not lines[index + 1].startswith("CONG")
            ):
                return CardVersion.CAN_CUOC_2024
        return CardVersion.UNKNOWN

    @staticmethod
    def _detect_back(text: str) -> CardVersion:
        clean_text = remove_accents(text).upper()

        is_2024 = (
            "BO CONG AN" in clean_text
            or "NOI CU TRU" in clean_text
            or "NOI CUTRU" in clean_text
            or "NOI CULRU" in clean_text
            or "NOI DANG KY KHAI SINH" in clean_text
            or "NOI DANG KI KHAI SINH" in clean_text
            or "KHAI SINH" in clean_text
            or "PLACE OF RESIDENCE" in clean_text
            or "RESIDENC" in clean_text
            or "PLACE OF BIRTH" in clean_text
            or "MINISTRY OF PUBLIC SECURITY" in clean_text
            or re.search(r"NGAY[^\d]{1,20}THANG[^\d]{1,20}NAM\s+HET\s+HAN", clean_text)
            or re.search(r"NGAY[^\d]{1,20}THANG[^\d]{1,20}NAM\s+CAP", clean_text)
        )

        is_2021 = (
            "CUC TRUONG" in clean_text
            or "CUC CANH SAT" in clean_text
            or "QUAN LY HANH CHINH" in clean_text
            or "TRAT TU XA HOI" in clean_text
        )

        return CardVersion.CAN_CUOC_2024 if is_2024 else (CardVersion.CCCD_2021 if is_2021 else CardVersion.UNKNOWN)

