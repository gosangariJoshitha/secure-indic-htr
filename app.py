"""
app.py
======
SecureDocAI — Main Controller

Responsibilities (ONLY these — no OCR logic ever goes here):
  - Page config / theme loading (style.css injection with Outfit & Inter Typography)
  - Session-state initialization & caching preloads
  - Auth-gate: auto-login bypass check, token refreshes, and invalid token protection
  - Google Drive: lazy connection status verification & tokens refresh
  - Mount global layout components (navbar, breadcrumbs, notifications, audit footers)
  - Protected routing to app pages (Home, Scan, Library, Profile)
  - Global try/except error boundary catch with Debug Mode toggle
"""
import os
import warnings

try:
    from requests.exceptions import RequestsDependencyWarning
    warnings.simplefilter("ignore", category=RequestsDependencyWarning)
except ImportError:
    pass

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
_local_tessdata = os.path.abspath(os.path.join(os.path.dirname(__file__), "tessdata"))
if os.path.exists(_local_tessdata):
    os.environ["TESSDATA_PREFIX"] = _local_tessdata

# Monkeypatch socket.getfqdn to handle None name on Windows
import socket
_orig_getfqdn = socket.getfqdn
def _safe_getfqdn(name=''):
    if name is None:
        name = ''
    return _orig_getfqdn(name)
socket.getfqdn = _safe_getfqdn

import streamlit as st
from pathlib import Path
import time
import logging
from config import APP_NAME, APP_ICON, FIREBASE_CONFIG, DATA_DIR, MODEL_PATH

# 1. Global Setup Constants
APP_VERSION = "2.0.0"
BUILD_NUMBER = "B2488"

logger = logging.getLogger("SecureDocAI.MainController")

# Streamlit Page Config (MUST be the first Streamlit call)
st.set_page_config(
    page_title=APP_NAME,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ------------------------------------------------------------------
# Global App Initialization
# ------------------------------------------------------------------
def initialize_app():
    """Validates required files, client configurations, and data directories exist."""
    if st.session_state.get("app_initialized"):
        return
        
    validation_status = {
        "Firebase Configuration": bool(FIREBASE_CONFIG.get("apiKey")),
        "Trained Model Weights": MODEL_PATH.exists(),
        "Assets Folder": (Path(__file__).parent / "assets").exists(),
        "Data Store Path": DATA_DIR.exists(),
        "Security Subsystem": (DATA_DIR / "security").exists()
    }
    
    # Auto-initialize paths
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "security").mkdir(parents=True, exist_ok=True)
    
    st.session_state["validation_status"] = validation_status
    st.session_state["app_initialized"] = True

def initialize_session():
    """Declares all default session variables in one unified schema."""
    _DEFAULTS = {
        "auth_view": "landing",
        "user": None,
        "drive_creds": None,
        "active_page": "Home",
        "prev_page": "Home",
        "recent_ocr_runs": [],
        "toast_queue": [],
        "alert_queue": [],
        "theme": "light",
        "language": "Auto",
        "dark_mode": False,
        
        # Fallback preference overrides
        "profile_preferred_engine": "Auto",
        "profile_fallback_threshold": 90,
        "profile_fallback_enabled": True,
        
        # Privacy compliance toggles
        "comp_aadhaar": True,
        "comp_pan": True,
        "comp_bank": True,
        "comp_contact": True,
    }
    for key, val in _DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = val

def load_theme():
    """Injects Google fonts, styling parameters, and validates assets/style.css."""
    css_path = Path(__file__).parent / "assets" / "style.css"
    if css_path.exists():
        css_content = css_path.read_text(encoding="utf-8")
        
        # Inject dark mode overrides dynamically in real-time
        if st.session_state.get("dark_mode", False):
            dark_css = """
            /* Premium Real-Time Dark Mode Overrides */
            :root {
                --bg: #0B0F19 !important;
                --card: #1E293B !important;
                --text: #F8FAFC !important;
                --text-secondary: #94A3B8 !important;
                --muted: #64748B !important;
                --border: #334155 !important;
                --hover: #1E293B !important;
                --ink: #0F172A !important;
                --shadow-soft: 0 4px 16px rgba(0, 0, 0, 0.3) !important;
                --shadow-lift: 0 12px 28px rgba(0, 0, 0, 0.4) !important;
            }
            html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stMainBlockContainer"] {
                background-color: #0B0F19 !important;
                color: #E2E8F0 !important;
            }
            [data-testid="stHeader"] {
                background-color: transparent !important;
            }
            [data-testid="stSidebar"] {
                background-color: #0F172A !important;
                border-right: 1px solid #1E293B !important;
            }
            [data-testid="stSidebar"] * {
                color: #F8FAFC !important;
            }
            div[data-testid="stVerticalBlockBorderWrapper"] {
                background-color: #1E293B !important;
                border: 1px solid #334155 !important;
                border-radius: 18px !important;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2), 0 2px 4px -1px rgba(0, 0, 0, 0.1) !important;
            }
            .sd-card {
                background-color: #1E293B !important;
                border: 1px solid #334155 !important;
                color: #E2E8F0 !important;
            }
            .sd-h1, .sd-h2, .sd-h3, h1, h2, h3, h4, h5, h6, p, span, label, strong, li {
                color: #F8FAFC !important;
            }
            input, textarea, select {
                background-color: #0F172A !important;
                color: #F8FAFC !important;
                border: 1px solid #334155 !important;
            }
            div[data-testid="stExpander"] {
                background-color: #1E293B !important;
                border: 1px solid #334155 !important;
                border-radius: 12px !important;
            }
            /* Glass container theme overrides (landing/auth) */
            .sd-glass, .st-key-login_card, .st-key-signup_card {
                background: rgba(30, 41, 59, 0.6) !important;
                border: 1px solid rgba(255, 255, 255, 0.08) !important;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3) !important;
            }
            /* Gradient background dark override */
            .sd-gradient-bg {
                background: linear-gradient(135deg, #0B0F19 0%, #0F172A 60%, #1E1B4B 100%) !important;
            }
            /* Streamlit tabs */
            button[data-baseweb="tab"] {
                color: #94A3B8 !important;
            }
            button[aria-selected="true"] {
                color: #F8FAFC !important;
            }
            /* Streamlit Buttons in Dark Mode */
            .stButton > button, .stPopover > div > button {
                background-color: #1E293B !important;
                color: #F8FAFC !important;
                border: 1px solid #334155 !important;
            }
            .stButton > button:hover, .stPopover > div > button:hover {
                border-color: #3B82F6 !important;
                background-color: #334155 !important;
                color: #F8FAFC !important;
            }
            /* Keep primary buttons standout */
            .stButton > button[kind="primary"],
            .stButton > button[data-testid="baseButton-primary"] {
                background: linear-gradient(135deg, #2563EB, #3B82F6) !important;
                color: #FFFFFF !important;
                border: none !important;
            }
            /* Restore navbar styling in dark mode */
            .app-navbar-wrapper + div[data-testid="stHorizontalBlock"] .stButton > button[kind="primary"],
            .app-navbar-wrapper + div[data-testid="stHorizontalBlock"] .stButton > button[data-testid="baseButton-primary"] {
                background: #2563EB !important;
                background-color: #2563EB !important;
                color: white !important;
            }
            .app-navbar-wrapper + div[data-testid="stHorizontalBlock"] .stButton > button[kind="secondary"],
            .app-navbar-wrapper + div[data-testid="stHorizontalBlock"] .stButton > button[data-testid="baseButton-secondary"] {
                background: transparent !important;
                background-color: transparent !important;
                color: #94A3B8 !important;
                border: 1px solid transparent !important;
            }
            .app-navbar-wrapper + div[data-testid="stHorizontalBlock"] .stButton > button:hover {
                background-color: rgba(255, 255, 255, 0.08) !important;
                color: white !important;
            }
            """
            css_content += "\n" + dark_css
            
        st.html(
            "<link rel='preconnect' href='https://fonts.googleapis.com'>\n"
            "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>\n"
            "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@500;600;700;800&display=swap' rel='stylesheet'>\n"
            "<style>\n"
            "html, body, [class*='css'] {\n"
            "    font-family: 'Inter', sans-serif;\n"
            "}\n"
            "h1, h2, h3, .sd-h1, .sd-h2, .sd-h3 {\n"
            "    font-family: 'Outfit', sans-serif !important;\n"
            "}\n"
            + css_content +
            "\n</style>"
        )


# ------------------------------------------------------------------
# Session Expiry & Auto-Refresh Controls
# ------------------------------------------------------------------
def check_session_expiry():
    """Authenticates the session using refresh token; logs user out if verification fails."""
    if st.session_state.user is not None:
        refresh_token = st.session_state.user.get("refresh_token")
        if refresh_token:
            try:
                from utils.security import refresh_token_login
                new_user = refresh_token_login(refresh_token)
                st.session_state.user = new_user
            except Exception as e:
                logger.warning(f"Session token expired or is invalid: {e}")
                from utils.security import clear_remember_session
                clear_remember_session()
                st.session_state.user = None
                st.session_state.auth_view = "login"
                st.session_state.toast_queue.append(("Your session has expired. Please log in again.", "error"))

def check_drive_connection():
    """Ensures Google Drive auth tokens stay active by refreshing them lazily."""
    if st.session_state.user is not None and st.session_state.drive_creds is not None:
        creds = st.session_state.drive_creds
        if creds.expired and creds.refresh_token:
            try:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
                st.session_state.drive_creds = creds
                from utils.security import save_persistent_drive_creds
                save_persistent_drive_creds(st.session_state.user.get("email"), creds)
            except Exception as e:
                logger.warning(f"Could not refresh expired Google Drive credentials: {e}")
                st.session_state.drive_creds = None

# ------------------------------------------------------------------
# Global Layout Helpers
# ------------------------------------------------------------------
def render_breadcrumbs():
    """Displays visual path navigation indicator at the top of authenticated pages."""
    from components.ui_helpers import html_block
    page = st.session_state.active_page
    breadcrumbs = ["Vault", page] if page != "Home" else ["Vault", "Home"]
    html_block(f"""
        <div style="font-size:0.8rem; color:#64748B; margin-bottom:12px; font-weight:500;">
            🔒 SecureDocAI &nbsp;&rsaquo;&nbsp; {' &nbsp;&rsaquo;&nbsp; '.join(breadcrumbs)}
        </div>
    """)

def render_notifications():
    """Processes notifications inside queues and triggers Streamlit Toast blocks."""
    if st.session_state.get("toast_queue"):
        for msg, level in st.session_state.toast_queue:
            if level == "error":
                st.error(msg)
            elif level == "warning":
                st.warning(msg)
            else:
                st.toast(msg)
        st.session_state.toast_queue = []

def render_footer():
    """Renders visual versioning and compliance labels."""
    from components.ui_helpers import html_block
    html_block(f"""
        <div class="sd-divider" style="margin-top:40px;"></div>
        <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.75rem; color:#94A3B8; padding: 12px 0;">
            <div>&copy; 2026 SecureDocAI. All rights reserved.</div>
            <div>Version {APP_VERSION} (Build {BUILD_NUMBER}) &bull; FIPS 140-2 Compliant</div>
        </div>
    """)

# ------------------------------------------------------------------
# Routing Views
# ------------------------------------------------------------------
def render_unauthenticated():
    """Splits flows between landing page, signup page, and login screen."""
    view = st.session_state.auth_view
    if view == "login":
        from app_pages.Login import render as render_login
        render_login()
    elif view == "signup":
        from app_pages.Signup import render as render_signup
        render_signup()
    else:
        from app_pages.Landing import render as render_landing
        render_landing()

def render_public_verification(doc_hash: str):
    """Renders the public ledger integrity verification workspace."""
    from components.ui_helpers import html_block
    from utils.security_engine import get_blockchain
    
    st.markdown("# 🔒 Ledger Integrity Verification")
    st.markdown("<p style='color:#64748B;'>SecureDocAI Blockchain Registry Integrity check.</p>", unsafe_allow_html=True)
    
    blockchain = get_blockchain()
    
    # Search for the hash in blockchain
    found_block = None
    for block in blockchain.chain:
        if block.index > 0:
            if block.file_hashes.get("sha256") == doc_hash:
                found_block = block
                break
                
    if found_block:
        chain_status = blockchain.verify_block(found_block.index)
        is_valid = chain_status["valid"]
        
        filename = found_block.metadata.get("original_filename", "Encrypted Document")
        upload_time = found_block.metadata.get("upload_time", found_block.timestamp)
        doc_type = found_block.metadata.get("doc_type", "General")
        
        if is_valid:
            st.success("✓ Integrity Verified: Document hash matches blockchain record and block signature is valid.")
            html_block(f"""
            <div style="background:#F8FAFC; border:1px solid #10B981; padding:20px; border-radius:12px; margin-bottom:20px;">
                <h3 style="color:#10B981; margin-top:0;">Registry Record Details</h3>
                <table style="width:100%; border-collapse:collapse; font-size:0.9rem;">
                    <tr style="border-bottom:1px solid #E2E8F0;"><td style="padding:8px 0; color:#64748B; font-weight:600;">Filename:</td><td style="padding:8px 0; font-weight:700;">{filename}</td></tr>
                    <tr style="border-bottom:1px solid #E2E8F0;"><td style="padding:8px 0; color:#64748B; font-weight:600;">Document Type:</td><td style="padding:8px 0; font-weight:700;">{doc_type}</td></tr>
                    <tr style="border-bottom:1px solid #E2E8F0;"><td style="padding:8px 0; color:#64748B; font-weight:600;">Upload Time:</td><td style="padding:8px 0; font-weight:700;">{upload_time}</td></tr>
                    <tr style="border-bottom:1px solid #E2E8F0;"><td style="padding:8px 0; color:#64748B; font-weight:600;">Blockchain Index:</td><td style="padding:8px 0; font-weight:700;">Block #{found_block.index}</td></tr>
                    <tr style="border-bottom:1px solid #E2E8F0;"><td style="padding:8px 0; color:#64748B; font-weight:600;">Node ID:</td><td style="padding:8px 0; font-weight:700;">{found_block.node_id}</td></tr>
                    <tr><td style="padding:8px 0; color:#64748B; font-weight:600;">SHA-256 Hash:</td><td style="padding:8px 0; font-family:monospace; font-size:0.8rem; word-break:break-all;">{doc_hash}</td></tr>
                </table>
            </div>
            """)
        else:
            st.error("❌ Registry Error: Block linkage or signature has been tampered with!")
    else:
        st.warning("⚠️ Registry Record Not Found: No blockchain block registered with this integrity hash.")
        
    if st.button("Go to SecureDocAI Home", key="btn_verify_back_home"):
        st.query_params.clear()
        st.rerun()


def render_public_share(share_id: str):
    """Renders the public secure share download gateway."""
    from utils.security_engine import validate_share_link, consume_share_link, get_document_versions
    import hashlib
    
    st.markdown("# 📥 Secure Shared Link")
    st.markdown("<p style='color:#64748B;'>Access-restricted document decryption gateway.</p>", unsafe_allow_html=True)
    
    status = validate_share_link(share_id)
    if not status["valid"]:
        st.error(status["reason"])
        if st.button("Go to SecureDocAI Home", key="btn_share_err_home"):
            st.query_params.clear()
            st.rerun()
        return
        
    record = status["record"]
    
    authorized = True
    if record.get("password_hash"):
        authorized = False
        pwd_input = st.text_input("Enter Passphrase to Decrypt", type="password", placeholder="Access key required", key="share_login_pw")
        if pwd_input:
            entered_hash = hashlib.sha256(pwd_input.encode("utf-8")).hexdigest()
            if entered_hash == record["password_hash"]:
                authorized = True
            else:
                st.error("Incorrect password. Access denied.")
                
    if authorized:
        st.success(f"✓ Access Granted: Decrypting '{record['filename']}'")
        versions = get_document_versions(record["file_id"])
        
        if versions:
            latest_text = versions[-1]["text"]
            
            from utils.layout_pipeline import LayoutDocument, Block, BlockType, RecognizedLine, Alignment
            lines = [RecognizedLine(text=line, alignment=Alignment.LEFT, y=idx*20) for idx, line in enumerate(latest_text.splitlines())]
            doc_obj = LayoutDocument(blocks=[Block(type=BlockType.PARAGRAPH, lines=lines)], page_width=800, page_height=1000)
            
            base_name = record["filename"].rsplit(".", 1)[0]
            from utils.exporters import export_txt, export_docx, export_pdf
            
            dl_col1, dl_col2, dl_col3 = st.columns(3)
            txt_data = export_txt(doc_obj).encode("utf-8")
            docx_data = export_docx(doc_obj, base_name)
            
            # Embed verification QR code directly inside public guest PDF downloads!
            pdf_data = export_pdf(doc_obj, base_name, doc_hash=hashlib.sha256(latest_text.encode("utf-8")).hexdigest())
            
            if record.get("one_time"):
                consume_share_link(share_id)
                
            with dl_col1:
                st.download_button("Download TXT", data=txt_data, file_name=f"{base_name}.txt", use_container_width=True, key="dl_share_txt")
            with dl_col2:
                st.download_button("Download Word DOCX", data=docx_data, file_name=f"{base_name}.docx", use_container_width=True, key="dl_share_docx")
            with dl_col3:
                st.download_button("Download PDF", data=pdf_data, file_name=f"{base_name}.pdf", use_container_width=True, key="dl_share_pdf")
        else:
            st.error("No document payload found on server storage for this file.")
            
    if st.button("Go to SecureDocAI Home", key="btn_home_share_back"):
        st.query_params.clear()
        st.rerun()


def render_authenticated():
    """Protected workspace view containing top navbar navigation routing."""
    from components.navbar import render_navbar
    render_navbar(user=st.session_state.user)
    
    render_breadcrumbs()
    
    page = st.session_state.active_page
    
    if page != "Home":
        if st.button("← Back", key="app_back_button"):
            st.session_state.prev_page = page
            st.session_state.active_page = "Home"
            st.rerun()
            
    # Page Routing
    if page == "Home":
        from app_pages.Home import render as render_page
    elif page == "Scan":
        from app_pages.Scan import render as render_page
    elif page == "Library":
        from app_pages.Library import render as render_page
    elif page == "Profile":
        from app_pages.Profile import render as render_page
    elif page == "Dashboard":
        from app_pages.Dashboard import render as render_page
    else:
        from app_pages.Home import render as render_page
        
    render_page()
    render_footer()

def main():
    initialize_app()
    initialize_session()
    load_theme()

    # 0. Handle Google OAuth Callback redirection parameters
    q_params = st.query_params
    
    if "error" in q_params:
        # Silent auto-login failed (e.g. Guest mode or unauthenticated Google Account)
        st.session_state.auto_login_attempted = True
        st.query_params.clear()
        st.rerun()

    if "code" in q_params and "state" in q_params:
        code = q_params["code"]
        state = q_params["state"]
        
        # Parse target page navigation back from state param
        target_page = "Home"
        if ":" in state:
            target_page = state.split(":", 1)[0]
            
        if st.session_state.get("last_oauth_code") != code:
            st.session_state.last_oauth_code = code
            try:
                from utils.security import exchange_google_code, save_persistent_drive_creds
                user, creds = exchange_google_code(code)
                
                # Persist local user profile and credentials
                st.session_state.user = user
                st.session_state.drive_creds = creds
                save_persistent_drive_creds(user.get("email"), creds)
                
                # Auto-create SecureDocAI app folders immediately
                try:
                    from utils.helpers import ensure_folders
                    ensure_folders(creds)
                except Exception as e:
                    logger.warning(f"Google Drive folder auto-creation failed: {e}")
                    
                st.session_state.toast_queue.append(("Google Account linked successfully! ☁️", "success"))
                st.session_state.auto_login_attempted = True
                
                # Restore active view/page routing state
                if target_page in ["login", "signup", "landing", "auto_login"]:
                    st.session_state.auth_view = "landing"
                    st.session_state.active_page = "Home"
                else:
                    st.session_state.active_page = target_page
                    st.session_state.auth_view = "landing"
            except Exception as e:
                st.session_state.toast_queue.append((f"Google Link failed: {e}", "error"))
                
        st.query_params.clear()
        st.rerun()
    
    # Auto-login checking and redirection logic completely removed.
            
    # 3. Check token renewals and Session Timeout
    if st.session_state.user is not None:
        # Check session inactivity timeout (15 mins)
        current_time = time.time()
        if "last_active_time" in st.session_state:
            if current_time - st.session_state.last_active_time > 900:
                from utils.security import logout_user
                logout_user()
                st.session_state.toast_queue.append(("Session expired due to inactivity. Please log in again.", "warning"))
                st.session_state.active_page = "Home"
                st.session_state.auth_view = "login"
                st.rerun()
        st.session_state.last_active_time = current_time

        check_session_expiry()
        check_drive_connection()
        
        # Sync Drive persistence
        if st.session_state.drive_creds is None:
            from utils.security import load_persistent_drive_creds
            email = st.session_state.user.get("email")
            if email:
                creds = load_persistent_drive_creds(email)
                if creds:
                    st.session_state.drive_creds = creds

    # V2: Intercept Public Verification or Share parameters
    if "verify" in q_params:
        render_public_verification(q_params["verify"])
        render_footer()
        return
        
    if "share" in q_params:
        render_public_share(q_params["share"])
        render_footer()
        return

    render_notifications()

    # Protected routing guard
    if st.session_state.user is None:
        if st.session_state.active_page != "Home":
            st.session_state.active_page = "Home"
        render_unauthenticated()
    else:
        render_authenticated()

if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        logger.exception("Global Application Crash Captured:")
        st.error("⚠️ An unexpected application error occurred.")
        st.info("Please reload the webpage or contact support.")
        if st.checkbox("Show technical debug log details (Debug Mode)"):
            st.code(str(err))

# Module hot-reload watcher trigger

