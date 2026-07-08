"""
utils/privacy.py
=================
Sensitive data pattern detection, compliance validation, and privacy scoring.
Upgraded to support 15+ patterns, severity rating metadata, image redaction bounding boxes,
compliance standards (GDPR, DPDP, HIPAA), whitelist ignores, and auto-mask hooks.
"""

from __future__ import annotations

import re
import time
from typing import Any
from dataclasses import dataclass, field
from PIL import Image, ImageDraw, ImageFont

# ============================================================
# Sensitive Data Pattern Library
# ============================================================
SENSITIVE_PATTERNS = {
    "Aadhaar Number": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
    "PAN Number": re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),
    "Phone Number": re.compile(r"\b(?:\+91[\-\s]?)?[6-9]\d{9}\b"),
    "Email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "Bank Account Number": re.compile(r"\b\d{9,18}\b"),
    "IFSC Code": re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b"),
    
    # V2 Additions
    "Passport Number": re.compile(r"\b[A-Z][0-9]{7}\b"),
    "Driving License": re.compile(r"\b[A-Z]{2}-\d{13}\b|\b[A-Z]{2}\d{13}\b"),
    "Voter ID": re.compile(r"\b[A-Z]{3}[0-9]{7}\b"),
    "UPI ID": re.compile(r"\b[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}\b"),
    "Credit Card": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{16}\b"),
    "CVV": re.compile(r"\b\d{3,4}\b"),
    "Expiry Date": re.compile(r"\b(0[1-9]|1[0-2])/[0-9]{2,4}\b"),
    "GSTIN": re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}\b"),
    "Vehicle Registration": re.compile(r"\b[A-Z]{2}\s?\d{2}\s?[A-Z]{1,2}\s?\d{4}\b"),
    "Employee ID": re.compile(r"\bEMP\d{4,8}\b"),
    "Student ID": re.compile(r"\bSTUD\d{4,8}\b"),
    "Health ID (ABHA)": re.compile(r"\b\d{2}-\d{4}-\d{4}-\d{4}\b"),
}

RISK_WEIGHTS = {
    "Aadhaar Number": 35,
    "PAN Number": 30,
    "Bank Account Number": 25,
    "Credit Card": 35,
    "Passport Number": 30,
    "Driving License": 25,
    "Health ID (ABHA)": 25,
    "UPI ID": 15,
    "GSTIN": 20,
    "Voter ID": 20,
    "IFSC Code": 10,
    "Phone Number": 10,
    "Email": 5,
    "CVV": 25,
    "Expiry Date": 10,
    "Vehicle Registration": 10,
    "Employee ID": 5,
    "Student ID": 5,
}

CRITICAL_TYPES = {"Aadhaar Number", "PAN Number", "Bank Account Number", "Credit Card", "Passport Number"}
WARNING_TYPES = {"IFSC Code", "Phone Number", "UPI ID", "Driving License", "Voter ID", "GSTIN"}


def get_enabled_patterns() -> set[str]:
    """Queries Streamlit session state keys to return the set of enabled PII filters."""
    try:
        import streamlit as st
        if st.runtime.exists():
            enabled = set()
            if st.session_state.get("comp_aadhaar", True):
                enabled.add("Aadhaar Number")
            if st.session_state.get("comp_pan", True):
                enabled.add("PAN Number")
            if st.session_state.get("comp_bank", True):
                enabled.add("Bank Account Number")
                enabled.add("IFSC Code")
                enabled.add("UPI ID")
            if st.session_state.get("comp_contact", True):
                enabled.add("Phone Number")
                enabled.add("Email")
            if st.session_state.get("comp_id", True):
                enabled.add("Passport Number")
                enabled.add("Driving License")
                enabled.add("Voter ID")
                enabled.add("Health ID (ABHA)")
                enabled.add("Employee ID")
                enabled.add("Student ID")
            # Always enable CC, CVV, Exp, GST, Vehicle
            enabled.update(["Credit Card", "CVV", "Expiry Date", "GSTIN", "Vehicle Registration"])
            return enabled
    except Exception:
        pass
    return set(SENSITIVE_PATTERNS.keys())


def detect_sensitive_data(text: str) -> dict:
    """Returns {pattern_name: [matched_strings]} for every match found, matching active filters."""
    findings = {}
    enabled = get_enabled_patterns()
    for name, pattern in SENSITIVE_PATTERNS.items():
        if name not in enabled:
            continue
        matches = pattern.findall(text)
        if matches:
            findings[name] = matches
    return findings


def scan_pii_details(text: str, ignore_whitelist: list[str] | None = None) -> list[dict]:
    """Scans and returns structured severity dictionary objects for each sensitive match."""
    findings = detect_sensitive_data(text)
    details = []
    whitelist = ignore_whitelist or []
    
    unique_matches = {} # deduplicate values
    
    for name, matches in findings.items():
        for match in matches:
            if match in whitelist:
                continue
                
            if match in unique_matches:
                unique_matches[match]["occurrences"] += 1
                continue
                
            severity = "Critical" if name in CRITICAL_TYPES else "Warning"
            risk = RISK_WEIGHTS.get(name, 5)
            
            unique_matches[match] = {
                "type": name,
                "value": match,
                "risk": risk,
                "severity": severity,
                "confidence": 0.95,
                "occurrences": 1
            }
            
    return list(unique_matches.values())


def redact_value(value: str, visible_suffix: int = 4, mask_char: str = "X", mask_level: str = "partial") -> str:
    """Masks input values based on visible suffix and mask level (full, partial)."""
    if mask_level == "full":
        return mask_char * len(value)
        
    chars = list(value)
    non_space_indices = [i for i, c in enumerate(chars) if c != " "]
    keep_from = max(0, len(non_space_indices) - visible_suffix)
    keep_set = set(non_space_indices[keep_from:])
    for i in non_space_indices:
        if i not in keep_set:
            chars[i] = mask_char
    return "".join(chars)


def auto_redact(text: str, mask_level: str = "partial") -> tuple[str, dict]:
    """Finds all sensitive matches and replaces them in-place with redacted versions."""
    findings = detect_sensitive_data(text)
    redacted_text = text
    for name, matches in findings.items():
        for match in set(matches):
            redacted_text = redacted_text.replace(match, redact_value(match, mask_level=mask_level))
    return redacted_text, findings


def compliance_scan(findings: dict) -> tuple[str, list]:
    """Returns (status, reasons) compliance validation check."""
    found_types = set(findings.keys())
    if found_types & CRITICAL_TYPES:
        status = "Critical"
    elif found_types & WARNING_TYPES:
        status = "Warning"
    elif found_types:
        status = "Warning"
    else:
        status = "Safe"

    reasons = [
        f"{name} detected ({len(matches)} instance(s))"
        for name, matches in findings.items()
    ]
    return status, reasons


def compute_privacy_score(text: str, is_encrypted: bool = False) -> tuple[int, dict]:
    findings = detect_sensitive_data(text)
    exposure_penalty = sum(RISK_WEIGHTS.get(name, 5) for name in findings)
    score = max(0, 100 - exposure_penalty)

    if is_encrypted and findings:
        score = min(100, score + 20)

    return score, findings


def generate_recommendations(findings: dict, is_encrypted: bool, score: int) -> list:
    recs = []
    if "Aadhaar Number" in findings:
        recs.append("Remove or mask Aadhaar number before sharing this document")
    if "PAN Number" in findings:
        recs.append("Remove or mask PAN number before sharing this document")
    if "Credit Card" in findings or "Bank Account Number" in findings:
        recs.append("Restrict download/export access; verify financial data is necessary")
    if findings and not is_encrypted:
        recs.append("Encrypt this document using Password Protection or AES-256")
    if score < 60:
        recs.append("High privacy risk: enforce role-based access control (RBAC)")
        
    if not recs:
        recs.append("No sensitive data detected — no special action needed")
    return recs


# ============================================================
# Hook Integration for OCR security pipeline
# ============================================================
def scan_and_mask_document(doc) -> Any:
    """Scans and masks sensitive data in-place inside the LayoutDocument blocks."""
    for block in doc.blocks:
        for line in block.lines:
            if line.text:
                redacted, _ = auto_redact(line.text)
                line.text = redacted
    return doc


def redact_image(image: Image.Image, doc, findings: list[dict]) -> Image.Image:
    """Draws solid black rectangles over original image coordinate regions where PII matches."""
    img = image.copy()
    draw = ImageDraw.Draw(img)
    
    words = getattr(doc, "word_metadata", [])
    for finding in findings:
        val = finding["value"]
        val_clean = val.replace(" ", "").lower()
        for word in words:
            w_text = word.get("text", "").replace(" ", "").lower()
            if w_text and (w_text in val_clean or val_clean in w_text):
                bbox = word.get("bbox")
                if bbox:
                    x, y, w, h = bbox
                    # Black-out target rectangle on image
                    draw.rectangle([x, y, x + w, y + h], fill="black")
    return img
