"""scripts/run_ocr_engine_test.py
Run the hybrid OCR engine in different modes on the test image.
"""
import os
import sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PIL import Image
from utils.ocr_engine import run_ocr


def main():
    img_path = os.path.join(os.path.dirname(__file__), '..', 'outputs', 'ocr', 'e2e_test_image.png')
    if not os.path.exists(img_path):
        print('Test image not found. Run scripts/run_e2e_test.py first.')
        return

    img = Image.open(img_path)
    for mode in ['auto', 'printed', 'handwritten', 'mixed']:
        print('--- MODE:', mode, '---')
        try:
            doc, overlay, engine = run_ocr(img, mode=mode, enhanced=False, language=None)
            print('Engine used:', engine)
            print('Mean confidence:', doc.mean_confidence)
            print('Char count:', doc.char_count)
            print('Plain text sample:', doc.plain_text[:200].replace('\n',' '))
        except Exception as e:
            print('Error during mode', mode, e)


if __name__ == '__main__':
    main()
