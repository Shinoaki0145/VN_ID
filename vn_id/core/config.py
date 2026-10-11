"""Global configuration and paths for VN_ID pipeline."""
from pathlib import Path

# Editable installs use the repo's existing model cache. A wheel keeps its
# cache in the user's home so it does not need write access to site-packages.
PACKAGE_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = PACKAGE_DIR.parent
MODEL_BASE_DIR = BASE_DIR if (BASE_DIR / "pyproject.toml").is_file() else Path.home() / ".cache" / "vn_id"

# Model weights directories
MODELS_DIR = MODEL_BASE_DIR / ".models"
QR_WEIGHTS_DIR = MODELS_DIR / "qrdet"
EASYOCR_STORAGE_DIR = MODEL_BASE_DIR / ".easyocr_models" / "model"
EASYOCR_USER_NETWORK_DIR = MODEL_BASE_DIR / ".easyocr_models" / "user_network"
VIETOCR_CFG_PATH = PACKAGE_DIR / "ocr" / "vgg_seq2seq.yml"
VIETOCR_WEIGHTS_PATH = EASYOCR_STORAGE_DIR / "vgg_seq2seq.pth"

# Default card alignment dimensions (ID-1 ratio)
STANDARD_CARD_WIDTH = 1000
STANDARD_CARD_HEIGHT = 630

# Reading order grouping threshold
LINE_GROUPING_THRESHOLD_PX = 18

