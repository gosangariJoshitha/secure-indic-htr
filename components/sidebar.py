"""
components/sidebar.py
======================
Left-hand navigation rail. Drives Streamlit's session-based "page" routing
(app.py reads st.session_state['active_page'] and renders the matching module
from /pages, since this project intentionally uses single-app routing rather
than Streamlit's native multipage folder, to keep full control over the shell).

Usage:
    from components.sidebar import render_sidebar
    render_sidebar()
"""

import streamlit as st
from components.ui_helpers import html_block, full_width_kwargs
from config import COLORS, NAV_ITEMS, APP_NAME

# Minimal icon glyphs (emoji fallback so no extra icon package is required).
# Swap for streamlit-extras / lucide if you want pixel-perfect icons later.
_ICONS = {
    "layout-dashboard": "🏠",
    "scan-text": "📷",
    "history": "📚",
    "settings": "👤",
}


def render_sidebar():
    if "active_page" not in st.session_state:
        st.session_state.active_page = "Home"

    with st.sidebar:
        html_block(f"""
            <div style="display:flex; align-items:center; gap:10px; padding:8px 4px 20px 4px;">
                <div style="
                    width:34px; height:34px; border-radius:9px;
                    background:linear-gradient(135deg, {COLORS['primary']}, {COLORS['accent']});
                    display:flex; align-items:center; justify-content:center;
                    color:white; font-weight:800;">S</div>
                <span style="font-weight:800; font-size:1rem; color:{COLORS['text']};">{APP_NAME}</span>
            </div>
            """)

        for item in NAV_ITEMS:
            is_active = st.session_state.active_page == item["page"]
            icon = _ICONS.get(item["icon"], "•")

            if st.button(
                f"{icon}  {item['label']}",
                key=f"nav_{item['page']}",
                **full_width_kwargs(widget=st.button),
                type="primary" if is_active else "secondary"):
                st.session_state.active_page = item["page"]
                st.rerun()

        html_block("<div class='sd-divider'></div>")

        html_block(f"""
            <div class="sd-card" style="padding:14px; text-align:center;">
                <div style="font-size:0.78rem; color:{COLORS['text_secondary']}; margin-bottom:6px;">
                    Storage
                </div>
                <div style="font-size:0.78rem; font-weight:700; color:{COLORS['primary']};">
                    Synced to your Google Drive
                </div>
            </div>
            """)

        if st.button("🚪  Log out", **full_width_kwargs(widget=st.button), key="nav_logout"):
            from utils.security import clear_remember_session
            clear_remember_session()
            for key in list(st.session_state.keys()):
                st.session_state.pop(key, None)
            st.session_state.auth_view = "landing"
            st.session_state.active_page = "Home"
            st.rerun()
