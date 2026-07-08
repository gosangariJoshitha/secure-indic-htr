"""
app_pages/Login.py
==================
Centered premium login page styled like a high-end SaaS product.
Eliminates nested columns to avoid Streamlit nesting layout exceptions.
"""

from __future__ import annotations

import re
import time
import streamlit as st
from components.ui_helpers import html_block, full_width_kwargs
from config import COLORS, APP_NAME, BUILD_DATE

EMAIL_REGEX = re.compile(r"^[^@]+@[^@]+\.[^@]+$")

def _go(view: str):
    st.session_state.auth_view = view
    st.rerun()

def _attempt_login(email: str, password: str, remember: bool):
    email = email.strip().lower()
    if not email or not password:
        st.error("Enter both email and password.")
        return

    if not EMAIL_REGEX.match(email):
        st.error("Please enter a valid email address.")
        return

    from utils.security import verify_email_password, save_remember_session, AuthError
    try:
        status_placeholder = st.empty()
        with status_placeholder.container():
            with st.spinner("Connecting to Firebase..."):
                time.sleep(0.3)
                user = verify_email_password(email, password)
    except AuthError as e:
        status_placeholder.empty()
        st.error(e.message)
        return

    status_placeholder.empty()
    st.session_state.user = user

    if remember and user.get("refresh_token"):
        save_remember_session(user["refresh_token"])

    st.success(f"Welcome back, {user['name']}! 👋 Login successful. Redirecting...")
    time.sleep(1.0)
    st.session_state.auth_view = "landing"
    st.rerun()

def _attempt_google_login():
    pass # Replaced by inline link_button in render()

def render():
    if st.session_state.get("user"):
        st.session_state.auth_view = "landing"
        st.rerun()
        return

    # 1. Header banner
    html_block(f"""
    <div class="sd-card" style="padding:36px; text-align:center;
        background: linear-gradient(135deg, #1E3A8A 0%, #0F172A 100%);
        border: none; border-radius: 16px; margin-bottom: 24px; box-shadow: 0 10px 20px rgba(15, 23, 42, 0.15);">
        
        <!-- Modern Security SVG Graphic -->
        <svg width="60" height="60" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="margin: 0 auto 12px auto; display:block;">
            <path d="M12 22C12 22 20 18 20 12V5L12 2L4 5V12C4 18 12 22 12 22Z" stroke="#38BDF8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M9 11L11 13L15 9" stroke="#34D399" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        
        <h2 style="font-weight:800; color:#ffffff; font-size:1.8rem; letter-spacing:-0.02em; margin-bottom:8px; margin-top:0;">
            Secure & Private Document Vault
        </h2>
        <p style="color:#94A3B8; font-size:0.95rem; line-height:1.5; margin: 0 auto; max-width: 560px;">
            Log in to your private database to scan, digitize and protect your documents using layout reconstruction and local keys.
        </p>
    </div>
    """)

    # 2. Form Card
    c_left, c_center, c_right = st.columns([1, 1.8, 1])
    with c_center:
        with st.container(border=True):
            html_block(f"""
            <div style="text-align:center; margin-bottom:20px; padding-top:10px;">
                <div style="width:44px; height:44px; border-radius:10px; margin:0 auto;
                    background:linear-gradient(135deg,{COLORS['primary']},{COLORS['accent']});
                    display:flex; align-items:center; justify-content:center; color:white; font-weight:950; font-size:1.3rem;">
                    S
                </div>
                <h3 style="margin-top:12px; font-weight:800; color:#0F172A; font-size:1.3rem; letter-spacing:-0.01em; margin-bottom:4px;">Welcome Back</h3>
                <p style="color:#64748B; font-size:0.88rem; margin:0;">Log in to access your secure database</p>
            </div>
            """)

            with st.form("login_form", clear_on_submit=False):
                email = st.text_input("Email Address", placeholder="name@company.com", key="login_email")
                password = st.text_input("Password", type="password", placeholder="••••••••", key="login_password")
                
                remember = st.checkbox("Remember me on this device", key="login_remember")
                
                if st.form_submit_button("Log In", type="primary", use_container_width=True):
                    _attempt_login(email, password, remember)

            if st.button("Forgot password?", key="login_forgot_toggle", use_container_width=True):
                st.session_state.show_reset_form = not st.session_state.get("show_reset_form", False)

            if st.session_state.get("show_reset_form"):
                reset_email = st.text_input("Enter reset email", key="login_reset_email")
                if st.button("📧 Send Reset Link", key="login_reset_submit", use_container_width=True):
                    from utils.security import send_password_reset, AuthError
                    try:
                        send_password_reset(reset_email)
                        st.success("Reset email sent — check your inbox.")
                    except AuthError as e:
                        st.error(e.message)

            html_block(f"<div style='text-align:center; color:{COLORS['text_secondary']}; font-size:0.75rem; margin:12px 0;'>— or —</div>")

            try:
                from utils.security import get_google_auth_url, AuthError
                if "google_auth_url_login" not in st.session_state:
                    auth_url, state = get_google_auth_url("login")
                    st.session_state.google_auth_url_login = auth_url
                    st.session_state.google_auth_state_login = state
                    
                st.session_state.oauth_state = st.session_state.google_auth_state_login
                btn_html = f'''<a href="{st.session_state.google_auth_url_login}" target="_blank" 
                               style="display:block; width:100%; padding:0.5rem; text-align:center; 
                                      background-color:#0EA5E9; color:white; border-radius:0.5rem; 
                                      text-decoration:none; font-family:sans-serif; font-weight:600;">
                               🔑 Continue with Google Account
                               </a>'''
                st.markdown(btn_html, unsafe_allow_html=True)
            except AuthError as e:
                st.error(e.message)
            except Exception as e:
                st.error(f"Failed to setup Google Auth: {e}")

            html_block("<div class='sd-divider' style='margin: 16px 0;'></div>")
            
            if st.button("New here? Create Account", use_container_width=True, key="login_to_signup"):
                _go("signup")

        if st.button("← Back to home", key="login_back", use_container_width=True):
            _go("landing")

    # Layout Footer
    html_block(f"""
    <div style="margin-top: 40px; text-align: center; padding: 20px 0; border-top: 1px solid #E2E8F0; font-size: 0.8rem; color: #64748B;">
        {APP_NAME} Core v2.0 • Privacy Policy • Terms of Service • Build {BUILD_DATE}
    </div>
    """)
