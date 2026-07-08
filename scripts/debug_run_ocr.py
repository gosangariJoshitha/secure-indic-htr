import sys, os
from PIL import Image

# Ensure project root is on sys.path so `utils` imports resolve
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.ocr_engine import run_ocr, _looks_like_single_character
from utils.layout_pipeline import BlockType
from utils.segment import segment_page, prepare_document_image

img_path = 'data/eval/images/telugu_00000.png'
print('Loading', img_path)
img = Image.open(img_path)

print('Running OCR...')
# First inspect segmentation results
prepared = prepare_document_image(img, segmentation_params=None, language=None)
print('Prepared image size:', prepared.size)
print('Looks like single char heuristic:', _looks_like_single_character(prepared))
lines, binarized = segment_page(prepared, enhanced=False, language=None, segmentation_params=None)
print(f'Segmentation: lines={len(lines)}')
for i, l in enumerate(lines[:10]):
    if l.is_blank:
        print(f' Line {i}: BLANK')
        continue
    wcount = len(l.words)
    ccount = sum(len(w.chars) for w in l.words)
    print(f' Line {i}: words={wcount}, chars={ccount}, y={l.y}, h={l.h}')

res = run_ocr(img, mode='auto', enhanced=False, language=None, segmentation_params=None, single_char_mode=False)
if res is None:
    print('run_ocr returned None')
else:
    doc, overlay, engine = res
    print('Engine:', engine)
    print('Detected script:', getattr(doc, 'detected_script', None))
    print('Mean confidence:', doc.mean_confidence)
    print('Char count:', doc.char_count)
    print('\nPlain text:\n')
    print(doc.plain_text)
    print('\nBlocks and lines:')
    for bi, b in enumerate(doc.blocks):
        print(f'Block {bi}: type={b.type}')
        if b.type == BlockType.TABLE and b.table:
            print('  Table ->', b.table.to_plain_text())
            continue
        for li, line in enumerate(b.lines):
            print(f'  Line {li}: conf={line.confidence:.3f} -> {line.text}')
