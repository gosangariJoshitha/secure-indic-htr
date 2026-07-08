"""
components/navbar.py
=====================
Horizontal top navigation header using native Streamlit columns.
"""

import streamlit as st
from components.ui_helpers import html_block
from config import COLORS, APP_NAME

def render_navbar(user: dict | None = None):
    # CSS scoping using sibling combinator to prevent style leakage to other pages
    with st.container():
        st.markdown(f"""
            <style>
            [data-testid="stSidebar"] {{
                display: none !important;
            }}
            [data-testid="collapsedControl"] {{
                display: none !important;
            }}

            /* Page-wide container sizing — intentionally global */
            .stMainBlockContainer {{
                max-width: 95% !important;
                padding-top: 1.5rem !important;
                padding-left: 2rem !important;
                padding-right: 2rem !important;
            }}

            /* --- Navbar Scoped styling via adjacent sibling selector --- */

            .app-navbar-wrapper + div[data-testid="stHorizontalBlock"] .stButton > button {{
                border-radius: 20px !important;
                padding: 4px 18px !important;
                font-size: 0.92rem !important;
                font-weight: 600 !important;
                height: 38px !important;
                min-width: fit-content !important;
                white-space: nowrap !important;
                border: 1px solid transparent !important;
                transition: all 0.2s ease-in-out !important;
            }}
            .app-navbar-wrapper + div[data-testid="stHorizontalBlock"] .stButton > button[kind="secondary"],
            .app-navbar-wrapper + div[data-testid="stHorizontalBlock"] .stButton > button[data-testid="baseButton-secondary"] {{
                background-color: transparent !important;
                color: #64748B !important;
                border: 1px solid transparent !important;
            }}
            .app-navbar-wrapper + div[data-testid="stHorizontalBlock"] .stButton > button[kind="secondary"]:hover,
            .app-navbar-wrapper + div[data-testid="stHorizontalBlock"] .stButton > button[data-testid="baseButton-secondary"]:hover {{
                background-color: {COLORS['hover']} !important;
                color: {COLORS['primary']} !important;
            }}
            .app-navbar-wrapper + div[data-testid="stHorizontalBlock"] .stButton > button[kind="primary"],
            .app-navbar-wrapper + div[data-testid="stHorizontalBlock"] .stButton > button[data-testid="baseButton-primary"] {{
                background-color: {COLORS['primary']} !important;
                color: white !important;
                box-shadow: none !important;
            }}

            .app-navbar-wrapper + div[data-testid="stHorizontalBlock"] div[data-testid="column"] {{
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }}
            .app-navbar-wrapper + div[data-testid="stHorizontalBlock"] div[data-testid="column"]:first-child {{
                justify-content: flex-start !important;
            }}
            .app-navbar-wrapper + div[data-testid="stHorizontalBlock"] div[data-testid="column"]:last-child {{
                justify-content: flex-end !important;
            }}

            .app-navbar-wrapper + div[data-testid="stHorizontalBlock"] .logout-btn-wrapper button {{
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }}
            .app-navbar-wrapper + div[data-testid="stHorizontalBlock"] .logout-btn-wrapper button::before {{
                content: "" !important;
                display: inline-block !important;
                width: 15px !important;
                height: 15px !important;
                background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="%2364748B" viewBox="0 0 16 16"><path fill-rule="evenodd" d="M10 12.5a.5.5 0 0 1-.5.5h-8a.5.5 0 0 1-.5-.5v-9a.5.5 0 0 1 .5-.5h8a.5.5 0 0 1 .5.5v2a.5.5 0 0 0 1 0v-2A1.5 1.5 0 0 0 9.5 2h-8A1.5 1.5 0 0 0 0 3.5v9A1.5 1.5 0 0 0 1.5 14h8a1.5 1.5 0 0 0 1.5-1.5v-2a.5.5 0 0 0-1 0v2z"/><path fill-rule="evenodd" d="M15.854 8.354a.5.5 0 0 0 0-.708l-3-3a.5.5 0 0 0-.708.708L14.293 7.5H5.5a.5.5 0 0 0 0 1h8.793l-2.147 2.146a.5.5 0 0 0 .708.708l3-3z"/></svg>') !important;
                background-size: 15px !important;
                background-repeat: no-repeat !important;
                margin-right: 6px !important;
            }}
            .app-navbar-wrapper + div[data-testid="stHorizontalBlock"] .logout-btn-wrapper button:hover::before {{
                background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="%2310B981" viewBox="0 0 16 16"><path fill-rule="evenodd" d="M10 12.5a.5.5 0 0 1-.5.5h-8a.5.5 0 0 1-.5-.5v-9a.5.5 0 0 1 .5-.5h8a.5.5 0 0 1 .5.5v2a.5.5 0 0 0 1 0v-2A1.5 1.5 0 0 0 9.5 2h-8A1.5 1.5 0 0 0 0 3.5v9A1.5 1.5 0 0 0 1.5 14h8a1.5 1.5 0 0 0 1.5-1.5v-2a.5.5 0 0 0-1 0v2z"/><path fill-rule="evenodd" d="M15.854 8.354a.5.5 0 0 0 0-.708l-3-3a.5.5 0 0 0-.708.708L14.293 7.5H5.5a.5.5 0 0 0 0 1h8.793l-2.147 2.146a.5.5 0 0 0 .708.708l3-3z"/></svg>') !important;
            }}
            </style>
        """, unsafe_allow_html=True)

        user = user or {"name": "Guest", "email": ""}
        current_page = st.session_state.get("active_page", "Home")

        # HTML class marker for adjacent sibling CSS targeting
        st.markdown('<div class="app-navbar-wrapper"></div>', unsafe_allow_html=True)

        # Native columns: Logo on left, spacer in middle, navigation buttons on right
        col_logo, col_spacer, col_home, col_scan, col_lib, col_prof, col_dash, col_logout = st.columns(
            [1.6, 1.8, 0.9, 0.9, 1.0, 1.0, 1.4, 1.4],
            gap="small"
        )

        with col_logo:
            # Stylized Green Shield logo matching the screenshot
            html_block(f"""<div style="display:flex; align-items:center; gap:10px; height:38px;">
                <div style="width:30px; height:30px; border-radius:50%; background-color:#10B981; display:flex; align-items:center; justify-content:center;">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                    </svg>
                </div>
                <span style="font-weight:800; font-size:1.3rem; color:#0F172A; letter-spacing:-0.03em; vertical-align: middle; white-space: nowrap;">SecureDoc<span style="color:#10B981;">.</span></span>
            </div>""")

        # col_spacer is left empty to create the space in the middle

        with col_home:
            if st.button("Home", key="nav_btn_home", type="primary" if current_page == "Home" else "secondary", use_container_width=True):
                st.session_state.active_page = "Home"
                st.rerun()

        with col_scan:
            if st.button("Scan", key="nav_btn_scan", type="primary" if current_page == "Scan" else "secondary", use_container_width=True):
                st.session_state.active_page = "Scan"
                st.rerun()

        with col_lib:
            if st.button("Library", key="nav_btn_lib", type="primary" if current_page == "Library" else "secondary", use_container_width=True):
                st.session_state.active_page = "Library"
                st.rerun()

        with col_prof:
            if st.button("Profile", key="nav_btn_prof", type="primary" if current_page == "Profile" else "secondary", use_container_width=True):
                st.session_state.active_page = "Profile"
                st.rerun()

        with col_dash:
            if st.button("Dashboard", key="nav_btn_dash", type="primary" if current_page == "Dashboard" else "secondary", use_container_width=True):
                st.session_state.active_page = "Dashboard"
                st.rerun()

        with col_logout:
            st.markdown('<div class="logout-btn-wrapper">', unsafe_allow_html=True)
            if st.button("Logout", key="nav_btn_logout", type="secondary", use_container_width=True):
                from utils.security import clear_remember_session
                clear_remember_session()
                for key in list(st.session_state.keys()):
                    st.session_state.pop(key, None)
                st.session_state.auth_view = "landing"
                st.session_state.active_page = "Home"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)