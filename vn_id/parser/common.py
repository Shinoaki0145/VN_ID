"""Common regex patterns and normalization helpers for rule-based extraction."""
from datetime import date
import re
from vn_id.core.constants import PROVINCE_CODES
from vn_id.core.schemas import CardVersion, FrontSideResult
from vn_id.core.utils import remove_accents, normalize_date

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

FRONT_ORIGIN_PATTERN = re.compile(
    ORIGIN_PATTERN.pattern + r"|^[^\w]*QUO\s*QUAN[:\s/;-]*", re.IGNORECASE,
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
    "SOCIAL",
    "REPUB",
    "NGAY SINH",
    "DATE OF BIRTH",
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
        r"^(?:[IJj]?\s*PLACE\s*(?:O[TF]?\s*)?T?RESIDENC[EO]?|T?RESIDENC[EO]?)\s*[:\-\/;]*\s*",
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


def clean_front_address_value(val: str) -> str:
    val = clean_address_value(val)
    return re.sub(r"^(?:[IJj]?\s*)?P[LH]ACE\s+(?:OF?\s+ORG+IN|NO\b)[:\s/;-]*", "", val, flags=re.IGNORECASE).strip(" :-,;/")


def is_front_field_header(val: str) -> bool:
    clean = remove_accents(val).upper()
    return any(clean.startswith(header) for header in HEADER_EXCLUSIONS_ADDR) or bool(
        RESIDENCE_PATTERN.search(clean) or FRONT_ORIGIN_PATTERN.search(clean)
        or re.match(r"^[IJ/ ]*PLACE\b", clean) or re.fullmatch(DATE_PATTERN, clean)
    )


def extract_front_raw(text: str) -> dict[str, str]:
    results: dict[str, str] = {}
    has_origin_label = False
    if not text:
        return results

    lines = [line.strip() for line in text.split("\n") if line.strip()]

    # 1. Extract 12-digit ID
    m_id = re.search(r"\b(\d{12})\b", text)
    if m_id:
        results["id"] = m_id.group(1)

    # 2. Extract DOB (DD/MM/YYYY or DDMMYYYY with OCR typo tolerance)
    m_dob_slash = re.search(r"\b" + DATE_PATTERN + r"\b", text)
    if m_dob_slash:
        d, m, y = m_dob_slash.groups()
        results["dob"] = normalize_date(d, m, y)
    else:
        # 8 consecutive chars where year is 19xx or 20xx (supporting OCR typos like 'c' or 'o' for '0')
        m_dob_raw = re.search(r"\b(\d{2})[/.-]?(\d{2})[/.-]?([12]\d[0-9cCooOO]{2})\b", text)
        if m_dob_raw:
            d, m, y_raw = m_dob_raw.groups()
            y = y_raw.replace("c", "0").replace("C", "0").replace("o", "0").replace("O", "0")
            results["dob"] = normalize_date(d, m, y)

    # Prefer the labelled identity region to uppercase text in the header.
    name_lines = lines
    name_pattern = (
        r"(?:HO\s*(?:,\s*CHU\s*DEM\s*)?(?:VA\s*)?TEN(?:\s*KHAI\s*SINH)?"
        r"(?:\s*[/I|]?\s*FULL\s*NAM[EO]?)?|FULL\s*NAM[EO]?)[:\s/|;-]*"
    )
    for i, line in enumerate(lines):
        label = re.search(name_pattern, remove_accents(line).upper())
        if label:
            name_lines = []
            for candidate_line in lines[i:]:
                candidate_label = re.search(name_pattern, remove_accents(candidate_line).upper())
                value = candidate_line[candidate_label.end():].strip() if candidate_label else candidate_line
                if not value:
                    continue
                next_field = re.search(
                    r"\b(?:NGAY(?:,\s*THANG,\s*NAM)?\s*SINH|DATE\s*OF\s*BIRTH|GIOI\s*TINH|SEX|QUOC\s*TICH|NATIONALITY)",
                    remove_accents(value).upper(),
                )
                name_lines = [value[:next_field.start()].strip() if next_field else value]
                break
            break
    # 3. Extract Name candidate
    for line in name_lines:
        clean_l = remove_accents(line).upper()
        if any(h in clean_l for h in HEADER_EXCLUSIONS_FRONT):
            continue
        words = [
            w for w in line.split()
            if len(w) >= 2 and sum(1 for c in w if c.isupper()) >= (len(w) // 2 + 1)
        ]
        if 2 <= len(words) <= 5:
            candidate = " ".join(w.upper() for w in words)
            clean_cand = remove_accents(candidate).upper()
            if not any(h in clean_cand for h in HEADER_EXCLUSIONS_FRONT):
                results["name"] = candidate
                break

    # 4. Keyword anchored extraction for Address & Origin
    for i, line in enumerate(lines):
        clean_l = remove_accents(line).upper()

        # Residence / Nơi cư trú / Nơi thường trú
        if "residence" not in results:
            m_res = RESIDENCE_PATTERN.search(clean_l)
            if m_res:
                val = clean_front_address_value(line[m_res.end():])
                clean_val = remove_accents(val).upper().strip(" 0123456789/:-_;,.")
                next_line_idx = i + 1
                if (not val or "RESIDENC" in clean_val) and next_line_idx < len(lines):
                    val = lines[next_line_idx].strip()
                    next_line_idx += 1
                elif val and next_line_idx < len(lines):
                    next_l = lines[next_line_idx].strip()
                    clean_next = remove_accents(next_l).upper()
                    if not any(h in clean_next for h in HEADER_EXCLUSIONS_ADDR) and len(next_l) > 3:
                        sep = ", " if not val.endswith(",") else " "
                        val = f"{val}{sep}{next_l}"
                        next_line_idx += 1
                if val and not is_front_field_header(val):
                    results["residence"] = val.strip(" /:-_;,")

            elif "NOI CU TRU" in clean_l or "NOI THUONG TRU" in clean_l:
                colon_idx = line.find(":")
                if colon_idx != -1:
                    val = line[colon_idx + 1:].strip()
                else:
                    for kw in ["NOI CU TRU", "NOI THUONG TRU"]:
                        if kw in clean_l:
                            idx = clean_l.find(kw) + len(kw)
                            val = line[idx:].lstrip(" :-,;/")
                            break
                    else:
                        val = ""
                val = clean_front_address_value(val)
                clean_val = remove_accents(val).upper().strip(" 0123456789/:-_;,.")
                next_line_idx = i + 1
                if (not val or "RESIDENC" in clean_val) and next_line_idx < len(lines):
                    val = lines[next_line_idx].strip()
                    next_line_idx += 1
                elif val and next_line_idx < len(lines):
                    next_l = lines[next_line_idx].strip()
                    clean_next = remove_accents(next_l).upper()
                    if not any(h in clean_next for h in HEADER_EXCLUSIONS_ADDR) and len(next_l) > 3:
                        sep = ", " if not val.endswith(",") else " "
                        val = f"{val}{sep}{next_l}"
                if val and not is_front_field_header(val):
                    results["residence"] = val.strip(" /:-_;,")

        # Origin / Nơi ĐKKS / Quê quán
        if "origin" not in results:
            m_orig = FRONT_ORIGIN_PATTERN.search(clean_l)
            if m_orig:
                has_origin_label = True
                val = clean_front_address_value(line[m_orig.end():])
                clean_val = remove_accents(val).upper().strip(" 0123456789/:-_;,.")
                if not val or "ORIGIN" in clean_val or "BIRTH" in clean_val or re.match(r"^[IJ/ ]*PLACE\b", clean_val):
                    val = lines[i + 1].strip() if i + 1 < len(lines) else ""
                if val and not is_front_field_header(val):
                    results["origin"] = val.strip(" /:-_;,")
            elif "NOI DANG KY KHAI SINH" in clean_l or "QUE QUAN" in clean_l or "NOI DKKS" in clean_l:
                has_origin_label = True
                colon_idx = line.find(":")
                if colon_idx != -1:
                    val = line[colon_idx + 1:].strip()
                else:
                    for kw in ["NOI DANG KY KHAI SINH", "QUE QUAN", "NOI DKKS"]:
                        if kw in clean_l:
                            idx = clean_l.find(kw) + len(kw)
                            val = line[idx:].lstrip(" :-,;/")
                            break
                    else:
                        val = ""
                val = clean_front_address_value(val)
                clean_val = remove_accents(val).upper().strip(" 0123456789/:-_;,.")
                if not val or "ORIGIN" in clean_val or "BIRTH" in clean_val:
                    val = lines[i + 1].strip() if i + 1 < len(lines) else ""
                if val and not is_front_field_header(val):
                    results["origin"] = val.strip(" /:-_;,")

    # 5. Extract Expiry Date / Có giá trị đến
    clean_text = remove_accents(text).upper()
    m_exp = re.search(
        r"(?:CO\s*GIA\s*T[R]?I\s*D[EÊ]N|GIA\s*T[R]?I\s*D[EÊ]N|DATE\s*O[TF]\s*E[X]?P[I]?R[Y]?|E[X]?P[I]?R[Y]?|HET\s*HAN)[^\d]{0,40}(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})",
        clean_text,
        flags=re.DOTALL,
    )
    if m_exp:
        d, m, y = m_exp.groups()
        results["expiry_date"] = normalize_date(d, m, y)
    elif "KHONG THOI HAN" in clean_text or "VO THOI HAN" in clean_text:
        results["expiry_date"] = "Không thời hạn"

    if "expiry_date" not in results:
        after_residence = False
        for line in lines:
            clean_line = remove_accents(line).upper()
            if "NOI THUONG TRU" in clean_line or "NOI CU TRU" in clean_line:
                after_residence = True
                continue
            if not after_residence or not ("DATE" in clean_line or "CO GIA" in clean_line):
                continue
            for match in re.finditer(r"(?<![\d/])(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})(?!\d)", line):
                d, m, y = match.groups()
                try:
                    date(int(y), int(m), int(d))
                except ValueError:
                    continue
                results["expiry_date"] = normalize_date(d, m, y)
                break
            if "expiry_date" in results:
                break

    # 6. A province without a residence label cannot identify a residence.
    if "origin" not in results and not has_origin_label:
        found_locs: list[str] = []
        for line in lines:
            clean_l = remove_accents(line).upper()
            for code, prov in PROVINCE_CODES.items():
                prov_clean = remove_accents(prov).upper()
                if prov_clean in clean_l:
                    if prov not in found_locs:
                        found_locs.append(prov)
                    break

        if found_locs:
            results["origin"] = found_locs[0]

    for field in ("origin", "residence"):
        address = results.get(field, "")
        if "," not in address:
            continue
        prefix, _, province = address.rpartition(",")
        matches = [
            name for name in PROVINCE_CODES.values()
            if remove_accents(name).casefold() == remove_accents(province.strip()).casefold()
        ]
        if len(matches) == 1:
            results[field] = f"{prefix}, {matches[0]}"

    return results


def parse_front_fields(text: str, version: CardVersion) -> FrontSideResult:
    """Extracts front card entities and packs into FrontSideResult schema."""
    raw = extract_front_raw(text)
    cccd_id = raw.get("id")
    name = raw.get("name")
    dob = raw.get("dob")
    origin = raw.get("origin")
    residence = raw.get("residence")
    expiry_date = raw.get("expiry_date")

    gender = None
    if cccd_id and len(cccd_id) == 12:
        century_code = int(cccd_id[3])
        gender = "Nam" if century_code % 2 == 0 else "Nữ"

    return FrontSideResult(
        card_version=version,
        id=cccd_id,
        name=name,
        dob=dob,
        gender=gender,
        nationality="Việt Nam",
        origin=origin,
        residence=residence,
        expiry_date=expiry_date,
        extraction_source="front_rules",
        confidence_scores={
            "id": 0.99 if cccd_id else 0.0,
            "name": 0.85 if name else 0.0,
            "dob": 0.95 if dob else 0.0,
        },
    )
