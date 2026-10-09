"""Common regex patterns and normalization helpers for rule-based extraction."""
import re
from vn_id.core.utils import remove_accents

DATE_PATTERN = r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})"

# Regex pattern for residence / nơi cư trú / nơi thường trú
RESIDENCE_PATTERN = re.compile(
    r"^(?:[^\w]*)(?:NOI\s*C[UƯ][LT]RU|NOI\s*C[UƯ]\s*TR[UÚ]|NOI\s*THUONG\s*TRU|NOI\s*THUONGTRU)"
    r"(?:\s*[/:]?\s*(?:[Jj]?\s*PLACE\s*O[TF]?\s*RESIDENC[EO]?|RESIDENC[EO]?))?[:\s\-\/;]*"
    r"|"
    r"^(?:[^\w]*)(?:[Jj]?\s*PLACE\s*O[TF]?\s*RESIDENC[EO]?|RESIDENC[EO]?)[:\s\-\/;]*",
    re.IGNORECASE,
)

# Regex pattern for origin / nơi đăng ký khai sinh / quê quán
ORIGIN_PATTERN = re.compile(
    r"^(?:[^\w]*)(?:NOI\s*[6ĐD]ANG\s*K[YÝIÍ]\s*KHAI\s*SINH|NOI\s*DKKS|QUE\s*QUAN|QUEQUAN)"
    r"(?:\s*[/:]?\s*(?:[Jj]?\s*PLACE\s*O[/TF]?\s*(?:B[IỈ][R]?TH|ORIGIN)|B[IỈ][R]?TH|ORIGIN))?[:\s\-\/;]*"
    r"|"
    r"^(?:[^\w]*)(?:[Jj]?\s*PLACE\s*O[/TF]?\s*(?:B[IỈ][R]?TH|ORIGIN)|B[IỈ][R]?TH|ORIGIN)[:\s\-\/;]*",
    re.IGNORECASE,
)

HEADER_EXCLUSIONS_FRONT = [
    "CONG HOA",
    "XA HOI",
    "CHU NGHIA",
    "VIET NAM",
    "DOC LAP",
    "TU DO",
    "HANH PHUC",
    "CAN CUOC",
    "CONG DAN",
    "CHUNG MINH",
    "NHAN DAN",
    "IDENTITY",
    "CARD",
    "CITIZEN",
    "SO / NO",
    "SO DINH DANH",
    "GIOI TINH",
    "QUOC TICH",
    "QUE QUAN",
    "NOI THUONG TRU",
    "NOI CU TRU",
]

HEADER_EXCLUSIONS_BACK = [
    "NOI DANG KY",
    "DANG KY KHAI SINH",
    "PLACE OF BIRTH",
    "PLACE O/ BIRTH",
    "NOI CU TRU",
    "NOI THUONG TRU",
    "PLACE OF RESIDENCE",
    "NGAY",
    "DATE",
    "BO CONG AN",
    "MINISTRY OF",
    "IDVNM",
    "CUC TRUONG",
    "CUC CANH SAT",
]

HEADER_EXCLUSIONS_ADDR = [
    "CO GIA TRI", "GIA TRI DEN", "DATE OF EXPIRY", "EXPIRY", "HET HAN",
    "SO / NO", "SO DINH DANH", "CAN CUOC", "GIOI TINH", "QUOC TICH",
    "QUE QUAN", "NOI DANG KY", "CONG HOA", "NOI CU TRU", "NOI THUONG TRU",
    "PLACE OF RESIDENCE", "PLACE OF BIRTH", "NGAY", "DATE",
]


def clean_address_value(val: str) -> str:
    """Cleans up leading English labels or noisy symbols from address values."""
    val = re.sub(
        r"^(?:[IJj]?\s*PLACE\s*(?:O[TF]?\s*)?RESIDENC[EO]?|RESIDENC[EO]?)\s*[:\-\/;]*\s*",
        "",
        val,
        flags=re.IGNORECASE,
    )
    val = re.sub(
        r"^(?:[Jj]?\s*PLACE\s*O[/TF]?\s*(?:B[IỈ][R]?TH|ORIGIN)|B[IỈ][R]?TH|ORIGIN)\s*[:\-\/;]*\s*",
        "",
        val,
        flags=re.IGNORECASE,
    )
    return val.strip(" :-,;/")

