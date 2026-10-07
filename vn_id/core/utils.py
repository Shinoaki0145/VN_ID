"""Text and date utilities for VN_ID pipeline."""
import re
import unicodedata


def remove_accents(input_str: str | None) -> str:
    """Removes Vietnamese diacritics/accents from a string."""
    if not input_str:
        return ""
    nfkd = unicodedata.normalize("NFKD", input_str)
    no_accents = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return no_accents.replace("đ", "d").replace("Đ", "D")


def normalize_date(date_input: str | None, month: str | None = None, year: str | None = None) -> str | None:
    """Normalizes date input into standard DD/MM/YYYY format.

    Supports:
    - 3 parameters: normalize_date(day, month, year) -> "DD/MM/YYYY"
    - 8 digits string: normalize_date("15081998") -> "15/08/1998"
    - Delimited string: normalize_date("15/8/1998") or "15-08-1998" -> "15/08/1998"
    """
    if month is not None and year is not None:
        if date_input is None:
            return None
        return f"{int(date_input):02d}/{int(month):02d}/{year}"

    if not date_input:
        return None

    clean_date = date_input.strip()

    # Case DDMMYYYY (8 digits)
    if len(clean_date) == 8 and clean_date.isdigit():
        return f"{clean_date[0:2]}/{clean_date[2:4]}/{clean_date[4:8]}"

    # Case DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
    m = re.match(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$", clean_date)
    if m:
        d, mo, y = m.groups()
        return f"{int(d):02d}/{int(mo):02d}/{y}"

    return clean_date
