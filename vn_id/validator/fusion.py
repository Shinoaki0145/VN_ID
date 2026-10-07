"""Data fusion engine combining Front, Back, and QR Code results."""
import time
import unicodedata
from typing import Any
from vn_id.core.schemas import (
    QRResult,
    FrontSideResult,
    BackSideResult,
    FinalCCCDResult,
    CCCDData,
    ValidationReport,
)
from vn_id.validator.cccd_rules import CCCDValidator
from vn_id.validator.fuzzy_address import AddressFuzzyMatcher


class DataFusion:
    """Fuses extraction candidate fields according to priority rules: QR > Front Rules + Back Rules."""

    @classmethod
    def fuse(
        cls,
        qr: QRResult | None = None,
        front: FrontSideResult | None = None,
        back: BackSideResult | None = None,
        side_detected: list[str] | None = None,
        timings: dict[str, float] | None = None,
    ) -> FinalCCCDResult:
        data = CCCDData()
        field_sources: dict[str, str] = {}

        t_fusion_start = time.time()
        # Resolve front extractor result
        front_res = front

        # Determine detected sides cleanly
        if side_detected is not None:
            detected_sides = list(side_detected)
        else:
            detected_sides = []
            if front_res and (front_res.id or front_res.name):
                detected_sides.append("front")
            if back and (back.issue_date or back.issue_loc or back.raw_text):
                detected_sides.append("back")
            if qr and qr.is_detected and not detected_sides:
                detected_sides.append("front")

        # 1. Fuse Front / Identity data
        # ID: Priority QR > Front
        if qr and qr.is_detected and qr.id:
            data.id = qr.id
            field_sources["id"] = "qr"
        elif front_res and front_res.id:
            data.id = front_res.id
            field_sources["id"] = "front_rules"

        # CMND Old (from QR)
        if qr and qr.is_detected and qr.cmnd_old:
            data.cmnd_old = qr.cmnd_old
            field_sources["cmnd_old"] = "qr"

        # Name: Priority QR > Front
        if qr and qr.is_detected and qr.name:
            data.name = qr.name
            field_sources["name"] = "qr"
        elif front_res and front_res.name:
            data.name = front_res.name
            field_sources["name"] = "front_rules"

        # DOB: Priority QR > Front
        if qr and qr.is_detected and qr.dob:
            data.dob = qr.dob
            field_sources["dob"] = "qr"
        elif front_res and front_res.dob:
            data.dob = front_res.dob
            field_sources["dob"] = "front_rules"

        # Gender: Priority QR > Front > Deduced from ID digit 4
        if qr and qr.is_detected and qr.gender:
            data.gender = qr.gender
            field_sources["gender"] = "qr"
        elif front_res and front_res.gender:
            data.gender = front_res.gender
            field_sources["gender"] = "front_rules"
        elif data.id and len(data.id) == 12 and data.id.isdigit():
            data.gender = "Nam" if int(data.id[3]) % 2 == 0 else "Nữ"
            field_sources["gender"] = "id_deduced"

        # Nationality
        data.nationality = "Việt Nam"
        field_sources["nationality"] = "default"

        # Origin / Quê quán: Front Rules > Back Rules (Can cuoc 2024)
        if front_res and front_res.origin:
            data.origin = AddressFuzzyMatcher.normalize_address(front_res.origin)
            field_sources["origin"] = "front_rules"
        elif back and back.origin:
            data.origin = AddressFuzzyMatcher.normalize_address(back.origin)
            field_sources["origin"] = "back_rules"

        # Residence / Nơi cư trú: Priority QR address > Front Rules > Back Rules (Can cuoc 2024)
        if qr and qr.is_detected and qr.address:
            data.residence = AddressFuzzyMatcher.normalize_address(qr.address)
            field_sources["residence"] = "qr"
        elif front_res and front_res.residence:
            data.residence = AddressFuzzyMatcher.normalize_address(front_res.residence)
            field_sources["residence"] = "front_rules"
        elif back and back.residence:
            data.residence = AddressFuzzyMatcher.normalize_address(back.residence)
            field_sources["residence"] = "back_rules"

        # 2. Fuse Back Side data
        if back:
            if back.issue_date:
                data.issue_date = back.issue_date
                field_sources["issue_date"] = "back_rules"
            elif qr and qr.is_detected and qr.issue_date and not data.issue_date:
                data.issue_date = qr.issue_date
                field_sources["issue_date"] = "qr"

            if back.issue_loc:
                data.issue_loc = back.issue_loc
                field_sources["issue_loc"] = "back_rules"

        # Expiry date:
        # Front card (CCCD chip 2021) has printed 'Có giá trị đến'.
        # Back card (Can cuoc 2024 / MRZ) has 'Ngày, tháng, năm hết hạn' or MRZ expiry.
        if front_res and front_res.expiry_date:
            data.expiry_date = front_res.expiry_date
            field_sources["expiry_date"] = "front_rules"
        elif back and back.expiry_date:
            data.expiry_date = back.expiry_date
            field_sources["expiry_date"] = "back_rules"

        # If issue date not filled from back, check QR
        if not data.issue_date and qr and qr.is_detected and qr.issue_date:
            data.issue_date = qr.issue_date
            field_sources["issue_date"] = "qr"

        # Thân nhân (Thẻ Căn cước 2024 trẻ em có trong QR)
        if qr and qr.is_detected:
            if qr.father_name:
                data.father_name = qr.father_name
                field_sources["father_name"] = "qr"
            if qr.mother_name:
                data.mother_name = qr.mother_name
                field_sources["mother_name"] = "qr"

        # 3. Validation
        validation = CCCDValidator.validate_12_digits(
            id_num=data.id,
            dob=data.dob,
            gender=data.gender,
        )

        # Ensure all fields are normalized to standard Unicode NFC precomposed form
        for field_name in [
            "id", "cmnd_old", "name", "dob", "gender", "nationality",
            "origin", "residence", "issue_date", "expiry_date", "issue_loc",
            "father_name", "mother_name",
        ]:
            val = getattr(data, field_name)
            if isinstance(val, str):
                setattr(data, field_name, unicodedata.normalize("NFC", val.strip()))

        success = bool(data.id or data.name or data.issue_date or data.issue_loc)
        if timings is not None:
            timings["fusion_ms"] = (time.time() - t_fusion_start) * 1000.0

        return FinalCCCDResult(
            success=success,
            side_detected=detected_sides,
            data=data,
            field_sources=field_sources,
            validation=validation,
            timings=timings or {},
        )
