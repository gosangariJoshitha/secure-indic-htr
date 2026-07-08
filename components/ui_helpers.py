"""
components/ui_helpers.py
==========================
Shared rendering helpers and reusable UI component toolkit.
Provides UI presentation layout helpers to display cards, badges, progress,
and status elements, keeping logic separated from the presentation layer.
"""

from __future__ import annotations

import re
import inspect
from typing import Any
import streamlit as st
from PIL import Image

# ------------------------------------------------------------------
# HTML & CSS Helper Methods
# ------------------------------------------------------------------
def html_block(content: str):
    """
    Render an HTML string safely. Collapses multi-line/indented HTML into
    a single line (no leading whitespace) before calling st.markdown, which
    avoids the rendered-as-literal-text parser bug.
    """
    flattened = re.sub(r"\s+", " ", content).strip()
    st.markdown(flattened, unsafe_allow_html=True)


def css_block(css: str):
    """Injects custom CSS stylesheets into the DOM."""
    html_block(f"<style>{css}</style>")


def inject_custom_css():
    """Injects global theme variables, glassmorphism containers, and typography overrides."""
    css_block("""
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
        }
        
        .premium-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 15px;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .premium-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
            border-color: rgba(255, 255, 255, 0.2);
        }
        
        .status-badge {
            display: inline-flex;
            align-items: center;
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 0.85rem;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .badge-success { background-color: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }
        .badge-warning { background-color: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); }
        .badge-danger { background-color: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); }
        .badge-info { background-color: rgba(59, 130, 246, 0.15); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.3); }
        .badge-neutral { background-color: rgba(107, 114, 128, 0.15); color: #9ca3af; border: 1px solid rgba(107, 114, 128, 0.3); }
    """)


# ------------------------------------------------------------------
# Version-agnostic width handling
# ------------------------------------------------------------------
_WIDTH_CACHE = {}

def _supports_width_kwarg(func) -> bool:
    key = getattr(func, "__qualname__", str(func))
    if key in _WIDTH_CACHE:
        return _WIDTH_CACHE[key]
    try:
        sig = inspect.signature(func)
        supported = "width" in sig.parameters
    except (TypeError, ValueError):
        supported = False
    _WIDTH_CACHE[key] = supported
    return supported


def full_width_kwargs(stretch: bool = True, widget=None) -> dict:
    target = widget if widget is not None else st.button
    if target is st.image:
        return {"use_container_width": stretch}

    if _supports_width_kwarg(target):
        return {"width": "stretch" if stretch else "content"}
    try:
        sig = inspect.signature(target)
        if "use_container_width" in sig.parameters:
            return {"use_container_width": stretch}
    except (TypeError, ValueError):
        pass
    return {}


# ------------------------------------------------------------------
# Page Layout & Header/Footer Helpers
# ------------------------------------------------------------------
def page_header(title: str, subtitle: str = ""):
    """Renders a clean premium page title and descriptor header."""
    html_block(f"""
        <div style='margin-bottom: 25px;'>
            <h1 style='font-size: 2.3rem; font-weight: 700; margin-bottom: 5px; color: #ffffff;'>
                {title}
            </h1>
            {f"<p style='font-size: 1.1rem; color: #a1a1aa; margin-top: 0;'>{subtitle}</p>" if subtitle else ""}
            <hr style='border: 0; height: 1px; background: linear-gradient(to right, rgba(255,255,255,0.1), rgba(255,255,255,0.01)); margin-top: 15px;' />
        </div>
    """)


def section_header(title: str):
    """Renders a clean sections division header."""
    html_block(f"""
        <div style='margin-top: 30px; margin-bottom: 15px;'>
            <h3 style='font-size: 1.4rem; font-weight: 600; color: #f4f4f5;'>
                {title}
            </h3>
        </div>
    """)


def page_footer():
    """Renders the trademark branding footer at the bottom of pages."""
    html_block("""
        <div style='margin-top: 80px; text-align: center; padding: 20px 0; border-top: 1px solid rgba(255,255,255,0.05);'>
            <p style='font-size: 0.85rem; color: #71717a;'>
                SecureDocAI V2 • Engineered for Intelligent Document Protection
            </p>
        </div>
    """)


# ------------------------------------------------------------------
# Reusable Status Cards
# ------------------------------------------------------------------
def success_card(message: str):
    html_block(f"""
        <div class="premium-card" style="border-left: 4px solid #10b981;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.3rem;">✅</span>
                <span style="font-weight: 500; color: #e4e4e7;">{message}</span>
            </div>
        </div>
    """)


def warning_card(message: str):
    html_block(f"""
        <div class="premium-card" style="border-left: 4px solid #f59e0b;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.3rem;">⚠️</span>
                <span style="font-weight: 500; color: #e4e4e7;">{message}</span>
            </div>
        </div>
    """)


def error_card(message: str):
    html_block(f"""
        <div class="premium-card" style="border-left: 4px solid #ef4444;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.3rem;">🚨</span>
                <span style="font-weight: 500; color: #e4e4e7;">{message}</span>
            </div>
        </div>
    """)


def info_card(message: str):
    html_block(f"""
        <div class="premium-card" style="border-left: 4px solid #3b82f6;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.3rem;">ℹ️</span>
                <span style="font-weight: 500; color: #e4e4e7;">{message}</span>
            </div>
        </div>
    """)


# ------------------------------------------------------------------
# Metric & Statistics Cards
# ------------------------------------------------------------------
def metric_card(label: str, value: str, subtext: str = ""):
    """Renders a single metric box in columns."""
    html_block(f"""
        <div class="premium-card" style="text-align: center;">
            <div style="font-size: 0.9rem; color: #a1a1aa; text-transform: uppercase; letter-spacing: 0.05em;">{label}</div>
            <div style="font-size: 2.2rem; font-weight: 700; margin: 10px 0; color: #ffffff;">{value}</div>
            {f"<div style='font-size: 0.8rem; color: #71717a;'>{subtext}</div>" if subtext else ""}
        </div>
    """)


def statistics_card(stats: dict[str, Any]):
    """Renders a metadata grid container card."""
    items = "".join(
        f"<div style='display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.05);'>"
        f"<span style='color: #a1a1aa;'>{k}</span>"
        f"<span style='font-weight: 600; color: #ffffff;'>{v}</span>"
        f"</div>"
        for k, v in stats.items()
    )
    html_block(f"""
        <div class="premium-card">
            <h4 style="margin-top: 0; margin-bottom: 15px; color: #f4f4f5;">Document Analytics</h4>
            {items}
        </div>
    """)


# ------------------------------------------------------------------
# Badge Rendering Helpers
# ------------------------------------------------------------------
def confidence_badge(conf: float) -> str:
    pct = conf * 100
    if pct >= 85:
        return f'<span class="status-badge badge-success">🟢 {pct:.1f}%</span>'
    elif pct >= 60:
        return f'<span class="status-badge badge-warning">🟡 {pct:.1f}%</span>'
    return f'<span class="status-badge badge-danger">🔴 {pct:.1f}%</span>'


def language_badge(lang: str) -> str:
    return f'<span class="status-badge badge-info">🌐 {lang}</span>'


def engine_badge(engine: str) -> str:
    return f'<span class="status-badge badge-neutral">⚙️ {engine}</span>'


def security_badge(status: str) -> str:
    if status == "Verified" or status == "Encrypted":
        return f'<span class="status-badge badge-success">🔒 {status}</span>'
    elif status == "Warning":
        return f'<span class="status-badge badge-warning">⚠️ {status}</span>'
    return f'<span class="status-badge badge-danger">🚨 {status}</span>'


def privacy_badge(level: str) -> str:
    if level == "Safe":
        return f'<span class="status-badge badge-success">🛡️ {level}</span>'
    elif level == "Warning":
        return f'<span class="status-badge badge-warning">⚠️ {level}</span>'
    return f'<span class="status-badge badge-danger">🚨 {level}</span>'


# ------------------------------------------------------------------
# Image Previews & Comparisons
# ------------------------------------------------------------------
def image_preview(image: Image.Image, caption: str = ""):
    st.image(image, **full_width_kwargs(widget=st.image))
    if caption:
        st.caption(caption)


def before_after_view(image_orig: Image.Image, image_mask: Image.Image):
    """Renders side-by-side tabs containing the original and masked outputs."""
    t1, t2 = st.tabs(["Original Source", "Masked Security Output"])
    with t1:
        st.image(image_orig, **full_width_kwargs(widget=st.image))
    with t2:
        st.image(image_mask, **full_width_kwargs(widget=st.image))


# ------------------------------------------------------------------
# Security Dashboard & Blockchain UI elements
# ------------------------------------------------------------------
def security_score_card(score: float, grade: str, hash_val: str, sig_val: str):
    """Renders cryptographic verification markers."""
    html_block(f"""
        <div class="premium-card">
            <h4 style="margin-top: 0; color: #f4f4f5;">Cryptographic Signature Report</h4>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 15px 0;">
                <div style="text-align: center; background: rgba(255,255,255,0.02); padding: 10px; border-radius: 8px;">
                    <div style="color: #a1a1aa; font-size: 0.8rem;">INTEGRITY SCORE</div>
                    <div style="font-size: 1.8rem; font-weight: 700; color: #10b981;">{score:.1f}%</div>
                </div>
                <div style="text-align: center; background: rgba(255,255,255,0.02); padding: 10px; border-radius: 8px;">
                    <div style="color: #a1a1aa; font-size: 0.8rem;">SECURITY GRADE</div>
                    <div style="font-size: 1.8rem; font-weight: 700; color: #3b82f6;">{grade}</div>
                </div>
            </div>
            <div style="font-size: 0.85rem; color: #a1a1aa; line-height: 1.4;">
                <div style="margin-bottom: 8px;">
                    <strong>Block Hash (SHA-256):</strong><br/>
                    <code style="word-break: break-all; color: #a5f3fc;">{hash_val}</code>
                </div>
                <div>
                    <strong>RSA-2048 Digital Signature:</strong><br/>
                    <code style="word-break: break-all; color: #a7f3d0;">{sig_val[:40]}...</code>
                </div>
            </div>
        </div>
    """)


# ------------------------------------------------------------------
# Empty States
# ------------------------------------------------------------------
def empty_document():
    html_block("""
        <div class="premium-card" style="text-align: center; padding: 40px 20px;">
            <div style="font-size: 3rem; margin-bottom: 15px;">📥</div>
            <h4 style="color: #ffffff; margin-top: 0;">No active document loaded</h4>
            <p style="color: #71717a; max-width: 320px; margin: 0 auto;">
                Please upload an image or PDF file in the scan center dropzone to get started.
            </p>
        </div>
    """)


def empty_history():
    html_block("""
        <div class="premium-card" style="text-align: center; padding: 40px 20px;">
            <div style="font-size: 3rem; margin-bottom: 15px;">📂</div>
            <h4 style="color: #ffffff; margin-top: 0;">Your Library is Empty</h4>
            <p style="color: #71717a; max-width: 320px; margin: 0 auto;">
                Documents you scan and save to your vault will be recorded securely here.
            </p>
        </div>
    """)


def no_results_found():
    html_block("""
        <div class="premium-card" style="text-align: center; padding: 30px 20px;">
            <div style="font-size: 2.5rem; margin-bottom: 10px;">🔍</div>
            <h5 style="color: #ffffff; margin-top: 0; margin-bottom: 5px;">No matches found</h5>
            <p style="color: #71717a; margin: 0;">Try adjusting your query keywords or search toggles.</p>
        </div>
    """)
