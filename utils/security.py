"""
utils/security.py
==================
Firebase Authentication + Google OAuth (for Drive access) — V2 upgrades.
Supports email verification check, token refresh login, session remembering,
AES encrypted credentials storage, profile checks, and connection dashboards.
"""

from __future__ import annotations

import json
import os
import socket
import time
import urllib.parse
from pathlib import Path
from typing import TYPE_CHECKING

import requests
from google.oauth2.credentials import Credentials

from config import FIREBASE_CONFIG, GOOGLE_OAUTH_CLIENT_SECRETS, GOOGLE_DRIVE_SCOPES
from utils.security_engine import aes_encrypt, aes_decrypt, log_audit_event, log_security_event

import logging
logger = logging.getLogger("SecureDocAI.Security")

if TYPE_CHECKING:
    from google_auth_oauthlib.flow import InstalledAppFlow

FIREBASE_API_KEY = FIREBASE_CONFIG["apiKey"]
_IDENTITY_BASE = "https://identitytoolkit.googleapis.com/v1/accounts"
_CREDS_DIR = Path("data") / "drive_connections"
_REMEMBER_PATH = Path("data") / "remember_session.enc"


class AuthError(Exception):
    """Raised for any login/signup failure; .message is safe to show the user."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


_ERROR_MESSAGES = {
    "EMAIL_EXISTS": "An account with this email already exists. Try logging in instead.",
    "EMAIL_NOT_FOUND": "No account found with this email.",
    "INVALID_PASSWORD": "Incorrect password.",
    "INVALID_LOGIN_CREDENTIALS": "Incorrect email or password.",
    "USER_DISABLED": "This account has been disabled.",
    "WEAK_PASSWORD": "Password should be at least 6 characters.",
    "INVALID_EMAIL": "That doesn't look like a valid email address.",
    "TOO_MANY_ATTEMPTS_TRY_LATER": "Too many attempts. Please wait a bit and try again.",
    "EMAIL_NOT_VERIFIED": "Please verify your email address before logging in.",
}


def _raise_friendly(response_json: dict):
    code = response_json.get("error", {}).get("message", "UNKNOWN_ERROR")
    code = code.split(":")[0].strip()
    raise AuthError(_ERROR_MESSAGES.get(code, "Something went wrong. Please try again."))


def _check_configured():
    if not FIREBASE_API_KEY:
        raise AuthError(
            "Firebase isn't configured yet. Add FIREBASE_API_KEY and the other "
            "FIREBASE_* values to your .env file."
        )


def is_internet_available() -> bool:
    """Performs a fast socket connection check to confirm internet connectivity."""
    try:
        socket.setdefaulttimeout(3)
        host = socket.gethostbyname("one.one.one.one")
        s = socket.create_connection((host, 80), 3)
        s.close()
        return True
    except Exception:
        return False


# ============================================================
# Email / Password Auth REST APIs
# ============================================================
def create_account(name: str, email: str, password: str, role: str) -> dict:
    """Registers a new user on Firebase Auth and requests email verification."""
    _check_configured()
    if not is_internet_available():
        raise AuthError("No internet connection. Please check your network and try again.")

    signup_url = f"{_IDENTITY_BASE}:signUp?key={FIREBASE_API_KEY}"
    resp = requests.post(signup_url, json={
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }, timeout=10)
    data = resp.json()

    if "error" in data:
        _raise_friendly(data)

    id_token = data["idToken"]
    uid = data["localId"]

    # Set display name
    update_url = f"{_IDENTITY_BASE}:update?key={FIREBASE_API_KEY}"
    requests.post(update_url, json={
        "idToken": id_token,
        "displayName": name,
        "returnSecureToken": False,
    }, timeout=10)

    # Trigger Verification Email
    try:
        send_email_verification(id_token)
    except Exception:
        pass

    log_audit_event("Signup", f"Account created for {email} with role {role}")

    return {
        "name": name,
        "email": email,
        "uid": uid,
        "photo_url": None,
        "role": role,
        "provider": "password",
        "id_token": id_token,
        "refresh_token": data.get("refreshToken"),
        "email_verified": False,
    }


def verify_email_password(email: str, password: str) -> dict:
    """Logs an existing user in via Firebase Auth and checks verification status."""
    _check_configured()
    if not is_internet_available():
        raise AuthError("No internet connection. Please check your network and try again.")

    login_url = f"{_IDENTITY_BASE}:signInWithPassword?key={FIREBASE_API_KEY}"
    resp = requests.post(login_url, json={
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }, timeout=10)
    data = resp.json()

    if "error" in data:
        _raise_friendly(data)

    id_token = data["idToken"]
    user_details = get_user_details(id_token)
    email_verified = user_details.get("emailVerified", False)

    log_audit_event("Login", f"User {email} logged in (verified: {email_verified})")

    return {
        "name": data.get("displayName") or email.split("@")[0].title(),
        "email": data["email"],
        "uid": data["localId"],
        "photo_url": None,
        "provider": "password",
        "id_token": id_token,
        "refresh_token": data.get("refreshToken"),
        "email_verified": email_verified,
    }


def send_email_verification(id_token: str):
    """Requests Firebase to send a verification email link."""
    _check_configured()
    url = f"{_IDENTITY_BASE}:sendOobCode?key={FIREBASE_API_KEY}"
    resp = requests.post(url, json={
        "requestType": "VERIFY_EMAIL",
        "idToken": id_token
    }, timeout=10)
    data = resp.json()
    if "error" in data:
        _raise_friendly(data)


def send_password_reset(email: str):
    """Triggers Firebase password reset link email."""
    _check_configured()
    url = f"{_IDENTITY_BASE}:sendOobCode?key={FIREBASE_API_KEY}"
    resp = requests.post(url, json={
        "requestType": "PASSWORD_RESET",
        "email": email,
    }, timeout=10)
    data = resp.json()
    if "error" in data:
        _raise_friendly(data)


def get_user_details(id_token: str) -> dict:
    """Lookup raw user profile and emailVerified status from Firebase REST."""
    _check_configured()
    url = f"{_IDENTITY_BASE}:lookup?key={FIREBASE_API_KEY}"
    resp = requests.post(url, json={"idToken": id_token}, timeout=10)
    data = resp.json()
    if "error" in data:
        _raise_friendly(data)
    return data.get("users", [{}])[0]


def change_password(id_token: str, new_password: str):
    """Updates user password on Firebase account."""
    _check_configured()
    url = f"{_IDENTITY_BASE}:update?key={FIREBASE_API_KEY}"
    resp = requests.post(url, json={
        "idToken": id_token,
        "password": new_password,
        "returnSecureToken": True
    }, timeout=10)
    data = resp.json()
    if "error" in data:
        _raise_friendly(data)
    log_audit_event("Password Change", "User changed account password successfully")


def update_profile_details(id_token: str, new_name: str, new_email: str) -> dict:
    """Updates user display name and email on Firebase account."""
    _check_configured()
    url = f"{_IDENTITY_BASE}:update?key={FIREBASE_API_KEY}"
    payload = {
        "idToken": id_token,
        "returnSecureToken": True
    }
    if new_name:
        payload["displayName"] = new_name
    if new_email:
        payload["email"] = new_email
        
    resp = requests.post(url, json=payload, timeout=10)
    data = resp.json()
    if "error" in data:
        _raise_friendly(data)
    log_audit_event("Profile Update", f"User profile details updated (name: {new_name}, email: {new_email})")
    return data


def delete_account(id_token: str):
    """Permanently deletes the Firebase authentication account."""
    _check_configured()
    url = f"{_IDENTITY_BASE}:delete?key={FIREBASE_API_KEY}"
    resp = requests.post(url, json={"idToken": id_token}, timeout=10)
    data = resp.json()
    if "error" in data:
        _raise_friendly(data)
    log_audit_event("Account Deleted", "User deleted authentication account")


# ============================================================
# Session Refresh & Token Persistence (Remember Me)
# ============================================================
def refresh_token_login(refresh_token: str) -> dict:
    """Uses a refresh token to request fresh ID tokens from securetoken endpoint."""
    _check_configured()
    url = f"https://securetoken.googleapis.com/v1/token?key={FIREBASE_API_KEY}"
    resp = requests.post(url, data={
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }, timeout=10)
    data = resp.json()
    if "error" in data:
        raise AuthError("Session expired. Please log in again.")

    id_token = data["id_token"]
    user_details = get_user_details(id_token)
    email_verified = user_details.get("emailVerified", False)

    return {
        "name": user_details.get("displayName") or user_details.get("email", "").split("@")[0].title(),
        "email": user_details.get("email", ""),
        "uid": user_details.get("localId"),
        "photo_url": user_details.get("photoUrl"),
        "provider": "password",
        "id_token": id_token,
        "refresh_token": data.get("refresh_token") or refresh_token,
        "email_verified": email_verified,
    }


def save_remember_session(refresh_token: str):
    """Encrypts and writes the refresh token to disk to allow login bypass."""
    try:
        encrypted = aes_encrypt(refresh_token)
        _REMEMBER_PATH.parent.mkdir(parents=True, exist_ok=True)
        _REMEMBER_PATH.write_text(encrypted, encoding="utf-8")
    except Exception:
        pass


def load_remember_session() -> dict | None:
    """Reads, decrypts, and logs in the user automatically if remember session file exists."""
    if not _REMEMBER_PATH.exists():
        return None
    try:
        encrypted = _REMEMBER_PATH.read_text(encoding="utf-8")
        refresh_token = aes_decrypt(encrypted)
        return refresh_token_login(refresh_token)
    except Exception:
        clear_remember_session()
        return None


def clear_remember_session():
    """Removes the persistent auto-login token file from disk."""
    try:
        _REMEMBER_PATH.unlink(missing_ok=True)
    except Exception:
        pass


def logout_user():
    """Clears remember tokens, Streamlit session states, and resets context."""
    import streamlit as st
    email = st.session_state.get("user", {}).get("email")
    if email:
        log_audit_event("Logout", f"User {email} logged out")
        delete_persistent_drive_creds(email)
        
    clear_remember_session()
    st.session_state.clear()
    st.session_state.auto_login_attempted = True


# ============================================================
# Google OAuth & Encrypted Credentials Storage
# ============================================================
_GOOGLE_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
] + GOOGLE_DRIVE_SCOPES


def build_google_auth_flow() -> InstalledAppFlow:
    """Builds the OAuth consent flow. Raises AuthError if secrets config missing."""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        raise AuthError("google-auth-oauthlib isn't installed.")

    if not os.path.exists(GOOGLE_OAUTH_CLIENT_SECRETS):
        raise AuthError(f"OAuth client secret not found at '{GOOGLE_OAUTH_CLIENT_SECRETS}'.")

    return InstalledAppFlow.from_client_secrets_file(
        GOOGLE_OAUTH_CLIENT_SECRETS,
        scopes=_GOOGLE_SCOPES,
    )


def get_google_auth_url(page: str = "Home", prompt: str = "consent") -> tuple[str, str]:
    """Generates the Google OAuth authorization URL for Web / Streamlit redirection."""
    import uuid
    flow = build_google_auth_flow()
    flow.redirect_uri = "http://localhost:8501/"
    
    # Store page navigation target inside state param
    csrf_token = uuid.uuid4().hex[:8]
    state_param = f"{page}:{csrf_token}"
    
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt=prompt,
        include_granted_scopes="true",
        state=state_param
    )
    return auth_url, state_param


def exchange_google_code(code: str) -> tuple[dict, Credentials]:
    """Exchanges the authorization code for credentials and fetches user profile."""
    flow = build_google_auth_flow()
    flow.redirect_uri = "http://localhost:8501/"
    flow.fetch_token(code=code)
    creds = flow.credentials

    userinfo_resp = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {creds.token}"},
        timeout=10,
    )
    info = userinfo_resp.json()

    user = {
        "name": info.get("name", info.get("email", "Google User")),
        "email": info.get("email", ""),
        "uid": info.get("id", ""),
        "photo_url": info.get("picture"),
        "provider": "google",
        "email_verified": True,
    }
    return user, creds


def save_persistent_drive_creds(email: str, creds: Credentials):
    """Encrypts and persists the Google Drive credentials to disk."""
    if not email:
        return
    _CREDS_DIR.mkdir(parents=True, exist_ok=True)
    safe_email = "".join(c for c in email if c.isalnum() or c in (".", "_", "-")).lower()
    filepath = _CREDS_DIR / f"{safe_email}.enc"
    
    try:
        creds_json = creds.to_json()
        encrypted = aes_encrypt(creds_json)
        filepath.write_text(encrypted, encoding="utf-8")
        log_audit_event("Drive Connected", f"Saved encrypted Drive credentials for {email}")
    except Exception as e:
        log_security_event("Drive Credential Encryption Failure", f"Error saving credentials: {e}")


def load_persistent_drive_creds(email: str) -> Credentials | None:
    """Loads and decrypts saved Drive credentials, auto-refreshing if expired."""
    if not email:
        return None
    safe_email = "".join(c for c in email if c.isalnum() or c in (".", "_", "-")).lower()
    filepath = _CREDS_DIR / f"{safe_email}.enc"
    legacy_path = _CREDS_DIR / f"{safe_email}.json"
    
    if not filepath.exists() and not legacy_path.exists():
        return None
        
    try:
        if filepath.exists():
            encrypted_content = filepath.read_text(encoding="utf-8")
            creds_json = aes_decrypt(encrypted_content)
        else:
            creds_json = legacy_path.read_text(encoding="utf-8")
            
        creds = Credentials.from_authorized_user_info(json.loads(creds_json))
        
        # Proactively refresh token
        if creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            save_persistent_drive_creds(email, creds)
            
        return creds
    except Exception as e:
        try:
            filepath.unlink(missing_ok=True)
            legacy_path.unlink(missing_ok=True)
        except Exception:
            pass
        return None


def delete_persistent_drive_creds(email: str):
    """Deletes persistent Google Drive credentials from local disk storage."""
    if not email:
        return
    safe_email = "".join(c for c in email if c.isalnum() or c in (".", "_", "-")).lower()
    filepath = _CREDS_DIR / f"{safe_email}.enc"
    legacy_path = _CREDS_DIR / f"{safe_email}.json"
    try:
        filepath.unlink(missing_ok=True)
        legacy_path.unlink(missing_ok=True)
        log_audit_event("Drive Disconnected", f"Removed credentials files for {email}")
    except Exception:
        pass


def get_drive_status(email: str) -> dict:
    """Returns connectivity, expiry, and storage status metrics for connected Drive."""
    creds = load_persistent_drive_creds(email)
    if not creds:
        return {"connected": False, "expired": True, "storage_used": 0}
        
    return {
        "connected": True,
        "expired": creds.expired,
        "has_refresh": creds.refresh_token is not None,
    }
