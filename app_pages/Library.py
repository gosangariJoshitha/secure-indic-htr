"""
app_pages/Library.py
=====================
Premium vault library and document manager workspace.
"""

import time
import io
import zipfile
import json
import pandas as pd
import streamlit as st
from datetime import datetime
from components.ui_helpers import html_block, full_width_kwargs
from config import COLORS, APP_NAME
from utils.helpers import (
    list_documents, get_text_for_image, delete_full_document_set,
    rename_document, get_storage_usage, update_document_text
)
from utils.privacy import detect_sensitive_data, compliance_scan, compute_privacy_score, auto_redact
from utils.security_engine import get_blockchain, compute_security_score, security_grade
from utils.notifications import push_notification
from utils.exporters import export_markdown, export_txt, export_html, export_docx, export_pdf, export_json

def _init_activity_log():
    if "activity_logs" not in st.session_state:
        from pathlib import Path
        log_file = Path("data") / "activity_logs.json"
        if log_file.exists():
            try:
                st.session_state.activity_logs = json.loads(log_file.read_text(encoding="utf-8"))
            except Exception:
                st.session_state.activity_logs = []
        else:
            st.session_state.activity_logs = []

def _save_activity_logs():
    from pathlib import Path
    log_file = Path("data") / "activity_logs.json"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        log_file.write_text(json.dumps(st.session_state.activity_logs, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

def _add_log(action: str, filename: str, log_type: str = "OCR"):
    _init_activity_log()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.activity_logs.insert(0, {
        "action": action,
        "time": timestamp,
        "file": filename,
        "type": log_type
    })
    _save_activity_logs()

def render():
    _init_activity_log()
    creds = st.session_state.get("drive_creds")

    col_title, col_search = st.columns([1.6, 1.0], gap="large")
    with col_title:
        html_block("""<div style="margin-bottom:18px;">
            <span class="sd-eyebrow" style="color: #10B981; font-weight:700;">PERSONAL LIBRARY</span>
            <h2 class="sd-h2" style="margin-top:6px; font-weight:800; font-size:2.2rem; color:#0F172A;">Your encrypted vault</h2>
        </div>""")

    if creds is None:
        html_block(f"""<div class='sd-card' style='padding: 32px; text-align: center;'>
            <div style='font-size: 2.2rem; margin-bottom: 8px;'>🔒</div>
            <div style='font-weight: 700; font-size:1.1rem;'>Library Disconnected</div>
            <div class='sd-caption' style='margin-bottom: 16px;'>Please connect your Google Drive account in Profile settings to load documents.</div>
        </div>""")
        if st.button("Configure Profile Settings", key="lib_connect_settings", type="primary"):
            st.session_state.active_page = "Profile"
            st.rerun()
        return

    # Sync Cache
    if "hist_documents_cache" not in st.session_state:
        with st.spinner("Loading file list from Google Drive..."):
            try:
                st.session_state.hist_documents_cache = list_documents(creds, page_size=100)
            except Exception as e:
                st.error(f"Failed to fetch documents: {e}")
                st.session_state.hist_documents_cache = []

    docs = st.session_state.hist_documents_cache

    if st.session_state.get("active_lib_doc"):
        _render_active_workspace(creds)
        return

    with col_search:
        html_block("<div style='height:28px;'></div>") # alignment spacer
        search_query = st.text_input("Search documents", placeholder="Search by name or language", label_visibility="collapsed", key="lib_search_input")

    # Apply Filters & Search (Instant Local Search)
    filtered_docs = []
    for d in docs:
        name = d.get("appProperties", {}).get("original_filename", d["name"])
        lang = d.get("appProperties", {}).get("language", "Auto")
        doc_type = d.get("appProperties", {}).get("doc_type", "")
        
        if search_query.strip():
            q = search_query.lower()
            in_name = q in name.lower()
            in_lang = q in lang.lower()
            in_type = q in doc_type.lower()
            if not (in_name or in_lang or in_type):
                continue

        filtered_docs.append(d)

    # Apply Sorting
    filtered_docs.sort(key=lambda x: x.get("createdTime", ""), reverse=True)

    # Style transparent buttons inside columns
    st.markdown("""
        <style>
        /* Scope selectors to only match columns inside the document table wrapper */
        .vault-table-wrapper div[data-testid="column"]:nth-child(1) button {
            background: transparent !important;
            border: none !important;
            color: var(--text) !important;
            font-weight: 700 !important;
            text-align: left !important;
            justify-content: flex-start !important;
            display: inline-flex !important;
            width: 100% !important;
            padding: 0 !important;
            font-size: 0.95rem !important;
            box-shadow: none !important;
            transform: none !important;
            height: auto !important;
            min-height: 0 !important;
        }
        .vault-table-wrapper div[data-testid="column"]:nth-child(1) button * {
            text-align: left !important;
            justify-content: flex-start !important;
        }
        .vault-table-wrapper div[data-testid="column"]:nth-child(1) button:hover {
            color: #2563EB !important;
            text-decoration: underline !important;
        }
        /* Fourth column (View) button circle styling */
        .vault-table-wrapper div[data-testid="column"]:nth-child(4) button {
            background-color: #F1F5F9 !important;
            border: 1px solid #E2E8F0 !important;
            color: #64748B !important;
            font-size: 1.1rem !important;
            border-radius: 50% !important;
            width: 32px !important;
            height: 32px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            transition: all 0.2s ease !important;
            box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05) !important;
            padding: 0 !important;
            margin: 0 auto !important;
            min-height: 0 !important;
            transform: none !important;
        }
        .vault-table-wrapper div[data-testid="column"]:nth-child(4) button:hover {
            background-color: #E0F2FE !important;
            border-color: #BAE6FD !important;
            color: #0284C7 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
        }
        /* Fifth column (Delete) button circle styling */
        .vault-table-wrapper div[data-testid="column"]:nth-child(5) button {
            background-color: #F1F5F9 !important;
            border: 1px solid #E2E8F0 !important;
            color: #64748B !important;
            font-size: 1.1rem !important;
            border-radius: 50% !important;
            width: 32px !important;
            height: 32px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            transition: all 0.2s ease !important;
            box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05) !important;
            padding: 0 !important;
            margin: 0 auto !important;
            min-height: 0 !important;
            transform: none !important;
        }
        .vault-table-wrapper div[data-testid="column"]:nth-child(5) button:hover {
            background-color: #FEE2E2 !important;
            border-color: #FECACA !important;
            color: #DC2626 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
        }
        .lib-lang-pill {
            background-color: rgba(16, 185, 129, 0.1) !important;
            color: #10B981 !important;
            border: 1px solid rgba(16, 185, 129, 0.2) !important;
            font-size: 0.72rem !important;
            font-weight: 700 !important;
            padding: 2px 8px !important;
            border-radius: 6px !important;
            text-transform: uppercase !important;
            display: inline-block !important;
        }
        </style>
    """, unsafe_allow_html=True)

    if filtered_docs:
        st.markdown('<div class="vault-table-wrapper">', unsafe_allow_html=True)
        with st.container(border=True):
            # Table layout header
            col_h1, col_h2, col_h3, col_h4 = st.columns([5, 2, 2, 2])
            with col_h1:
                st.markdown("<span style='font-size:0.75rem; font-weight:700; color:#64748B; text-transform:uppercase;'>Document Name</span>", unsafe_allow_html=True)
            with col_h2:
                st.markdown("<span style='font-size:0.75rem; font-weight:700; color:#64748B; text-transform:uppercase;'>Language</span>", unsafe_allow_html=True)
            with col_h3:
                st.markdown("<span style='font-size:0.75rem; font-weight:700; color:#64748B; text-transform:uppercase;'>Date</span>", unsafe_allow_html=True)
            with col_h4:
                st.markdown("<span style='font-size:0.75rem; font-weight:700; color:#64748B; text-transform:uppercase; display:block; text-align:center;'>Actions</span>", unsafe_allow_html=True)
                
            st.markdown("<hr style='border:0; height:1px; background:#E2E8F0; margin: 8px 0 16px 0;' />", unsafe_allow_html=True)
            
            for idx, d in enumerate(filtered_docs):
                file_id = d["id"]
                name = d.get("appProperties", {}).get("original_filename", d["name"])
                created = d.get("createdTime", "")[:10]
                try:
                    from datetime import datetime
                    dt = datetime.strptime(created, "%Y-%m-%d")
                    created_formatted = f"{dt.month}/{dt.day}/{dt.year}"
                except Exception:
                    created_formatted = created
                    
                lang = d.get("appProperties", {}).get("language", "Auto")
                
                c_doc, c_lang, c_date, c_view, c_del = st.columns([5, 2, 2, 1, 1])
                with c_doc:
                    if st.button(name, key=f"btn_name_row_{file_id}", use_container_width=True, type="secondary"):
                        st.session_state.active_lib_doc = d
                        st.rerun()
                with c_lang:
                    st.markdown(f"<span class='lib-lang-pill'>{lang}</span>", unsafe_allow_html=True)
                with c_date:
                    st.markdown(f"<span style='font-size:0.9rem; color:var(--text-secondary);'>{created_formatted}</span>", unsafe_allow_html=True)
                with c_view:
                    with st.popover("📥", help="Download document options", use_container_width=True):
                        txt_key = f"lib_text_{file_id}"
                        if txt_key not in st.session_state:
                            try:
                                with st.spinner("Preparing export files..."):
                                    text = get_text_for_image(creds, d["name"])
                                    st.session_state[txt_key] = text or ""
                            except Exception:
                                st.session_state[txt_key] = ""
                        
                        doc_text = st.session_state.get(txt_key, "")
                        from utils.layout_pipeline import LayoutDocument, Block, BlockType, RecognizedLine, Alignment
                        lines = [RecognizedLine(text=line, alignment=Alignment.LEFT, y=idx*20) for idx, line in enumerate(doc_text.splitlines())]
                        doc_obj = LayoutDocument(blocks=[Block(type=BlockType.PARAGRAPH, lines=lines)], page_width=800, page_height=1000)
                        base_name = name.rsplit(".", 1)[0]
                        
                        from utils.exporters import export_txt, export_docx, export_pdf, export_json
                        st.download_button("TXT Format", data=export_txt(doc_obj).encode("utf-8"), file_name=f"{base_name}.txt", use_container_width=True, key=f"dl_txt_row_{file_id}")
                        try:
                            st.download_button("JSON Data", data=export_json(doc_obj).encode("utf-8"), file_name=f"{base_name}.json", use_container_width=True, key=f"dl_json_row_{file_id}")
                        except Exception:
                            pass
                        try:
                            st.download_button("Word DOCX", data=export_docx(doc_obj, base_name), file_name=f"{base_name}.docx", use_container_width=True, key=f"dl_docx_row_{file_id}")
                        except Exception:
                            pass
                        try:
                            st.download_button("PDF Document", data=export_pdf(doc_obj, base_name), file_name=f"{base_name}.pdf", use_container_width=True, key=f"dl_pdf_row_{file_id}")
                        except Exception:
                            pass
                with c_del:
                    if st.button("🗑", key=f"btn_del_row_{file_id}", use_container_width=True):
                        try:
                            delete_full_document_set(creds, d["name"], file_id)
                            st.session_state.pop(f"lib_text_{file_id}", None)
                            st.session_state.pop("hist_documents_cache", None)
                            if st.session_state.get("active_lib_doc", {}).get("id") == file_id:
                                st.session_state.pop("active_lib_doc", None)
                            _add_log("Delete completed", name, "Delete")
                            st.toast("Deleted Successfully")
                            st.rerun()
                        except Exception as e:
                            st.error("Delete failed")
                            
                # Thin divider line
                if idx < len(filtered_docs) - 1:
                    st.markdown("<hr style='border:0; height:1px; background:#F1F5F9; margin: 8px 0;' />", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("No documents found in library.")
        if st.button("🔄 Sync & Refresh Library", type="primary", use_container_width=True):
            st.session_state.pop("hist_documents_cache", None)
            st.rerun()


def _render_active_workspace(creds):
    d = st.session_state.active_lib_doc
    file_id = d["id"]
    name = d.get("appProperties", {}).get("original_filename", d["name"])
    
    st.markdown(f"## 👁️ {name}")
    if st.button("❌ Close", key="btn_close_active_view"):
        st.session_state.pop("active_lib_doc", None)
        st.rerun()

    # Load Full Text Content
    txt_key = f"lib_text_{file_id}"
    if txt_key not in st.session_state:
        try:
            text = get_text_for_image(creds, d["name"])
            st.session_state[txt_key] = text or ""
        except Exception:
            st.session_state[txt_key] = ""

    doc_text = st.session_state[txt_key]

    # Side-by-side: Left Preview Image, Right Workspace Tabs
    prev_col, work_col = st.columns([1, 1.2], gap="large")

    with prev_col:
        st.markdown("### Preview")
        thumb = d.get("thumbnailLink")
        web_link = d.get("webViewLink", "")
        if thumb:
            st.image(thumb, use_column_width=True)
        else:
            st.info("No preview available")
            
        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        
        # Rename & Delete
        new_name = st.text_input("Rename Document Name", value=name.rsplit(".", 1)[0] if "." in name else name, key="rename_doc_input")
        if st.button("Rename Document", use_container_width=True, key="btn_rename_doc"):
            try:
                ext = name.rsplit(".", 1)[-1] if "." in name else "png"
                rename_document(creds, file_id, f"{new_name}.{ext}")
                st.session_state.pop("hist_documents_cache", None)
                _add_log(f"Renamed document to {new_name}", d["name"], "OCR")
                st.toast("Renamed Successfully")
                if "appProperties" not in st.session_state.active_lib_doc or st.session_state.active_lib_doc["appProperties"] is None:
                    st.session_state.active_lib_doc["appProperties"] = {}
                st.session_state.active_lib_doc["appProperties"]["original_filename"] = f"{new_name}.{ext}"
                st.rerun()
            except Exception as e:
                st.error(f"Rename failed: {e}")
                
        if st.button("🗑️ Delete Document", use_container_width=True, type="secondary", key="btn_delete_active_doc"):
            try:
                delete_full_document_set(creds, d["name"], file_id)
                st.session_state.pop(f"lib_text_{file_id}", None)
                st.session_state.pop("hist_documents_cache", None)
                st.session_state.pop("active_lib_doc", None)
                _add_log("Delete completed", name, "Delete")
                st.toast("Deleted Successfully")
                st.rerun()
            except Exception as e:
                st.error("Delete failed")

        # V2: Secure Share Link Expander
        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        with st.expander("🔗 Generate Secure Share Link", expanded=False):
            st.markdown("<p style='font-size:0.82rem; color:#64748B;'>Configure secure access parameters for sharing this file:</p>", unsafe_allow_html=True)
            
            share_pw = st.text_input("Access Password (Optional)", type="password", key=f"share_pw_input_{file_id}", placeholder="Leave empty for no password")
            share_expiry = st.selectbox("Expiration", [1, 12, 24, 48, 168], index=2, format_func=lambda x: f"{x} hour(s)", key=f"share_exp_select_{file_id}")
            share_onetime = st.checkbox("One-time Download Limit", value=False, key=f"share_onetime_cb_{file_id}")
            
            if st.button("Generate Link", key=f"btn_gen_share_{file_id}", use_container_width=True, type="primary"):
                from utils.security_engine import create_share_link
                share_token = create_share_link(
                    file_id=file_id,
                    filename=name,
                    drive_name=d["name"],
                    password=share_pw if share_pw.strip() else None,
                    expire_hours=share_expiry,
                    one_time=share_onetime
                )
                if share_token:
                    share_url = f"http://localhost:8501/?share={share_token}"
                    st.session_state[f"generated_share_url_{file_id}"] = share_url
                    _add_log(f"Generated secure share link for {name}", d["name"], "Shared")
                    st.toast("Share link generated successfully!")
                    st.rerun()
                else:
                    st.error("Failed to generate link.")
            
            gen_url_key = f"generated_share_url_{file_id}"
            if gen_url_key in st.session_state:
                st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
                st.success("Secure link is active:")
                share_url_val = st.session_state[gen_url_key]
                st.code(share_url_val, language="text")
                
                import qrcode
                import io
                import base64
                qr = qrcode.QRCode(version=1, box_size=5, border=2)
                qr.add_data(share_url_val)
                qr.make(fit=True)
                qr_img = qr.make_image(fill_color="black", back_color="white")
                buf = io.BytesIO()
                qr_img.save(buf, format="PNG")
                qr_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                
                st.markdown(f"<div style='display:flex; align-items:center; gap:16px; margin-top:10px; padding:12px; border:1px solid #E2E8F0; border-radius:12px; background:#F8FAFC;'><img src='data:image/png;base64,{qr_b64}' width='120' height='120'/><div><div style='font-weight:700; color:#0F172A;'>QR code sharing ready</div><div style='font-size:0.8rem; color:#64748B; margin-top:6px;'>Scan this code to open the verification link on a phone or share it with a teammate.</div></div></div>", unsafe_allow_html=True)
                
                st.markdown("<span style='font-size:0.75rem; color:#94A3B8;'>Anyone with this link and password (if set) can access this document.</span>", unsafe_allow_html=True)

    with work_col:
        st.markdown("### Digitized Text")
        
        draft_key = f"lib_draft_{file_id}"
        if draft_key not in st.session_state or st.session_state.get("last_lib_doc_id") != file_id:
            st.session_state[draft_key] = doc_text
            st.session_state["last_lib_doc_id"] = file_id
        
        edited_txt = st.text_area("Edit text content below:", value=st.session_state[draft_key], height=320, key=f"edit_area_widget_{file_id}")
        if edited_txt != st.session_state[draft_key]:
            st.session_state[draft_key] = edited_txt

        if edited_txt != doc_text:
            if st.button("Save Changes", type="primary", use_container_width=True, key="btn_save_changes_drive"):
                try:
                    update_document_text(creds, d["name"], edited_txt)
                    
                    # Smart OCR Learning
                    from utils.security_engine import learn_ocr_corrections, save_document_version, get_document_versions
                    learn_ocr_corrections(doc_text, edited_txt)
                    
                    # V2 Version history tracking
                    get_document_versions(file_id, default_text=doc_text) # initialize version 1
                    save_document_version(file_id, edited_txt) # save version 2+
                    
                    st.session_state[txt_key] = edited_txt
                    _add_log("Edited OCR text saved to Drive", d["name"], "OCR")
                    st.toast("Saved Successfully")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save changes: {e}")

        # V2: Document Version History Rollback panel
        from utils.security_engine import get_document_versions, save_document_version
        versions = get_document_versions(file_id, default_text=doc_text)
        if versions:
            with st.expander("📜 Version History & Rollback", expanded=False):
                st.markdown("<p style='font-size:0.85rem; color:#64748B; margin-bottom:10px;'>Select a previous version to restore this document's text.</p>", unsafe_allow_html=True)
                for v in reversed(versions):
                    col_v1, col_v2 = st.columns([3, 1])
                    with col_v1:
                        st.markdown(f"**Version {v['version']}**  \n<span style='font-size:0.75rem; color:#94A3B8;'>{v['timestamp']}</span>", unsafe_allow_html=True)
                    with col_v2:
                        if v["version"] == len(versions):
                            st.write("(Current)")
                        else:
                            if st.button("Restore", key=f"btn_restore_v_{file_id}_{v['version']}", use_container_width=True):
                                try:
                                    update_document_text(creds, d["name"], v["text"])
                                    st.session_state[txt_key] = v["text"]
                                    st.session_state[draft_key] = v["text"]
                                    save_document_version(file_id, v["text"]) # Save rollback as new version
                                    _add_log(f"Restored document to Version {v['version']}", d["name"], "OCR")
                                    st.toast(f"Restored to Version {v['version']} successfully!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Restore failed: {e}")

        st.markdown("### Download Document")
        
        from utils.layout_pipeline import LayoutDocument, Block, BlockType, RecognizedLine, Alignment
        lines = [RecognizedLine(text=line, alignment=Alignment.LEFT, y=idx*20) for idx, line in enumerate(edited_txt.splitlines())]
        doc_obj = LayoutDocument(blocks=[Block(type=BlockType.PARAGRAPH, lines=lines)], page_width=800, page_height=1000)
        
        base_name = name.rsplit(".", 1)[0]
        dl_col1, dl_col2, dl_col3, dl_col4 = st.columns(4)
        with dl_col1:
            st.download_button("TXT Format", data=export_txt(doc_obj).encode("utf-8"), file_name=f"{base_name}.txt", use_container_width=True, key="dl_txt_active")
        with dl_col2:
            try:
                st.download_button("Word DOCX", data=export_docx(doc_obj, base_name), file_name=f"{base_name}.docx", use_container_width=True, key="dl_docx_active")
            except Exception:
                pass
        with dl_col3:
            try:
                st.download_button("PDF Document", data=export_pdf(doc_obj, base_name), file_name=f"{base_name}.pdf", use_container_width=True, key="dl_pdf_active")
            except Exception:
                pass
        with dl_col4:
            try:
                from utils.exporters import export_json
                st.download_button("JSON Data", data=export_json(doc_obj).encode("utf-8"), file_name=f"{base_name}.json", use_container_width=True, key="dl_json_active")
            except Exception:
                pass
