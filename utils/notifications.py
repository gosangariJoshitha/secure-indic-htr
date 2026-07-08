"""
utils/notifications.py
========================
In-session notification system with Toast triggers, auto-dismiss logs,
kind-specific wrappers, and special hooks for tracking OCR, exports,
Google Drive uploads, security scanning, and privacy warnings.
"""

from __future__ import annotations

import time
import streamlit as st

_SESSION_KEY = "_notifications"
MAX_NOTIFICATIONS = 25


def _ensure_list() -> list[dict]:
    if _SESSION_KEY not in st.session_state:
        st.session_state[_SESSION_KEY] = []
    return st.session_state[_SESSION_KEY]


def push_notification(message: str, kind: str = "info", system: bool = True):
    """
    kind: 'info' | 'success' | 'warning' | 'error' — controls the icon
    shown in the dropdown.
    """
    notifications = _ensure_list()
    item = {
        "message": message,
        "kind": kind,
        "timestamp": time.time(),
        "read": False,
        "system": system
    }
    notifications.insert(0, item)
    del notifications[MAX_NOTIFICATIONS:]

    # Trigger native Streamlit toast notifications in the UI if in active context
    try:
        if st.runtime.exists():
            if kind == "success":
                st.toast(message, icon="✅")
            elif kind == "error":
                st.toast(message, icon="🚨")
            elif kind == "warning":
                st.toast(message, icon="⚠️")
            else:
                st.toast(message, icon="ℹ️")
    except Exception:
        pass


# ============================================================
# Success / Error / Warning / Info wrappers
# ============================================================
def notify_success(message: str):
    push_notification(message, "success")


def notify_error(message: str):
    push_notification(message, "error")


def notify_warning(message: str):
    push_notification(message, "warning")


def notify_info(message: str):
    push_notification(message, "info")


# ============================================================
# Specialized OCR / Export / Security Helpers
# ============================================================
def notify_ocr_complete(filename: str, duration: float, char_count: int):
    message = f"OCR completed successfully for '{filename}' in {duration:.2f}s ({char_count} characters recognized)."
    notify_success(message)


def notify_export_success(filename: str, format_type: str):
    message = f"Document successfully exported to {format_type.upper()} format as '{filename}'."
    notify_success(message)


def notify_drive_upload(filename: str, email: str):
    message = f"Successfully uploaded '{filename}' to Google Drive for {email}."
    notify_success(message)


def notify_security_scan(score: float, grade: str):
    message = f"Security Scan completed: Integrity Score: {score:.1f} ({grade})."
    if score < 70:
        notify_warning(message)
    else:
        notify_success(message)


def notify_privacy_warning(findings_count: int):
    if findings_count > 0:
        message = f"Privacy check flagged {findings_count} sensitive PII instances in the document."
        notify_warning(message)
    else:
        notify_info("Privacy check complete: no sensitive PII instances detected.")


# ============================================================
# History and Utility operations
# ============================================================
def get_notifications() -> list[dict]:
    return _ensure_list()


def unread_count() -> int:
    return sum(1 for n in _ensure_list() if not n["read"])


def mark_all_read():
    for n in _ensure_list():
        n["read"] = True


def format_relative_time(ts: float) -> str:
    delta = time.time() - ts
    if delta < 60:
        return "just now"
    if delta < 3600:
        return f"{int(delta // 60)}m ago"
    if delta < 86400:
        return f"{int(delta // 3600)}h ago"
    return f"{int(delta // 86400)}d ago"
