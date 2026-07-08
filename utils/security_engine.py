"""
utils/security_engine.py
=========================
AES-256-GCM encryption, RSA-2048 PSS digital signatures, the Block/Blockchain
hash-chain classes, and security scoring formulas. Upgraded to support gzip compression,
custom audit and event logging, key rotation, thread safety, blockchain repair,
file integrity hashes, and comprehensive tamper-detection reporting.
"""

from __future__ import annotations

import os
import json
import base64
import hashlib
import time
import uuid
import threading
import gzip
import csv
import io
import logging
from datetime import datetime
from pathlib import Path

from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes as crypto_hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric import rsa, padding as asym_padding
from cryptography.hazmat.primitives.serialization import (
    Encoding, PrivateFormat, PublicFormat, NoEncryption,
    load_pem_private_key, load_pem_public_key,
)

from config import DATA_DIR

SECURITY_DIR = DATA_DIR / "security"
SECURITY_DIR.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger(__name__)

AES_KEY_PATH = SECURITY_DIR / "aes_key.bin"
AES_SALT_PATH = SECURITY_DIR / "aes_salt.bin"
RSA_PRIVATE_PATH = SECURITY_DIR / "rsa_private.pem"
RSA_PUBLIC_PATH = SECURITY_DIR / "rsa_public.pem"
CHAIN_PATH = SECURITY_DIR / "blockchain.json"
AUDIT_LOG_PATH = SECURITY_DIR / "audit.log"
BACKUP_DIR = SECURITY_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

_PASSPHRASE = b"SecureDocAI_Project_2026"
_blockchain_lock = threading.Lock()


# ============================================================
# Audit Logging & Security Events
# ============================================================
def log_audit_event(action: str, details: str):
    """Log standard operational audit details to security/audit.log."""
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{now}] [AUDIT] [{action}] {details}\n"
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(log_line)
    except Exception:
        pass


def log_security_event(event_type: str, details: str):
    """Log critical security events (tampering, invalid sig) to security/audit.log."""
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{now}] [SECURITY_EVENT] [{event_type}] {details}\n"
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(log_line)
    except Exception:
        pass


# ============================================================
# Key bootstrap
# ============================================================
def derive_key(password: bytes, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=crypto_hashes.SHA256(), length=32, salt=salt, iterations=200_000)
    return kdf.derive(password)


def _load_or_create_aes_key() -> bytes:
    if AES_KEY_PATH.exists() and AES_SALT_PATH.exists():
        return AES_KEY_PATH.read_bytes()

    salt = os.urandom(16)
    key = derive_key(_PASSPHRASE, salt)
    AES_SALT_PATH.write_bytes(salt)
    AES_KEY_PATH.write_bytes(key)
    
    # Auto Backup
    try:
        (BACKUP_DIR / "aes_key.bin.bak").write_bytes(key)
        (BACKUP_DIR / "aes_salt.bin.bak").write_bytes(salt)
    except Exception:
        pass
        
    return key


def _load_or_create_rsa_keypair():
    if RSA_PRIVATE_PATH.exists() and RSA_PUBLIC_PATH.exists():
        private_key = load_pem_private_key(RSA_PRIVATE_PATH.read_bytes(), password=None)
        public_key = load_pem_public_key(RSA_PUBLIC_PATH.read_bytes())
        return private_key, public_key

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    
    priv_bytes = private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    pub_bytes = public_key.bytes = public_key.public_bytes(
        Encoding.PEM, 
        PublicFormat.SubjectPublicKeyInfo,
        )
    
    RSA_PRIVATE_PATH.write_bytes(priv_bytes)
    RSA_PUBLIC_PATH.write_bytes(pub_bytes)
    
    # Auto Backup
    try:
        (BACKUP_DIR / "rsa_private.pem.bak").write_bytes(priv_bytes)
        (BACKUP_DIR / "rsa_public.pem.bak").write_bytes(pub_bytes)
    except Exception:
        pass
        
    return private_key, public_key


_AES_KEY = _load_or_create_aes_key()
_RSA_PRIVATE_KEY, _RSA_PUBLIC_KEY = _load_or_create_rsa_keypair()


# ============================================================
# AES-256-GCM Encryption with Optional gzip compression
# ============================================================
def aes_encrypt(plaintext: str, compress: bool = True) -> str:
    """AES-256-GCM encryption with optional gzip compression."""
    t0 = time.perf_counter()
    data = plaintext.encode("utf-8")
    
    if compress:
        data = gzip.compress(data)
        
    nonce = os.urandom(12)
    cipher = Cipher(algorithms.AES(_AES_KEY), modes.GCM(nonce))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(data) + encryptor.finalize()
    auth_tag = encryptor.tag

    payload = nonce + auth_tag + ciphertext
    encrypted_str = base64.b64encode(payload).decode("ascii")
    
    t_elapsed = time.perf_counter() - t0
    log_audit_event("Encryption", f"Encrypted {len(plaintext)} chars (compressed: {compress}) in {t_elapsed*1000:.2f}ms")
    return encrypted_str


def aes_decrypt(token: str) -> str:
    """AES-256-GCM decryption with backward compatibility for non-gzipped payloads."""
    t0 = time.perf_counter()
    payload = base64.b64decode(token)
    nonce = payload[:12]
    auth_tag = payload[12:28]
    ciphertext = payload[28:]

    cipher = Cipher(algorithms.AES(_AES_KEY), modes.GCM(nonce, auth_tag))
    decryptor = cipher.decryptor()
    data = decryptor.update(ciphertext) + decryptor.finalize()
    
    # Check if data is compressed (gzip magic header starts with 1f 8b)
    if data.startswith(b'\x1f\x8b'):
        try:
            data = gzip.decompress(data)
        except Exception:
            pass
            
    decrypted_str = data.decode("utf-8")
    t_elapsed = time.perf_counter() - t0
    log_audit_event("Decryption", f"Decrypted {len(decrypted_str)} chars in {t_elapsed*1000:.2f}ms")
    return decrypted_str


# ============================================================
# RSA-2048 Digital Signatures
# ============================================================
def sign_hash(block_hash: str) -> str:
    signature = _RSA_PRIVATE_KEY.sign(
        block_hash.encode("utf-8"),
        asym_padding.PSS(mgf=asym_padding.MGF1(crypto_hashes.SHA256()),
                          salt_length=asym_padding.PSS.MAX_LENGTH),
        crypto_hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("ascii")


def verify_signature(block_hash: str, signature_b64: str) -> bool:
    try:
        _RSA_PUBLIC_KEY.verify(
            base64.b64decode(signature_b64),
            block_hash.encode("utf-8"),
            asym_padding.PSS(mgf=asym_padding.MGF1(crypto_hashes.SHA256()),
                              salt_length=asym_padding.PSS.MAX_LENGTH),
            crypto_hashes.SHA256(),
        )
        return True
    except Exception:
        return False


# ============================================================
# Block
# ============================================================
class Block:
    def __init__(self, index, timestamp, encrypted_text, language, record_id,
                 previous_hash, signature=None, node_id="Client_01",
                 model_version="SecureIndicHTR_v1", block_version="1.0", device="cpu",
                 file_hashes: dict | None = None, metadata: dict | None = None):
        self.index = index
        self.timestamp = timestamp
        self.encrypted_text = encrypted_text
        self.language = language
        self.record_id = record_id
        self.previous_hash = previous_hash

        self.node_id = node_id
        self.model_version = model_version
        self.block_version = block_version
        self.device = device
        self.commit_id = str(uuid.uuid4())
        
        # V2 Metadata and Hashes
        self.file_hashes = file_hashes or {}
        self.metadata = metadata or {}

        self.hash = self.compute_hash()
        self.signature = signature if signature else sign_hash(self.hash)

    def compute_hash(self) -> str:
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "encrypted_text": self.encrypted_text,
            "language": self.language,
            "record_id": self.record_id,
            "previous_hash": self.previous_hash,
            "node_id": self.node_id,
            "model_version": self.model_version,
            "block_version": self.block_version,
            "device": self.device,
            "commit_id": self.commit_id,
            "file_hashes": self.file_hashes,
            "metadata": self.metadata,
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode("utf-8")).hexdigest()

    def is_signature_valid(self) -> bool:
        return verify_signature(self.hash, self.signature)

    def to_dict(self) -> dict:
        return {
            "index": self.index, "timestamp": self.timestamp,
            "encrypted_text": self.encrypted_text, "language": self.language,
            "record_id": self.record_id, "previous_hash": self.previous_hash,
            "hash": self.hash, "signature": self.signature,
            "node_id": self.node_id, "model_version": self.model_version,
            "block_version": self.block_version, "device": self.device,
            "commit_id": self.commit_id,
            "file_hashes": self.file_hashes, "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(d: dict) -> "Block":
        b = Block(
            d["index"], d["timestamp"], d["encrypted_text"], d["language"], d["record_id"],
            d["previous_hash"], signature=d.get("signature"),
            node_id=d.get("node_id", "Client_01"),
            model_version=d.get("model_version", "SecureIndicHTR_v1"),
            block_version=d.get("block_version", "1.0"),
            device=d.get("device", "cpu"),
            file_hashes=d.get("file_hashes"),
            metadata=d.get("metadata"),
        )
        b.hash = d["hash"]
        b.commit_id = d.get("commit_id", "")
        return b


# ============================================================
# Blockchain
# ============================================================
class Blockchain:
    def __init__(self, chain_file: Path = CHAIN_PATH):
        self.chain_file = Path(chain_file)
        self.chain: list[Block] = []
        self.block_latencies: list[float] = []

        self.load_chain()

    def load_chain(self):
        with _blockchain_lock:
            if self.chain_file.exists():
                try:
                    raw = json.loads(self.chain_file.read_text(encoding="utf-8"))
                    self.chain = [Block.from_dict(b) for b in raw]
                except Exception as e:
                    log_security_event("Corrupt Chain File", f"Error loading blockchain file: {e}. Attempting recovery.")
                    self.recover_from_backup()
            else:
                genesis = Block(0, str(datetime.now()), "GENESIS_BLOCK", "N/A", -1, "0" * 64)
                self.chain.append(genesis)
                self._save_unlocked()

    def latest_block(self) -> Block:
        return self.chain[-1]

    def add_block(self, encrypted_text: str, language: str, record_id,
                  file_hashes: dict | None = None, metadata: dict | None = None) -> Block:
        with _blockchain_lock:
            t0 = time.perf_counter()
            prev = self.latest_block()
            new_block = Block(
                index=prev.index + 1,
                timestamp=str(datetime.now()),
                encrypted_text=encrypted_text,
                language=language,
                record_id=record_id,
                previous_hash=prev.hash,
                file_hashes=file_hashes,
                metadata=metadata
            )
            self.chain.append(new_block)
            self._save_unlocked()
            
            latency = time.perf_counter() - t0
            self.block_latencies.append(latency)
            
            log_audit_event("Block Added", f"Block {new_block.index} saved with record_id {record_id}")
            
            # Backup every 50 blocks
            if new_block.index % 50 == 0:
                self.create_backup()
                
            return new_block

    def _save_unlocked(self):
        self.chain_file.write_text(json.dumps([b.to_dict() for b in self.chain], indent=2), encoding="utf-8")

    def create_backup(self):
        try:
            backup_path = BACKUP_DIR / f"blockchain_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            backup_path.write_text(json.dumps([b.to_dict() for b in self.chain], indent=2), encoding="utf-8")
            log_audit_event("Blockchain Backup", f"Saved backup to {backup_path.name}")
        except Exception as e:
            log_security_event("Backup Error", str(e))

    def recover_from_backup(self):
        try:
            backups = sorted(BACKUP_DIR.glob("blockchain_backup_*.json"), reverse=True)
            if backups:
                latest = backups[0]
                raw = json.loads(latest.read_text(encoding="utf-8"))
                self.chain = [Block.from_dict(b) for b in raw]
                self._save_unlocked()
                log_audit_event("Blockchain Recovery", f"Recovered blockchain from backup {latest.name}")
            else:
                # Re-init genesis if no backup
                genesis = Block(0, str(datetime.now()), "GENESIS_BLOCK", "N/A", -1, "0" * 64)
                self.chain = [genesis]
                self._save_unlocked()
        except Exception as e:
            log_security_event("Recovery Error", str(e))

    def verify_block(self, index: int) -> dict:
        """Verifies a single block's signature and hash alignment."""
        if index < 0 or index >= len(self.chain):
            return {"valid": False, "reason": "Index out of bounds"}
            
        block = self.chain[index]
        if block.index == 0:
            return {"valid": True, "reason": "Genesis Block"}
            
        # Hash integrity
        hash_ok = block.hash == block.compute_hash()
        if not hash_ok:
            return {"valid": False, "reason": "Hash mismatch"}
            
        # Signature authenticity
        sig_ok = block.is_signature_valid()
        if not sig_ok:
            return {"valid": False, "reason": "Signature mismatch"}
            
        # Link integrity
        link_ok = block.previous_hash == self.chain[index - 1].hash
        if not link_ok:
            return {"valid": False, "reason": "Previous hash linkage mismatch"}
            
        return {"valid": True}

    def verify_chain(self) -> dict:
        """Verifies the full chain: per-block hash integrity, RSA signature validity, and previous_hash linkage."""
        data_blocks = [b for b in self.chain if b.index > 0]
        
        tampered_blocks = []
        tampered_reasons = {}
        first_invalid = None
        
        for idx in range(1, len(self.chain)):
            status = self.verify_block(idx)
            if not status["valid"]:
                tampered_blocks.append(idx)
                tampered_reasons[idx] = status["reason"]
                if first_invalid is None:
                    first_invalid = idx
                    
        n = max(1, len(data_blocks))
        hash_ok_count = len(data_blocks) - len([b for b in tampered_blocks if tampered_reasons[b] == "Hash mismatch"])
        sig_ok_count = len(data_blocks) - len([b for b in tampered_blocks if tampered_reasons[b] == "Signature mismatch"])
        link_ok_count = len(self.chain) - 1 - len([b for b in tampered_blocks if "linkage" in tampered_reasons[b]])

        if tampered_blocks:
            log_security_event("Tampering Detected", f"Tampered blocks indices: {tampered_blocks}")

        return {
            "total_blocks": len(self.chain),
            "data_blocks": len(data_blocks),
            "hash_verified_count": hash_ok_count,
            "signature_verified_count": sig_ok_count,
            "link_verified_count": link_ok_count,
            "hash_integrity_pct": round(100 * hash_ok_count / n, 2),
            "signature_integrity_pct": round(100 * sig_ok_count / n, 2),
            "tampered_blocks": tampered_blocks,
            "tampered_reasons": tampered_reasons,
            "first_invalid_block": first_invalid,
            "fully_valid": len(tampered_blocks) == 0,
        }

    def repair_chain(self):
        """Rebuilds the blockchain previous hash linkage and signs all blocks in sequence."""
        with _blockchain_lock:
            for idx in range(1, len(self.chain)):
                block = self.chain[idx]
                block.previous_hash = self.chain[idx - 1].hash
                block.hash = block.compute_hash()
                block.signature = sign_hash(block.hash)
            self._save_unlocked()
            log_audit_event("Chain Repaired", "Rebuilt hash linkages across all blocks.")

    def export_blockchain(self, export_format: str = "json") -> str | bytes:
        """Exports the chain as JSON or formatted CSV."""
        if export_format == "csv":
            out = io.StringIO()
            writer = csv.writer(out)
            writer.writerow(["Index", "Timestamp", "Language", "Record ID", "Hash", "Signature", "Node ID", "Model Version"])
            for b in self.chain:
                writer.writerow([b.index, b.timestamp, b.language, b.record_id, b.hash, b.signature, b.node_id, b.model_version])
            return out.getvalue()
        return json.dumps([b.to_dict() for b in self.chain], indent=2)

    def get_statistics(self) -> dict:
        """Returns statistical metrics of the blockchain."""
        total_lat = sum(self.block_latencies)
        avg_lat = total_lat / len(self.block_latencies) if self.block_latencies else 0.0
        
        largest_size = 0
        total_encrypted_bytes = 0
        for b in self.chain:
            text_size = len(b.encrypted_text.encode('utf-8'))
            total_encrypted_bytes += text_size
            largest_size = max(largest_size, text_size)
            
        return {
            "total_blocks": len(self.chain),
            "average_latency_s": avg_lat,
            "largest_block_bytes": largest_size,
            "encrypted_bytes": total_encrypted_bytes,
        }


# ============================================================
# Security scoring
# ============================================================
def compute_security_score(block: Block, blockchain: Blockchain) -> tuple:
    score, breakdown = 0, {}

    hash_ok = block.hash == block.compute_hash()
    breakdown["hash_integrity"] = 40 if hash_ok else 0
    score += breakdown["hash_integrity"]

    sig_ok = block.is_signature_valid()
    breakdown["signature_authenticity"] = 30 if sig_ok else 0
    score += breakdown["signature_authenticity"]

    enc_ok = len(block.encrypted_text) > 0
    breakdown["encryption_present"] = 15 if enc_ok else 0
    score += breakdown["encryption_present"]

    chain_idx = next((i for i, b in enumerate(blockchain.chain) if b.index == block.index), None)
    linked_ok = (chain_idx is not None and chain_idx > 0 and
                 block.previous_hash == blockchain.chain[chain_idx - 1].hash)
    breakdown["chain_linkage"] = 15 if linked_ok else 0
    score += breakdown["chain_linkage"]

    return score, breakdown


def security_grade(score: float) -> str:
    if score >= 95:
        return "A+"
    if score >= 90:
        return "A"
    if score >= 80:
        return "B+"
    if score >= 70:
        return "B"
    if score >= 60:
        return "C"
    return "D"


def get_security_dashboard(blockchain: Blockchain) -> dict:
    """Assembles security status parameters for visual dashboard reporting."""
    report = blockchain.verify_chain()
    
    total_data = report["data_blocks"]
    tampered_cnt = len(report["tampered_blocks"])
    valid_blocks = total_data - tampered_cnt
    
    score = 100.0 if report["fully_valid"] else max(0.0, 100.0 - (tampered_cnt * 20.0))
    grade = security_grade(score)
    
    return {
        "security_score": score,
        "grade": grade,
        "valid_blocks": valid_blocks,
        "tampered_blocks": report["tampered_blocks"],
        "encrypted_records": total_data,
    }


def get_security_recommendations(blockchain: Blockchain) -> list[str]:
    """Scans chain and returns automated security configuration recommendations."""
    report = blockchain.verify_chain()
    recs = []
    
    if not report["fully_valid"]:
        recs.append("CRITICAL: Tampering detected! Run repair_chain() to check logs.")
    else:
        recs.append("Chain healthy: No block tampering detected.")
        
    # Check backup directory age / count
    backups = list(BACKUP_DIR.glob("blockchain_backup_*.json"))
    if not backups:
        recs.append("Warning: No blockchain backups found. Recommend creating a backup.")
    
    return recs


# ============================================================
# Module-level singleton
# ============================================================
_blockchain_instance = None


def get_blockchain() -> Blockchain:
    global _blockchain_instance
    if _blockchain_instance is None:
        _blockchain_instance = Blockchain()
    return _blockchain_instance


# ============================================================
# Security V2: Image Quality, Fake Detection & Duplicate Check
# ============================================================
def calculate_document_hash(image_bytes: bytes) -> str:
    """Computes SHA-256 integrity hash of document raw bytes."""
    return hashlib.sha256(image_bytes).hexdigest()


def find_document_by_hash(doc_hash: str, blockchain: Blockchain | None = None) -> Block | None:
    """Returns the first blockchain entry that matches a document SHA-256 hash."""
    if not doc_hash:
        return None
    chain = blockchain or get_blockchain()
    for block in getattr(chain, "chain", []):
        if block.index > 0 and block.file_hashes and block.file_hashes.get("sha256") == doc_hash:
            return block
    return None


def estimate_handwriting_difficulty(sharpness: float, uniformity: float, noise: float, mean_confidence: float = 1.0) -> str:
    """Produces a simple handwriting difficulty estimate from image and OCR quality signals."""
    risk_score = 0.0
    if sharpness < 120:
        risk_score += 0.45
    elif sharpness < 250:
        risk_score += 0.25
    if uniformity < 70:
        risk_score += 0.35
    elif uniformity < 85:
        risk_score += 0.18
    if noise > 3.0:
        risk_score += 0.45
    elif noise > 1.2:
        risk_score += 0.20
    if mean_confidence < 0.84:
        risk_score += 0.25
    if risk_score >= 0.9:
        return "Hard"
    if risk_score >= 0.45:
        return "Medium"
    return "Easy"


def log_ocr_benchmark_run(run_data: dict) -> int:
    """Appends one OCR benchmark run to a lightweight JSON log."""
    benchmark_path = SECURITY_DIR / "ocr_benchmark.json"
    runs = []
    if benchmark_path.exists():
        try:
            runs = json.loads(benchmark_path.read_text(encoding="utf-8")) or []
        except Exception:
            runs = []
    runs.append(run_data)
    benchmark_path.write_text(json.dumps(runs, indent=2), encoding="utf-8")
    return len(runs)


def get_ocr_benchmark_summary() -> dict:
    """Returns a compact summary of logged OCR benchmark runs."""
    benchmark_path = SECURITY_DIR / "ocr_benchmark.json"
    if not benchmark_path.exists():
        return {"runs": 0, "avg_confidence": 0.0, "avg_runtime": 0.0, "latest_engine": "None"}
    try:
        runs = json.loads(benchmark_path.read_text(encoding="utf-8")) or []
    except Exception:
        return {"runs": 0, "avg_confidence": 0.0, "avg_runtime": 0.0, "latest_engine": "None"}
    if not runs:
        return {"runs": 0, "avg_confidence": 0.0, "avg_runtime": 0.0, "latest_engine": "None"}
    avg_conf = sum(r.get("confidence", 0.0) for r in runs) / len(runs)
    avg_time = sum(r.get("runtime_seconds", 0.0) for r in runs) / len(runs)
    latest = runs[-1].get("engine", "None")
    return {"runs": len(runs), "avg_confidence": round(avg_conf, 3), "avg_runtime": round(avg_time, 2), "latest_engine": latest}


def calculate_sharpness(image_bytes: bytes) -> float:
    """Computes image sharpness indicator using variance of adjacent gradients."""
    try:
        from PIL import Image, ImageOps
        import numpy as np
        img = Image.open(io.BytesIO(image_bytes))
        gray = ImageOps.grayscale(img)
        arr = np.array(gray, dtype=np.int32)
        dx = arr[:, 1:] - arr[:, :-1]
        dy = arr[1:, :] - arr[:-1, :]
        return float(np.var(dx) + np.var(dy))
    except Exception as e:
        logger.warning(f"Could not calculate sharpness: {e}")
        return 1000.0  # default healthy threshold fallback


def detect_fake_scan(image_bytes: bytes) -> dict:
    """Analyzes image for digital metadata, screenshot compression ratios, and extreme colors."""
    try:
        from PIL import Image, ImageOps
        import numpy as np
        img = Image.open(io.BytesIO(image_bytes))
        
        is_screenshot = False
        reasons = []
        
        # 1. Metadata check
        info = str(img.info).lower()
        for kw in ["screenshot", "adobe", "photoshop", "figma", "canva", "snagit", "gimp"]:
            if kw in info:
                is_screenshot = True
                reasons.append(f"Metadata matches capture/edit tool ({kw})")
                break
                
        # 2. Digital color uniformity check
        gray = ImageOps.grayscale(img)
        arr = np.array(gray)
        total = arr.size
        exact_extremes = np.sum(arr == 255) + np.sum(arr == 0)
        extreme_pct = exact_extremes / total
        if extreme_pct > 0.85:
            is_screenshot = True
            reasons.append(f"Extreme color distribution uniform ({extreme_pct*100:.1f}%)")
            
        # 3. Compression ratio check
        w, h = img.size
        ratio = len(image_bytes) / (w * h)
        if ratio < 0.05:
            is_screenshot = True
            reasons.append("Highly compressed digital screenshot compression profile")
            
        return {
            "is_fake": is_screenshot,
            "reasons": reasons,
            "extreme_pct": extreme_pct,
            "compression_ratio": ratio
        }
    except Exception as e:
        logger.warning(f"Fake scan detection failed: {e}")
        return {"is_fake": False, "reasons": []}


def duplicate_check(image_bytes: bytes, blockchain: Blockchain) -> dict:
    """Checks the blockchain registry to detect duplicate uploads by document hash."""
    file_hash = calculate_document_hash(image_bytes)
    for b in blockchain.chain:
        if b.index > 0:
            existing_hash = b.file_hashes.get("sha256")
            if existing_hash == file_hash:
                return {
                    "is_duplicate": True,
                    "record_id": b.record_id,
                    "filename": b.metadata.get("original_filename", "Unknown Document"),
                    "hash": file_hash
                }
    return {"is_duplicate": False, "hash": file_hash}


VERSIONS_DIR = SECURITY_DIR / "versions"
VERSIONS_DIR.mkdir(parents=True, exist_ok=True)


def save_document_version(file_id: str, text: str):
    """Saves a new encrypted version revision for a document."""
    try:
        version_file = VERSIONS_DIR / f"{file_id}.json"
        versions = []
        if version_file.exists():
            try:
                versions = json.loads(version_file.read_text(encoding="utf-8"))
            except Exception:
                versions = []
                
        new_version_num = len(versions) + 1
        versions.append({
            "version": new_version_num,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "encrypted_text": aes_encrypt(text)
        })
        version_file.write_text(json.dumps(versions, indent=2), encoding="utf-8")
        log_audit_event("Version Created", f"Document {file_id} saved version {new_version_num}")
    except Exception as e:
        logger.warning(f"Could not save document version: {e}")


def get_document_versions(file_id: str, default_text: str = "") -> list[dict]:
    """Loads and decrypts all version revisions for a document."""
    try:
        version_file = VERSIONS_DIR / f"{file_id}.json"
        if not version_file.exists() and default_text:
            save_document_version(file_id, default_text)
            
        if not version_file.exists():
            return []
            
        versions = json.loads(version_file.read_text(encoding="utf-8"))
        decrypted_versions = []
        for v in versions:
            try:
                decrypted_versions.append({
                    "version": v["version"],
                    "timestamp": v["timestamp"],
                    "text": aes_decrypt(v["encrypted_text"])
                })
            except Exception:
                pass
        return decrypted_versions
    except Exception as e:
        logger.warning(f"Could not read document versions: {e}")
        return []


SHARES_FILE = SECURITY_DIR / "shares.json"


def create_share_link(file_id: str, filename: str, drive_name: str, password: str | None = None, expire_hours: int = 24, one_time: bool = False) -> str:
    """Generates a secure share link metadata record and returns the share token."""
    try:
        shares = {}
        if SHARES_FILE.exists():
            try:
                shares = json.loads(SHARES_FILE.read_text(encoding="utf-8"))
            except Exception:
                shares = {}
                
        share_id = str(uuid.uuid4())[:12]  # compact readable token
        expiration_time = time.time() + (expire_hours * 3600)
        
        # Hash password if provided to verify on login
        hashed_pass = None
        if password:
            hashed_pass = hashlib.sha256(password.encode("utf-8")).hexdigest()
            
        shares[share_id] = {
            "share_id": share_id,
            "file_id": file_id,
            "filename": filename,
            "drive_name": drive_name,
            "expiration": expiration_time,
            "password_hash": hashed_pass,
            "one_time": one_time,
            "downloaded": False
        }
        SHARES_FILE.write_text(json.dumps(shares, indent=2), encoding="utf-8")
        log_audit_event("Share Link Created", f"File {filename} shared with link {share_id}")
        return share_id
    except Exception as e:
        logger.warning(f"Could not create share link: {e}")
        return ""


def validate_share_link(share_id: str) -> dict:
    """Verifies if a share link exists, is not expired, and complies with download policies."""
    try:
        if not SHARES_FILE.exists():
            return {"valid": False, "reason": "No active share links found"}
            
        shares = json.loads(SHARES_FILE.read_text(encoding="utf-8"))
        if share_id not in shares:
            return {"valid": False, "reason": "Invalid or non-existent share link"}
            
        record = shares[share_id]
        if time.time() > record["expiration"]:
            return {"valid": False, "reason": "This secure link has expired (24-hour limit reached)"}
            
        if record.get("one_time") and record.get("downloaded"):
            return {"valid": False, "reason": "This one-time download link has already been claimed"}
            
        return {"valid": True, "record": record}
    except Exception as e:
        logger.warning(f"Share link validation failed: {e}")
        return {"valid": False, "reason": "Could not validate link"}


def consume_share_link(share_id: str):
    """Marks a one-time download link as claimed."""
    try:
        if not SHARES_FILE.exists():
            return
        shares = json.loads(SHARES_FILE.read_text(encoding="utf-8"))
        if share_id in shares:
            shares[share_id]["downloaded"] = True
            SHARES_FILE.write_text(json.dumps(shares, indent=2), encoding="utf-8")
            log_audit_event("Share Link Consumed", f"Link {share_id} was claimed")
    except Exception as e:
        logger.warning(f"Could not consume share link: {e}")


OCR_LEARNING_FILE = SECURITY_DIR / "ocr_learning.json"


def learn_ocr_corrections(original: str, edited: str):
    """Learns correction patterns from raw OCR text and user-corrected edits."""
    try:
        if not original or not edited or original.strip() == edited.strip():
            return
            
        import difflib
        orig_words = original.split()
        edit_words = edited.split()
        
        matcher = difflib.SequenceMatcher(None, orig_words, edit_words)
        corrections = {}
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "replace":
                orig_sub = orig_words[i1:i2]
                edit_sub = edit_words[j1:j2]
                if len(orig_sub) == len(edit_sub):
                    for w_orig, w_edit in zip(orig_sub, edit_sub):
                        w_orig_clean = w_orig.strip(".,;:?!()\"'-").lower()
                        w_edit_clean = w_edit.strip(".,;:?!()\"'-")
                        if w_orig_clean and w_edit_clean and w_orig_clean != w_edit_clean.lower():
                            corrections[w_orig_clean] = w_edit_clean
                            
        if not corrections:
            return
            
        learned = {}
        if OCR_LEARNING_FILE.exists():
            try:
                learned = json.loads(OCR_LEARNING_FILE.read_text(encoding="utf-8"))
            except Exception:
                learned = {}
                
        learned.update(corrections)
        OCR_LEARNING_FILE.write_text(json.dumps(learned, indent=2, ensure_ascii=False), encoding="utf-8")
        log_audit_event("OCR Learned", f"Learned {len(corrections)} word correction mappings")
    except Exception as e:
        logger.warning(f"Failed to learn OCR corrections: {e}")


def apply_learned_ocr_corrections(text: str) -> str:
    """Applies learned corrections dynamically to the raw OCR output."""
    try:
        if not text or not OCR_LEARNING_FILE.exists():
            return text
            
        learned = json.loads(OCR_LEARNING_FILE.read_text(encoding="utf-8"))
        if not learned:
            return text
            
        words = text.split()
        for idx, w in enumerate(words):
            cleaned = w.strip(".,;:?!()\"'-").lower()
            if cleaned in learned:
                replacement = learned[cleaned]
                left_punct = ""
                for char in w:
                    if char in ".,;:?!()\"'-":
                        left_punct += char
                    else:
                        break
                right_punct = ""
                for char in reversed(w):
                    if char in ".,;:?!()\"'-":
                        right_punct = char + right_punct
                    else:
                        break
                words[idx] = left_punct + replacement + right_punct
                
        return " ".join(words)
    except Exception as e:
        logger.warning(f"Failed to apply learned OCR corrections: {e}")
        return text


def calculate_lighting_uniformity(image_bytes: bytes) -> float:
    """Estimates lighting uniformity (checking for shadows). Returns percentage (0.0 to 100.0)."""
    try:
        from PIL import Image, ImageStat
        import io
        img = Image.open(io.BytesIO(image_bytes)).convert("L")
        w, h = img.size
        quads = [
            img.crop((0, 0, w//2, h//2)),
            img.crop((w//2, 0, w, h//2)),
            img.crop((0, h//2, w//2, h)),
            img.crop((w//2, h//2, w, h))
        ]
        means = [ImageStat.Stat(q).mean[0] for q in quads]
        max_mean = max(means)
        min_mean = min(means)
        if max_mean == 0:
            return 100.0
        uniformity = (min_mean / max_mean) * 100.0
        return min(100.0, max(0.0, uniformity))
    except Exception:
        return 92.5


def calculate_noise_ratio(image_bytes: bytes) -> float:
    """Estimates high-frequency noise ratio using pixel deviation. Returns percentage (0.0 to 100.0)."""
    try:
        from PIL import Image, ImageFilter, ImageStat
        import io
        img = Image.open(io.BytesIO(image_bytes)).convert("L")
        blurred = img.filter(ImageFilter.GaussianBlur(1.0))
        from PIL import ImageChops
        diff = ImageChops.difference(img, blurred)
        stddev = ImageStat.Stat(diff).stddev[0]
        noise_pct = (stddev / 128.0) * 100.0
        return min(100.0, max(0.0, noise_pct))
    except Exception:
        return 1.2


def parse_template_fields(text: str) -> dict | None:
    """Detects Aadhaar or PAN card templates and parses key fields."""
    import re
    if not text:
        return None
        
    text_lower = text.lower()
    
    # 1. Aadhaar Card
    if "aadhaar" in text_lower or "unique identification" in text_lower or re.search(r"\b\d{4}\s\d{4}\s\d{4}\b", text):
        parsed = {"template": "Aadhaar Card"}
        
        num_match = re.search(r"\b\d{4}\s\d{4}\s\d{4}\b", text)
        if num_match:
            parsed["Aadhaar Number"] = num_match.group(0)
            
        dob_match = re.search(r"(?:dob|date of birth|birth)\s*[:\-]*\s*(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
        if dob_match:
            parsed["Date of Birth"] = dob_match.group(1)
            
        gender_match = re.search(r"\b(male|female|transgender)\b", text, re.IGNORECASE)
        if gender_match:
            parsed["Gender"] = gender_match.group(1).capitalize()
            
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        for idx, line in enumerate(lines):
            if "dob" in line.lower() or "date of birth" in line.lower():
                if idx > 0 and len(lines[idx-1].split()) <= 4:
                    parsed["Full Name"] = lines[idx-1]
                break
                
        return parsed
        
    # 2. PAN Card
    elif "income tax" in text_lower or "permanent account" in text_lower or re.search(r"\b[A-Z]{5}\d{4}[A-Z]\b", text):
        parsed = {"template": "Permanent Account (PAN) Card"}
        
        pan_match = re.search(r"\b[A-Z]{5}\d{4}[A-Z]\b", text)
        if pan_match:
            parsed["PAN Number"] = pan_match.group(0)
            
        dob_match = re.search(r"(?:dob|date of birth|birth|date)\s*[:\-]*\s*(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
        if dob_match:
            parsed["Date of Birth"] = dob_match.group(1)
            
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        for idx, line in enumerate(lines):
            if "father" in line.lower():
                if idx > 0:
                    parsed["Father's Name"] = lines[idx-1]
                if idx > 1:
                    parsed["Full Name"] = lines[idx-2]
                break
        if "Full Name" not in parsed:
            for idx, line in enumerate(lines):
                if re.match(r"^[A-Z\s]+$", line) and "INCOME" not in line and "TAX" not in line and "GOVT" not in line:
                    parsed["Full Name"] = line
                    break
                    
        return parsed
        
    return None


def calculate_camera_guidance(image_bytes: bytes) -> dict:
    """Evaluates a captured camera frame and provides real-time guidance feedback."""
    try:
        from PIL import Image
        import io
        import numpy as np
        img = Image.open(io.BytesIO(image_bytes))
        gray = img.convert("L")
        arr = np.array(gray)
        mean_brightness = float(np.mean(arr))
        
        # Calculate sharpness using Laplacians
        import cv2
        laplacian_var = float(cv2.Laplacian(arr, cv2.CV_64F).var())
        
        status = "Optimal focus and lighting ✓"
        recs = []
        if mean_brightness < 90:
            status = "Low Light Warning ⚠️"
            recs.append("Increase external light or flash.")
        elif mean_brightness > 225:
            status = "High Glare Warning ⚠️"
            recs.append("Reposition document to avoid reflections.")
            
        if laplacian_var < 100:
            status = "Motion Blur / Out of Focus 🚨"
            recs.append("Hold the camera steady and move closer to the document.")
            
        if not recs:
            recs.append("Hold document in frame and start scanning.")
            
        return {
            "status": status,
            "recs": recs,
            "brightness": mean_brightness,
            "sharpness": laplacian_var
        }
    except Exception:
        return {
            "status": "Ready",
            "recs": ["Hold document in frame and start scanning."],
            "brightness": 128.0,
            "sharpness": 200.0
        }





