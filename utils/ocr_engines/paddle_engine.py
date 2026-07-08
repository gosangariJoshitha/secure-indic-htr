"""
utils/ocr_engines/paddle_engine.py
==================================
Runs PaddleOCR engine for printed text and mixed document layouts.
"""

import time
from PIL import Image
import numpy as np
from utils.ocr_result import OCRResult
from utils.layout_pipeline import LayoutDocument, Block, BlockType, RecognizedLine, Alignment

_PADDLE_READER = None

def run(image: Image.Image, language: str | None = None) -> OCRResult:
    global _PADDLE_READER
    t_start = time.time()
    
    try:
        from paddleocr import PaddleOCR
    except ImportError:
        raise ImportError("PaddleOCR package is not installed. Please install 'paddleocr'.")
        
    if _PADDLE_READER is None:
        lang_code = 'en'
        if language:
            l = language.lower()
            if l.startswith('h'):
                lang_code = 'hi'
            elif l.startswith('t'):
                lang_code = 'te'
        # Lazy initialization
        _PADDLE_READER = PaddleOCR(use_angle_cls=True, lang=lang_code, show_log=False, enable_mkldnn=False)
        
    img_arr = np.array(image.convert("RGB"))
    img_cv = img_arr[:, :, ::-1] # RGB to BGR
    
    result = _PADDLE_READER.ocr(img_cv, cls=True)
    
    blocks = []
    text_lines = []
    confidences = []
    
    if result and result[0]:
        for line in result[0]:
            box = line[0]
            text, conf = line[1]
            text_lines.append(text)
            confidences.append(conf)
            
            top_y = int(min(pt[1] for pt in box))
            rl = RecognizedLine(text=text, alignment=Alignment.LEFT, y=top_y, confidence=conf)
            blocks.append(Block(type=BlockType.PARAGRAPH, lines=[rl]))
            
    plain_text = "\n".join(text_lines)
    mean_conf = sum(confidences) / len(confidences) if confidences else 0.0
    
    doc = LayoutDocument(
        blocks=blocks,
        page_width=image.width,
        page_height=image.height,
        mean_confidence=mean_conf,
        char_count=len(plain_text)
    )
    
    t_elapsed = time.time() - t_start
    return OCRResult(
        text=plain_text,
        confidence=mean_conf,
        language=language or "Auto",
        engine="PaddleOCR",
        processing_time=t_elapsed,
        layout=doc,
        word_confidences=confidences
    )
