"""
utils/ocr_result.py
===================
Standardized OCR result data structure used across all OCR engines.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from utils.layout_pipeline import LayoutDocument

@dataclass
class OCRResult:
    text: str
    confidence: float
    language: str
    engine: str
    fallback_used: bool = False
    fallback_reason: str = ""
    processing_time: float = 0.0
    layout: LayoutDocument = field(default_factory=LayoutDocument)
    metadata: dict = field(default_factory=dict)
    word_confidences: list[float] = field(default_factory=list)

    @property
    def engine_name(self) -> str:
        return self.engine

    @property
    def engine_version(self) -> str:
        return "2.0"

    @property
    def bounding_boxes(self) -> list:
        return self.metadata.get("bounding_boxes", [])
