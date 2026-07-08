"""
utils/ocr_engines/easy_engine.py
================================
Runs EasyOCR engine for camera images and noisy scans.
"""

import time
from PIL import Image
import numpy as np
from utils.ocr_result import OCRResult
from utils.layout_pipeline import LayoutDocument, Block, BlockType, RecognizedLine, Alignment

_EASY_READER = None

_EASY_READERS = {}

def run(image: Image.Image, language: str | None = None) -> OCRResult:
    global _EASY_READERS
    t_start = time.time()
    
    try:
        import easyocr
    except ImportError:
        raise ImportError("EasyOCR package is not installed. Please install 'easyocr'.")
        
    lang_codes = ['en']
    if language:
        l = language.lower()
        if 'te' in l or 'tel' in l:
            lang_codes = ['te', 'en']
        elif 'hi' in l or 'hin' in l:
            lang_codes = ['hi', 'en']
            
    lang_key = ",".join(sorted(list(set(lang_codes))))
    if lang_key not in _EASY_READERS:
        import logging
        logging.getLogger('easyocr').setLevel(logging.ERROR)
        _EASY_READERS[lang_key] = easyocr.Reader(lang_codes, gpu=False)
        
    reader = _EASY_READERS[lang_key]
        
    img_arr = np.array(image.convert("RGB"))
    img_cv = img_arr[:, :, ::-1]
    
    result = reader.readtext(img_cv)
    
    blocks = []
    text_lines = []
    confidences = []
    
    if result:
        for line in result:
            box = line[0]
            text = line[1]
            conf = float(line[2])
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
        engine="EasyOCR",
        processing_time=t_elapsed,
        layout=doc,
        word_confidences=confidences
    )
