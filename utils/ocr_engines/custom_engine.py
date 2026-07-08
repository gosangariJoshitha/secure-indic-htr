"""
utils/ocr_engines/custom_engine.py
==================================
Runs the custom PyTorch character-reconstruction HTR engine.
"""

import time
from PIL import Image
from utils.layout_pipeline import run_layout_pipeline, LayoutDocument
from utils.ocr_result import OCRResult

def run(image: Image.Image, language: str | None = None, enhanced: bool = False, segmentation_params: dict | None = None) -> OCRResult:
    t_start = time.time()
    
    # Run the custom layout pipeline
    doc, overlay = run_layout_pipeline(
        image, 
        enhanced=enhanced, 
        language=language, 
        segmentation_params=segmentation_params
    )
    
    t_elapsed = time.time() - t_start
    setattr(doc, "processing_time", t_elapsed)
    
    return OCRResult(
        text=doc.plain_text,
        confidence=doc.mean_confidence,
        language=language or "Auto",
        engine="Custom AI",
        processing_time=t_elapsed,
        layout=doc,
        metadata={"overlay": overlay},
        word_confidences=[doc.mean_confidence]
    )
