"""
utils/constants.py
===================
Maps the symbolic label names found in models/label_map.json (e.g.
"Hindi_character_1_ka", "Telugu_kha") to the ACTUAL Unicode glyph the
model predicted (क, ఖ, ...).

Two label families exist in this project's label_map.json:

  1. HINDI (Devanagari) — 36 consonants + 10 digits. This is the standard
     DHCD (Devanagari Handwritten Character Dataset) naming scheme, so the
     mapping below is exact, not a guess.

  2. TELUGU — 381 labels following a `<consonant><vowel-suffix>` pattern,
     e.g. "ka" = క (base "k" + inherent "a"), "kaa" = కా (+ vowel sign ా),
     "ki" = కి, etc. This is reconstructed algorithmically: a base-consonant
     table + a vowel-suffix table are combined to build every syllable.

If your training notebook used a slightly different transliteration
convention for any specific Telugu syllables, fix it in TELUGU_OVERRIDES
below rather than editing the generator logic — overrides always win.
"""

from __future__ import annotations

# ============================================================
# HINDI (Devanagari) — exact DHCD scheme
# ============================================================
HINDI_CHARACTER_MAP = {
    "Hindi_character_1_ka": "क",
    "Hindi_character_2_kha": "ख",
    "Hindi_character_3_ga": "ग",
    "Hindi_character_4_gha": "घ",
    "Hindi_character_5_kna": "ङ",
    "Hindi_character_6_cha": "च",
    "Hindi_character_7_chha": "छ",
    "Hindi_character_8_ja": "ज",
    "Hindi_character_9_jha": "झ",
    "Hindi_character_10_yna": "ञ",
    "Hindi_character_11_taamatar": "ट",
    "Hindi_character_12_thaa": "ठ",
    "Hindi_character_13_daa": "ड",
    "Hindi_character_14_dhaa": "ढ",
    "Hindi_character_15_adna": "ण",
    "Hindi_character_16_tabala": "त",
    "Hindi_character_17_tha": "थ",
    "Hindi_character_18_da": "द",
    "Hindi_character_19_dha": "ध",
    "Hindi_character_20_na": "न",
    "Hindi_character_21_pa": "प",
    "Hindi_character_22_pha": "फ",
    "Hindi_character_23_ba": "ब",
    "Hindi_character_24_bha": "भ",
    "Hindi_character_25_ma": "म",
    "Hindi_character_26_yaw": "य",
    "Hindi_character_27_ra": "र",
    "Hindi_character_28_la": "ल",
    "Hindi_character_29_waw": "व",
    "Hindi_character_30_motosaw": "श",
    "Hindi_character_31_petchiryakha": "ष",
    "Hindi_character_32_patalosaw": "स",
    "Hindi_character_33_ha": "ह",
    "Hindi_character_34_chhya": "क्ष",
    "Hindi_character_35_tra": "त्र",
    "Hindi_character_36_gya": "ज्ञ",
    "Hindi_digit_0": "0",
    "Hindi_digit_1": "1",
    "Hindi_digit_2": "2",
    "Hindi_digit_3": "3",
    "Hindi_digit_4": "4",
    "Hindi_digit_5": "5",
    "Hindi_digit_6": "6",
    "Hindi_digit_7": "7",
    "Hindi_digit_8": "8",
    "Hindi_digit_9": "9",
}

# ============================================================
# TELUGU — base consonants (independent / inherent-"a" form)
# ============================================================
TELUGU_CONSONANTS = {
    "k": "క", "kh": "ఖ", "g": "గ", "gh": "ఘ",
    "c": "చ", "ch": "చ", "chh": "ఛ",
    "j": "జ", "jh": "ఝ", "jna": "జ్ఞ",
    "t": "త", "th": "థ", "d": "ద", "dh": "ధ",
    "tt": "ట", "dd": "డ",
    "n": "న", "nn": "ణ",
    "p": "ప", "ph": "ఫ", "P": "ప", "Ph": "ఫ",
    "b": "బ", "bh": "భ",
    "m": "మ",
    "y": "య",
    "r": "ర", "R": "ఱ", "rr": "ర్ర",
    "l": "ల", "ll": "ళ",
    "v": "వ",
    "sh": "శ", "s": "స",
    "h": "హ",
    "ks": "క్స", "ksh": "క్ష",
    "z": "జ",
}

# Independent (non-consonant-attached) vowels, used when the label has no
# consonant prefix at all — e.g. "Telugu_a" -> అ, "Telugu_ii" -> ఈ.
TELUGU_INDEPENDENT_VOWELS = {
    "a": "అ", "aa": "ఆ", "i": "ఇ", "ii": "ఈ",
    "u": "ఉ", "uu": "ఊ", "e": "ఎ", "ee": "ఏ",
    "ai": "ఐ", "o": "ఒ", "oo": "ఓ", "ou": "ఔ",
    "am": "అం", "ah": "అః",
    "RRA": "ఋ", "RRI": "ఋ", "RRII": "ౠ",
    "RRU": "ఋ", "RRUU": "ౠ",
}

# Vowel signs (matras) attached AFTER a consonant — e.g. క + ా = కా
TELUGU_VOWEL_SIGNS = {
    "a": "",        # inherent vowel — no visible sign needed
    "aa": "ా",
    "i": "ి",
    "ii": "ీ",
    "u": "ు",
    "uu": "ూ",
    "e": "ె",
    "ee": "ే",
    "ai": "ై",
    "o": "ొ",
    "oo": "ో",
    "ou": "ౌ",
    "ow": "ౌ",
    "m": "ం",        # anusvara
    "h": "ః",        # visarga
    "n": "న్",        # consonant cluster marker (approximate)
    "nm": "న్మ్",
    "nn": "న్న",
    "r": "ర్",
    "ru": "్రు",
    "ruu": "్రూ",
    "rm": "ర్మ్",
}

# Any label whose exact rendering doesn't follow the generic
# consonant+vowel-sign rule below. These ALWAYS take priority.
TELUGU_OVERRIDES = {
    "Telugu_jna": "జ్ఞ",
    "Telugu_ksh": "క్ష",
    "Telugu_ksha": "క్ష",

    # "an<vowel>" labels = న (na) + vowel sign, e.g. "ana" -> న + ా = నా
    "Telugu_an": "న్",
    "Telugu_ana": "నా",
    "Telugu_anah": "నః",
    "Telugu_anai": "నై",
    "Telugu_ane": "నె",
    "Telugu_anee": "నే",
    "Telugu_ani": "ని",
    "Telugu_anii": "నీ",
    "Telugu_anm": "న్మ్",
    "Telugu_ano": "నొ",
    "Telugu_anoo": "నో",
    "Telugu_anou": "నౌ",
    "Telugu_anr": "న్ర్",
    "Telugu_anru": "న్రు",
    "Telugu_anu": "ను",
    "Telugu_anuu": "నూ",
    "Telugu_ao": "నౌ",

    # "<cons>au" — diphthong vowel-sign variant (ౌ), separate from "ou"
    "Telugu_bau": "బౌ",
    "Telugu_bhau": "భౌ",

    # "<cons>aha" — visarga-attached form (consonant + అః style ending)
    "Telugu_gaha": "గః",
    "Telugu_ghaha": "ఘః",
    "Telugu_kaha": "కః",
    "Telugu_khaha": "ఖః",
    "Telugu_taha": "తః",
}


def _build_telugu_map() -> dict[str, str]:
    """
    Generates the full Telugu_<suffix> -> glyph table by combining
    TELUGU_CONSONANTS with TELUGU_VOWEL_SIGNS, falling back to
    TELUGU_INDEPENDENT_VOWELS for vowel-only labels.
    """
    table: dict[str, str] = {}

    # Independent vowels first (labels with no consonant, e.g. "Telugu_a")
    for suffix, glyph in TELUGU_INDEPENDENT_VOWELS.items():
        table[f"Telugu_{suffix}"] = glyph

    # Consonant + vowel-sign combinations, longest consonant prefix wins
    # (so "kh" + "a" is tried before "k" + "ha").
    sorted_consonants = sorted(TELUGU_CONSONANTS.keys(), key=len, reverse=True)

    # We need every actual suffix seen in the label map, but constants.py
    # has no import on label_map.json by design (keeps this module pure/
    # offline-testable) — so instead we generate the full cartesian
    # product of consonants x vowel-signs, which covers every pattern
    # observed (ka, kaa, ki, kii, ku, kuu, ke, kee, kai, ko, koo, kou,
    # kam, kah, kru, kruu, etc.) plus a few extra combos that are simply
    # unused by label_map.json and ignored.
    extra_suffixes = {
        "ah": "ః", "am": "ం",
        "ru": "్రు", "ruu": "్రూ", "rm": "ర్మ్",
        "m": "్మ్", "n": "్న్", "nm": "్న్మ్",
    }
    all_vowel_signs = {**TELUGU_VOWEL_SIGNS, **extra_suffixes}

    for cons, cons_glyph in TELUGU_CONSONANTS.items():
        for suffix, sign_glyph in all_vowel_signs.items():
            label = f"Telugu_{cons}{suffix}"
            if label not in table:  # don't clobber independent-vowel entries
                table[label] = cons_glyph + sign_glyph

        # Bare consonant labels too (e.g. "Telugu_k" meaning the half-form)
        table.setdefault(f"Telugu_{cons}", cons_glyph)

    # Overrides always win
    table.update(TELUGU_OVERRIDES)
    return table


TELUGU_CHARACTER_MAP: dict[str, str] = _build_telugu_map()

# ============================================================
# Combined lookup used by utils/predictor.py
# ============================================================
LABEL_TO_GLYPH: dict[str, str] = {**HINDI_CHARACTER_MAP, **TELUGU_CHARACTER_MAP}


def label_to_char(label: str) -> str:
    """
    Converts one model label (e.g. 'Hindi_character_1_ka', 'Telugu_kaa')
    into its real Unicode character/syllable. Falls back to a bracketed
    tag for any label this table doesn't yet cover, so nothing silently
    disappears — missing entries are easy to spot and add here.
    """
    return LABEL_TO_GLYPH.get(label, f"[{label}]")


# ============================================================
# V2 Application-level configuration constants
# ============================================================
APP_NAME = "SecureDocAI"
APP_VERSION = "2.0.0"

# OCR Settings
OCR_ENGINES = ["auto", "printed", "handwritten"]
SUPPORTED_LANGUAGES = ["Hindi", "Telugu", "Mixed", "Auto"]
DEFAULT_OCR_SETTINGS = {
    "use_v2_preprocess": True,
    "use_v2_word_gap": True,
    "use_watershed": True,
    "word_gap_multiplier": 2.5
}

# File type filters
SUPPORTED_IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".tiff", ".bmp"]
SUPPORTED_DOCUMENT_EXTENSIONS = [".pdf"]
SUPPORTED_EXPORT_FORMATS = ["txt", "md", "html", "docx", "pdf", "json", "xml", "csv", "xlsx", "zip"]

# Security & Compliance Constants
SECURITY_GRADES = ["A+", "A", "B+", "B", "C", "D"]
PRIVACY_STATUS_LEVELS = ["Safe", "Warning", "Critical"]
COMPLIANCE_STANDARDS = ["GDPR", "DPDP", "HIPAA", "ISO27001"]

# Notification Category Constants
NOTIFICATION_KIND_INFO = "info"
NOTIFICATION_KIND_SUCCESS = "success"
NOTIFICATION_KIND_WARNING = "warning"
NOTIFICATION_KIND_ERROR = "error"

# UI / Message template strings
SUCCESS_LOGIN = "Logged in successfully."
SUCCESS_SIGNUP = "Account created. Please check your email to verify your account."
ERROR_NO_CONNECTION = "No internet connection detected."
