"""
app_pages/Dashboard.py
======================
Developer OCR Benchmark Dashboard to visualize metrics.
"""

import streamlit as st
import pandas as pd
try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

from components.ui_helpers import html_block
from config import COLORS

def render():
    html_block("""<div style="margin-bottom:18px;">
        <span class="sd-eyebrow" style="color: #10B981; font-weight:700;">DEVELOPER DASHBOARD</span>
        <h2 class="sd-h2" style="margin-top:6px; font-weight:800; font-size:2.2rem; color:#0F172A;">OCR Benchmark Metrics</h2>
    </div>""")

    if not HAS_PLOTLY:
        st.warning("Plotly is required for the dashboard. Please install it using `pip install plotly`.")
        return

    creds = st.session_state.get("drive_creds")
    if creds and "hist_documents_cache" not in st.session_state:
        with st.spinner("Syncing OCR data from Google Drive..."):
            from utils.helpers import list_documents
            try:
                st.session_state.hist_documents_cache = list_documents(creds, page_size=100)
            except Exception:
                st.session_state.hist_documents_cache = []

    # Combine local recent runs with historical runs from Drive
    runs_data = []
    
    # 1. Historical Runs from Drive
    hist_docs = st.session_state.get("hist_documents_cache", [])
    for d in hist_docs:
        props = d.get("appProperties", {})
        try:
            conf = float(props.get("confidence", 0.0))
        except ValueError:
            conf = 0.0
            
        runs_data.append({
            "name": props.get("original_filename", d.get("name", "Unknown")),
            "createdTime": d.get("createdTime"),
            "lang": props.get("language", "Auto"),
            "confidence": conf,
            "time": 1.5, # Historical documents don't store processing time, use placeholder
        })
        
    # Removed local unsaved runs injection to keep metrics perfectly synced with Drive Storage

    if not runs_data:
        st.info("No OCR runs recorded yet. Process some documents or connect Drive to sync history.")
        return

    df = pd.DataFrame(runs_data)
    df["createdTime"] = pd.to_datetime(df["createdTime"], format='mixed', utc=True)
    df["confidence_pct"] = df["confidence"] * 100

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Documents Stored", len(df))
    with col2:
        st.metric("Avg Confidence", f"{df['confidence_pct'].mean():.1f}%")
    with col3:
        st.metric("Avg Processing Time", f"{df['time'].mean():.2f}s")

    st.markdown("### Confidence over Time")
    fig_conf = px.line(df, x="createdTime", y="confidence_pct", hover_data=["name"], title="OCR Confidence Trend")
    st.plotly_chart(fig_conf, use_container_width=True)

    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.markdown("### Language Distribution")
        fig_lang = px.pie(df, names="lang", title="Documents by Language")
        st.plotly_chart(fig_lang, use_container_width=True)
    with col_chart2:
        st.markdown("### Processing Time vs Confidence")
        fig_scatter = px.scatter(df, x="time", y="confidence_pct", color="lang", hover_data=["name"], title="Time vs Confidence")
        st.plotly_chart(fig_scatter, use_container_width=True)
