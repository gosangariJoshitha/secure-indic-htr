"""
utils/search.py
================
Full-text search, regex search, whole word matching, fuzzy string search,
highlighting, block/table query lookups, and search history queue.
"""

from __future__ import annotations

import re
import difflib
from typing import Any

# Re-use the existing search index for page navigation mapping
_SEARCH_INDEX = [
    {"label": "Dashboard — Home overview", "page": "Dashboard", "keywords": ["dashboard", "home", "overview", "stats"]},
    {"label": "OCR — Scan or upload a document", "page": "OCR", "keywords": ["ocr", "scan", "upload", "camera", "document", "recognize", "handwriting"]},
    {"label": "Privacy — Sensitive data detection", "page": "Privacy", "keywords": ["privacy", "aadhaar", "pan", "phone", "email", "redact", "sensitive", "compliance"]},
    {"label": "Security — Encryption & blockchain", "page": "Security", "keywords": ["security", "encrypt", "aes", "rsa", "blockchain", "hash", "sign", "verify", "tamper"]},
    {"label": "Reports — OCR, privacy, evaluation reports", "page": "Reports", "keywords": ["report", "reports", "export", "evaluation", "accuracy"]},
    {"label": "History — Your saved documents", "page": "History", "keywords": ["history", "library", "saved", "documents", "search", "delete"]},
    {"label": "Settings — Account & preferences", "page": "Settings", "keywords": ["settings", "account", "drive", "connect", "theme", "model", "preferences"]},
    {"label": "About — Project & architecture", "page": "About", "keywords": ["about", "architecture", "phases", "technology", "stack"]},
]

_SEARCH_HISTORY: list[str] = []


def search_pages(query: str) -> list:
    """Returns matching entries from _SEARCH_INDEX for navigation page search."""
    query = query.strip().lower()
    if not query:
        return []

    # Cache search query to history
    if query not in _SEARCH_HISTORY:
        _SEARCH_HISTORY.insert(0, query)
        del _SEARCH_HISTORY[10:] # Limit history size

    results = []
    for entry in _SEARCH_INDEX:
        haystack = entry["label"].lower() + " " + " ".join(entry["keywords"])
        if query in haystack:
            results.append(entry)
    return results


def get_search_history() -> list[str]:
    """Returns the search history list of queries."""
    return _SEARCH_HISTORY


# ============================================================
# V2 Advanced Document & OCR Text Search
# ============================================================
def search_text(
    text: str,
    query: str,
    case_sensitive: bool = False,
    use_regex: bool = False,
    whole_word: bool = False,
    fuzzy: bool = False,
    fuzzy_threshold: float = 0.6
) -> list[dict[str, Any]]:
    """
    Searches a block of text and returns a list of match dictionaries containing:
    - start: character index
    - end: character index
    - match: exact text match
    - snippet: context snippet with HTML bold highlight tags
    """
    matches = []
    if not query:
        return matches

    if fuzzy:
        # Simple fuzzy line-level matching
        lines = text.splitlines()
        char_idx = 0
        for line in lines:
            words = line.split()
            for word in words:
                ratio = difflib.SequenceMatcher(None, query.lower(), word.lower()).ratio()
                if ratio >= fuzzy_threshold:
                    match_start = line.find(word)
                    snippet_start = max(0, match_start - 30)
                    snippet_end = min(len(line), match_start + len(word) + 30)
                    snippet = (
                        line[snippet_start:match_start] +
                        f"<mark>{line[match_start:match_start + len(word)]}</mark>" +
                        line[match_start + len(word):snippet_end]
                    )
                    matches.append({
                        "start": char_idx + match_start,
                        "end": char_idx + match_start + len(word),
                        "match": word,
                        "snippet": snippet,
                        "confidence": ratio
                    })
            char_idx += len(line) + 1
        return matches

    # Compile search pattern
    flags = 0 if case_sensitive else re.IGNORECASE
    pattern_str = re.escape(query) if not use_regex else query
    
    if whole_word and not use_regex:
        pattern_str = f"\\b{pattern_str}\\b"

    try:
        pattern = re.compile(pattern_str, flags)
    except re.error:
        # Fallback if invalid regex was input
        pattern = re.compile(re.escape(query), flags)

    for m in pattern.finditer(text):
        start, end = m.span()
        # Create context snippet (up to 30 chars before and after match)
        snippet_start = max(0, start - 30)
        snippet_end = min(len(text), end + 30)
        
        snippet = (
            text[snippet_start:start] +
            f"<mark>{text[start:end]}</mark>" +
            text[end:snippet_end]
        ).replace("\n", " ")

        matches.append({
            "start": start,
            "end": end,
            "match": m.group(),
            "snippet": snippet,
            "confidence": 1.0
        })

    return matches


def search_document(
    doc: Any,
    query: str,
    case_sensitive: bool = False,
    use_regex: bool = False,
    whole_word: bool = False,
    fuzzy: bool = False
) -> dict[str, Any]:
    """
    Searches an entire LayoutDocument and returns matches separated by:
    - total_matches: int
    - findings: list of matched items (containing page, block_idx, text_match, snippet)
    - table_findings: list of matched cells inside tables
    """
    findings = []
    table_findings = []
    total = 0

    blocks = getattr(doc, "blocks", [])
    for block_idx, block in enumerate(blocks):
        block_text = ""
        # Check if block has lines or if it is a table
        if block.type.name == "TABLE":
            # Scan cell rows
            rows = block.metadata.get("table_data", [])
            for row_idx, row in enumerate(rows):
                for col_idx, cell in enumerate(row):
                    cell_text = str(cell)
                    cell_matches = search_text(
                        cell_text, query, case_sensitive, use_regex, whole_word, fuzzy
                    )
                    for m in cell_matches:
                        table_findings.append({
                            "row": row_idx,
                            "column": col_idx,
                            "match": m["match"],
                            "snippet": f"Table Row {row_idx+1}, Col {col_idx+1}: {m['snippet']}"
                        })
                        total += 1
            continue

        # Standard text blocks
        block_text = "\n".join(line.text for line in block.lines if line.text)
        block_matches = search_text(
            block_text, query, case_sensitive, use_regex, whole_word, fuzzy
        )
        for m in block_matches:
            findings.append({
                "block_index": block_idx,
                "block_type": block.type.name,
                "match": m["match"],
                "snippet": m["snippet"]
            })
            total += 1

    return {
        "total_matches": total,
        "findings": findings,
        "table_findings": table_findings
    }


def replace_text(
    text: str,
    query: str,
    replacement: str,
    case_sensitive: bool = False,
    use_regex: bool = False,
    whole_word: bool = False
) -> tuple[str, int]:
    """Replaces matched occurrences with replacement text and returns (new_text, count_replaced)."""
    if not query:
        return text, 0

    flags = 0 if case_sensitive else re.IGNORECASE
    pattern_str = re.escape(query) if not use_regex else query
    if whole_word and not use_regex:
        pattern_str = f"\\b{pattern_str}\\b"

    pattern = re.compile(pattern_str, flags)
    new_text, count = pattern.subn(replacement, text)
    return new_text, count
