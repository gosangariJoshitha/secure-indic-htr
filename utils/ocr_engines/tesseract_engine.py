"""
utils/ocr_engines/tesseract_engine.py
=====================================
Runs Tesseract OCR engine wrapper.
"""

import time
import os
import shutil
import logging
from PIL import Image
from utils.ocr_result import OCRResult
from utils.layout_pipeline import LayoutDocument, Block, BlockType, RecognizedLine, Alignment

logger = logging.getLogger("SecureDocAI.TesseractEngine")

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
    if os.path.exists(r"C:\Program Files\Tesseract-OCR\tesseract.exe"):
        pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
except Exception as e:
    TESSERACT_AVAILABLE = False

TESSERACT_BIN_AVAILABLE = (
    TESSERACT_AVAILABLE and 
    (bool(shutil.which('tesseract')) or os.path.exists(r"C:\Program Files\Tesseract-OCR\tesseract.exe"))
)

def run(image: Image.Image, language: str | None = None) -> OCRResult:
    t_start = time.time()
    
    if not TESSERACT_BIN_AVAILABLE:
        raise RuntimeError("Tesseract OCR is not available; install the native binary to enable printed-text OCR")
        
    lang_code = 'eng'
    if language:
        l = language.lower()
        if 'te' in l or 'tel' in l:
            lang_code = 'tel+eng'
        elif 'hi' in l or 'hin' in l:
            lang_code = 'hin+eng'
            
    try:
        from pytesseract import Output
        data = pytesseract.image_to_data(image, lang=lang_code, output_type=Output.DICT)
    except Exception as e:
        logger.exception("Tesseract execution failed:")
        raise RuntimeError(f"Tesseract OCR failed: {e}")
        
    n = len(data['level'])
    blocks_map = {}
    for i in range(n):
        block_no = int(data['block_num'][i])
        par_no = int(data['par_num'][i])
        line_no = int(data['line_num'][i])
        word_no = int(data['word_num'][i])
        left = int(data['left'][i])
        top = int(data['top'][i])
        width = int(data['width'][i])
        height = int(data['height'][i])
        conf = float(data['conf'][i]) if data['conf'][i] != '-1' else 0.0
        text = str(data['text'][i]).strip()
        
        if not text:
            continue
            
        b_key = (block_no, par_no)
        if b_key not in blocks_map:
            blocks_map[b_key] = {}
            
        if line_no not in blocks_map[b_key]:
            blocks_map[b_key][line_no] = {'words': [], 'y': top}
            
        blocks_map[b_key][line_no]['words'].append({
            'left': left, 'top': top, 'width': width, 'height': height, 'text': text, 'conf': conf
        })
            
    blocks = []
    text_lines = []
    confidences = []
    
    for b_key in sorted(blocks_map.keys()):
        b_data = blocks_map[b_key]
        block_lines = []
        for l_no in sorted(b_data.keys()):
            line_data = b_data[l_no]
            words = sorted(line_data['words'], key=lambda w: w['left'])
            line_text = " ".join(w['text'] for w in words if w['text'])
            if line_text:
                line_conf = sum(w['conf'] for w in words if w['text']) / len(words)
                text_lines.append(line_text)
                confidences.append(line_conf / 100.0) # Scale to 0-1 range
                
                rl = RecognizedLine(text=line_text, alignment=Alignment.LEFT, y=line_data['y'], confidence=line_conf / 100.0)
                block_lines.append(rl)
                
        if block_lines:
            blocks.append(Block(type=BlockType.PARAGRAPH, lines=block_lines))
            
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
        engine="Tesseract",
        processing_time=t_elapsed,
        layout=doc,
        word_confidences=confidences
    )
