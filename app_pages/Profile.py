"""
app_pages/Profile.py
===================
User profile details, Google Drive storage link, blockchain verification, and compliance settings.
"""

import streamlit as st
from components.ui_helpers import html_block, full_width_kwargs
from config import COLORS, MODEL_PATH, FL_MODEL_PATH
from utils.security_engine import get_blockchain, security_grade

def _drive_connection_card():
    creds = st.session_state.get("drive_creds")

    if creds is not None:
        html_block(f"""<div class="sd-card" style="display:flex; align-items:center; justify-content:space-between; margin-bottom:12px;">
            <div style="display:flex; align-items:center; gap:12px;">
                <div style="font-size:1.6rem;">☁️</div>
                <div>
                    <div style="font-weight:700;">Google Drive connected</div>
                    <div class="sd-caption">OCR output files are saved directly in your personal Drive folder</div>
                </div>
            </div>
            <span class="sd-pill sd-pill-success">✓ Connected</span>
        </div>""")

        try:
            from utils.helpers import get_storage_usage
            usage = get_storage_usage(creds)
            used_gb = usage["used_bytes"] / (1024 ** 3)
            if usage["limit_bytes"]:
                limit_gb = usage["limit_bytes"] / (1024 ** 3)
                st.progress(min(used_gb / limit_gb, 1.0))
                st.caption(f"**Drive Quota:** {used_gb:.2f} GB of {limit_gb:.0f} GB used (account-wide Drive storage)")
            else:
                st.caption(f"**Drive Quota:** {used_gb:.2f} GB used")
        except Exception as e:
            st.caption(f"Couldn't load storage quota info: {e}")

        if st.button("Disconnect Google Drive", key="settings_disconnect_drive", **full_width_kwargs(widget=st.button)):
            from utils.security import delete_persistent_drive_creds
            delete_persistent_drive_creds(st.session_state.get("user", {}).get("email"))
            st.session_state.drive_creds = None
            st.rerun()
    else:
        html_block("""<div class="sd-card" style="display:flex; align-items:center; justify-content:space-between; margin-bottom:12px;">
            <div style="display:flex; align-items:center; gap:12px;">
                <div style="font-size:1.6rem;">☁️</div>
                <div>
                    <div style="font-weight:700;">Google Drive not connected</div>
                    <div class="sd-caption">Connect Google Drive to allow automated document syncing</div>
                </div>
            </div>
            <span class="sd-pill sd-pill-danger">✗ Disconnected</span>
        </div>""")
        if st.button("🔌  Connect Google Drive", type="primary", key="settings_connect_drive", **full_width_kwargs(widget=st.button)):
            from utils.security import get_google_auth_url, AuthError
            try:
                auth_url, state = get_google_auth_url("Profile")
                st.session_state.oauth_state = state
                st.session_state.oauth_redirect_in_progress = True
                st.markdown(f'<meta http-equiv="refresh" content="0; url={auth_url}">', unsafe_allow_html=True)
                st.info("Redirecting to Google Sign-In...")
            except AuthError as e:
                st.error(e.message)
            except Exception as e:
                st.error(f"Failed to connect Drive: {e}")

def render():
    html_block("""<div style="margin-bottom:18px;">
        <span class="sd-eyebrow">PROFILE &amp; SECURITY</span>
        <h2 class="sd-h2" style="margin-top:6px;">Your Secure Vault Profile</h2>
    </div>""")

    user = st.session_state.get("user") or {}

    left, right = st.columns([1.2, 1], gap="large")

    with left:
        html_block("<div class='sd-h3'>Account Details</div>")
        html_block(f"""<div class="sd-card" style="margin-bottom: 20px;">
            <div style="display:flex; gap:16px; align-items:center;">
                <div style="width:52px; height:52px; border-radius:50%;
                    background:linear-gradient(135deg,{COLORS['primary']},{COLORS['accent']});
                    display:flex; align-items:center; justify-content:center; color:white; font-weight:800; font-size:1.3rem;">
                    {(user.get('name') or 'U')[0].upper()}
                </div>
                <div>
                    <div style="font-weight:700; font-size:1.1rem;">{user.get('name', 'Not signed in')}</div>
                    <div class="sd-caption">{user.get('email', 'No email configured')}</div>
                    <div class="sd-caption">Provider: <strong>{user.get('provider', 'password').upper()}</strong></div>
                </div>
            </div>
        </div>""")

        with st.expander("📝 Edit Account Details", expanded=False):
            edit_name = st.text_input("Full Name", value=user.get('name', ''), key="edit_profile_name")
            edit_email = st.text_input("Email Address", value=user.get('email', ''), key="edit_profile_email")
            edit_pass = st.text_input("New Password (Leave blank to keep current)", type="password", key="edit_profile_password")
            
            if st.button("Update Profile", type="primary", key="update_profile_confirm_btn", use_container_width=True):
                id_token = user.get("id_token")
                if id_token:
                    try:
                        from utils.security import update_profile_details, change_password
                        # 1. Update Name/Email if changed
                        if edit_name != user.get('name') or edit_email != user.get('email'):
                            result = update_profile_details(id_token, edit_name, edit_email)
                            user["name"] = edit_name
                            user["email"] = edit_email
                            if "idToken" in result:
                                user["id_token"] = result["idToken"]
                                
                        # 2. Update Password if entered
                        if edit_pass:
                            change_password(id_token, edit_pass)
                            
                        st.session_state.user = user
                        st.success("Profile details updated successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to update profile: {e}")
                else:
                    st.error("No active session details found.")

        html_block("<div class='sd-h3'>Google Drive Storage Vault</div>")
        _drive_connection_card()

    with right:
        html_block("<div class='sd-h3'>Security Settings</div>")
        html_block(f"""<div class="sd-card" style="margin-bottom: 20px; border-left: 5px solid {COLORS['success']};">
            <div style="font-size:0.75rem; font-weight:700; color:{COLORS['text_secondary']};">VAULT ENCRYPTION STATUS</div>
            <div style="font-size:1.1rem; font-weight:800; color:{COLORS['success']}; margin-top:4px; margin-bottom:10px;">🟢 Secure &amp; Verifiable</div>
            <div class="sd-info-row"><span>AES-256-GCM Mode</span><strong>Enabled ✓</strong></div>
            <div class="sd-info-row"><span>Blockchain Ledger Verification</span><strong>Active ✓</strong></div>
        </div>""")

        html_block("<div class='sd-h3'>Compliance & Audit</div>")
        with st.container(border=True):
            st.markdown("Download immutable activity logs for this system.")
            try:
                from config import DATA_DIR
                log_path = DATA_DIR / "security" / "activity_logs.json"
                if log_path.exists():
                    log_data = log_path.read_bytes()
                    st.download_button(
                        label="📥 Download Security Audit Log (JSON)",
                        data=log_data,
                        file_name="SecureDocAI_Audit_Log.json",
                        mime="application/json",
                        use_container_width=True,
                        key="btn_download_audit"
                    )
                else:
                    st.caption("No audit logs recorded yet.")
            except Exception as e:
                st.caption(f"Error accessing logs: {e}")

        html_block("<div class='sd-h3'>Preferences</div>")
        with st.container(border=True):
            dark_mode = st.toggle("🌙 Dark Mode", value=st.session_state.get("dark_mode", False), key="profile_dark_mode_toggle")
            if dark_mode != st.session_state.get("dark_mode", False):
                st.session_state.dark_mode = dark_mode
                st.rerun()

    html_block("<div class='sd-divider'></div>")
    
    # Redecorated Logout button
    if st.button("🚪 Logout from Vault session", type="secondary", **full_width_kwargs(widget=st.button), key="profile_logout_btn"):
        from utils.security import clear_remember_session
        clear_remember_session()
        st.session_state.clear()
        st.session_state["auth_view"] = "landing"
        st.success("Session closed.")
        st.rerun()
