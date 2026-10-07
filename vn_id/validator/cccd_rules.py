"""12-digit CCCD validation logic rules."""
import re
from vn_id.core.schemas import ValidationReport
from vn_id.core.constants import PROVINCE_CODES, GENDER_CENTURY_MAP, CENTURY_GENDER_TO_INFO


class CCCDValidator:
    """Validates 12-digit CCCD numbers against Vietnamese national ID rules."""

    @classmethod
    def validate_12_digits(
        cls, id_num: str | None, dob: str | None = None, gender: str | None = None
    ) -> ValidationReport:
        warnings: list[str] = []
        if not id_num or len(id_num) != 12 or not id_num.isdigit():
            warnings.append("Độ dài số CCCD không hợp lệ (yêu cầu đúng 12 chữ số)")
            return ValidationReport(is_valid_12_digits=False, warnings=warnings)

        # 1. 3 digits: Province code
        province_code = id_num[:3]
        province_valid = province_code in PROVINCE_CODES
        if not province_valid:
            warnings.append(f"Mã tỉnh '{province_code}' không tồn tại trong danh mục 63 tỉnh thành BCA")

        # 2. 4th digit: Century and Gender
        century_digit = int(id_num[3])
        gender_century_valid = True
        birth_year_valid = True

        # Parse birth year from dob (format DD/MM/YYYY or YYYY)
        birth_year: int | None = None
        if dob:
            m_year = re.search(r"(\d{4})", dob)
            if m_year:
                birth_year = int(m_year.group(1))

        if birth_year and gender:
            century = (birth_year // 100) * 100
            expected_code = GENDER_CENTURY_MAP.get(century, {}).get(gender)
            if expected_code is not None and expected_code != century_digit:
                gender_century_valid = False
                warnings.append(
                    f"Chữ số thứ 4 ({century_digit}) không khớp với giới tính '{gender}' và thế kỷ sinh ({century})"
                )

        if birth_year:
            expected_2_digits = f"{birth_year % 100:02d}"
            actual_2_digits = id_num[4:6]
            if expected_2_digits != actual_2_digits:
                birth_year_valid = False
                warnings.append(
                    f"2 chữ số năm sinh ({actual_2_digits}) không khớp với năm sinh ({birth_year})"
                )

        return ValidationReport(
            is_valid_12_digits=True,
            province_valid=province_valid,
            gender_century_valid=gender_century_valid,
            birth_year_valid=birth_year_valid,
            address_fuzzy_score=1.0,
            warnings=warnings,
        )

