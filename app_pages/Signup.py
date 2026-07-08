"""
app_pages/Signup.py
==================
Centered premium registration page styled like a high-end SaaS product.
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

def check_password_strength(pwd: str) -> tuple[str, str]:
    if not pwd:
        return "", ""
    score = 0
    if len(pwd) >= 8:
        score += 1
    if any(c.isupper() for c in pwd):
        score += 1
    if any(c.islower() for c in pwd):
        score += 1
    if any(c.isdigit() for c in pwd):
        score += 1
    if any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in pwd):
        score += 1

    if score <= 2:
        return "🔴 Weak (requires 8+ characters, uppercase, number, special character)", "red"
    elif score <= 4:
        return "🟡 Medium (add numbers or special characters)", "orange"
    else:
        return "🟢 Strong Password", "green"

def _attempt_register(name: str, email: str, password: str, confirm: str, role: str):
    name = name.strip()
    email = email.strip().lower()

    if not all([name, email, password, confirm]):
        st.error("Please fill in every field.")
        return

    if len(name) < 3:
        st.error("Name must be at least 3 characters long.")
        return

    if not EMAIL_REGEX.match(email):
        st.error("Please enter a valid email address.")
        return

    if password != confirm:
        st.error("Passwords do not match.")
        return

    strength_msg, color = check_password_strength(password)
    if color == "red":
        st.error("Your password is too weak. Please satisfy the security requirements.")
        return

    from utils.security import create_account, AuthError
    try:
        status_placeholder = st.empty()
        with status_placeholder.container():
            with st.spinner("Creating account..."):
                time.sleep(0.3)
                create_account(name, email, password, role)
    except AuthError as e:
        status_placeholder.empty()
        st.error(e.message)
        return

    status_placeholder.empty()
    st.success("🎉 Account created successfully! Please verify your email before logging in.")
    st.toast("Redirecting to Login...")
    time.sleep(1.5)
    st.session_state.auth_view = "login"
    st.rerun()

def render():
    if st.session_state.get("user"):
        st.session_state.auth_view = "landing"
        st.rerun()
        return

    # 1. Header banner
    html_block(f"""
    <div class="sd-card" style="padding:36px; text-align:center;
        background: linear-gradient(135deg, #0D9488 0%, #0F172A 100%);
        border: none; border-radius: 16px; margin-bottom: 24px; box-shadow: 0 10px 20px rgba(15, 23, 42, 0.15);">
        
        <!-- Modern Database SVG Graphic -->
        <svg width="60" height="60" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="margin: 0 auto 12px auto; display:block;">
            <path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM13 17H11V15H13V17ZM13 13H11V7H13V13Z" fill="#38BDF8"/>
        </svg>
        
        <h2 style="font-weight:800; color:#ffffff; font-size:1.8rem; letter-spacing:-0.02em; margin-bottom:8px; margin-top:0;">
            Create Your Free Secure Vault
        </h2>
        <p style="color:#94A3B8; font-size:0.95rem; line-height:1.5; margin: 0 auto; max-width: 560px;">
            Register to get access to multi-language handwriting recognition, real-time PDF scanning, and digital signature ledgers.
        </p>
    </div>
    """)

    # 2. Form Card
    c_left, c_center, c_right = st.columns([1, 1.8, 1])
    with c_center:
        with st.container(border=True):
            html_block(f"""
            <div style="text-align:center; margin-bottom:20px; padding-top:10px;">
                <h3 style="font-weight:800; color:#0F172A; font-size:1.3rem; letter-spacing:-0.01em; margin-bottom:4px;">Create Account</h3>
                <p style="color:#64748B; font-size:0.88rem; margin:0;">Create a secure local profile in under a minute</p>
            </div>
            """)

            with st.form("signup_form", clear_on_submit=False):
                name = st.text_input("Full Name", placeholder="John Doe", key="su_name")
                email = st.text_input("Email Address", placeholder="name@company.com", key="su_email")
                
                password = st.text_input("Password", type="password", placeholder="••••••••", key="su_password")
                confirm = st.text_input("Confirm Password", type="password", placeholder="••••••••", key="su_confirm")

                if password:
                    strength_msg, color = check_password_strength(password)
                    st.markdown(f"<span style='color:{color}; font-size:0.8rem; font-weight:600;'>{strength_msg}</span>", unsafe_allow_html=True)

                if st.form_submit_button("Register Account", type="primary", use_container_width=True):
                    _attempt_register(name, email, password, confirm, "Other")

            html_block(f"<div style='text-align:center; color:{COLORS['text_secondary']}; font-size:0.75rem; margin:12px 0;'>— or —</div>")

            if st.button("🔑 Continue with Google Account", use_container_width=True, key="su_google"):
                from utils.security import get_google_auth_url, AuthError
                try:
                    auth_url, state = get_google_auth_url("signup")
                    st.session_state.oauth_state = state
                    st.session_state.oauth_redirect_in_progress = True
                    st.markdown(f'<meta http-equiv="refresh" content="0; url={auth_url}">', unsafe_allow_html=True)
                    st.info("Redirecting to Google Sign-In...")
                except AuthError as e:
                    st.error(e.message)
                except Exception as e:
                    st.error(f"Google Sign-In failed: {e}")

            html_block(f"""
            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:12px; margin-top:16px; font-size:0.75rem; color:#64748B; text-align:center; line-height:1.4;">
                ☁️ Your files remain inside your own Google Drive. SecureDocAI never stores them on our servers.
            </div>
            """)

            html_block("<div class='sd-divider' style='margin: 16px 0;'></div>")
            
            if st.button("Have an account? Log In Instead", use_container_width=True, key="su_to_login"):
                _go("login")

        if st.button("← Back to home", key="su_back", use_container_width=True):
            _go("landing")

    # Layout Footer
    html_block(f"""
    <div style="margin-top: 40px; text-align: center; padding: 20px 0; border-top: 1px solid #E2E8F0; font-size: 0.8rem; color: #64748B;">
        {APP_NAME} Core v2.0 • Privacy Policy • Terms of Service • Build {BUILD_DATE}
    </div>
    """)
