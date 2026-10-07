"""Constants for VN_ID pipeline: province codes, century/gender map, and keywords."""

# 63 tỉnh, thành phố trực thuộc Trung ương theo quy chuẩn của Bộ Công an
PROVINCE_CODES: dict[str, str] = {
    "001": "Hà Nội",
    "002": "Hà Giang",
    "004": "Cao Bằng",
    "006": "Bắc Kạn",
    "008": "Tuyên Quang",
    "010": "Lào Cai",
    "011": "Điện Biên",
    "012": "Lai Châu",
    "014": "Sơn La",
    "015": "Yên Bái",
    "017": "Hoà Bình",
    "019": "Thái Nguyên",
    "020": "Lạng Sơn",
    "022": "Quảng Ninh",
    "024": "Bắc Giang",
    "025": "Phú Thọ",
    "026": "Vĩnh Phúc",
    "027": "Bắc Ninh",
    "030": "Hải Dương",
    "031": "Hải Phòng",
    "033": "Hưng Yên",
    "034": "Thái Bình",
    "035": "Hà Nam",
    "036": "Nam Định",
    "037": "Ninh Bình",
    "038": "Thanh Hóa",
    "040": "Nghệ An",
    "042": "Hà Tĩnh",
    "044": "Quảng Bình",
    "045": "Quảng Trị",
    "046": "Thừa Thiên Huế",
    "048": "Đà Nẵng",
    "049": "Quảng Nam",
    "051": "Quảng Ngãi",
    "052": "Bình Định",
    "054": "Phú Yên",
    "056": "Khánh Hòa",
    "058": "Ninh Thuận",
    "060": "Bình Thuận",
    "062": "Kon Tum",
    "064": "Gia Lai",
    "066": "Đắk Lắk",
    "067": "Đắk Nông",
    "068": "Lâm Đồng",
    "070": "Bình Phước",
    "072": "Tây Ninh",
    "074": "Bình Dương",
    "075": "Đồng Nai",
    "077": "Bà Rịa - Vũng Tàu",
    "079": "Thành phố Hồ Chí Minh",
    "080": "Long An",
    "082": "Tiền Giang",
    "083": "Bến Tre",
    "084": "Trà Vinh",
    "086": "Vĩnh Long",
    "087": "Đồng Tháp",
    "089": "An Giang",
    "091": "Kiên Giang",
    "092": "Cần Thơ",
    "093": "Hậu Giang",
    "094": "Sóc Trăng",
    "095": "Bạc Liêu",
    "096": "Cà Mau",
}

# Quy luật mã thế kỷ & giới tính trong số định danh 12 số CCCD:
# Thế kỷ 20 (1900-1999): Nam = 0, Nữ = 1
# Thế kỷ 21 (2000-2099): Nam = 2, Nữ = 3
# Thế kỷ 22 (2100-2199): Nam = 4, Nữ = 5
# Thế kỷ 23 (2200-2299): Nam = 6, Nữ = 7
# Thế kỷ 24 (2300-2399): Nam = 8, Nữ = 9
GENDER_CENTURY_MAP: dict[int, dict[str, int]] = {
    1900: {"Nam": 0, "Nữ": 1},
    2000: {"Nam": 2, "Nữ": 3},
    2100: {"Nam": 4, "Nữ": 5},
    2200: {"Nam": 6, "Nữ": 7},
    2300: {"Nam": 8, "Nữ": 9},
}

# Code sang thế kỷ & giới tính ngược lại
CENTURY_GENDER_TO_INFO: dict[int, tuple[int, str]] = {
    0: (1900, "Nam"),
    1: (1900, "Nữ"),
    2: (2000, "Nam"),
    3: (2000, "Nữ"),
    4: (2100, "Nam"),
    5: (2100, "Nữ"),
    6: (2200, "Nam"),
    7: (2200, "Nữ"),
    8: (2300, "Nam"),
    9: (2300, "Nữ"),
}

# Từ khóa chuẩn hóa nơi cấp
POLICE_DEPT_ISSUER = "Cục Cảnh sát Quản lý hành chính về trật tự xã hội"
MINISTRY_OF_PUBLIC_SECURITY = "Bộ Công an"

# Anchor keywords
KEYWORDS_FRONT_CAN_CUOC_2024 = [
    "SỐ ĐỊNH DANH CÁ NHÂN",
    "HỌ, CHỮ ĐỆM VÀ TÊN KHAI SINH",
    "NGÀY, THÁNG, NĂM SINH",
    "GIỚI TÍNH",
    "QUỐC TỊCH"
]

KEYWORDS_BACK_CAN_CUOC_2024 = [
    "NƠI CƯ TRÚ",
    "NƠI ĐĂNG KÝ KHAI SINH",
    "NGÀY, THÁNG, NĂM CẤP",
    "NGÀY, THÁNG, NĂM HẾT HẠN",
    "BỘ CÔNG AN"
]

KEYWORDS_FRONT_CCCD_2021 = [
    "SỐ / NO",
    "HỌ VÀ TÊN",
    "NGÀY SINH",
    "GIỚI TÍNH",
    "QUỐC TỊCH",
    "QUÊ QUÁN",
    "NƠI THƯỜNG TRÚ",
    "CÓ GIÁ TRỊ ĐẾN"
]

KEYWORDS_BACK_CCCD_2021 = [
    "CỤC TRƯỞNG CỤC CẢNH SÁT",
    "CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI",
    "NGÀY, THÁNG, NĂM"
]

