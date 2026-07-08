"""
utils/table_detect.py
======================
Detects ruled and borderless tables using morphological line extraction
and x-coordinate text clustering fallbacks, then recognizes the text inside
each cell using a hybrid OCR routing structure.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger("SecureDocAI.Table")


@dataclass
class TableRegion:
    x: int
    y: int
    w: int
    h: int
    row_bounds: list = field(default_factory=list)   # [(y0, y1), ...]
    col_bounds: list = field(default_factory=list)    # [(x0, x1), ...]
    cells: list = field(default_factory=list)          # [row][col] -> text
    table_type: str = "Ruled"
    overall_confidence: float = 0.0
    cell_metadata: list = field(default_factory=list)  # [row][col] -> dict

    def recognize_cells(self, predictor, binarized: np.ndarray, language: str | None = None):
        """Fills self.cells by running character segmentation+recognition inside each grid cell."""
        from utils.segment import segment_words, segment_characters, crop_char, LineBox
        from utils.ocr_engine import run_ocr

        self.cells = []
        self.cell_metadata = []
        
        total_conf_sum = 0.0
        total_cell_count = 0

        for r_idx, (y0, y1) in enumerate(self.row_bounds):
            row_texts = []
            row_metadata = []
            
            row_band = binarized[y0:y1, :]
            # Sort words and run segmenter
            words = segment_words(row_band, LineBox(x=0, y=0, w=row_band.shape[1], h=row_band.shape[0]))

            for c_idx, (x0, x1) in enumerate(self.col_bounds):
                cell_w = x1 - x0
                cell_h = y1 - y0
                
                # Check empty cell bounds
                if cell_w < 5 or cell_h < 5:
                    row_texts.append(None)
                    row_metadata.append({
                        "text": None, "confidence": 1.0,
                        "x": x0, "y": y0, "w": cell_w, "h": cell_h
                    })
                    continue

                # Collect words inside cell columns
                cell_words = [w for w in words if w.x >= (x0 - 2) and (w.x + w.w) <= (x1 + 2)]
                
                # Crop cell with padding
                pad = 6
                cx0 = max(0, x0 - pad)
                cy0 = max(0, y0 - pad)
                cx1 = min(binarized.shape[1], x1 + pad)
                cy1 = min(binarized.shape[0], y1 + pad)
                
                cell_crop = binarized[cy0:cy1, cx0:cx1]
                if cell_crop.size == 0 or np.sum(cell_crop > 0) < 5:
                    row_texts.append(None)
                    row_metadata.append({
                        "text": None, "confidence": 1.0,
                        "x": x0, "y": y0, "w": cell_w, "h": cell_h
                    })
                    continue

                # Hybrid OCR inside cell crop
                cell_img = Image.fromarray(cell_crop)
                try:
                    cell_doc, _, _ = run_ocr(cell_img, mode='auto', enhanced=True, language=language)
                    text = cell_doc.plain_text.strip()
                    conf = cell_doc.mean_confidence
                except Exception:
                    # Fallback to character classifier
                    cell_text_parts = []
                    conf_sum = 0.0
                    char_count = 0
                    for word in cell_words:
                        chars = segment_characters(row_band, word)
                        for cb in chars:
                            crop = crop_char(row_band, cb)
                            char, c_conf = predictor.predict_char(crop, language=language)
                            cell_text_parts.append(char)
                            conf_sum += c_conf
                            char_count += 1
                    text = "".join(cell_text_parts)
                    conf = conf_sum / max(1, char_count)

                if not text:
                    text = None

                row_texts.append(text)
                row_metadata.append({
                    "text": text, "confidence": conf,
                    "x": x0, "y": y0, "w": cell_w, "h": cell_h
                })
                
                total_conf_sum += conf
                total_cell_count += 1

            self.cells.append(row_texts)
            self.cell_metadata.append(row_metadata)

        self.overall_confidence = total_conf_sum / max(1, total_cell_count)

    def to_plain_text(self) -> str:
        """Renders the table as a simple pipe-delimited block for TXT/plain output."""
        if not self.cells:
            return ""
        lines = []
        for row in self.cells:
            row_str = [c if c is not None else "" for c in row]
            lines.append(" | ".join(row_str))
        return "\n".join(lines)

    def to_markdown(self) -> str:
        if not self.cells:
            return ""
        header = [c if c is not None else "" for c in self.cells[0]]
        out = ["| " + " | ".join(header) + " |"]
        out.append("|" + "|".join(["---"] * len(header)) + "|")
        for row in self.cells[1:]:
            row_str = [c if c is not None else "" for c in row]
            out.append("| " + " | ".join(row_str) + " |")
        return "\n".join(out)


def detect_borderless_tables_from_binary(binary: np.ndarray) -> list[TableRegion]:
    """Detects borderless tables directly from the binary page mask using projection gaps."""
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    
    boxes = []
    for label_id in range(1, num_labels):
        x, y, w, h, area = stats[label_id]
        if area > 4 and w < 100 and h < 50:
            boxes.append((x, y, w, h))
            
    if len(boxes) < 10:
        return []
        
    boxes.sort(key=lambda b: b[1])
    line_bands = []
    for box in boxes:
        bx, by, bw, bh = box
        placed = False
        for band in line_bands:
            overlap = min(by + bh, band["y1"]) - max(by, band["y0"])
            min_h = min(bh, band["y1"] - band["y0"])
            if overlap > 0.5 * min_h:
                band["boxes"].append(box)
                band["y0"] = min(band["y0"], by)
                band["y1"] = max(band["y1"], by + bh)
                placed = True
                break
        if not placed:
            line_bands.append({
                "y0": by,
                "y1": by + bh,
                "boxes": [box]
            })
            
    line_bands = [b for b in line_bands if len(b["boxes"]) >= 2]
    line_bands.sort(key=lambda b: b["y0"])
    
    table_candidates = []
    current_table = []
    for band in line_bands:
        band_boxes = sorted(band["boxes"], key=lambda b: b[0])
        gaps = [band_boxes[i+1][0] - (band_boxes[i][0] + band_boxes[i][2]) for i in range(len(band_boxes)-1)]
        large_gaps = [gap for gap in gaps if gap > 20]
        
        if len(large_gaps) >= 1:
            current_table.append(band)
        else:
            if len(current_table) >= 3:
                table_candidates.append(current_table)
            current_table = []
            
    if len(current_table) >= 3:
        table_candidates.append(current_table)
        
    regions = []
    for t_bands in table_candidates:
        xs = []
        for band in t_bands:
            for bx, by, bw, bh in band["boxes"]:
                xs.append((bx, bx + bw))
                
        hist = np.zeros(binary.shape[1], dtype=np.int32)
        for x0, x1 in xs:
            hist[x0:x1] += 1
            
        columns = []
        in_col = False
        col_start = 0
        for x in range(len(hist)):
            if hist[x] > 0 and not in_col:
                in_col = True
                col_start = x
            elif hist[x] == 0 and in_col:
                in_col = False
                if x - col_start >= 10:
                    columns.append((col_start, x))
        if in_col:
            columns.append((col_start, len(hist)))
            
        if len(columns) < 2:
            continue
            
        min_x = min(b["boxes"][0][0] for b in t_bands)
        max_x = max(b["boxes"][-1][0] + b["boxes"][-1][2] for b in t_bands)
        min_y = min(b["y0"] for b in t_bands)
        max_y = max(b["y1"] for b in t_bands)
        
        table_h = max_y - min_y
        table_w = max_x - min_x
        area = table_w * table_h
        page_area = binary.shape[0] * binary.shape[1]
        
        # Filter false-positive borderless tables (e.g. single text line with diacritics)
        if table_h < 80 or (area / page_area) < 0.04:
            continue
            
        row_bounds = [(b["y0"], b["y1"]) for b in t_bands]
        col_bounds = columns
        
        regions.append(TableRegion(
            x=min_x, y=min_y, w=table_w, h=table_h,
            row_bounds=row_bounds, col_bounds=col_bounds,
            table_type="Borderless"
        ))
        
    return regions


def detect_tables(image: Image.Image, min_table_area_ratio: float = 0.03) -> list:
    """Finds ruled-table regions via morphological line detection, with a borderless fallback."""
    gray = np.array(image.convert("L"))
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    h, w = binary.shape
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(40, w // 8), 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(40, h // 8)))

    horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)
    vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)
    grid = cv2.bitwise_or(horizontal_lines, vertical_lines)

    contours, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    regions = []
    page_area = h * w

    for contour in contours:
        x, y, cw, ch = cv2.boundingRect(contour)
        if (cw * ch) / page_area < min_table_area_ratio:
            continue

        table_horizontal = horizontal_lines[y:y + ch, x:x + cw]
        table_vertical = vertical_lines[y:y + ch, x:x + cw]

        row_ys = _line_positions(table_horizontal, axis=1, min_coverage_ratio=0.6, extent=cw)
        col_xs = _line_positions(table_vertical, axis=0, min_coverage_ratio=0.6, extent=ch)

        if len(row_ys) < 2 or len(col_xs) < 2:
            continue

        row_bounds = [(y + row_ys[i], y + row_ys[i + 1]) for i in range(len(row_ys) - 1)]
        col_bounds = [(x + col_xs[i], x + col_xs[i + 1]) for i in range(len(col_xs) - 1)]

        regions.append(TableRegion(x=x, y=y, w=cw, h=ch, row_bounds=row_bounds, col_bounds=col_bounds, table_type="Ruled"))

    # Fallback to borderless table detection if no ruled tables are found
    if not regions:
        regions = detect_borderless_tables_from_binary(binary)

    regions.sort(key=lambda r: r.y)
    return regions


def _line_positions(mask: np.ndarray, axis: int, merge_distance: int = 6,
                     min_coverage_ratio: float = 0.0, extent: int = 0) -> list:
    """Returns the sorted pixel positions of horizontal/vertical lines from a binary mask."""
    sums = np.sum(mask > 0, axis=1) if axis == 1 else np.sum(mask > 0, axis=0)

    if min_coverage_ratio > 0 and extent > 0:
        threshold = extent * min_coverage_ratio
        positions = np.where(sums >= threshold)[0]
    else:
        positions = np.where(sums > 0)[0]

    if len(positions) == 0:
        return []

    merged = [int(positions[0])]
    for p in positions[1:]:
        if p - merged[-1] > merge_distance:
            merged.append(int(p))
    return merged
