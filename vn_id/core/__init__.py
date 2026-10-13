"""Core components, schemas and constants for VN_ID."""
from vn_id.core.schemas import (
    CardSide,
    CardVersion,
    AlignedCardResult,
    TextBox,
    OCRResult,
    NERResult,
    BackSideResult,
    QRResult,
    ValidationReport,
    CCCDData,
    FinalCCCDResult,
)
from vn_id.core.constants import PROVINCE_CODES, CENTURY_GENDER_TO_INFO

__all__ = [
    "CardSide",
    "CardVersion",
    "AlignedCardResult",
    "TextBox",
    "OCRResult",
    "NERResult",
    "BackSideResult",
    "QRResult",
    "ValidationReport",
    "CCCDData",
    "FinalCCCDResult",
    "PROVINCE_CODES",
    "CENTURY_GENDER_TO_INFO",
]

