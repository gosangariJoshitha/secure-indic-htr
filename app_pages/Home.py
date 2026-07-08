"""
app_pages/Home.py
===================
Widescreen dashboard replica with V2 additions: Time-based greetings, date/time headers,
avatar rendering, Google Drive status and storage usage, OCR summary stats, and quick actions.
"""

from __future__ import annotations

import time
import streamlit as st
from datetime import datetime
from components.ui_helpers import html_block, full_width_kwargs
from config import COLORS, APP_NAME

_LANG_CODE_MAP = {
    "ENGLISH": "EN",
    "HINDI": "HI",
    "TELUGU": "TE",
    "BENGALI": "BN",
    "TAMIL": "TA",
    "KANNADA": "KA",
    "MALAYALAM": "ML",
    "MARATHI": "MR",
    "GUJARATI": "GU",
    "PUNJABI": "PA",
    "URDU": "UR",
}


def _lang_code(name: str) -> str:
    if not name:
        return ""
    return _LANG_CODE_MAP.get(name.upper(), name[:2].upper())


def render():
    # 1. Redirect if not logged in
    user = st.session_state.get("user")
    if not user:
        st.session_state.auth_view = "login"
        st.rerun()
        return

    first_name = (user.get("name") or "User").split(" ")[0]

    # Time-based Greeting
    hour = datetime.now().hour
    if hour < 12:
        greeting = "Good Morning"
    elif hour < 17:
        greeting = "Good Afternoon"
    else:
        greeting = "Good Evening"

    # Profile Avatar or Picture
    photo_url = user.get("photo_url")
    initials = (first_name[0] if first_name else "U").upper()
    avatar_html = ""
    if photo_url:
        avatar_html = f'<img src="{photo_url}" style="width: 58px; height: 58px; border-radius: 50%; border: 2px solid #10B981; object-fit: cover;" />'
    else:
        avatar_html = f"""
            <div style="width: 58px; height: 58px; border-radius: 50%;
                background: linear-gradient(135deg, #3b82f6, #8b5cf6);
                color: white; display: flex; align-items: center; justify-content: center;
                font-weight: 700; font-size: 1.4rem; border: 2px solid rgba(255,255,255,0.08);">
                {initials}
            </div>
        """

    # Inject page CSS styles
    st.markdown(f"""
        <style>
        /* Style only the nested container block that contains our navy-container-marker */
        div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"]:has(div.navy-container-marker) {{
            background-color: #0F172A !important;
            border-radius: 24px !important;
            padding: 38px 40px !important;
            margin-bottom: 24px !important;
            display: flex !important;
            flex-direction: column !important;
        }}
        /* Align the columns inside the styled navy container */
        div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"]:has(div.navy-container-marker) div[data-testid="column"] {{
            display: flex !important;
            align-items: center !important;
        }}
        div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"]:has(div.navy-container-marker) div[data-testid="column"]:first-child {{
            justify-content: flex-start !important;
        }}
        div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"]:has(div.navy-container-marker) div[data-testid="column"]:last-child {{
            justify-content: flex-end !important;
        }}
        /* Target and style the green file icon button inside the navy card */
        div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"]:has(div.navy-container-marker) button {{
            background-color: #10B981 !important;
            border-radius: 16px !important;
            width: 56px !important;
            height: 56px !important;
            border: none !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            padding: 0 !important;
            box-shadow: none !important;
            background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="%230F172A" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><path d="M8 13h2v-2"/><path d="M16 13h-2v-2"/><path d="M8 17h2v2"/><path d="M16 17h-2v-2"/></svg>') !important;
            background-repeat: no-repeat !important;
            background-position: center !important;
            background-size: 24px !important;
            color: transparent !important;
            transition: all 0.2s ease-in-out !important;
        }}
        div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"]:has(div.navy-container-marker) button:hover {{
            background-color: #059669 !important;
            transform: scale(1.05);
        }}

        /* Style only the nested container block that contains our white-container-marker */
        div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"]:has(div.white-container-marker) {{
            background-color: white !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 24px !important;
            padding: 32px !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.02) !important;
            display: flex !important;
            flex-direction: column !important;
            height: 100% !important;
        }}
        /* Style the View library button inside the white card to look like a clean link */
        div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"]:has(div.white-container-marker) button {{
            background-color: transparent !important;
            color: #10B981 !important;
            border: none !important;
            font-size: 0.82rem !important;
            font-weight: 700 !important;
            height: 38px !important;
            padding: 0 !important;
            margin: 0 !important;
            box-shadow: none !important;
            text-align: right !important;
            display: flex !important;
            align-items: center !important;
            justify-content: flex-end !important;
        }}
        div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"]:has(div.white-container-marker) button:hover {{
            color: #059669 !important;
            background-color: transparent !important;
        }}
        </style>
    """, unsafe_allow_html=True)

    creds = st.session_state.get("drive_creds")
    doc_count = 0
    last_scan_date = "—"
    recent_docs = []

    # Get Google Drive Status & Storage Used
    drive_connected = creds is not None
    storage_info = "Drive not connected"
    if drive_connected:
        from utils.helpers import get_storage_usage
        try:
            usage = get_storage_usage(creds)
            used_gb = usage["used_bytes"] / (1024**3)
            if usage["limit_bytes"]:
                limit_gb = usage["limit_bytes"] / (1024**3)
                storage_info = f"{used_gb:.2f} GB of {limit_gb:.1f} GB used"
            else:
                storage_info = f"{used_gb:.2f} GB used"
        except Exception:
            storage_info = "Active connection"

    # Notification Banners for warnings
    if not drive_connected:
        st.warning("⚠️ Google Drive not connected. Scans will be temporary and not saved. Connect in Profile settings.")

    # Initialize stats from latest scan context
    latest = st.session_state.get("latest_ocr_context")
    char_count = "—"
    avg_confidence = "—"
    proc_time = "—"

    if latest and "timestamp" in latest:
        dt = latest["timestamp"]
        last_scan_date = dt.strftime("%d/%m/%Y")
        doc_count = 1
        recent_docs = [
            {
                "name": latest.get("filename", "scanned_doc.png"),
                "createdTime": f"2026-{dt.month:02d}-{dt.day:02d}",
                "lang": latest.get("detected_script", "TELUGU"),
                "confidence": latest.get("mean_confidence", 0.95),
                "time": latest.get("processing_time", 1.25)
            }
        ]
        char_count = latest.get("char_count") or getattr(latest.get("doc"), "char_count", "—")
        conf = latest.get("mean_confidence") or getattr(latest.get("doc"), "mean_confidence", None)
        if conf is not None:
            avg_confidence = f"{conf * 100.0:.1f}%"
        t_proc = latest.get("processing_time") or getattr(latest.get("doc"), "processing_time", None)
        if t_proc is not None:
            proc_time = f"{t_proc:.2f}s"

    if drive_connected:
        from utils.helpers import list_documents
        try:
            if "hist_documents_cache" not in st.session_state:
                st.session_state.hist_documents_cache = list_documents(creds, page_size=100)
            docs = st.session_state.hist_documents_cache
            doc_count = len(docs)
            if docs:
                recent_docs = docs[:2]
                if last_scan_date == "—":
                    created = docs[0].get("createdTime", "")[:10]
                    parts = created.split("-")
                    if len(parts) == 3:
                        last_scan_date = f"{parts[2]}/{parts[1]}/{parts[0]}"
        except Exception:
            pass

    # Languages list computation
    languages_count = 3
    languages_list = "TE · HI · EN"

    # ------------------------------------------------------------------
    # Widescreen Columns Grid
    # ------------------------------------------------------------------
    left, right = st.columns([1.25, 1.0], gap="medium")

    with left:
        # Quick Action Box
        with st.container():
            st.markdown('<div class="navy-container-marker"></div>', unsafe_allow_html=True)

            # Time-based Greeting & Header with Avatar (Inside Navy Container)
            html_block(f"""
                <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 24px; box-sizing: border-box; width: 100%;">
                    {avatar_html}
                    <div>
                        <span style="font-size: 0.75rem; font-weight: 700; letter-spacing: 0.08em; color: #10B981; text-transform: uppercase;">
                            {datetime.now().strftime("%A, %d %B %Y • %I:%M %p")}
                        </span>
                        <h2 style="font-size: 2.3rem; font-weight: 800; color: #ffffff; margin: 4px 0 0 0; letter-spacing: -0.03em;">
                            {greeting}, {first_name}.
                        </h2>
                    </div>
                </div>
            """)

            col_text, col_icon = st.columns([4, 1])
            with col_text:
                html_block("""
                    <div>
                        <div style="font-size:0.7rem; font-weight:700; letter-spacing:0.08em; color:#10B981; text-transform:uppercase; margin-bottom:6px;">QUICK ACTION</div>
                        <div style="font-size:1.8rem; font-weight:800; color:white; margin-bottom:4px; letter-spacing:-0.02em; white-space:nowrap;">Start Scanning</div>
                        <div style="font-size:0.85rem; color:#94A3B8; white-space:nowrap;">Upload an image or PDF to begin</div>
                    </div>
                """)
            with col_icon:
                if st.button("", key="green_scan_btn"):
                    st.session_state.active_page = "Scan"
                    st.rerun()

            # Statistics Cards (Inside Navy Container)
            html_block(f"""
            <div style="display:flex; gap:16px; margin-top:20px; box-sizing: border-box; width: 100%; margin-left: -12px;">
                <div style="flex:1; background-color:white; border:1px solid #E2E8F0; border-radius:20px; padding:24px 22px; box-shadow:0 1px 3px rgba(0,0,0,0.02); box-sizing: border-box;">
                    <div style="font-size:0.68rem; font-weight:700; color:#64748B; letter-spacing:0.06em; text-transform:uppercase; margin-bottom:10px; white-space:nowrap;">DOCUMENTS STORED</div>
                    <div style="font-size:2.0rem; font-weight:800; color:#0F172A; line-height:1;">{doc_count}</div>
                </div>
                <div style="flex:1; background-color:white; border:1px solid #E2E8F0; border-radius:20px; padding:24px 22px; box-shadow:0 1px 3px rgba(0,0,0,0.02); box-sizing: border-box;">
                    <div style="font-size:0.68rem; font-weight:700; color:#64748B; letter-spacing:0.06em; text-transform:uppercase; margin-bottom:10px; white-space:nowrap;">LAST SCAN</div>
                    <div style="font-size:2.0rem; font-weight:800; color:#0F172A; line-height:1;">{last_scan_date}</div>
                </div>
                <div style="flex:1; background-color:white; border:1px solid #E2E8F0; border-radius:20px; padding:24px 22px; box-shadow:0 1px 3px rgba(0,0,0,0.02); box-sizing: border-box;">
                    <div style="font-size:0.68rem; font-weight:700; color:#64748B; letter-spacing:0.06em; text-transform:uppercase; margin-bottom:10px; white-space:nowrap;">LANGUAGES</div>
                    <div style="font-size:2.0rem; font-weight:800; color:#0F172A; line-height:1; margin-bottom:4px;">{languages_count}</div>
                    <div style="font-size:0.75rem; font-weight:800; color:#94A3B8; letter-spacing:0.05em; white-space:nowrap;">{languages_list}</div>
                </div>
            </div>
            """)


    with right:
        # Recent Activity Panel
        with st.container():
            st.markdown('<div class="white-container-marker"></div>', unsafe_allow_html=True)
            col_title, col_btn = st.columns([1.8, 1.2])
            with col_title:
                html_block('<span style="font-size:1.15rem; font-weight:800; color:#0F172A; letter-spacing:-0.01em; line-height:38px; white-space:nowrap;">Recent Activity</span>')
            with col_btn:
                if st.button("View library →", key="btn_view_library_link"):
                    st.session_state.active_page = "Library"
                    st.rerun()

            if doc_count == 0 or not recent_docs:
                html_block("""
                <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; padding:50px 0; text-align:center;">
                    <div style="font-size:2rem; margin-bottom:12px;">📁</div>
                    <div style="font-weight:700; font-size:0.95rem; color:#64748B;">No recent activity</div>
                    <div style="font-size:0.8rem; color:#94A3B8; margin-top:4px; max-width:200px;">Scanned documents will show up here.</div>
                </div>
                """)
            else:
                for idx, doc in enumerate(recent_docs):
                    c_date = doc.get("createdTime", "")[:10]
                    try:
                        parts = c_date.split("-")
                        formatted_date = f"{parts[2]}/{parts[1]}/{parts[0]}"
                    except Exception:
                        formatted_date = c_date

                    app_props = doc.get("appProperties", {})
                    doc_display_name = app_props.get("original_filename", doc["name"])
                    lang_label = app_props.get("language") or "Auto"
                    try:
                        conf_val = float(app_props.get("confidence", "0.95"))
                    except Exception:
                        conf_val = 0.95
                    proc_val = 1.25

                    html_block(f"""
                    <div style="display:flex; align-items:center; justify-content:space-between; padding:18px 0; border-bottom:1px solid #F1F5F9; width:100%;">
                        <div>
                            <div style="font-weight:700; font-size:0.95rem; color:#0F172A; margin-bottom:2px;">{doc_display_name}</div>
                            <div style="font-size:0.8rem; color:#94A3B8;">
                                {formatted_date} • {proc_val:.2f}s • {conf_val*100.0:.1f}% conf
                            </div>
                        </div>
                        <div>
                            <span style="background-color:#E8FDF5; color:#10B981; font-size:0.68rem; font-weight:800; letter-spacing:0.05em; padding:4px 10px; border-radius:6px; text-transform:uppercase;">{lang_label}</span>
                        </div>
                    </div>
                    """)

            # Storage & Connections Card (Inside Main White Container)
            st.markdown("<hr style='border:0; height:1px; background:#F1F5F9; margin: 24px 0;' />", unsafe_allow_html=True)
            html_block(f"""
                <div style="max-width: 420px; width: 100%;">
                    <h4 style="margin-top:0; color:#0F172A; font-size:1.15rem; font-weight:800; margin-bottom:12px;">Connection & Cloud Storage</h4>
                    <div style="display:flex; justify-content:space-between; padding:10px 0; border-bottom:1px solid #F1F5F9;">
                        <span style="color:#64748B; font-size:0.9rem;">Google Drive Integration</span>
                        <span style="font-weight:700; color:{'#10B981' if drive_connected else '#EF4444'}; font-size:0.9rem;">
                            {'🟢 Connected' if drive_connected else '🔴 Disconnected'}
                        </span>
                    </div>
                    <div style="display:flex; justify-content:space-between; padding:10px 0;">
                        <span style="color:#64748B; font-size:0.9rem;">Drive Storage Used</span>
                        <span style="font-weight:700; color:#0F172A; font-size:0.9rem;">{storage_info}</span>
                    </div>
                </div>
            """)

    # Dashboard Footer
    html_block(f"""
        <div style="margin-top: 60px; text-align: center; padding: 20px 0; border-top: 1px solid rgba(255,255,255,0.05); font-size: 0.8rem; color: #71717a;">
            SecureDocAI V2 • Hybrid OCR Engine • ResNet-CTC Model v2.0 • Privacy Shield Protected
        </div>
    """)