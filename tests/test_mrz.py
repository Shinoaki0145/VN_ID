import pytest

from vn_id.core.schemas import FrontSideResult, QRResult
from vn_id.parser.back import BackRuleExtractor
from vn_id.validator.fusion import DataFusion


SAMPLES = [
    ("IDVNM0690052512046069005251<<0", "6904281M2904283VNM<<<<<<<<<<<4", "046069005251", "28/04/1969", "28/04/2029"),
    ("IDVNM2060092818052206009281<<5", "0604257M3104253VNM<<<<<<<<<<<2", "052206009281", "25/04/2006", "25/04/2031"),
    ("IDVNM0680304494038068030449<<1", "6812137M2812139VNM<<<<<<<<<<<2", "038068030449", "13/12/1968", "13/12/2028"),
    ("IDVNM0910112671024091011267<<1", "9108161M3108169VNM<<<<<<<<<<<0", "024091011267", "16/08/1991", "16/08/2031"),
]


@pytest.mark.parametrize("line1,line2,id_num,dob,expiry", SAMPLES)
def test_mrz_fills_back_only_identity(line1, line2, id_num, dob, expiry):
    back = BackRuleExtractor.extract(f"{line1}\n{line2}\nNGUYEN<<VAN<A<<<<<<<<<<<<<<<<<")
    final = DataFusion.fuse(back=back)
    assert final.data.id == id_num
    assert final.data.dob == dob
    assert final.data.gender == "Nam"
    assert final.data.expiry_date == expiry
    assert final.data.issue_date is None
    assert final.data.issue_loc is None
    assert final.data.name is None
    assert all(final.field_sources[field] == "mrz" for field in ("id", "dob", "gender", "expiry_date"))
    assert back.mrz.checksums == {"document_number": True, "dob": True, "expiry_date": True, "composite": True}
    assert final.validation.mrz_checks == {}


def test_mrz_reports_disagreements_without_overwriting_existing_values():
    line1, line2, *_ = SAMPLES[0]
    back = BackRuleExtractor.extract(f"{line1}\n{line2}")
    qr = QRResult(is_detected=True, id="052206009281", dob="25/04/2006", gender="Nữ")
    front = FrontSideResult(expiry_date="25/04/2031")
    final = DataFusion.fuse(qr=qr, front=front, back=back)
    assert final.data.id == qr.id
    assert final.data.dob == qr.dob
    assert final.data.gender == qr.gender
    assert final.data.expiry_date == front.expiry_date
    assert final.validation.mrz_checks == {"id": False, "dob": False, "gender": False, "expiry_date": False}
    assert all(any(f"MRZ {field}" in w for w in final.validation.warnings) for field in final.validation.mrz_checks)


def test_mrz_reports_matching_independent_fields():
    line1, line2, id_num, dob, expiry = SAMPLES[0]
    final = DataFusion.fuse(
        front=FrontSideResult(id=id_num, dob=dob, gender="Nam", expiry_date=expiry),
        back=BackRuleExtractor.extract(f"{line1}\n{line2}"),
    )
    assert final.validation.mrz_checks == {"id": True, "dob": True, "gender": True, "expiry_date": True}


def test_mrz_accepts_partial_filler_and_contextual_numeric_substitutions():
    line1, line2, id_num, dob, expiry = SAMPLES[0]
    back = BackRuleExtractor.extract(f"{line1[:27].replace('0', 'O')}\n{line2[:18][:11]} {line2[:18][11:]}")
    assert back.mrz.id == id_num
    assert back.mrz.dob == dob
    assert back.mrz.expiry_date == expiry
    assert back.mrz.checksums["composite"] is None


def test_mrz_combines_valid_candidates_from_both_recognizers():
    line1, line2, id_num, dob, _ = SAMPLES[1]
    back = BackRuleExtractor.extract(f"{line1[:27]}\n00604257M3104253VNM", mrz_text=f"IDVNM29600928180522060092817\n{line2[:18]}")
    assert back.mrz.id == id_num
    assert back.mrz.dob == dob


def test_mrz_rejects_bad_composite_check():
    line1, line2, *_ = SAMPLES[0]
    final = DataFusion.fuse(back=BackRuleExtractor.extract(f"{line1}\n{line2[:-1]}5"))
    assert final.data.id is None
    assert final.data.expiry_date is None
    assert final.validation.mrz_checksums["composite"] is False
    assert any("MRZ" in w for w in final.validation.warnings)


def test_mrz_rejects_bad_field_checksum_without_losing_other_fields():
    line1, line2, _, _, expiry = SAMPLES[0]
    back = BackRuleExtractor.extract(f"{line1[:27]}\n{line2[:6]}2{line2[7:18]}")
    assert back.mrz.dob is None
    assert back.mrz.expiry_date == expiry
    assert back.mrz.checksums["dob"] is False


def test_mrz_rejects_invalid_calendar_date_even_with_valid_checksum():
    line1, line2, *_ = SAMPLES[0]
    back = BackRuleExtractor.extract(f"{line1[:27]}\n6902313{line2[7:18]}")
    assert back.mrz.dob is None
    assert any("date" in w.lower() for w in back.mrz.warnings)


def test_mrz_abstains_on_conflicting_valid_id_candidates():
    first = "\n".join(SAMPLES[0][:2])
    second = "\n".join(SAMPLES[1][:2])
    final = DataFusion.fuse(back=BackRuleExtractor.extract(first, mrz_text=second))
    assert final.data.id is None
    assert final.data.dob is None
    assert any("ambiguous" in w.lower() for w in final.validation.warnings)


def test_mrz_does_not_guess_dob_century_without_verified_id():
    back = BackRuleExtractor.extract(SAMPLES[0][1][:18])
    assert back.mrz.dob is None
    assert back.mrz.expiry_date == "28/04/2029"


def test_mrz_does_not_accept_shifted_date_substrings():
    assert BackRuleExtractor.extract("09108161M3108169VNM").expiry_date is None


def test_mrz_empty_and_ordinary_back_text():
    assert BackRuleExtractor.extract("").mrz is None
    assert BackRuleExtractor.extract("Ngày cấp: 15/05/2022").mrz is None


def test_mrz_ignores_personal_number_checksum_when_second_row_is_partial():
    line1, line2, *_ = SAMPLES[0]
    wrong_personal_checksum = line1[:-1] + "1"
    back = BackRuleExtractor.extract(f"{wrong_personal_checksum}\n{line2[:18]}")
    assert back.mrz.id == "046069005251"
    assert "personal_number" not in back.mrz.checksums
    assert back.mrz.warnings == []


def test_mrz_accepts_truncated_optional_tail_without_prefix_warning():
    line1, line2, *_ = SAMPLES[0]
    back = BackRuleExtractor.extract(f"{line1[:27]}\n{line2[:18]}")
    assert back.mrz.id == "046069005251"
    assert "personal_number" not in back.mrz.checksums
    assert back.mrz.warnings == []


def test_mrz_expiry_after_2050_stays_in_21st_century():
    line1, line2, *_ = SAMPLES[0]
    back = BackRuleExtractor.extract(f"{line1[:27]}\n{line2[:8]}6504289VNM")
    assert back.mrz.expiry_date == "28/04/2065"


@pytest.mark.parametrize("sex,expected", [("M", "Nam"), ("F", "Nữ"), ("<", None)])
@pytest.mark.parametrize("first_row", ["", "IDVNMCSJJEBGC2I542<<9\n"])
def test_mrz_reads_gender_without_verified_id_and_keeps_dob_unknown(sex, expected, first_row):
    back = BackRuleExtractor.extract(f"{first_row}9306015{sex}3306013VNM")
    final = DataFusion.fuse(back=back)
    assert back.mrz.gender == expected
    assert final.data.gender == expected
    if expected:
        assert final.field_sources["gender"] == "mrz"
    assert final.data.id is None
    assert final.data.dob is None
    assert final.data.expiry_date == "01/06/2033"


@pytest.mark.parametrize("source", ["qr", "front_rules"])
def test_mrz_gender_without_id_cross_checks_existing_gender(source):
    back = BackRuleExtractor.extract("9306015M3306013VNM")
    existing = {"qr": QRResult(is_detected=True, gender="Nữ")} if source == "qr" else {"front": FrontSideResult(gender="Nữ")}
    final = DataFusion.fuse(back=back, **existing)
    assert final.data.gender == "Nữ"
    assert final.field_sources["gender"] == source
    assert final.validation.mrz_checks["gender"] is False
    assert any("MRZ gender" in warning for warning in final.validation.warnings)


def test_mrz_gender_still_checks_verified_id_when_available():
    line1, line2, *_ = SAMPLES[0]
    back = BackRuleExtractor.extract(f"{line1[:27]}\n{line2[:7]}F{line2[8:18]}")
    assert back.mrz.id == "046069005251"
    assert back.mrz.gender is None
    assert any("MRZ gender" in warning for warning in back.mrz.warnings)
