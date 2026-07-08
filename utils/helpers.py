"""
utils/helpers.py
=================
Google Drive operations — save scanned documents + OCR text directly into
the SIGNED-IN USER's own Drive. Every function takes `creds` so
each call acts strictly on behalf of the user.
"""

from __future__ import annotations

import io
import json
import uuid
import logging
from datetime import datetime
from typing import Any

from config import GOOGLE_DRIVE_APP_FOLDER

logger = logging.getLogger("SecureDocAI.Helpers")

_FOLDER_MIME = "application/vnd.google-apps.folder"


def store_latest_ocr_context(
    state: dict,
    *,
    doc: Any,
    elapsed: float,
    overlay: Any = None,
    engine_used: str = "handwritten",
    edited_text: str | None = None,
    filename: str | None = None,
    language: str | None = None,
    detected_script: str | None = None,
    metadata: dict | None = None,
) -> dict:
    """Store the most recent OCR output in a single session-state payload."""
    import re
    # Extract entities for the search index
    text = edited_text or getattr(doc, "plain_text", "")
    text_lower = text.lower() if text else ""
    
    # Aadhaar, PAN, emails, phones matching
    aadhaar_match = re.search(r'\b\d{4}\s\d{4}\s\d{4}\b|\b\d{12}\b', text_lower)
    pan_match = re.search(r'\b[a-z]{5}\d{4}[a-z]\b', text_lower)
    emails = list(set(re.findall(r'\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b', text_lower)))
    phones = list(set(re.findall(r'\b(?:\+91[\-\s]?)?[789]\d{9}\b', text_lower)))
    
    # Classify document type
    if "invoice" in text_lower or "bill" in text_lower or "tax invoice" in text_lower:
        doc_type = "Invoice"
    elif "prescription" in text_lower or "medical" in text_lower or "hospital" in text_lower:
        doc_type = "Medical"
    elif "certificate" in text_lower or "degree" in text_lower or "diploma" in text_lower:
        doc_type = "Certificate"
    elif "bank statement" in text_lower or "transaction" in text_lower:
        doc_type = "Bank"
    else:
        doc_type = "Government"

    context = {
        "doc": doc,
        "overlay": overlay,
        "engine_used": engine_used,
        "edited_text": text,
        "filename": filename,
        "language": language,
        "detected_script": detected_script,
        "metrics": {
            "confidence": float(getattr(doc, "mean_confidence", 0.0)),
            "char_count": int(getattr(doc, "char_count", 0)),
            "elapsed": float(elapsed),
            "engine_used": engine_used,
        },
        "metadata": {
            **(metadata or {}),
            "doc_type": doc_type,
            "has_aadhaar": bool(aadhaar_match),
            "has_pan": bool(pan_match),
            "emails": emails,
            "phones": phones,
        },
    }
    state["latest_ocr_context"] = context
    return context


def get_latest_ocr_context(state: dict) -> dict | None:
    """Read the most recently stored OCR context from session state."""
    return state.get("latest_ocr_context")


def update_latest_ocr_text(state: dict, text: str) -> dict | None:
    """Update the edited OCR text without losing the rest of the OCR context."""
    context = get_latest_ocr_context(state)
    if context is None:
        return None
    context["edited_text"] = text
    state["latest_ocr_context"] = context
    return context


def _get_service(creds):
    """Builds an authenticated Drive v3 client from stored credentials."""
    import socket
    socket.setdefaulttimeout(45)
    from googleapiclient.discovery import build
    return build("drive", "v3", credentials=creds)


def ensure_app_folder(creds) -> str:
    """Finds the SecureDocAI folder in the user's Drive, creating it on first use."""
    service = _get_service(creds)

    query = (
        f"name='{GOOGLE_DRIVE_APP_FOLDER}' and "
        f"mimeType='{_FOLDER_MIME}' and trashed=false"
    )
    results = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
    folders = results.get("files", [])

    if folders:
        return folders[0]["id"]

    folder_metadata = {"name": GOOGLE_DRIVE_APP_FOLDER, "mimeType": _FOLDER_MIME}
    folder = service.files().create(body=folder_metadata, fields="id").execute()
    return folder["id"]


def ensure_folders(creds) -> dict[str, str]:
    """Ensures parent folder and subfolders exist."""
    service = _get_service(creds)
    parent_id = ensure_app_folder(creds)
    
    subfolders = ["Images", "PDF", "Reports", "Metadata", "JSON", "OCR", "Masked", "Logs", "Documents", "Encrypted", "Exports", "Backups"]
    folder_ids = {"root": parent_id}
    
    for folder in subfolders:
        query = (
            f"name='{folder}' and "
            f"'{parent_id}' in parents and "
            f"mimeType='{_FOLDER_MIME}' and trashed=false"
        )
        results = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
        files = results.get("files", [])
        if files:
            folder_ids[folder] = files[0]["id"]
        else:
            folder_metadata = {
                "name": folder,
                "mimeType": _FOLDER_MIME,
                "parents": [parent_id]
            }
            new_f = service.files().create(body=folder_metadata, fields="id").execute()
            folder_ids[folder] = new_f["id"]
            
    return folder_ids


def upload_document(creds, image_bytes: bytes, image_filename: str,
                    ocr_text: str, metadata: dict | None = None,
                    pdf_bytes: bytes | None = None, docx_bytes: bytes | None = None,
                    html_bytes: bytes | None = None, markdown_bytes: bytes | None = None,
                    json_bytes: bytes | None = None, masked_text: str | None = None) -> dict:
    """Uploads the scanned image, metadata sidecars, and format bundles into encrypted subfolders."""
    from googleapiclient.http import MediaIoBaseUpload
    from utils.security_engine import aes_encrypt

    service = _get_service(creds)
    folders = ensure_folders(creds)
    
    doc_id = str(uuid.uuid4())
    ext = image_filename.rsplit(".", 1)[-1] if "." in image_filename else "png"
    
    # Classify & Index Search Fields
    meta_dict = metadata or {}
    doc_type = meta_dict.get("doc_type", "Government")
    conf = meta_dict.get("confidence", 0.0)
    lang = meta_dict.get("language", "Auto")
    engine = meta_dict.get("engine", "Hybrid")
    
    # Attach AppProperties for fast indexing on the Image File
    app_props = {
        "doc_id": doc_id,
        "confidence": str(conf),
        "language": lang,
        "engine": engine,
        "doc_type": doc_type,
        "original_filename": image_filename,
    }

    result = {}

    # 1. Upload original image
    img_media = MediaIoBaseUpload(io.BytesIO(image_bytes), mimetype=f"image/{ext}", resumable=False)
    img_file = service.files().create(
        body={"name": f"{doc_id}.{ext}", "parents": [folders["Images"]], "appProperties": app_props},
        media_body=img_media,
        fields="id, webViewLink",
    ).execute()
    result["image"] = img_file

    # 2. Encrypt & Upload OCR text
    enc_ocr = aes_encrypt(ocr_text)
    txt_media = MediaIoBaseUpload(io.BytesIO(enc_ocr.encode("utf-8")), mimetype="text/plain", resumable=False)
    txt_file = service.files().create(
        body={"name": f"{doc_id}.txt", "parents": [folders["OCR"]]},
        media_body=txt_media,
        fields="id, webViewLink",
    ).execute()
    result["text"] = txt_file

    # 3. Encrypt & Upload Masked OCR text (if available)
    if masked_text:
        enc_masked = aes_encrypt(masked_text)
        masked_media = MediaIoBaseUpload(io.BytesIO(enc_masked.encode("utf-8")), mimetype="text/plain", resumable=False)
        masked_file = service.files().create(
            body={"name": f"{doc_id}_masked.txt", "parents": [folders["Masked"]]},
            media_body=masked_media,
            fields="id, webViewLink",
        ).execute()
        result["masked_text"] = masked_file

    # 4. Upload format bundles (PDF & DOCX)
    if pdf_bytes:
        pdf_media = MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype="application/pdf", resumable=False)
        pdf_file = service.files().create(
            body={"name": f"{doc_id}.pdf", "parents": [folders["PDF"]]},
            media_body=pdf_media,
            fields="id",
        ).execute()
        result["pdf"] = pdf_file

    if docx_bytes:
        docx_media = MediaIoBaseUpload(io.BytesIO(docx_bytes), mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document", resumable=False)
        docx_file = service.files().create(
            body={"name": f"{doc_id}.docx", "parents": [folders["PDF"]]},
            media_body=docx_media,
            fields="id",
        ).execute()
        result["docx"] = docx_file

    # 5. Encrypt & Upload Metadata JSON sidecar
    meta_payload = {**meta_dict, "doc_id": doc_id, "original_filename": image_filename, "saved_at": datetime.now().isoformat()}
    enc_meta = aes_encrypt(json.dumps(meta_payload, ensure_ascii=False, indent=2))
    meta_media = MediaIoBaseUpload(io.BytesIO(enc_meta.encode("utf-8")), mimetype="text/plain", resumable=False)
    meta_file = service.files().create(
        body={"name": f"{doc_id}.meta.json", "parents": [folders["Metadata"]]},
        media_body=meta_media,
        fields="id, webViewLink",
    ).execute()
    result["metadata"] = meta_file

    return result


def list_documents(creds, page_size: int = 50) -> list[dict]:
    """Lists files inside the user's SecureDocAI folder using fast cached metadata index."""
    service = _get_service(creds)
    folders = ensure_folders(creds)

    query = f"'{folders['Images']}' in parents and trashed=false"
    results = service.files().list(
        q=query,
        orderBy="createdTime desc",
        pageSize=page_size,
        fields="files(id, name, createdTime, webViewLink, thumbnailLink, size, appProperties)",
    ).execute()
    return results.get("files", [])


def get_text_for_image(creds, image_filename: str) -> str | None:
    """Fetches and decrypts the matching OCR text payload for an image document."""
    service = _get_service(creds)
    folders = ensure_folders(creds)

    doc_id = image_filename.rsplit(".", 1)[0]
    query = f"'{folders['OCR']}' in parents and trashed=false and name='{doc_id}.txt'"
    results = service.files().list(q=query, fields="files(id)").execute()
    files = results.get("files", [])
    if not files:
        return None

    request = service.files().get_media(fileId=files[0]["id"])
    buf = io.BytesIO()
    from googleapiclient.http import MediaIoBaseDownload
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
        
    raw_data = buf.getvalue().decode("utf-8")
    try:
        from utils.security_engine import aes_decrypt
        return aes_decrypt(raw_data)
    except Exception:
        return raw_data


def delete_document(creds, file_id: str):
    """Soft deletes a document by moving it to the Google Drive Trash folder."""
    service = _get_service(creds)
    service.files().update(fileId=file_id, body={"trashed": True}).execute()


def restore_document(creds, file_id: str):
    """Restores a soft-deleted document from the Google Drive Trash folder."""
    service = _get_service(creds)
    service.files().update(fileId=file_id, body={"trashed": False}).execute()


def rename_document(creds, file_id: str, new_name: str):
    """Renames the specified document title."""
    service = _get_service(creds)
    service.files().update(fileId=file_id, body={"name": new_name}).execute()


def get_storage_usage(creds) -> dict:
    """Returns the user's overall Drive account storage usage."""
    service = _get_service(creds)
    about = service.about().get(fields="storageQuota").execute()
    quota = about.get("storageQuota", {})
    return {
        "used_bytes": int(quota.get("usage", 0)),
        "limit_bytes": int(quota.get("limit", 0)) if quota.get("limit") else None,
    }


def get_dashboard_stats(creds) -> dict:
    """Computes overall statistics using properties of the listed files."""
    files = list_documents(creds)
    
    total_docs = len(files)
    last_scan = "—"
    if files:
        created_time = files[0].get("createdTime", "")
        if created_time:
            try:
                dt = datetime.fromisoformat(created_time.replace("Z", "+00:00"))
                last_scan = dt.strftime("%Y-%m-%d")
            except Exception:
                last_scan = created_time[:10]
                
    langs = set()
    for f in files:
        props = f.get("appProperties", {})
        lang = props.get("language")
        if lang:
            langs.add(lang)
            
    return {
        "documents_stored": total_docs,
        "last_scan": last_scan,
        "languages": list(langs),
    }


def delete_full_document_set(creds, image_filename: str, image_file_id: str):
    """Soft deletes the entire document bundle (image, OCR text, masked text, metadata, etc.) from Google Drive."""
    service = _get_service(creds)
    # Trash the image file
    service.files().update(fileId=image_file_id, body={"trashed": True}).execute()
    
    # Extract doc_id from filename
    doc_id = image_filename.rsplit(".", 1)[0]
    
    # Query for sister files with the same prefix (OCR text, metadata, etc.)
    folders = ensure_folders(creds)
    query = f"name contains '{doc_id}' and trashed = false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    for f in results.get("files", []):
        if f["id"] != image_file_id:
            try:
                service.files().update(fileId=f["id"], body={"trashed": True}).execute()
            except Exception as e:
                logger.warning(f"Could not trash sister file {f['name']}: {e}")


def update_document_text(creds, image_filename: str, new_text: str):
    """Encrypts and overwrites the existing OCR text file on Google Drive."""
    import io
    from utils.security_engine import aes_encrypt
    from googleapiclient.http import MediaIoBaseUpload
    
    service = _get_service(creds)
    folders = ensure_folders(creds)
    
    doc_id = image_filename.rsplit(".", 1)[0]
    query = f"'{folders['OCR']}' in parents and name='{doc_id}.txt' and trashed=false"
    results = service.files().list(q=query, fields="files(id)").execute()
    files = results.get("files", [])
    
    enc_ocr = aes_encrypt(new_text)
    media = MediaIoBaseUpload(io.BytesIO(enc_ocr.encode("utf-8")), mimetype="text/plain", resumable=False)
    
    if files:
        service.files().update(fileId=files[0]["id"], media_body=media).execute()
    else:
        service.files().create(
            body={"name": f"{doc_id}.txt", "parents": [folders["OCR"]]},
            media_body=media
        ).execute()


