"""
utils/layout_pipeline.py
=========================
Orchestrates the full pipeline: page image -> segmented characters ->
recognized text -> structured LayoutDocument (paragraphs, alignment,
lists, tables, blank-line spacing).

This is where utils/segment.py (CV) and utils/predictor.py (the trained
model) meet. utils/exporters.py turns the resulting LayoutDocument into
TXT/Markdown/HTML/DOCX/PDF/JSON.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np
from PIL import Image

from utils.segment import segment_page, crop_char, LineBox, prepare_document_image
from utils.predictor import get_predictor
from utils.table_detect import detect_tables, TableRegion


from utils.layout_builder import (
    Alignment, BlockType, RecognizedLine, Block, LayoutDocument,
    preserve_bullet_points, preserve_indentation, detect_alignment
)

def _detect_list_marker(text: str) -> tuple[BlockType | None, str]:
    return preserve_bullet_points(text)

def _detect_alignment(line: LineBox, page_width: int, left_margin: int, right_margin: int) -> Alignment:
    if not line.words:
        return Alignment.LEFT
    content_left = line.words[0].x
    content_right = line.words[-1].x + line.words[-1].w
    return detect_alignment(content_left, content_right, left_margin, right_margin)

def _detect_indent_level(line: LineBox, left_margin: int, indent_unit: int = 40) -> int:
    if not line.words:
        return 0
    return preserve_indentation(line.words[0].x, left_margin, indent_unit)

def _is_probable_heading(line: LineBox, median_height: float) -> bool:
    word_count = len(line.words)
# ============================================================
# DOCUMENT ANALYZER
# ============================================================

class DocumentType(str, Enum):
    HANDWRITTEN = "handwritten"
    PRINTED = "printed"
    MIXED = "mixed"


def analyze_document(image: Image.Image) -> DocumentType:
    """
    Detect whether the document is handwritten,
    printed or mixed.
    """

    import cv2
    import numpy as np

    gray = cv2.cvtColor(
        np.array(image),
        cv2.COLOR_RGB2GRAY
    )

    # Crop to the foreground text region to ignore large white margins
    _, thresh = cv2.threshold(gray, 220, 255, cv2.THRESH_BINARY_INV)
    pts = np.argwhere(thresh > 0)
    if pts.size > 0:
        y1, x1 = pts.min(axis=0)
        y2, x2 = pts.max(axis=0)
        h, w = gray.shape
        y1 = max(0, y1 - 5)
        y2 = min(h - 1, y2 + 5)
        x1 = max(0, x1 - 5)
        x2 = min(w - 1, x2 + 5)
        cropped = gray[y1:y2+1, x1:x2+1]
    else:
        cropped = gray

    edges = cv2.Canny(cropped, 80, 180)
    density = edges.mean()

    if density < 5:
        return DocumentType.HANDWRITTEN
    elif density > 18:
        return DocumentType.PRINTED
    return DocumentType.MIXED


def image_quality_score(image):

    import cv2
    import numpy as np

    gray = cv2.cvtColor(
        np.array(image),
        cv2.COLOR_RGB2GRAY
    )

    score = cv2.Laplacian(
        gray,
        cv2.CV_64F
    ).var()

    return score


def run_layout_pipeline(image: Image.Image, model_path=None, enhanced: bool = False, language: str | None = None,
                        segmentation_params: dict | None = None) -> tuple[LayoutDocument, Image.Image | None]:
    """
    Runs the complete character-level OCR reconstruction pipeline:
    Input Image -> Image Preprocessing -> Text Region Detection -> Paragraph Detection ->
    Line Detection -> Word Detection -> Character Segmentation -> Each Character Image ->
    Custom PyTorch Character Classifier -> Character Prediction -> Word Reconstruction ->
    Sentence Reconstruction -> Paragraph Reconstruction -> Layout Reconstruction.
    """
    predictor = get_predictor(model_path)

    doc_type = analyze_document(image)

    # Save for Dashboard / Reports
    engine_used = "Custom OCR"

    if doc_type == DocumentType.PRINTED:
        engine_used = "Tesseract"

    elif doc_type == DocumentType.MIXED:
        engine_used = "Hybrid OCR"

    else:
        engine_used = "Custom OCR"

    quality = image_quality_score(image)

    if quality < 50:
        print("Warning : Blurry image")

    # ----------------------------------------------------
    # Future Hybrid OCR

    # Printed
    #     ↓
    # Tesseract

    # Handwritten
    #     ↓
    # Custom Model

    # Mixed
    #     ↓
    # Merge

    # (Will be implemented inside
    # utils/ocr_engine.py)
    # ----------------------------------------------------

    prepared_image = prepare_document_image(image, segmentation_params=segmentation_params, language=language)
    page_w, page_h = prepared_image.size
    table_regions = detect_tables(prepared_image)

    # 1. Classical page segmentation into lines and character components
    lines, binarized = segment_page(prepared_image, enhanced=enhanced, language=language,
                                    segmentation_params=segmentation_params)

    # Drop lines inside tables (tables are recognized separately)
    def _inside_any_table(line: LineBox) -> bool:
        for t in table_regions:
            if line.y >= t.y and (line.y + line.h) <= (t.y + t.h):
                return True
        return False

    lines = [l for l in lines if not _inside_any_table(l)]

    if not lines:
        return LayoutDocument(page_width=page_w, page_height=page_h), None

    text_lines = [l for l in lines if not l.is_blank]
    if not text_lines:
        return LayoutDocument(page_width=page_w, page_height=page_h), None

    left_margin = min((l.words[0].x for l in text_lines if l.words), default=0)
    right_margin = max((l.words[-1].x + l.words[-1].w for l in text_lines if l.words), default=page_w)
    median_height = (sorted(l.h for l in text_lines)[len(text_lines) // 2] if text_lines else 20)

    # 2. Run character predictions for all segmented crops in batch
    all_crops = []
    crop_info = []
    for line_idx, line in enumerate(lines):
        if line.is_blank:
            continue
        for word_idx, word in enumerate(line.words):
            for char_box in word.chars:
                crop = crop_char(binarized, char_box)
                all_crops.append(crop)
                crop_info.append((line_idx, word_idx, char_box))

    if all_crops:
        predictions = predictor.predict_chars(all_crops, language=language)
    else:
        predictions = []

    all_chars_flat = []
    char_count = 0
    temp_chars_by_line = {}

    for idx, (line_idx, word_idx, char_box) in enumerate(crop_info):
        char, conf = predictions[idx]
        
        char_info = {
            "char": char or "?",
            "confidence": conf,
            "bbox": (char_box.x, char_box.y, char_box.w, char_box.h),
            "line_num": line_idx,
            "word_num": word_idx,
            "char_box_obj": char_box
        }
        char_box.char = char
        char_box.confidence = conf
        
        if line_idx not in temp_chars_by_line:
            temp_chars_by_line[line_idx] = []
        temp_chars_by_line[line_idx].append(char_info)
        all_chars_flat.append(char_info)
        char_count += 1

    if not all_chars_flat:
        # Fallback empty state
        return LayoutDocument(page_width=page_w, page_height=page_h), None

    # Get segmentation parameters for spacing
    seg_params = segmentation_params or {}
    word_gap_multiplier = seg_params.get('word_gap_multiplier', 2.5)

    # 3. Word and Sentence Reconstruction
    reconstructed_lines = []
    line_lookup = {}
    all_word_confidences = []
    all_word_metadata = []

    for line_idx, line in enumerate(lines):
        if line.is_blank:
            reconstructed_lines.append(None)
            continue

        line_chars = temp_chars_by_line.get(line_idx, [])
        if not line_chars:
            reconstructed_lines.append(None)
            continue

        # Sort characters by X coordinate
        line_chars.sort(key=lambda c: c["bbox"][0])

        # Word boundaries reconstruction using spacing thresholds
        reconstructed_words = []
        current_word_chars = [line_chars[0]]
        
        # Compute horizontal gaps between adjacent characters in this line
        gaps = []
        for i in range(len(line_chars) - 1):
            x1 = line_chars[i]["bbox"][0] + line_chars[i]["bbox"][2] # x + w
            x2 = line_chars[i+1]["bbox"][0]
            gap = max(0, x2 - x1)
            gaps.append(gap)
        
        median_char_gap = float(np.median(gaps)) if gaps else 2.0
        word_boundary_threshold = max(median_char_gap * word_gap_multiplier, 12.0)

        for i in range(len(line_chars) - 1):
            x1 = line_chars[i]["bbox"][0] + line_chars[i]["bbox"][2]
            x2 = line_chars[i+1]["bbox"][0]
            gap = max(0, x2 - x1)

            if gap > word_boundary_threshold:
                # Close current word, start new one
                reconstructed_words.append(current_word_chars)
                current_word_chars = [line_chars[i+1]]
            else:
                current_word_chars.append(line_chars[i+1])
        reconstructed_words.append(current_word_chars)

        # Build word objects & compute Word Confidence
        line_word_objects = []
        for word_chars in reconstructed_words:
            word_text = "".join(c["char"] for c in word_chars)
            word_conf = sum(c["confidence"] for c in word_chars) / len(word_chars)
            all_word_confidences.append(word_conf)
            line_word_objects.append({
                "text": word_text,
                "confidence": word_conf,
                "chars": word_chars
            })
        all_word_metadata.extend(line_word_objects)

        # Sentence Reconstruction: sort words and merge them with spacing
        sentence_text = " ".join(w["text"] for w in line_word_objects)
        line_confidence = sum(w["confidence"] for w in line_word_objects) / len(line_word_objects)

        alignment = _detect_alignment(line, page_w, left_margin, right_margin)
        indent = _detect_indent_level(line, left_margin)

        rl = RecognizedLine(
            text=sentence_text,
            alignment=alignment,
            y=line.y,
            indent_level=indent,
            confidence=line_confidence,
            x=line.x,
            w=line.w
        )
        reconstructed_lines.append(rl)
        line_lookup[line.y] = line

    # Apply smart column-aware sorting order
    from utils.layout_builder import sort_text_blocks
    reconstructed_lines = sort_text_blocks(reconstructed_lines)

    # 4. Paragraph Reconstruction (Group lines based on vertical gaps)
    # Calculate vertical gaps between consecutive lines
    vertical_gaps = []
    line_y_coords = sorted([l.y for l in text_lines])
    for i in range(len(line_y_coords) - 1):
        # find matching LineBox to compute height
        l1 = next(l for l in text_lines if l.y == line_y_coords[i])
        l2 = next(l for l in text_lines if l.y == line_y_coords[i+1])
        gap = max(0, l2.y - (l1.y + l1.h))
        vertical_gaps.append(gap)
    
    median_line_gap = float(np.median(vertical_gaps)) if vertical_gaps else 18.0
    paragraph_boundary_threshold = max(median_line_gap * 1.8, 25.0)

    blocks: list[Block] = []
    current_lines: list[RecognizedLine] = []
    current_list_type: BlockType | None = None

    def flush_paragraph():
        nonlocal current_lines, current_list_type
        if current_lines:
            # Paragraph confidence is the average of its line confidences
            p_conf = sum(l.confidence for l in current_lines) / len(current_lines)
            block = Block(type=current_list_type or BlockType.PARAGRAPH, lines=list(current_lines))
            # Save paragraph confidence dynamically on the block object
            setattr(block, "confidence", p_conf)
            blocks.append(block)
        current_lines = []
        current_list_type = None

    for i, rl in enumerate(reconstructed_lines):
        if rl is None:
            flush_paragraph()
            blocks.append(Block(type=BlockType.BLANK))
            continue

        # Check for paragraph break based on vertical spacing to the next line
        is_paragraph_break = False
        if i < len(reconstructed_lines) - 1 and reconstructed_lines[i+1] is not None:
            next_rl = reconstructed_lines[i+1]
            l_curr = line_lookup.get(rl.y)
            l_next = line_lookup.get(next_rl.y)
            if l_curr and l_next:
                v_gap = l_next.y - (l_curr.y + l_curr.h)
                if v_gap > paragraph_boundary_threshold:
                    is_paragraph_break = True

        list_type, remaining_text = _detect_list_marker(rl.text)
        if list_type is not None:
            flush_paragraph()
            rl.text = remaining_text
            block = Block(type=list_type, lines=[rl])
            setattr(block, "confidence", rl.confidence)
            blocks.append(block)
            continue

        starting_fresh = len(blocks) == 0 or blocks[-1].type == BlockType.BLANK
        source_line = line_lookup.get(rl.y)
        if starting_fresh and source_line and _is_probable_heading(source_line, median_height):
            flush_paragraph()
            block = Block(type=BlockType.HEADING, lines=[rl])
            setattr(block, "confidence", rl.confidence)
            blocks.append(block)
            continue

        current_lines.append(rl)
        
        if is_paragraph_break:
            flush_paragraph()

    flush_paragraph()

    # 5. Insert detected tables
    for table in table_regions:
        table.recognize_cells(predictor, binarized)
        insert_idx = len(blocks)
        for i, b in enumerate(blocks):
            if b.lines and b.lines[0].y > table.y:
                insert_idx = i
                break
        table_block = Block(type=BlockType.TABLE, table=table)
        setattr(table_block, "confidence", 0.90) # default high-level confidence for structure
        blocks.insert(insert_idx, table_block)

    # 6. Overall Document Confidence (average of all character predictions)
    overall_confidence = sum(c["confidence"] for c in all_chars_flat) / len(all_chars_flat) if all_chars_flat else 0.0

    # Build final LayoutDocument
    doc = LayoutDocument(
        blocks=blocks,
        page_width=page_w,
        page_height=page_h,
        mean_confidence=overall_confidence,
        char_count=char_count,
    )
    
    # Expose individual level confidences
    setattr(doc, "character_metadata", all_chars_flat)
    setattr(doc, "word_confidences", all_word_confidences)
    setattr(doc, "line_confidences", [l.confidence for l in reconstructed_lines if l is not None])
    setattr(doc, "paragraph_confidences", [getattr(b, "confidence", 0.0) for b in blocks if b.type != BlockType.BLANK])

    setattr(
        doc,
        "ocr_engine",
        engine_used
    )
    setattr(
        doc,
        "language",
        language or "Auto"
    )
    setattr(
        doc,
        "resolution",
        f"{page_w} × {page_h}"
    )
    setattr(
        doc,
        "word_metadata",
        all_word_metadata
    )
    setattr(
        doc,
        "paragraph_count",
        len(
            [
                b
                for b in blocks
                if b.type == BlockType.PARAGRAPH
            ]
        )
    )
    setattr(
        doc,
        "line_count",
        len(
            [
                l
                for l in reconstructed_lines
                if l
            ]
        )
    )

    word_count = 0
    for b in blocks:
        for line in b.lines:
            word_count += len(
                line.text.split()
            )
    setattr(
        doc,
        "word_count",
        word_count
    )

    setattr(
        doc,
        "rotation_angle",
        0
    )
    setattr(
        doc,
        "processing_pipeline",
        [
            "Preprocessing",
            "Segmentation",
            "Character Recognition",
            "Word Reconstruction",
            "Paragraph Reconstruction",
            "Layout Reconstruction"
        ]
    )
    setattr(
        doc,
        "ocr_version",
        "SecureDocAI V2"
    )

    # 7. Create debug overlay
    overlay = None
    try:
        from PIL import ImageDraw
        overlay = prepared_image.convert('RGB')
        draw = ImageDraw.Draw(overlay)
        for line in lines:
            if line.is_blank:
                continue
            draw.rectangle([line.x, line.y, line.x + line.w, line.y + line.h], outline=(0, 128, 0), width=1)
            for w in line.words:
                draw.rectangle([w.x, w.y, w.x + w.w, w.y + w.h], outline=(0, 0, 255), width=1)
                for c in w.chars:
                    draw.rectangle([c.x, c.y, c.x + c.w, c.y + c.h], outline=(255, 0, 0), width=1)
                    if getattr(c, 'char', ''):
                        try:
                            draw.text((c.x, c.y), c.char, fill=(255, 0, 0))
                        except Exception:
                            pass
    except Exception:
        overlay = None

    return doc, overlay