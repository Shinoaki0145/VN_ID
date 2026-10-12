"""Shared contract for version-specific card parsers."""
from abc import ABC, abstractmethod

from vn_id.core.schemas import CardVersion, FrontSideResult, BackSideResult, MRZResult
from vn_id.parser.common import parse_front_fields


class BaseCardParser(ABC):
    @property
    @abstractmethod
    def version(self) -> CardVersion:
        """Version assigned when this strategy is explicitly selected."""

    def parse_front(self, text: str) -> FrontSideResult:
        """Both layouts share identity rules; retain tolerant OCR recovery."""
        return parse_front_fields(text, self.version)

    @abstractmethod
    def parse_back(
        self, text: str, mrz: MRZResult | None = None, *, mrz_text: str | None = None,
    ) -> BackSideResult:
        """Parse the back with either a checked MRZ result or raw MRZ OCR."""
