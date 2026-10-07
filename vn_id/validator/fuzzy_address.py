"""Address normalization and administrative unit matching."""
import re
from vn_id.core.constants import PROVINCE_CODES

class AddressFuzzyMatcher:
    """Normalizes address punctuation and calculates similarity against administrative units."""

    @classmethod
    def normalize_address(cls, address: str | None) -> str | None:
        """Cleans up punctuation, spaces, and formatting without hardcoded dictionary replacements."""
        if not address:
            return None
        cleaned = address.strip().replace(";", ",")
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = re.sub(r"\s+([,.;])", r"\1", cleaned)
        cleaned = re.sub(r",([^\s])", r", \1", cleaned)
        cleaned = re.sub(r"(,\s*)+", ", ", cleaned)
        cleaned = cleaned.rstrip(".,;")
        return cleaned

    @classmethod
    def match_province(cls, address: str | None) -> tuple[str | None, float]:
        """Finds most matching province in address string."""
        if not address:
            return None, 0.0

        addr_upper = address.upper()
        for code, province_name in PROVINCE_CODES.items():
            if province_name.upper() in addr_upper:
                return province_name, 1.0

        return None, 0.5

