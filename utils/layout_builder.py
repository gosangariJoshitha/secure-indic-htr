"""
utils/layout_builder.py
=======================
Dedicated module for document layout reconstruction.
Responsibilities:
  - Sort text blocks
  - Detect paragraphs
  - Preserve blank lines
  - Preserve indentation
  - Preserve bullet points
  - Preserve tables
  - Rebuild page structure
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class Alignment(str, Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class BlockType(str, Enum):
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    BULLET_LIST = "bullet_list"
    NUMBERED_LIST = "numbered_list"
    TABLE = "table"
    BLANK = "blank"


@dataclass
class RecognizedLine:
    text: str
    alignment: Alignment
    y: int
    indent_level: int = 0
    confidence: float = 0.0
    x: int = 0
    w: int = 0


@dataclass
class Block:
    type: BlockType
    lines: list[RecognizedLine] = field(default_factory=list)
    table: Any = None  # Holds table region if block type == TABLE
    confidence: float = 0.0


@dataclass
class LayoutDocument:
    blocks: list[Block] = field(default_factory=list)
    page_width: int = 0
    page_height: int = 0
    mean_confidence: float = 0.0
    char_count: int = 0
    page_number: int = 1

    @property
    def plain_text(self) -> str:
        out = []
        for block in self.blocks:
            if block.type == BlockType.BLANK:
                out.append("")
                continue
            if block.type == BlockType.TABLE and block.table:
                # Delegate to table format
                if hasattr(block.table, "to_plain_text"):
                    out.append(block.table.to_plain_text())
                else:
                    out.append(str(block.table))
                continue
            for line in block.lines:
                out.append(line.text)
        return "\n".join(out)


_BULLET_CHARS = {"•", "●", "○", "◦", "-", "*", "[*]", "[ * ]"}


def preserve_bullet_points(text: str) -> tuple[BlockType | None, str]:
    """Detects list bullets and numbering markers from raw line text."""
    stripped = text.strip()
    if not stripped:
        return None, text

    first_token = stripped.split(" ", 1)[0]
    if first_token in _BULLET_CHARS:
        return BlockType.BULLET_LIST, stripped[len(first_token):].strip()

    digits = ""
    for ch in stripped:
        if ch.isdigit():
            digits += ch
        else:
            break
    if digits and len(stripped) > len(digits) and stripped[len(digits)] in ".)":
        return BlockType.NUMBERED_LIST, stripped[len(digits) + 1:].strip()

    return None, text


def preserve_indentation(line_box_x: int, left_margin: int, indent_unit: int = 40) -> int:
    """Computes left indentation level relative to the left margin."""
    offset = line_box_x - left_margin
    return max(0, round(offset / indent_unit))


def detect_alignment(content_left: int, content_right: int, left_margin: int, right_margin: int) -> Alignment:
    """Detects alignment (Left, Center, Right) based on line boundary gaps."""
    content_width = content_right - content_left
    usable_width = max(1, right_margin - left_margin)

    left_gap = content_left - left_margin
    right_gap = right_margin - content_right

    if content_width < usable_width * 0.85 and abs(left_gap - right_gap) < usable_width * 0.08:
        return Alignment.CENTER

    if left_gap > usable_width * 0.25 and right_gap < usable_width * 0.05:
        return Alignment.RIGHT

    return Alignment.LEFT


def sort_text_blocks(lines: list[Any]) -> list[Any]:
    """Sorts text line boxes using a smart reading order that handles multi-column pages."""
    if not lines:
        return []
        
    valid_lines = [l for l in lines if l is not None]
    nones = [l for l in lines if l is None]
    
    if len(valid_lines) < 4:
        return sorted(lines, key=lambda l: getattr(l, 'y', 0) if l is not None else 999999)
        
    try:
        left_coords = []
        right_coords = []
        for rl in valid_lines:
            x = getattr(rl, 'x', 0)
            w = getattr(rl, 'w', 100)
            left_coords.append(x)
            right_coords.append(x + w)
            
        min_x = min(left_coords) if left_coords else 0
        max_x = max(right_coords) if right_coords else 1000
        mid = (min_x + max_x) / 2
        
        left_col = []
        right_col = []
        for rl in valid_lines:
            x = getattr(rl, 'x', 0)
            w = getattr(rl, 'w', 100)
            center = x + w / 2
            if center < mid:
                left_col.append(rl)
            else:
                right_col.append(rl)
                
        total = len(valid_lines)
        if len(left_col) > 0.20 * total and len(right_col) > 0.20 * total:
            sorted_left = sorted(left_col, key=lambda l: getattr(l, 'y', 0))
            sorted_right = sorted(right_col, key=lambda l: getattr(l, 'y', 0))
            return sorted_left + sorted_right
    except Exception:
        pass
        
    return sorted(lines, key=lambda l: getattr(l, 'y', 0) if l is not None else 999999)


def detect_paragraphs(
    reconstructed_lines: list[RecognizedLine | None],
    line_lookup: dict[int, Any],
    paragraph_threshold: float = 25.0
) -> list[Block]:
    """Rebuilds paragraph blocks, preserving list styles, headings, and blank lines."""
    blocks: list[Block] = []
    current_lines: list[RecognizedLine] = []

    def flush_paragraph():
        if current_lines:
            p_conf = sum(l.confidence for l in current_lines) / len(current_lines)
            block = Block(type=BlockType.PARAGRAPH, lines=list(current_lines), confidence=p_conf)
            blocks.append(block)
            current_lines.clear()

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
                if v_gap > paragraph_threshold:
                    is_paragraph_break = True

        # Bullet List Check
        list_type, remaining_text = preserve_bullet_points(rl.text)
        if list_type is not None:
            flush_paragraph()
            rl.text = remaining_text
            block = Block(type=list_type, lines=[rl], confidence=rl.confidence)
            blocks.append(block)
            continue

        # Header detection heuristics
        if len(blocks) == 0 or blocks[-1].type == BlockType.BLANK:
            # Simple word-count heuristic
            if len(rl.text.split()) < 8 and rl.text.strip().endswith((":", "?")) or rl.text.isupper():
                flush_paragraph()
                block = Block(type=BlockType.HEADING, lines=[rl], confidence=rl.confidence)
                blocks.append(block)
                continue

        current_lines.append(rl)
        
        if is_paragraph_break:
            flush_paragraph()

    flush_paragraph()
    return blocks


def rebuild_page_structure(
    blocks: list[Block],
    page_width: int,
    page_height: int,
    mean_confidence: float,
    char_count: int
) -> LayoutDocument:
    """Wraps blocks into a final LayoutDocument payload."""
    return LayoutDocument(
        blocks=blocks,
        page_width=page_width,
        page_height=page_height,
        mean_confidence=mean_confidence,
        char_count=char_count
    )
