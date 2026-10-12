"""CCCD 2021 back layout and shared front identity extraction."""
import re
from vn_id.core.schemas import CardVersion, BackSideResult, MRZResult
from vn_id.core.utils import remove_accents, normalize_date
from vn_id.parser.base import BaseCardParser
from vn_id.parser.mrz import parse_mrz
from vn_id.core.constants import POLICE_DEPT_ISSUER
from vn_id.parser.common import DATE_PATTERN


class CCCD2021Parser(BaseCardParser):
    version = CardVersion.CCCD_2021

    def parse_back(
        self, text: str, mrz: MRZResult | None = None, *, mrz_text: str | None = None,
    ) -> BackSideResult:
        mrz = mrz if mrz is not None else parse_mrz(text, mrz_text)
        clean_text = remove_accents(text).upper()
        issue_date = expiry_date = issue_loc = origin = residence = None

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

        if mrz:
            expiry_date = mrz.expiry_date

        return BackSideResult(
            card_version=self.version,
            issue_date=issue_date,
            expiry_date=expiry_date,
            issue_loc=issue_loc,
            origin=origin,
            residence=residence,
            mrz=mrz,
            mrz_raw=mrz.raw_text if mrz else None,
            raw_text=text,
        )


class UnknownCardParser(CCCD2021Parser):
    """Retain legacy date recovery while abstaining on card generation."""
    version = CardVersion.UNKNOWN
