"""
config.py
==========
Single source of truth for:
  - App-level constants (name, paths, model paths)
  - UI theme tokens (colors, spacing, radius) — used by every component
  - Firebase / Google Drive config keys (read from environment / secrets)

Never hardcode colors or secrets anywhere else. Import from here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load variables from .env (if present) into os.environ before anything
# below reads them. Safe to call even if .env doesn't exist yet.
load_dotenv()

# Helper function to get secrets from st.secrets (Streamlit Cloud) or os.environ
def get_env_or_secret(key: str, default: str = "") -> str:
    # First try Streamlit secrets
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    # Fallback to os.environ
    return os.environ.get(key, default)

# ------------------------------------------------------------------
# App identity
# ------------------------------------------------------------------
APP_NAME = "SecureDocAI"
APP_TAGLINE = "Handwritten OCR, secured by you."
APP_ICON = "✍️"  # used only as a Streamlit page_icon fallback, not in UI body

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
MODELS_DIR = BASE_DIR / "models"
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "outputs"
DATA_DIR = BASE_DIR / "data"

for _d in (UPLOADS_DIR, OUTPUTS_DIR, DATA_DIR, MODELS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# Path to your trained PyTorch model (CRNN: CNN + BiLSTM + CTC)
MODEL_PATH = Path(os.environ.get("MODEL_PATH", MODELS_DIR / "model_best.pth"))
LABEL_MAP_PATH = Path(os.environ.get("LABEL_MAP_PATH", MODELS_DIR / "label_map.json"))
FL_MODEL_PATH = Path(os.environ.get("FL_MODEL_PATH", MODELS_DIR / "fl_global_model_final.pth"))
FORCE_CPU = os.environ.get("FORCE_CPU", "0") == "1"

# ------------------------------------------------------------------
# Firebase (Auth) — values come from environment or st.secrets
# ------------------------------------------------------------------
FIREBASE_CONFIG = {
    "apiKey": get_env_or_secret("FIREBASE_API_KEY", ""),
    "authDomain": get_env_or_secret("FIREBASE_AUTH_DOMAIN", ""),
    "projectId": get_env_or_secret("FIREBASE_PROJECT_ID", ""),
    "storageBucket": get_env_or_secret("FIREBASE_STORAGE_BUCKET", ""),
    "messagingSenderId": get_env_or_secret("FIREBASE_MSG_SENDER_ID", ""),
    "appId": get_env_or_secret("FIREBASE_APP_ID", ""),
    "databaseURL": get_env_or_secret("FIREBASE_DB_URL", ""),
}
FIREBASE_ADMIN_CRED_PATH = get_env_or_secret("FIREBASE_ADMIN_CRED", "firebase_admin_key.json")

# ------------------------------------------------------------------
# Google Drive (per-user storage) — OAuth client, NOT a service account.
# Each user authorizes SecureDocAI to write to THEIR OWN Drive.
# ------------------------------------------------------------------
GOOGLE_OAUTH_CLIENT_SECRETS = get_env_or_secret("GOOGLE_OAUTH_CLIENT_SECRETS", "google_client_secret.json")
GOOGLE_DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]
GOOGLE_DRIVE_APP_FOLDER = "SecureDocAI"  # folder created inside the user's own Drive

# ------------------------------------------------------------------
# Local metadata cache (SQLite) — NOT where files live. Files always
# live in the user's own Google Drive. This DB only caches names,
# Drive file IDs, OCR status, and timestamps so the Library/History
# pages load instantly instead of hitting the Drive API on every render.
# ------------------------------------------------------------------
DB_PATH = DATA_DIR / "securedocai.db"

# ------------------------------------------------------------------
# THEME TOKENS — matches the brief exactly. Every component pulls from here.
# ------------------------------------------------------------------
COLORS = {
    "background": "#F8FAFC",
    "card": "#FFFFFF",
    "primary": "#2563EB",
    "secondary": "#3B82F6",
    "accent": "#06B6D4",
    "success": "#10B981",
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "text": "#0F172A",
    "text_secondary": "#64748B",
    "border": "#E2E8F0",
    "hover": "#DBEAFE",
}

RADIUS = "18px"
RADIUS_SM = "12px"
FONT_FAMILY = "'Manrope', 'Inter', -apple-system, sans-serif"

# ------------------------------------------------------------------
# OCR output formats offered on the OCR page
# ------------------------------------------------------------------
EXPORT_FORMATS = ["TXT", "Markdown", "HTML", "DOCX", "PDF", "JSON"]

# ------------------------------------------------------------------
# Sidebar navigation map: label -> (icon name, page module)
# Icon names follow lucide naming used in components/sidebar.py
# ------------------------------------------------------------------
NAV_ITEMS = [
    {"label": "Home", "icon": "layout-dashboard", "page": "Home"},
    {"label": "Scan Center", "icon": "scan-text", "page": "Scan"},
    {"label": "Library", "icon": "history", "page": "Library"},
    {"label": "Profile", "icon": "settings", "page": "Profile"},
]

# ==================================================================
# V2 EXTENDED CONFIGURATION
# ==================================================================

# --- App Information ---
APP_VERSION = "2.0.0"
APP_AUTHOR = "SecureDocAI Team"
APP_DESCRIPTION = "Intelligent hybrid OCR system with blockchain verification and PII redaction."
APP_WEBSITE = "https://securedoc.ai"
APP_GITHUB = "https://github.com/securedocai"
BUILD_DATE = "2026-07-07"

# --- OCR Configuration ---
SUPPORTED_LANGUAGES = ["Auto", "Telugu", "Hindi"]
DEFAULT_LANGUAGE = "Auto"
OCR_ENGINE_MODES = ["Auto", "Printed", "Handwritten", "Mixed"]
DEFAULT_OCR_ENGINE = "Auto"
MAX_UPLOAD_SIZE_MB = 10
SUPPORTED_IMAGE_FORMATS = ["png", "jpg", "jpeg"]
SUPPORTED_DOCUMENT_FORMATS = ["pdf"]

# --- Model Configuration ---
MODEL_VERSION = "2.0.0"
MODEL_DEVICE = "cuda" if not FORCE_CPU else "cpu"
DEFAULT_CONFIDENCE_THRESHOLD = 0.90
ENABLE_MIXED_PRECISION = True

# --- Security Configuration ---
AES_KEY_SIZE = 256
RSA_KEY_SIZE = 2048
HASH_ALGORITHM = "SHA-256"
ENABLE_BLOCKCHAIN = True
SESSION_TIMEOUT_MINUTES = 30

# --- Privacy Configuration ---
AUTO_REDACTION = True
ENABLE_PII_SCAN = True
DEFAULT_COMPLIANCE_MODE = "Standard"

# --- Google Drive Configuration ---
MAX_RESULTS_PER_PAGE = 50
CACHE_TIMEOUT = 300
DEFAULT_DRIVE_FOLDER = GOOGLE_DRIVE_APP_FOLDER

# --- UI Configuration ---
DEFAULT_THEME = "Light"
DEFAULT_PAGE = "Home"
SIDEBAR_WIDTH = 280
ANIMATION_ENABLED = True

# --- Export Configuration ---
DEFAULT_EXPORT_FORMAT = "ZIP"
EXPORT_FILENAME_FORMAT = "digitized_{filename}_{timestamp}"

# --- Logging ---
LOG_LEVEL = "INFO"
LOG_DIRECTORY = "data/logs"
LOG_FILE = "securedocai.log"

# --- Performance ---
CACHE_SIZE = 100
CACHE_EXPIRY = 3600
MAX_HISTORY_ITEMS = 50

# --- Notifications ---
MAX_NOTIFICATIONS = 5
NOTIFICATION_TIMEOUT = 4

# --- Dashboard ---
RECENT_FILES_LIMIT = 5
HOME_CARD_LIMIT = 3

# --- Scan Defaults ---
DEFAULT_ENHANCED_PREPROCESSING = True
DEFAULT_AUTO_ROTATE = True
DEFAULT_SHOW_OVERLAY = False
DEFAULT_SINGLE_CHARACTER_MODE = False

# --- Library Defaults ---
DEFAULT_DOCUMENTS_PER_PAGE = 10
DEFAULT_SORTING = "Newest"
DEFAULT_SEARCH_MODE = "Fuzzy"

# --- Profile Defaults ---
DEFAULT_COMPLIANCE_SETTINGS = {
    "comp_aadhaar": True,
    "comp_pan": True,
    "comp_bank": True,
    "comp_contact": True
}
DEFAULT_MODEL = "model_best.pth"

# --- Constants & Mappings ---
PAGES = {
    "Home": "Home",
    "Scan": "Scan",
    "Library": "Library",
    "Profile": "Profile"
}

# Reusable Status values
STATUS_SUCCESS = "success"
STATUS_WARNING = "warning"
STATUS_ERROR = "error"

# Reusable OCR modes
OCR_MODE_AUTO = "Auto"
OCR_MODE_PRINTED = "Printed"
OCR_MODE_HANDWRITTEN = "Handwritten"
OCR_MODE_MIXED = "Mixed"

# Reusable Privacy levels
PRIVACY_SAFE = "Safe"
PRIVACY_WARNING = "Warning"
PRIVACY_CRITICAL = "Critical"

# Reusable Security grades
SECURITY_GRADE_APLUS = "A+"
SECURITY_GRADE_A = "A"
SECURITY_GRADE_BPLUS = "B+"
SECURITY_GRADE_B = "B"

