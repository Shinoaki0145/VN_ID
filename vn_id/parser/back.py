"""Back-side rule-based extractor for CCCD 2021 chip card and Can cuoc 2024 card."""
import re
from vn_id.core.schemas import BackSideResult
from vn_id.core.constants import POLICE_DEPT_ISSUER, MINISTRY_OF_PUBLIC_SECURITY
from vn_id.core.utils import remove_accents, normalize_date
from vn_id.parser.common import (
    DATE_PATTERN,
    RESIDENCE_PATTERN,
    ORIGIN_PATTERN,
    HEADER_EXCLUSIONS_BACK,
    clean_address_value,
)


class BackRuleExtractor:
    """Extracts issue date, expiry date, issuer location, and addresses from card back text."""

    @classmethod
    def extract(cls, text: str) -> BackSideResult:
        if not text:
            return BackSideResult(raw_text="")

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
            or "DATE" in clean_text
            or "NGAY" in clean_text
            or "IDVNM" in clean_text
        )

        version = "can_cuoc_2024" if is_2024 else ("cccd_chip_2021" if is_2021 else "unknown")

        issue_date: str | None = None
        expiry_date: str | None = None
        issue_loc: str | None = None
        origin: str | None = None
        residence: str | None = None

        lines = [line.strip() for line in text.split("\n") if line.strip()]

        if is_2024:
            # Extract issue date: "Ngày, tháng, năm cấp: ..."
            m_issue = re.search(r"NGAY[^\d]{1,20}THANG[^\d]{1,20}NAM\s+CAP[^\d]*" + DATE_PATTERN, clean_text)
            if m_issue:
                issue_date = normalize_date(m_issue.group(1), m_issue.group(2), m_issue.group(3))

            # Extract expiry date: "Ngày, tháng, năm hết hạn: ..."
            m_expiry = re.search(r"NGAY[^\d]{1,20}THANG[^\d]{1,20}NAM\s+HET\s+HAN[^\d]*" + DATE_PATTERN, clean_text)
            if m_expiry:
                expiry_date = normalize_date(m_expiry.group(1), m_expiry.group(2), m_expiry.group(3))

            # Issuer location
            if "BO CONG AN" in clean_text:
                issue_loc = MINISTRY_OF_PUBLIC_SECURITY

            # Extract Residence & Origin from 2024 card back
            for i, line in enumerate(lines):
                clean_l = remove_accents(line).upper()

                # Residence / Nơi cư trú
                if not residence:
                    m_res = RESIDENCE_PATTERN.search(clean_l)
                    if m_res:
                        val = clean_address_value(line[m_res.end():])
                        clean_v = remove_accents(val).upper().strip(" 0123456789/:-_;,.")
                        next_i = i + 1
                        if (not val or "RESIDENC" in clean_v) and next_i < len(lines):
                            val = lines[next_i].strip()
                            next_i += 1
                        elif val and next_i < len(lines):
                            next_l = lines[next_i].strip()
                            clean_next = remove_accents(next_l).upper()
                            if not any(h in clean_next for h in HEADER_EXCLUSIONS_BACK) and len(next_l) > 3:
                                val = f"{val}, {next_l}"
                                next_i += 1
                        residence = val.strip(" /:-_;,")
                    elif any(k in clean_l for k in ["NOI CU TRU", "NOI CUTRU", "NOI CULRU", "NOI THUONG TRU", "RESIDENC"]):
                        if ":" in line:
                            val = line[line.find(":") + 1:].strip(" :-,;/")
                        else:
                            val = ""
                            for kw in ["NOI CU TRU", "NOI CUTRU", "NOI CULRU", "NOI THUONG TRU"]:
                                if kw in clean_l:
                                    idx = clean_l.find(kw) + len(kw)
                                    val = line[idx:].lstrip(" :-,;/")
                                    break
                        val = clean_address_value(val)
                        clean_v = remove_accents(val).upper().strip(" 0123456789/:-_;,.")
                        next_i = i + 1
                        if (not val or "RESIDENC" in clean_v) and next_i < len(lines):
                            val = lines[next_i].strip()
                            next_i += 1
                        elif val and next_i < len(lines):
                            next_l = lines[next_i].strip()
                            clean_next = remove_accents(next_l).upper()
                            if not any(h in clean_next for h in HEADER_EXCLUSIONS_BACK) and len(next_l) > 3:
                                val = f"{val}, {next_l}"
                                next_i += 1
                        residence = val.strip(" /:-_;,")

                # Origin / Nơi đăng ký khai sinh
                if not origin:
                    m_orig = ORIGIN_PATTERN.search(clean_l)
                    if m_orig:
                        val = clean_address_value(line[m_orig.end():])
                        clean_v = remove_accents(val).upper().strip(" 0123456789/:-_;,.")
                        next_i = i + 1
                        if (not val or "BIRTH" in clean_v or "ORIGIN" in clean_v) and next_i < len(lines):
                            val = lines[next_i].strip()
                            next_i += 1
                        elif val and next_i < len(lines):
                            next_l = lines[next_i].strip()
                            clean_next = remove_accents(next_l).upper()
                            if not any(h in clean_next for h in HEADER_EXCLUSIONS_BACK) and len(next_l) > 3:
                                val = f"{val}, {next_l}"
                                next_i += 1
                        origin = val.strip(" /:-_;,")
                    elif any(k in clean_l for k in ["KHAI SINH", "NOI DKKS", "QUE QUAN", "BIRTH"]):
                        if ":" in line:
                            val = line[line.find(":") + 1:].strip(" :-,;/")
                        else:
                            val = ""
                            for kw in ["NOI DANG KY KHAI SINH", "NOI DKKS", "QUE QUAN"]:
                                if kw in clean_l:
                                    idx = clean_l.find(kw) + len(kw)
                                    val = line[idx:].lstrip(" :-,;/")
                                    break
                        val = clean_address_value(val)
                        clean_v = remove_accents(val).upper().strip(" 0123456789/:-_;,.")
                        next_i = i + 1
                        if (not val or "BIRTH" in clean_v or "ORIGIN" in clean_v) and next_i < len(lines):
                            val = lines[next_i].strip()
                            next_i += 1
                        elif val and next_i < len(lines):
                            next_l = lines[next_i].strip()
                            clean_next = remove_accents(next_l).upper()
                            if not any(h in clean_next for h in HEADER_EXCLUSIONS_BACK) and len(next_l) > 3:
                                val = f"{val}, {next_l}"
                                next_i += 1
                        origin = val.strip(" /:-_;,")

        else:
            # 2021 Chip Card
            # Extract issue date: "Ngày, tháng, năm / Date, month, year..."
            m_issue = re.search(
                r"(?:NGAY[^\d]{1,30}THANG[^\d]{1,30}NAM|DATE[^\d]{1,30}MONTH[^\d]{1,30}YEAR)[^\d]*" + DATE_PATTERN,
                clean_text,
            )
            if m_issue:
                issue_date = normalize_date(m_issue.group(1), m_issue.group(2), m_issue.group(3))
            else:
                m_any = re.search(DATE_PATTERN, clean_text)
                if m_any:
                    issue_date = normalize_date(m_any.group(1), m_any.group(2), m_any.group(3))

            # Issuer location
            if (
                "CANH SAT" in clean_text
                or "QUAN LY HANH CHINH" in clean_text
                or "TRAT TU XA HOI" in clean_text
                or "CUC TRUONG" in clean_text
            ):
                issue_loc = POLICE_DEPT_ISSUER

            # Extract expiry date from MRZ line 2 if present
            if not expiry_date:
                m_mrz = re.search(r"(\d{6})\d[MFmf](\d{6})\d", clean_text)
                if m_mrz:
                    exp_raw = m_mrz.group(2)
                    yy, mm, dd = int(exp_raw[:2]), exp_raw[2:4], exp_raw[4:6]
                    full_year = 2000 + yy if yy < 50 else 1900 + yy
                    expiry_date = normalize_date(dd, mm, str(full_year))

        return BackSideResult(
            card_version=version,
            issue_date=issue_date,
            expiry_date=expiry_date,
            issue_loc=issue_loc,
            origin=origin,
            residence=residence,
            raw_text=text,
        )

