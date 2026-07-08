"""scripts/run_e2e_test.py
Create a synthetic test image, run the layout pipeline, save overlay, and print results.
"""
from PIL import Image, ImageDraw, ImageFont
import os
import sys

# Ensure repo root is importable when running from scripts/
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from utils.layout_pipeline import run_layout_pipeline


def make_test_image(path: str):
    W, H = 900, 1200
    img = Image.new('RGB', (W, H), color='white')
    draw = ImageDraw.Draw(img)
    # Try to use a default font; size chosen for readability
    try:
        font = ImageFont.truetype('arial.ttf', 36)
    except Exception:
        font = ImageFont.load_default()

    y = 40
    lines = [
        "SecureDocAI — End-to-end test",
        "This is a printed-like test line 1.",
        "This is a printed-like test line 2.",
        "Contact: test@example.com | Phone: 9999999999",
        "",
        "Table-like area:",
        "Col1\tCol2\tCol3",
        "1\t2\t3",
    ]
    for ln in lines:
        draw.text((40, y), ln, fill='black', font=font)
        y += 48

    img.save(path)


def main():
    out_dir = os.path.join(os.path.dirname(__file__), '..', 'outputs', 'ocr')
    os.makedirs(out_dir, exist_ok=True)
    img_path = os.path.join(out_dir, 'e2e_test_image.png')
    make_test_image(img_path)

    img = Image.open(img_path)
    doc, overlay = run_layout_pipeline(img)

    print('--- OCR Result ---')
    print('Mean confidence:', doc.mean_confidence)
    print('Char count:', doc.char_count)
    print('Plain text:')
    print(doc.plain_text)

    if overlay is not None:
        overlay_path = os.path.join(out_dir, 'e2e_test_overlay.png')
        overlay.save(overlay_path)
        print('Saved overlay to', overlay_path)


if __name__ == '__main__':
    main()
