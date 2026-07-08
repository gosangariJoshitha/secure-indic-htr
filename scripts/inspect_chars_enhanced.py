from PIL import Image
import sys, os
from pathlib import Path

# Ensure project root is on sys.path when running from scripts/
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from utils.segment import segment_page, crop_char, prepare_document_image
from utils.predictor import get_predictor
from utils.ocr_engine import run_ocr


def main(img_path: str):
    img = Image.open(img_path)
    print('Image:', img_path, 'size=', img.size)

    prepared = prepare_document_image(img, segmentation_params=None, language=None)
    print('Prepared size:', prepared.size)

    lines, binarized = segment_page(prepared, enhanced=True, language=None, segmentation_params=None)
    total_chars = sum(len(w.chars) for l in lines for w in l.words)
    print('Segmented lines:', len(lines), ' total_chars=', total_chars)

    predictor = get_predictor()

    for li, l in enumerate(lines):
        if getattr(l, 'is_blank', False):
            print(f'Line {li}: BLANK')
            continue
        for wi, w in enumerate(l.words):
            for ci, c in enumerate(w.chars):
                crop = crop_char(binarized, c)
                char_tel, conf_tel = predictor.predict_char(crop, language='Telugu')
                char_auto, conf_auto = predictor.predict_char(crop, language=None)
                print(f'Line{li} Word{wi} Char{ci}: box={c.w}x{c.h} -> tel={char_tel!r}:{conf_tel:.3f} auto={char_auto!r}:{conf_auto:.3f}')

    # Try printed OCR if available
    try:
        printed_doc, printed_overlay, engine = run_ocr(img, mode='printed', enhanced=True, language='Telugu')
        print('\nPrinted OCR engine result:')
        print('Engine:', engine)
        print('Mean conf:', printed_doc.mean_confidence)
        print('Char count:', printed_doc.char_count)
        print('Plain text:', printed_doc.plain_text)
    except Exception as e:
        print('\nPrinted OCR not available or failed:', repr(e))


if __name__ == '__main__':
    path = 'data/eval/images/telugu_00000.png'
    if len(sys.argv) > 1:
        path = sys.argv[1]
    main(path)
