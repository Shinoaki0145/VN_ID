"""Core components, schemas and constants for VN_ID."""
from vn_id.core.schemas import (
    CardSide,
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
from vn_id.core.constants import PROVINCE_CODES, GENDER_CENTURY_MAP

__all__ = [
    "CardSide",
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
    "GENDER_CENTURY_MAP",
]

