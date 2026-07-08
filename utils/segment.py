"""
utils/segment.py
=================
Classical computer-vision page segmentation. The trained model
(utils/predictor.py) classifies ONE character per call, so getting from
"a photo of a handwritten page" to "recognized text" requires building the
layers the model doesn't provide:

    page image
      -> binarize + deskew
      -> LINE segmentation      (horizontal projection profile)
      -> WORD segmentation      (vertical gap analysis within each line)
      -> CHARACTER segmentation (connected components within each word)
      -> each character crop -> predictor.predict_char()
      -> reassemble: characters -> words -> lines -> paragraphs

This module owns segmentation + bounding boxes only. utils/layout_pipeline.py
owns turning the segmented+recognized result into the LayoutDocument
structure and exporting it to TXT/Markdown/HTML/DOCX/PDF/JSON.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger("SecureDocAI.Segment")


def _estimate_rotation_angle(image: Image.Image) -> int | None:
    """Best-effort orientation detection using pytesseract OSD if available."""
    try:
        import pytesseract
    except Exception:
        return None

    try:
        osd = pytesseract.image_to_osd(image)
        for line in osd.splitlines():
            line = line.strip()
            if line.lower().startswith("rotate:"):
                return int(line.split(":", 1)[1].strip())
    except Exception:
        return None
    return None


def _auto_rotate_document(image: Image.Image) -> Image.Image:
    """Rotate a document to upright orientation when the OCR engine reports one."""
    angle = _estimate_rotation_angle(image)
    if angle in {90, 180, 270}:
        return image.rotate(angle, expand=True, fillcolor=255)
    return image


def _auto_crop_document(image: Image.Image, padding: int = 18) -> Image.Image:
    """Crop whitespace around the main foreground content to focus OCR on the document."""
    gray = np.array(image.convert("L"))
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coords = cv2.findNonZero(thresh)
    if coords is None:
        return image

    x, y, w, h = cv2.boundingRect(coords)
    x0 = max(0, x - padding)
    y0 = max(0, y - padding)
    x1 = min(image.width, x + w + padding)
    y1 = min(image.height, y + h + padding)

    if x1 <= x0 or y1 <= y0:
        return image

    return image.crop((x0, y0, x1, y1))


def sauvola_threshold(gray: np.ndarray, window_size: int = 25, k: float = 0.2, R: float = 128.0) -> np.ndarray:
    """Fast Sauvola local adaptive binarization using OpenCV boxFilter."""
    mean = cv2.boxFilter(gray, cv2.CV_32F, (window_size, window_size))
    sq_gray = np.square(gray.astype(np.float32))
    sq_mean = cv2.boxFilter(sq_gray, cv2.CV_32F, (window_size, window_size))
    variance = sq_mean - np.square(mean)
    variance[variance < 0] = 0
    std = np.sqrt(variance)
    thresh = mean * (1.0 + k * ((std / R) - 1.0))
    binarized = np.zeros_like(gray)
    binarized[gray > thresh] = 255
    return binarized

def enhance_document_image(image: Image.Image, language: str | None = None) -> Image.Image:
    """Applies advanced image preprocessing:
    1. Grayscale conversion
    2. Morphological background subtraction (shadow removal)
    3. CLAHE (Contrast Limited Adaptive Histogram Equalization)
    4. Bilateral Filtering (Denoising)
    5. Sauvola Adaptive Thresholding (Binarization)
    Returns enhanced PIL Image.
    """
    try:
        # Convert PIL Image to OpenCV BGR
        img_cv = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        # 1. Shadow removal: Morphological background subtraction
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 21))
        background = cv2.dilate(gray, kernel)
        normalized = cv2.divide(gray, background, scale=255)
        
        # 2. Contrast Enhancement: CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(normalized)
        
        # 3. Denoising: Bilateral filter (preserves sharp character edges)
        denoised = cv2.bilateralFilter(enhanced, d=9, sigmaColor=75, sigmaSpace=75)
        
        # 4. Binarization: Sauvola adaptive thresholding
        binarized = sauvola_threshold(denoised, window_size=25, k=0.2, R=128.0)
        
        # Convert back to RGB PIL Image
        result_img = Image.fromarray(cv2.cvtColor(binarized, cv2.COLOR_GRAY2RGB))
        return result_img
    except Exception as e:
        logger.warning(f"enhance_document_image failed: {e}")
        return image

def prepare_document_image(image: Image.Image, segmentation_params: dict | None = None,
                            language: str | None = None) -> Image.Image:
    """Normalize a document image before OCR: auto-rotate and auto-crop whitespace."""
    params = segmentation_params or {}
    if not params.get("auto_rotate_crop", True):
        return image

    prepared = _auto_rotate_document(image)
    prepared = _auto_crop_document(prepared, padding=int(params.get("crop_padding", 18)))
    
    # Run advanced contrast and shadow correction binarization
    prepared = enhance_document_image(prepared, language=language)
    
    return prepared.convert("RGB") if prepared.mode != "RGB" else prepared


# ============================================================
# Data structures
# ============================================================
@dataclass
class CharBox:
    x: int
    y: int
    w: int
    h: int
    char: str = ""
    confidence: float = 0.0


@dataclass
class WordBox:
    x: int
    y: int
    w: int
    h: int
    chars: list[CharBox] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "".join(c.char for c in self.chars)


@dataclass
class LineBox:
    x: int
    y: int
    w: int
    h: int
    words: list[WordBox] = field(default_factory=list)
    is_blank: bool = False

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)


# ============================================================
# Preprocessing: grayscale + binarize + deskew
# ============================================================
def load_and_binarize(image: Image.Image, enhanced: bool = False, language: str | None = None, use_v2_preprocess: bool = False) -> np.ndarray:
    """Returns a binarized (0/255) numpy array, white text on black background."""
    gray = np.array(image.convert("L"))

    if use_v2_preprocess:
        # V2 Preprocessing path: Blur Detection + Sharpening + CLAHE + Gamma + Contrast Stretch + Adaptive Threshold + Noise Removal
        lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if lap_var < 50.0:
            logger.info(f"Blur detected ({lap_var:.1f}), applying sharpening kernel.")
            sharpen_kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            gray = cv2.filter2D(gray, -1, sharpen_kernel)

        clahe = cv2.createCLAHE(clipLimit=3.0 if enhanced else 2.0, tileGridSize=(8, 8))
        work = clahe.apply(gray)
        
        gamma = 1.25 if enhanced else 1.0
        invGamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** invGamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
        work = cv2.LUT(work, table)
        
        work = cv2.normalize(work, None, 0, 255, cv2.NORM_MINMAX)

        binarized = cv2.adaptiveThreshold(
            work, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 15 if enhanced else 11, 3 if enhanced else 2
        )

        kernel = np.ones((2, 2), np.uint8)
        binarized = cv2.morphologyEx(binarized, cv2.MORPH_OPEN, kernel)
    else:
        # Original binarization path (preserved verbatim)
        if enhanced:
            filtered = cv2.bilateralFilter(gray, d=11, sigmaColor=150, sigmaSpace=150)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        else:
            filtered = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

        equalized = clahe.apply(filtered)
        _, binarized = cv2.threshold(equalized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        white = np.sum(binarized > 127)
        black = np.sum(binarized <= 127)
        total = binarized.size
        if white < total * 0.01 or black < total * 0.01:
            if enhanced:
                binarized = cv2.adaptiveThreshold(equalized, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                                  cv2.THRESH_BINARY, 15, 3)
            else:
                binarized = cv2.adaptiveThreshold(equalized, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                                  cv2.THRESH_BINARY, 11, 2)

        kernel = np.ones((2, 2), np.uint8)
        binarized = cv2.morphologyEx(binarized, cv2.MORPH_OPEN, kernel)

    if enhanced:
        if language and language.lower().startswith('h'):
            kernel2 = np.ones((3, 2), np.uint8)
            binarized = cv2.morphologyEx(binarized, cv2.MORPH_CLOSE, kernel2)
        else:
            kernel2 = np.ones((2, 2), np.uint8)
            binarized = cv2.morphologyEx(binarized, cv2.MORPH_CLOSE, kernel2)

    # Ensure text is white-on-black
    white = np.sum(binarized > 127)
    black = np.sum(binarized <= 127)
    if white > black:
        binarized = cv2.bitwise_not(binarized)

    return binarized


def deskew(binarized: np.ndarray, max_correction_degrees: float = 8.0) -> np.ndarray:
    """Estimates and corrects small rotation using minimum-area bounding rectangles."""
    coords = np.column_stack(np.where(binarized > 0))
    if len(coords) < 50:
        return binarized

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    if abs(angle) < 0.5 or abs(angle) > max_correction_degrees:
        return binarized

    (h, w) = binarized.shape
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(binarized, matrix, (w, h), flags=cv2.INTER_CUBIC, borderValue=0)


# ============================================================
# Line segmentation — horizontal projection profile
# ============================================================
def segment_lines(binarized: np.ndarray, min_line_height: int = 8,
                   blank_gap_threshold: int = 18) -> list[LineBox]:
    """Finds horizontal text bands by summing foreground pixels per row."""
    h, w = binarized.shape
    row_sums = np.sum(binarized > 0, axis=1)
    is_text_row = row_sums > 0

    lines: list[LineBox] = []
    in_line = False
    start = 0
    last_end = 0

    for y in range(h):
        if is_text_row[y] and not in_line:
            in_line = True
            start = y
            gap = start - last_end
            if gap > blank_gap_threshold and lines:
                lines.append(LineBox(x=0, y=last_end, w=w, h=gap, is_blank=True))
        elif not is_text_row[y] and in_line:
            in_line = False
            if y - start >= min_line_height:
                lines.append(LineBox(x=0, y=start, w=w, h=y - start))
            last_end = y

    if in_line and h - start >= min_line_height:
        lines.append(LineBox(x=0, y=start, w=w, h=h - start))

    return lines


# ============================================================
# Word segmentation — vertical gap analysis within one line band
# ============================================================
def segment_words(binarized: np.ndarray, line: LineBox,
                   word_gap_multiplier: float = 2.5, use_v2_word_gap: bool = False) -> list[WordBox]:
    """Finds vertical spaces using dynamic IQR gap analysis within a line band."""
    band = binarized[line.y: line.y + line.h, :]
    col_sums = np.sum(band > 0, axis=0)
    is_text_col = col_sums > 0

    runs = []
    in_run = False
    start = 0
    for x in range(len(is_text_col)):
        if is_text_col[x] and not in_run:
            in_run = True
            start = x
        elif not is_text_col[x] and in_run:
            in_run = False
            runs.append((start, x))
    if in_run:
        runs.append((start, len(is_text_col)))

    if not runs:
        return []

    # Dynamic thresholding based on inter-character spacing (median & IQR)
    gaps = [runs[i + 1][0] - runs[i][1] for i in range(len(runs) - 1)]
    if use_v2_word_gap and gaps:
        median_gap = float(np.median(gaps))
        q75, q25 = np.percentile(gaps, [75, 25])
        iqr = q75 - q25
        word_gap_threshold = max(median_gap + 1.5 * iqr, median_gap * word_gap_multiplier, 10.0)
    else:
        median_gap = float(np.median(gaps)) if gaps else 0.0
        word_gap_threshold = max(median_gap * word_gap_multiplier, 10)

    words: list[WordBox] = []
    cluster_start = runs[0][0]
    cluster_end = runs[0][1]

    for i in range(1, len(runs)):
        gap = runs[i][0] - cluster_end
        if gap > word_gap_threshold:
            span = cluster_end - cluster_start
            if span >= max(8, int(0.35 * line.w)):
                words.append(WordBox(x=cluster_start, y=line.y, w=cluster_end - cluster_start, h=line.h))
                cluster_start = runs[i][0]
            else:
                cluster_start = runs[i][0]
        cluster_end = runs[i][1]

    span = cluster_end - cluster_start
    if span >= max(8, int(0.35 * line.w)):
        words.append(WordBox(x=cluster_start, y=line.y, w=cluster_end - cluster_start, h=line.h))
    return words


# ============================================================
# Character segmentation — connected components within one word
# ============================================================
def segment_characters(binarized: np.ndarray, word: WordBox,
                        min_char_width: int = 4, use_watershed: bool = False) -> list[CharBox]:
    """Segments characters within a word's bounding box using watershed contours + projection refinement."""
    crop = binarized[word.y: word.y + word.h, word.x: word.x + word.w]
    if crop.size == 0:
        return []

    boxes = []

    # 1. If watershed segmentation is requested, run it to separate joined glyphs
    if use_watershed:
        dist_transform = cv2.distanceTransform(crop, cv2.DIST_L2, 5)
        _, sure_fg = cv2.threshold(dist_transform, 0.15 * dist_transform.max() if dist_transform.max() > 0 else 0.0, 255, 0)
        sure_fg = np.uint8(sure_fg)
        
        unknown = cv2.subtract(crop, sure_fg)
        _, markers = cv2.connectedComponents(sure_fg)
        markers = markers + 1
        markers[unknown == 255] = 0
        
        crop_rgb = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
        markers = cv2.watershed(crop_rgb, markers)
        
        for label_id in range(2, markers.max() + 1):
            mask = np.uint8(markers == label_id)
            coords = cv2.findNonZero(mask)
            if coords is not None:
                x, y, w, h = cv2.boundingRect(coords)
                area = int(mask.sum())
                if area >= 3:
                    boxes.append([x, y, w, h, area])
                    
        if not boxes:
            num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(crop, connectivity=8)
            for label_id in range(1, num_labels):
                x, y, w, h, area = stats[label_id]
                if area >= 3:
                    boxes.append([x, y, w, h, area])

        if not boxes:
            return []

        boxes.sort(key=lambda b: b[0])

        merged: list[list[int]] = []
        for box in boxes:
            if not merged:
                merged.append([box[0], box[1], box[2], box[3]])
                continue

            prev = merged[-1]
            gap_x = box[0] - (prev[0] + prev[2])
            gap_y = abs(box[1] - (prev[1] + prev[3]))
            if (box[2] < min_char_width or box[3] < min_char_width) and gap_x < max(4, min_char_width) and gap_y < max(4, min_char_width):
                new_x = min(prev[0], box[0])
                new_y = min(prev[1], box[1])
                new_x2 = max(prev[0] + prev[2], box[0] + box[2])
                new_y2 = max(prev[1] + prev[3], box[1] + box[3])
                merged[-1] = [new_x, new_y, new_x2 - new_x, new_y2 - new_y]
            else:
                merged.append([box[0], box[1], box[2], box[3]])

        widths = [b[2] for b in merged] if merged else [0]
        try:
            median_w = float(np.median(widths))
        except Exception:
            median_w = widths[0] if widths else 0

        final_boxes: list[list[int]] = []
        for b in merged:
            bx, by, bw, bh = b
            if bw > max(median_w * 1.6, min_char_width * 3):
                sub_crop = crop[by:by + bh, bx:bx + bw]
                col_sums = np.sum(sub_crop > 0, axis=0)
                is_text_col = col_sums > 0
                runs = []
                in_run = False
                start = 0
                for x in range(len(is_text_col)):
                    if is_text_col[x] and not in_run:
                        in_run = True
                        start = x
                    elif not is_text_col[x] and in_run:
                        in_run = False
                        runs.append((start, x))
                if in_run:
                    runs.append((start, len(is_text_col)))

                if runs:
                    merged_runs = []
                    for r in runs:
                        rx0, rx1 = r
                        rw = rx1 - rx0
                        if merged_runs and rw < 3:
                            pr = merged_runs[-1]
                            merged_runs[-1] = (pr[0], rx1)
                        else:
                            merged_runs.append((rx0, rx1))

                    for mr in merged_runs:
                        mx0, mx1 = mr
                        final_boxes.append([bx + mx0, by, mx1 - mx0, bh])
                    continue

            final_boxes.append([bx, by, bw, bh])

        return [CharBox(x=word.x + b[0], y=word.y + b[1], w=b[2], h=b[3]) for b in final_boxes]
    else:
        # Verbatim original code path to preserve compatibility with existing tests
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(crop, connectivity=8)
        for label_id in range(1, num_labels):
            x, y, w, h, area = stats[label_id]
            if area < 3:
                continue
            boxes.append([x, y, w, h, area])

        if not boxes:
            return []

        boxes.sort(key=lambda b: b[0])

        merged = []
        for box in boxes:
            if not merged:
                merged.append([box[0], box[1], box[2], box[3]])
                continue

            prev = merged[-1]
            gap_x = box[0] - (prev[0] + prev[2])
            gap_y = abs(box[1] - (prev[1] + prev[3]))
            if (box[2] < min_char_width or box[3] < min_char_width) and gap_x < max(4, min_char_width) and gap_y < max(4, min_char_width):
                new_x = min(prev[0], box[0])
                new_y = min(prev[1], box[1])
                new_x2 = max(prev[0] + prev[2], box[0] + box[2])
                new_y2 = max(prev[1] + prev[3], box[1] + box[3])
                merged[-1] = [new_x, new_y, new_x2 - new_x, new_y2 - new_y]
            else:
                merged.append([box[0], box[1], box[2], box[3]])

        widths = [b[2] for b in merged] if merged else [0]
        try:
            median_w = float(np.median(widths))
        except Exception:
            median_w = widths[0] if widths else 0

        final_boxes = []
        for b in merged:
            bx, by, bw, bh = b
            if bw > max(median_w * 1.6, min_char_width * 3):
                # attempt split (using exact original page-indexing bug)
                crop_split = binarized[by:by + bh, bx:bx + bw]
                col_sums = np.sum(crop_split > 0, axis=0)
                is_text_col = col_sums > 0
                runs = []
                in_run = False
                start = 0
                for x in range(len(is_text_col)):
                    if is_text_col[x] and not in_run:
                        in_run = True
                        start = x
                    elif not is_text_col[x] and in_run:
                        in_run = False
                        runs.append((start, x))
                if in_run:
                    runs.append((start, len(is_text_col)))

                if runs:
                    merged_runs = []
                    for r in runs:
                        rx0, rx1 = r
                        rw = rx1 - rx0
                        if merged_runs and rw < 3:
                            pr = merged_runs[-1]
                            merged_runs[-1] = (pr[0], rx1)
                        else:
                            merged_runs.append((rx0, rx1))

                    for mr in merged_runs:
                        mx0, mx1 = mr
                        final_boxes.append([bx + mx0, by, mx1 - mx0, bh])
                    continue

            final_boxes.append([bx, by, bw, bh])

        return [CharBox(x=word.x + b[0], y=word.y + b[1], w=b[2], h=b[3]) for b in final_boxes]


# ============================================================
# Full-page segmentation pipeline
# ============================================================
def segment_page(image: Image.Image, enhanced: bool = False, language: str | None = None,
                 segmentation_params: dict | None = None) -> tuple[list[LineBox], np.ndarray]:
    """Runs the full line -> word -> character segmentation pipeline."""
    prepared_image = prepare_document_image(image, segmentation_params=segmentation_params, language=language)
    
    seg_params = segmentation_params or {}
    use_v2_preprocess = seg_params.get('use_v2_preprocess', False)
    use_v2_word_gap = seg_params.get('use_v2_word_gap', False)
    use_watershed = seg_params.get('use_watershed', False)
    
    binarized = load_and_binarize(prepared_image, enhanced=enhanced, language=language, use_v2_preprocess=use_v2_preprocess)
    
    max_deg = float(seg_params.get('deskew_max_degrees', 8.0))
    binarized = deskew(binarized, max_correction_degrees=max_deg)

    min_line_height = seg_params.get('min_line_height', 8)
    blank_gap_threshold = seg_params.get('blank_gap_threshold', 18)
    word_gap_multiplier = seg_params.get('word_gap_multiplier', 2.5)
    min_char_width = seg_params.get('min_char_width', 4)

    lines = segment_lines(binarized, min_line_height=min_line_height,
                          blank_gap_threshold=blank_gap_threshold)
    for line in lines:
        if line.is_blank:
            continue
        words = segment_words(binarized, line, word_gap_multiplier=word_gap_multiplier, use_v2_word_gap=use_v2_word_gap)
        for word in words:
            word.chars = segment_characters(binarized, word, min_char_width=min_char_width, use_watershed=use_watershed)
        line.words = [w for w in words if w.chars]

    return lines, binarized


def crop_char(binarized: np.ndarray, box: CharBox, padding: int = 6) -> Image.Image:
    """Crops a single character region out of the binarized page, with a small margin."""
    h, w = binarized.shape
    x0 = max(0, box.x - padding)
    y0 = max(0, box.y - padding)
    x1 = min(w, box.x + box.w + padding)
    y1 = min(h, box.y + box.h + padding)
    crop = binarized[y0:y1, x0:x1]
    return Image.fromarray(crop)
