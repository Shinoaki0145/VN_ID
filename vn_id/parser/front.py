"""Front-side rule-based extractor for Vietnamese CCCD / ID cards."""
from datetime import date
import re
from vn_id.core.utils import remove_accents, normalize_date
from vn_id.core.constants import PROVINCE_CODES
from vn_id.core.schemas import FrontSideResult
from vn_id.parser.common import (
    DATE_PATTERN,
    RESIDENCE_PATTERN,
    ORIGIN_PATTERN,
    HEADER_EXCLUSIONS_FRONT,
    HEADER_EXCLUSIONS_ADDR,
    clean_address_value,
)


class FrontRuleExtractor:
    """Extracts front card entities based on anchor keywords, patterns, and regex."""

    @classmethod
    def extract_raw(cls, text: str) -> dict[str, str]:
        results: dict[str, str] = {}
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

        # 3. Extract Name candidate
        for line in lines:
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
                    val = clean_address_value(line[m_res.end():])
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
                    if val:
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
                    val = clean_address_value(val)
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
                    if val:
                        results["residence"] = val.strip(" /:-_;,")

            # Origin / Nơi ĐKKS / Quê quán
            if "origin" not in results:
                m_orig = ORIGIN_PATTERN.search(clean_l)
                if m_orig:
                    val = clean_address_value(line[m_orig.end():])
                    clean_val = remove_accents(val).upper().strip(" 0123456789/:-_;,.")
                    if (not val or "ORIGIN" in clean_val or "BIRTH" in clean_val) and i + 1 < len(lines):
                        val = lines[i + 1].strip()
                    if val:
                        results["origin"] = val.strip(" /:-_;,")
                elif "NOI DANG KY KHAI SINH" in clean_l or "QUE QUAN" in clean_l or "NOI DKKS" in clean_l:
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
                    val = clean_address_value(val)
                    clean_val = remove_accents(val).upper().strip(" 0123456789/:-_;,.")
                    if (not val or "ORIGIN" in clean_val or "BIRTH" in clean_val) and i + 1 < len(lines):
                        val = lines[i + 1].strip()
                    if val:
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
        if "origin" not in results:
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

    @classmethod
    def extract(cls, text: str) -> FrontSideResult:
        """Extracts front card entities and packs into FrontSideResult schema."""
        raw = cls.extract_raw(text)
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
