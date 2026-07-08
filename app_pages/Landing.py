"""
app_pages/Landing.py
=====================
Premium SaaS landing page for SecureDocAI.
"""

import streamlit as st
import time
from components.ui_helpers import html_block, full_width_kwargs
from config import COLORS, APP_NAME, APP_VERSION, BUILD_DATE, ASSETS_DIR

def _go(view: str):
    st.session_state.auth_view = view
    st.rerun()

def render():
    html_block(f"""
    <link href="https://fonts.googleapis.com/css2?family=Kalam:wght@400;700&family=Lakki+Reddy&display=swap" rel="stylesheet">
    <style>
        html {{
            scroll-behavior: smooth;
        }}
        .sticky-navbar {{
            position: sticky;
            top: 0;
            background: rgba(248, 250, 252, 0.85);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid #E2E8F0;
            z-index: 999;
            padding: 10px 0;
            margin-bottom: 24px;
        }}
        .nav-links {{
            display: flex;
            gap: 20px;
            align-items: center;
        }}
        .nav-links a {{
            color: #64748B;
            text-decoration: none;
            font-size: 0.9rem;
            font-weight: 600;
            transition: color 0.2s ease;
        }}
        .nav-links a:hover {{
            color: #2563EB;
        }}
        .hover-card {{
            transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.3s ease;
        }}
        .hover-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 12px 20px rgba(15, 23, 42, 0.08);
        }}
        .timeline-container {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            margin-top: 24px;
        }}
        .timeline-arrow {{
            font-size: 1.5rem;
            color: #94A3B8;
            align-self: center;
        }}
        .footer-col h5 {{
            color: #0F172A;
            font-size: 0.95rem;
            font-weight: 700;
            margin-bottom: 12px;
        }}
        .footer-col ul {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        .footer-col ul li {{
            margin-bottom: 8px;
        }}
        .footer-col ul li a {{
            color: #64748B;
            text-decoration: none;
            font-size: 0.85rem;
            transition: color 0.15s ease;
        }}
        .footer-col ul li a:hover {{
            color: #2563EB;
        }}
        @media (max-width: 768px) {{
            .timeline-container {{
                flex-direction: column;
            }}
            .timeline-arrow {{
                transform: rotate(90deg);
                margin: 8px 0;
            }}
        }}
    </style>
    """)

    _render_navbar()
    _render_hero()
    _render_ocr_demo()
    _render_security_section()
    _render_features()
    _render_how_it_works()
    _render_faq()
    _render_cta()
    _render_footer()


def _render_navbar():
    col_brand, col_links, col_actions = st.columns([1.5, 2.5, 1.6])
    
    with col_brand:
        html_block(f"""
        <div style="display:flex; align-items:center; gap:10px; padding-top:6px;">
            <div style="width:34px; height:34px; border-radius:10px;
                background: linear-gradient(135deg, {COLORS['primary']}, {COLORS['accent']});
                display:flex; align-items:center; justify-content:center; color:white; font-weight:800; font-size:1.1rem;">S</div>
            <span style="font-weight:900; font-size:1.25rem; letter-spacing:-0.03em; color:#0F172A;">{APP_NAME}</span>
        </div>
        """)
        
    with col_links:
        html_block(f"""
        <div class="nav-links" style="padding-top:12px; justify-content:center;">
            <a href="#why-securedocai">Security</a>
            <a href="#features">Features</a>
            <a href="#timeline">Workflow</a>
            <a href="#faq">FAQ</a>
        </div>
        """)
        
    with col_actions:
        b1, b2 = st.columns([1, 1.2])
        with b1:
            if st.button("Sign In", **full_width_kwargs(widget=st.button), key="nav_signin"):
                _go("login")
        with b2:
            if st.button("Get Started", type="primary", **full_width_kwargs(widget=st.button), key="nav_getstarted"):
                _go("signup")
                
    html_block("<div class='sd-divider' style='margin-top:12px; margin-bottom:32px;'></div>")


def _render_hero():
    left, right = st.columns([1.1, 1], gap="large")
    with left:
        html_block(f"""
        <div style="padding-top:10px;">
            <div style="display:inline-flex; align-items:center; gap:6px; background:#EFF6FF; border:1px solid #BFDBFE; border-radius:30px; padding:4px 12px; margin-bottom:16px;">
                <span style="width:6px; height:6px; border-radius:50%; background:#2563EB;"></span>
                <span style="font-size:0.75rem; font-weight:700; color:#1E40AF;">Telugu · Hindi · English Support</span>
            </div>
            <h1 class="sd-h1" style="font-size:2.8rem; font-weight:850; line-height:1.15; letter-spacing:-0.03em; margin-bottom:18px;">
                Your handwriting,<br/>
                <span style="background:linear-gradient(to right, {COLORS['primary']}, {COLORS['accent']}); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">securely digitized.</span>
            </h1>
            <p class="sd-body" style="font-size:1.05rem; line-height:1.6; color:{COLORS['text_secondary']}; max-width:480px; margin-bottom:28px;">
                Scan or upload handwritten pages. SecureDocAI reconstructs the layout structure (paragraphs, tables, bullet points) dynamically, detects PII compliance fields, and uploads encrypted files straight to your own Google Drive.
            </p>
        </div>
        """)
        
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button("🚀 Start Free Vault", type="primary", **full_width_kwargs(widget=st.button), key="hero_start_vault"):
                _go("signup")
        with btn_col2:
            if st.button("🚪 Sign In to Account", **full_width_kwargs(widget=st.button), key="hero_signin_btn"):
                _go("login")

        # Hero Statistics (6 Points)
        html_block("<div style='height:36px;'></div>")
        st.markdown("<div style='font-size:0.7rem; font-weight:700; color:#94A3B8; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:12px;'>PERFORMANCE & SECURITY RATINGS</div>", unsafe_allow_html=True)
        
        s_col1, s_col2, s_col3 = st.columns(3)
        with s_col1:
            st.markdown("<div class='sd-stat-value' style='font-size:1.6rem; color:#2563EB;'>Zero-Trust</div><div class='sd-stat-label' style='font-size:0.75rem;'>Privacy Model</div>", unsafe_allow_html=True)
            st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
            st.markdown("<div class='sd-stat-value' style='font-size:1.6rem; color:#2563EB;'>AES-256</div><div class='sd-stat-label' style='font-size:0.75rem;'>E2E Encryption</div>", unsafe_allow_html=True)
        with s_col2:
            st.markdown("<div class='sd-stat-value' style='font-size:1.6rem; color:#2563EB;'>95.9%</div><div class='sd-stat-label' style='font-size:0.75rem;'>OCR Accuracy</div>", unsafe_allow_html=True)
            st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
            st.markdown("<div class='sd-stat-value' style='font-size:1.6rem; color:#2563EB;'>Active</div><div class='sd-stat-label' style='font-size:0.75rem;'>PII Auto-Redaction</div>", unsafe_allow_html=True)
        with s_col3:
            st.markdown("<div class='sd-stat-value' style='font-size:1.6rem; color:#2563EB;'>3</div><div class='sd-stat-label' style='font-size:0.75rem;'>Languages</div>", unsafe_allow_html=True)
            st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
            st.markdown("<div class='sd-stat-value' style='font-size:1.6rem; color:#2563EB;'>Preserved</div><div class='sd-stat-label' style='font-size:0.75rem;'>Document Layouts</div>", unsafe_allow_html=True)

    with right:
        # Load the generated premium illustration
        illustration_path = ASSETS_DIR / "hero_illustration.png"
        if illustration_path.exists():
            st.image(str(illustration_path), use_column_width=True)
        else:
            html_block(f"""
            <div class="sd-card" style="padding:48px; text-align:center; background:{COLORS['hover']}; border: 1px dashed {COLORS['border']};">
                <div style="font-size:3rem; margin-bottom:12px;">✍️</div>
                <div style="font-weight:700; font-size:1.2rem;">Premium Layout Segmentation Engine</div>
                <div class="sd-body" style="font-size:0.85rem; margin-top:6px;">OCR pipeline active and ready. Sign up to build your secure database.</div>
            </div>
            """)

    html_block("<div class='sd-divider' style='margin-top:40px; margin-bottom:40px;'></div>")


def _render_ocr_demo():
    html_block("<div id='demo'></div>")
    html_block("""
    <div style="text-align:center; margin-bottom:28px;">
        <span class="sd-eyebrow">INTERACTIVE DEMO</span>
        <h2 class="sd-h2" style="margin-top:6px;">See the hybrid OCR manager in action</h2>
        <p class="sd-body" style="max-width:560px; margin: 8px auto 0 auto;">Select a sample script image below to simulate how the model segments character glyphs and reconstructs text layout.</p>
    </div>
    """)
    
    demo_left, demo_right = st.columns([1, 1.2], gap="medium")
    with demo_left:
        sample_choice = st.selectbox(
            "Select Sample Script Document",
            ["Telugu Handwritten", "Telugu Printed", "Hindi Handwritten", "Hindi Printed"],
            key="demo_sample_selector"
        )
        
        if sample_choice == "Telugu Handwritten":
            html_block(f"""
            <div class="sd-card" style="padding:16px; text-align:center; background:#F8FAFC;">
                <div style="font-size:0.7rem; font-weight:700; color:{COLORS['text_secondary']}; margin-bottom:8px; text-align:left;">SAMPLE IMAGE INPUT</div>
                <div style="background:white; border:1px solid {COLORS['border']}; border-radius:8px; padding:16px 12px; display:flex; align-items:center; justify-content:center;">
                    <div style="font-size:2.2rem; font-family:'Lakki Reddy', cursive; color:#1E1B4B; line-height:1.2;">రాముడు మంచి బాలుడు</div>
                </div>
            </div>
            """)
            extracted_text = "రాముడు మంచి బాలుడు"
            conf = 98.4
            detected_lang = "Telugu"
        elif sample_choice == "Telugu Printed":
            html_block(f"""
            <div class="sd-card" style="padding:16px; text-align:center; background:#F8FAFC;">
                <div style="font-size:0.7rem; font-weight:700; color:{COLORS['text_secondary']}; margin-bottom:8px; text-align:left;">SAMPLE IMAGE INPUT</div>
                <div style="background:white; border:1px solid {COLORS['border']}; border-radius:8px; padding:24px 12px; display:flex; align-items:center; justify-content:center;">
                    <div style="font-size:1.6rem; font-weight:700; font-family:'Inter', sans-serif; color:#111827; letter-spacing:0.03em;">తెలుగు వికీపీడియా</div>
                </div>
            </div>
            """)
            extracted_text = "తెలుగు వికీపీడియా"
            conf = 99.5
            detected_lang = "Telugu"
        elif sample_choice == "Hindi Handwritten":
            html_block(f"""
            <div class="sd-card" style="padding:16px; text-align:center; background:#F8FAFC;">
                <div style="font-size:0.7rem; font-weight:700; color:{COLORS['text_secondary']}; margin-bottom:8px; text-align:left;">SAMPLE IMAGE INPUT</div>
                <div style="background:white; border:1px solid {COLORS['border']}; border-radius:8px; padding:16px 12px; display:flex; align-items:center; justify-content:center;">
                    <div style="font-size:2.2rem; font-family:'Kalam', cursive; font-weight:700; color:#1E1B4B; line-height:1.2;">मेरा भारत महान</div>
                </div>
            </div>
            """)
            extracted_text = "मेरा भारत महान"
            conf = 97.9
            detected_lang = "Hindi"
        else:
            html_block(f"""
            <div class="sd-card" style="padding:16px; text-align:center; background:#F8FAFC;">
                <div style="font-size:0.7rem; font-weight:700; color:{COLORS['text_secondary']}; margin-bottom:8px; text-align:left;">SAMPLE IMAGE INPUT</div>
                <div style="background:white; border:1px solid {COLORS['border']}; border-radius:8px; padding:24px 12px; display:flex; align-items:center; justify-content:center;">
                    <div style="font-size:1.6rem; font-weight:700; font-family:'Inter', sans-serif; color:#111827; letter-spacing:0.02em;">नई दिल्ली, भारत</div>
                </div>
            </div>
            """)
            extracted_text = "नई दिल्ली, भारत"
            conf = 99.1
            detected_lang = "Hindi"

        if st.button("⚡ Run Extraction Simulation", type="primary", use_container_width=True, key="btn_run_simulation"):
            status_placeholder = st.empty()
            with status_placeholder:
                with st.spinner("Analyzing document layout..."):
                    time.sleep(0.5)
                with st.spinner("Segmenting text character contours..."):
                    time.sleep(0.5)
                with st.spinner("Finished character decoding!"):
                    time.sleep(0.3)
            status_placeholder.empty()
            st.session_state.demo_extracted = True
        else:
            if "demo_extracted" not in st.session_state:
                st.session_state.demo_extracted = False

    with demo_right:
        if st.session_state.demo_extracted:
            html_block(f"""
            <div class="sd-card" style="border-left: 5px solid {COLORS['success']}; padding: 20px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <span class="sd-pill sd-pill-success">✓ Processing Finished</span>
                    <span class="sd-caption">Confidence: <strong>{conf}%</strong></span>
                </div>
                <div class="sd-info-row"><span>Detected Language</span><strong>{detected_lang}</strong></div>
                
                <div style="height:14px;"></div>
                <div style="font-size:0.7rem; font-weight:700; color:{COLORS['text_secondary']}; margin-bottom:6px;">DIGITIZED LAYOUT PREVIEW</div>
                <div style="background:{COLORS['background']}; border:1px solid {COLORS['border']}; border-radius:8px; padding:16px; font-size:1.2rem; font-weight:700; color:#111827; text-align:center;">
                    {extracted_text}
                </div>
                <div style="font-size:0.7rem; color:#10B981; margin-top:8px; font-weight:600; display:flex; align-items:center; gap:4px;">
                    ● Bounding boxes aligned successfully
                </div>
            </div>
            """)
        else:
            html_block(f"""
            <div class="sd-card" style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:210px; background:#F8FAFC; border:1px dashed {COLORS['border']};">
                <div style="font-size:2.2rem; margin-bottom:8px; filter:grayscale(100%);">🤖</div>
                <div style="color:{COLORS['text_secondary']}; font-size:0.9rem; font-weight:700;">Extraction Idle</div>
                <div class="sd-caption" style="margin-top:2px;">Click the button on the left to start OCR</div>
            </div>
            """)

    html_block("<div class='sd-divider' style='margin-top:40px; margin-bottom:40px;'></div>")


def _render_security_section():
    html_block("<div id='why-securedocai'></div>")
    left, right = st.columns([1, 1.1], gap="large")
    with left:
        html_block(f"""
        <div style="padding-top:14px;">
            <span class="sd-eyebrow">ZERO-TRUST SECURITY</span>
            <h2 class="sd-h2" style="margin-top:6px;">Why SecureDocAI is different</h2>
            <p class="sd-body" style="margin-bottom:20px;">Unlike standard online OCR tools that upload your private documents to third-party vendor servers, SecureDocAI follows a strict zero-trust decentralization model.</p>
        </div>
        """)
        
        st.markdown(f"""
        <div class="sd-card" style="background:#FFFBEB; border: 1px solid #FDE68A; margin-bottom:12px; padding:16px;">
            <strong style="color:#B45309; font-size:0.95rem;">🔒 Decoupled Personal Storage</strong>
            <p class="sd-body" style="font-size:0.85rem; margin-top:4px; margin-bottom:0;">Files are saved directly to your <strong>personal Google Drive storage vault</strong>, encrypted using local AES-256 keys. We never store your files.</p>
        </div>
        <div class="sd-card" style="background:#ECFDF5; border: 1px solid #A7F3D0; margin-bottom:12px; padding:16px;">
            <strong style="color:#047857; font-size:0.95rem;">⛓️ Tamper-Evident Ledger</strong>
            <p class="sd-body" style="font-size:0.85rem; margin-top:4px; margin-bottom:0;">Every saved document hash is registered on a local tamper-evident blockchain ledger, complete with digital signatures to guarantee origin authenticity.</p>
        </div>
        """, unsafe_allow_html=True)

    with right:
        html_block(f"""
        <div class="sd-card" style="padding:24px;">
            <h4 style="font-weight:800; font-size:1.15rem; margin-bottom:16px;">SecureDocAI vs Standard OCR</h4>
            
            <div style="display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid #F1F5F9; font-size:0.85rem;">
                <span style="color:#64748B;">PII Compliance Masking</span>
                <strong style="color:#10B981;">✓ Auto Redaction</strong>
                <span style="color:#EF4444; font-weight:600;">✗ None</span>
            </div>
            
            <div style="display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid #F1F5F9; font-size:0.85rem;">
                <span style="color:#64748B;">Layout Reconstruction</span>
                <strong style="color:#10B981;">✓ Paragraphs &amp; Columns</strong>
                <span style="color:#EF4444; font-weight:600;">✗ Plain Text Only</span>
            </div>
            
            <div style="display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid #F1F5F9; font-size:0.85rem;">
                <span style="color:#64748B;">Tamper Proof Hash Chain</span>
                <strong style="color:#10B981;">✓ Blockchain Seal</strong>
                <span style="color:#EF4444; font-weight:600;">✗ None</span>
            </div>
            
            <div style="display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid #F1F5F9; font-size:0.85rem;">
                <span style="color:#64748B;">Storage Model</span>
                <strong style="color:#10B981;">✓ Your own Google Drive</strong>
                <span style="color:#EF4444; font-weight:600;">✗ Vendor Database</span>
            </div>
            
            <div style="display:flex; justify-content:space-between; padding:8px 0; font-size:0.85rem;">
                <span style="color:#64748B;">Document Ownership</span>
                <strong style="color:#10B981;">✓ 100% User Owned</strong>
                <span style="color:#EF4444; font-weight:600;">✗ Terms Apply</span>
            </div>
        </div>
        """)

    html_block("<div class='sd-divider' style='margin-top:40px; margin-bottom:40px;'></div>")


def _render_features():
    html_block("<div id='features'></div>")
    html_block("""
    <div style="text-align:center; margin-bottom:28px;">
        <span class="sd-eyebrow">FEATURES</span>
        <h2 class="sd-h2" style="margin-top:6px;">High-performance features for researchers, students, and teams</h2>
    </div>
    """)

    features_list = [
        ("📂", "AI Layout Reconstruction", "Automatically detects paragraphs, list bullets, tables, and spacing margins to output clean DOCX/PDFs."),
        ("✏️", "Character-level OCR", "Uses custom character-level crop segmentation to decode dense Hindi and Telugu script strokes."),
        ("📄", "Full PDF Support", "Import multi-page PDF scans, running parallel batch OCR processes across pages automatically."),
        ("📷", "Live Lens Scan", "Scan documents on the spot using camera lens video frames directly from your mobile/desktop browser."),
        ("☁️", "GDrive Connection", "Integrate your Google Drive account, saving digitized bundles to a designated SecureDocAI folder."),
        ("📦", "Rich Export Formats", "Export output directly to plain text, Markdown, HTML, Microsoft Word DOCX, layout JSON, or formatted PDF."),
        ("🔍", "Searchable Database", "Run regex, case-sensitive, or fuzzy matches inside the library history index to search your documents."),
        ("📊", "OCR Performance Analytics", "Track scan statistics, character counts, average confidence ratings, and model processing durations.")
    ]

    col1, col2, col3, col4 = st.columns(4)
    cols = [col1, col2, col3, col4]
    
    for idx, (icon, title, desc) in enumerate(features_list):
        with cols[idx % 4]:
            html_block(f"""
            <div class="sd-card hover-card" style="margin-bottom:18px; min-height: 200px;">
                <div style="font-size:1.8rem; margin-bottom:10px;">{icon}</div>
                <div style="font-weight:800; font-size:1rem; color:#0F172A; margin-bottom:6px;">{title}</div>
                <div style="font-size:0.82rem; line-height:1.5; color:#64748B;">{desc}</div>
            </div>
            """)

    html_block("<div class='sd-divider' style='margin-top:40px; margin-bottom:40px;'></div>")


def _render_how_it_works():
    html_block("<div id='timeline'></div>")
    html_block("""
    <div style="text-align:center; margin-bottom:32px;">
        <span class="sd-eyebrow">WORKFLOW TIMELINE</span>
        <h2 class="sd-h2" style="margin-top:6px;">Four steps from paper to encrypted database</h2>
    </div>
    """)

    steps = [
        ("1. Import", "Upload a document image (PNG/JPG), multi-page PDF, or snap with a live camera.", "📥"),
        ("2. OCR Routing", "The Hybrid Manager routes text to our Custom HTR AI model with fallback protection.", "⚙️"),
        ("3. Review Grid", "Compare original bounding boxes with decoded text and correct uncertainties.", "📝"),
        ("4. Ledger Seal", "The document is sealed on the blockchain and saved directly inside your Drive.", "🔒")
    ]

    html_block('<div class="timeline-container">')
    for i, (title, desc, icon) in enumerate(steps):
        st.markdown(
            f"""<div class="sd-card hover-card" style="flex:1; background:#F8FAFC; border:1px solid #E2E8F0; padding:20px; text-align:center;">
                <div style="font-size:2.2rem; margin-bottom:8px;">{icon}</div>
                <div style="font-size:0.7rem; font-weight:700; color:{COLORS['primary']}; text-transform:uppercase; letter-spacing:0.05em;">STEP 0{i+1}</div>
                <div style="font-weight:800; font-size:1.05rem; color:#0F172A; margin-top:4px;">{title}</div>
                <div style="font-size:0.8rem; color:#64748B; margin-top:6px; line-height:1.4;">{desc}</div>
            </div>""",
            unsafe_allow_html=True
        )
        if i < len(steps) - 1:
            st.markdown('<div class="timeline-arrow">➔</div>', unsafe_allow_html=True)
    html_block('</div>')

    html_block("<div class='sd-divider' style='margin-top:40px; margin-bottom:40px;'></div>")


def _render_faq():
    html_block("<div id='faq'></div>")
    html_block("""
    <div style="text-align:center; margin-bottom:28px;">
        <span class="sd-eyebrow">FAQ</span>
        <h2 class="sd-h2" style="margin-top:6px;">Frequently Asked Questions</h2>
    </div>
    """)

    faqs = [
        ("What languages are supported?", "SecureDocAI natively supports handwritten and printed Hindi, Telugu, and English. The Hybrid Engine automatically detects the language and routes it accordingly."),
        ("How does the Google Drive integration work?", "SecureDocAI uses per-user OAuth. It generates a folder named 'SecureDocAI' inside your personal Google Drive and saves your files directly there. We never store or access your files on our servers."),
        ("What is the role of blockchain in document storage?", "Each document's unique cryptographic hash is recorded on a local tamper-evident blockchain ledger. This allows you to verify that your document has not been altered or tampered with since it was digitized."),
        ("Is my data secure?", "Yes. Credentials and documents are encrypted using AES-256 keys on your disk. PII fields (like Aadhaar card numbers, PAN IDs, phone numbers) are masked using compliance redacting filters."),
        ("Is it free to use?", "SecureDocAI is fully open-source and free to run on your local machine. All standard OCR features, exports, and Drive storage integrations are fully included.")
    ]

    for question, answer in faqs:
        with st.expander(f"❓ {question}", expanded=False):
            st.write(answer)

    html_block("<div class='sd-divider' style='margin-top:40px; margin-bottom:40px;'></div>")


def _render_cta():
    html_block("""
    <div style="background: linear-gradient(135deg, #1E3A8A, #0D9488); border-radius:20px; padding:48px 32px; text-align:center; margin-bottom:40px; box-shadow: 0 10px 25px rgba(37, 99, 235, 0.15);">
        <h2 style="color:white; font-size:2.2rem; font-weight:850; letter-spacing:-0.02em; margin-bottom:12px;">Start securing your digitized records today</h2>
        <p style="color:#E2E8F0; font-size:1.05rem; max-width:540px; margin: 0 auto 32px auto; line-height:1.6;">Setup your local database, connect Google Drive, and digitize your Telugu or Hindi handwritings in minutes.</p>
    </div>
    """)
    
    col_l, col_r = st.columns(2)
    with col_l:
        if st.button("🚪 Sign In to Account", type="primary", **full_width_kwargs(widget=st.button), key="cta_signin"):
            _go("login")
    with col_r:
        if st.button("🔐 Create Secure Vault", **full_width_kwargs(widget=st.button), key="cta_signup"):
            _go("signup")

    html_block("<div style='height:40px;'></div>")


def _render_footer():
    html_block("<div class='sd-divider' style='margin-top:10px; margin-bottom:32px;'></div>")
    
    col_about, col_product, col_compliance, col_meta = st.columns([1.5, 1, 1, 1.2])
    
    with col_about:
        html_block(f"""
        <div class="footer-col">
            <h5>About SecureDocAI</h5>
            <p style="font-size:0.8rem; line-height:1.5; color:#64748B; max-width:240px;">
                SecureDocAI is a high-performance open-source project building intelligent hybrid document digitalization workflows.
            </p>
        </div>
        """)
        
    with col_product:
        html_block("""
        <div class="footer-col">
            <h5>Product</h5>
            <ul>
                <li><a href="#why-securedocai">Security</a></li>
                <li><a href="#features">Features</a></li>
                <li><a href="#demo">Live Demo</a></li>
            </ul>
        </div>
        """)
        
    with col_compliance:
        html_block("""
        <div class="footer-col">
            <h5>Resources</h5>
            <ul>
                <li><a href="#">Privacy Policy</a></li>
                <li><a href="#">Terms of Service</a></li>
            </ul>
        </div>
        """)
        
    with col_meta:
        html_block(f"""
        <div class="footer-col" style="text-align:right;">
            <h5>Version Info</h5>
            <p style="font-size:0.8rem; color:#64748B; margin-bottom:4px;">SecureDocAI Core v{APP_VERSION}</p>
            <p style="font-size:0.75rem; color:#94A3B8;">Built on {BUILD_DATE}</p>
        </div>
        """)
        
    html_block("<div style='height:24px;'></div>")
    html_block("<div class='sd-caption' style='text-align:center;'>© 2026 SecureDocAI. All rights reserved. Open-source under Apache-2.0.</div>")
    html_block("<div style='height:20px;'></div>")