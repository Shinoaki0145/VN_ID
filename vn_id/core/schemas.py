"""Pydantic data schemas for VN_ID pipeline stages."""
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field, ConfigDict


class CardSide(str, Enum):
    FRONT = "front"
    BACK = "back"
    UNKNOWN = "unknown"


class AlignedCardResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    aligned_image: Any = None
    qr_crop_image: Any | None = None
    side: CardSide = CardSide.UNKNOWN
    corners: list[tuple[int, int]] = Field(default_factory=list)
    is_aligned: bool = False
    confidence: float = 0.0


class TextBox(BaseModel):
    bbox: list[int]  # [x_min, y_min, x_max, y_max]
    text: str
    confidence: float = 1.0
    line_number: int = 0


class OCRResult(BaseModel):
    boxes: list[TextBox] = Field(default_factory=list)
    full_text: str = ""
    time_taken_ms: float = 0.0
    det_time_ms: float = 0.0
    rec_time_ms: float = 0.0
    sort_time_ms: float = 0.0


class FrontSideResult(BaseModel):
    """Result of front card entity extraction using rule-based parser."""
    id: str | None = None
    name: str | None = None
    dob: str | None = None  # DD/MM/YYYY
    gender: str | None = None
    nationality: str = "Việt Nam"
    origin: str | None = None  # Quê quán / Nơi đăng ký khai sinh
    residence: str | None = None  # Nơi thường trú / Nơi cư trú
    expiry_date: str | None = None  # Có giá trị đến
    extraction_source: str = "front_rules"
    confidence_scores: dict[str, float] = Field(default_factory=dict)


# Aliases for semantic clarity and backward compatibility
FrontExtractResult = FrontSideResult
NERResult = FrontSideResult


class BackSideResult(BaseModel):
    card_version: str = "unknown"  # "cccd_chip_2021" | "can_cuoc_2024" | "unknown"
    issue_date: str | None = None  # DD/MM/YYYY
    expiry_date: str | None = None  # DD/MM/YYYY (Thẻ Căn cước 2024)
    issue_loc: str | None = None  # Nơi cấp (Cục Cảnh sát QLHC về TTXH / Bộ Công an)
    origin: str | None = None  # Nơi đăng ký khai sinh (Thẻ Căn cước 2024)
    residence: str | None = None  # Nơi cư trú (Thẻ Căn cước 2024)
    mrz_raw: str | None = None
    raw_text: str = ""


class QRResult(BaseModel):
    is_detected: bool = False
    raw_payload: str | None = None
    id: str | None = None
    cmnd_old: str | None = None
    name: str | None = None
    dob: str | None = None  # DD/MM/YYYY
    gender: str | None = None
    address: str | None = None
    issue_date: str | None = None  # DD/MM/YYYY
    father_name: str | None = None  # Thông tin cha (Thẻ Căn cước 2024 dưới 14 tuổi)
    mother_name: str | None = None  # Thông tin mẹ (Thẻ Căn cước 2024 dưới 14 tuổi)


class ValidationReport(BaseModel):
    is_valid_12_digits: bool = False
    province_valid: bool = False
    gender_century_valid: bool = False
    birth_year_valid: bool = False
    address_fuzzy_score: float = 1.0
    warnings: list[str] = Field(default_factory=list)


class CCCDData(BaseModel):
    # Định danh & Nhân thân (Mặt trước / QR)
    id: str | None = None
    cmnd_old: str | None = None
    name: str | None = None
    dob: str | None = None  # DD/MM/YYYY
    gender: str | None = None
    nationality: str = "Việt Nam"
    origin: str | None = None  # Quê quán / Nơi ĐKKS
    residence: str | None = None  # Nơi thường trú / Nơi cư trú

    # Hiệu lực & Cấp thẻ (Mặt trước / Mặt sau)
    issue_date: str | None = None  # Ngày cấp
    expiry_date: str | None = None  # Ngày hết hạn / Có giá trị đến
    issue_loc: str | None = None  # Nơi cấp (Cục Cảnh sát QLHC về TTXH / Bộ Công an)

    # Thân nhân (Thẻ Căn cước 2024 dưới 14 tuổi)
    father_name: str | None = None
    mother_name: str | None = None


# Backward compatibility alias
CCCCDData = CCCDData


class FinalCCCDResult(BaseModel):
    success: bool = False
    side_detected: list[str] = Field(default_factory=list)
    data: CCCDData = Field(default_factory=CCCDData)
    field_sources: dict[str, str] = Field(default_factory=dict)
    validation: ValidationReport = Field(default_factory=ValidationReport)
    timings: dict[str, float] = Field(default_factory=dict)

