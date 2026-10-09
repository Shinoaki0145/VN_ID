"""Fixed-position CCCD chip-card MRZ parsing with ICAO field checksums."""
import re
from datetime import date

from vn_id.core.constants import CENTURY_GENDER_TO_INFO
from vn_id.core.schemas import MRZResult


NUMERIC_OCR = str.maketrans({"O": "0", "I": "1", "L": "1"})


def check_digit(value: str) -> str:
    """ICAO 9303: digits, A=10..Z=35, filler=0; repeating weights 7,3,1."""
    values = [0 if c == "<" else int(c, 36) for c in value]
    return str(sum(v * (7, 3, 1)[i % 3] for i, v in enumerate(values)) % 10)


def _normalize_line(line: str) -> str:
    line = re.sub(r"\s+", "", line.upper())
    if line.startswith("IDVNM"):
        line = line[:5] + line[5:27].translate(NUMERIC_OCR) + line[27:]
    else:
        line = line[:7].translate(NUMERIC_OCR) + line[7:8] + line[8:15].translate(NUMERIC_OCR) + line[15:]
    if len(line) == 30:
        line = line[:29] + line[29].translate(NUMERIC_OCR)
    return line


def _calendar_date(raw: str, century: int, result: MRZResult, field: str) -> str | None:
    try:
        return date(century + int(raw[:2]), int(raw[2:4]), int(raw[4:6])).strftime("%d/%m/%Y")
    except ValueError:
        result.warnings.append(f"MRZ {field}: invalid calendar date ({raw}).")
        return None


def parse_mrz(text: str, alternate_text: str | None = None) -> MRZResult | None:
    """Combine validated candidates from Latin OCR and VietOCR; never shift offsets.

    A truncated filler tail still permits independent field checks. A complete,
    canonical pair additionally requires the composite checksum to pass.
    """
    lines = list(dict.fromkeys(
        _normalize_line(line)
        for source in (alternate_text, text) if source
        for line in source.splitlines() if line.strip()
    ))
    first = [line for line in lines if line.startswith("IDVNM")]
    second = [line for line in lines if re.match(r"^\d{7}[MF<]\d{7}VNM", line)]
    if not first and not second:
        return None
    result = MRZResult(raw_text="\n".join(first + second), checksums={
        "document_number": None,
        "dob": None, "expiry_date": None, "composite": None,
    })
    valid_first = [line for line in first if (
        re.match(r"^IDVNM\d{22}", line)
        and check_digit(line[5:14]) == line[14]
        and line[5:14] == line[18:27]
    )]
    ids = {line[15:27] for line in valid_first}
    if len(ids) > 1:
        result.warnings.append("MRZ: ambiguous valid ID candidates; fields withheld.")
        return result
    if first:
        result.checksums["document_number"] = bool(valid_first)
        if not valid_first:
            result.warnings.append("MRZ id: document checksum or duplicated ID failed.")
    if ids:
        result.id = ids.pop()

    # Prefer rows whose field checks pass, and abstain on equally valid conflicts.
    def score(line: str) -> int:
        return int(check_digit(line[:6]) == line[6]) + int(check_digit(line[8:14]) == line[14])

    if not second:
        return result
    best_score = max(map(score, second))
    best = [line for line in second if score(line) == best_score]
    if len({line[:15] for line in best}) > 1:
        result.warnings.append("MRZ: ambiguous date/gender candidates; fields withheld.")
        return result
    row = best[0]

    # Only canonical full rows provide a composite check. No invented fillers.
    composites = []
    for row1 in valid_first:
        for row2 in best:
            if re.fullmatch(r"IDVNM\d{22}<<\d", row1) and re.fullmatch(r"\d{7}[MF<]\d{7}VNM<{11}\d", row2):
                combined = row1[5:30] + row2[:7] + row2[8:15] + row2[18:29]
                composites.append(check_digit(combined) == row2[29])
    if composites:
        result.checksums["composite"] = any(composites)
        if not result.checksums["composite"]:
            result.id = None
            result.warnings.append("MRZ: composite checksum failed; fields withheld.")
            return result

    for field, value, digit in (("dob", row[:6], row[6]), ("expiry_date", row[8:14], row[14])):
        result.checksums[field] = check_digit(value) == digit
        if not result.checksums[field]:
            result.warnings.append(f"MRZ {field}: checksum failed.")

    if result.checksums["expiry_date"]:
        result.expiry_date = _calendar_date(row[8:14], 2000, result, "expiry_date")
    if result.checksums["dob"] and result.id:
        century = CENTURY_GENDER_TO_INFO[int(result.id[3])][0]
        if row[:2] == result.id[4:6]:
            result.dob = _calendar_date(row[:6], century, result, "dob")
        else:
            result.warnings.append("MRZ dob: birth year differs from verified CCCD ID.")
    elif result.checksums["dob"]:
        result.warnings.append("MRZ dob: no verified CCCD ID to resolve birth century.")

    # Sex can be read from a validated MRZ row without resolving birth century.
    if result.checksums["dob"]:
        gender = {"M": "Nam", "F": "Nữ"}.get(row[7])
        if result.id and gender and gender != CENTURY_GENDER_TO_INFO[int(result.id[3])][1]:
            result.warnings.append("MRZ gender: differs from verified CCCD ID.")
        else:
            result.gender = gender
    return result
