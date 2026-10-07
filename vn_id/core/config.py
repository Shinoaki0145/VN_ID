"""Global configuration and paths for VN_ID pipeline."""
import os
from pathlib import Path

# Base project directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Model weights directories
MODELS_DIR = BASE_DIR / ".models"
QR_WEIGHTS_DIR = MODELS_DIR / "qrdet"
EASYOCR_STORAGE_DIR = BASE_DIR / ".easyocr_models" / "model"
EASYOCR_USER_NETWORK_DIR = BASE_DIR / ".easyocr_models" / "user_network"
VIETOCR_CFG_PATH = BASE_DIR / "vn_id" / "ocr" / "vgg_seq2seq.yml"
VIETOCR_WEIGHTS_PATH = EASYOCR_STORAGE_DIR / "vgg_seq2seq.pth"

# Default card alignment dimensions (ID-1 ratio)
STANDARD_CARD_WIDTH = 1000
STANDARD_CARD_HEIGHT = 630

# Reading order grouping threshold
LINE_GROUPING_THRESHOLD_PX = 18

