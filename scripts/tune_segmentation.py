"""Tune segmentation parameters by running the pipeline on an eval set.

Usage: run this from project root with the venv activated.
It will try a few combinations and write `data/eval/tune_report.csv` and `data/eval/confusions_best.csv`.
"""
import os
import csv
import sys
from collections import Counter
from PIL import Image

# Ensure repo root is importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from utils.layout_pipeline import run_layout_pipeline
from scripts.evaluate_ocr import levenshtein_alignment


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
IMG_DIR = os.path.join(ROOT, 'data', 'eval', 'images')
GT_DIR = os.path.join(ROOT, 'data', 'eval', 'labels')
OUT_DIR = os.path.join(ROOT, 'data', 'eval')
os.makedirs(OUT_DIR, exist_ok=True)

# parameter grid
grid = [
    {'word_gap_multiplier': 2.0, 'min_char_width': 3},
    {'word_gap_multiplier': 2.5, 'min_char_width': 4},
    {'word_gap_multiplier': 3.0, 'min_char_width': 5},
]

images = [f for f in os.listdir(IMG_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff'))]
images.sort()

def evaluate_with_params(params):
    total_gt = 0
    total_correct = 0
    confusions = Counter()
    per_image = []

    for img_name in images:
        base = os.path.splitext(img_name)[0]
        img_path = os.path.join(IMG_DIR, img_name)
        gt_path = os.path.join(GT_DIR, base + '.txt')
        if not os.path.exists(gt_path):
            continue
        img = Image.open(img_path)
        doc, overlay = run_layout_pipeline(img, enhanced=True, language=None, segmentation_params=params)
        pred = doc.plain_text.replace('\r', '')
        with open(gt_path, 'r', encoding='utf-8') as fh:
            gt = fh.read().replace('\r', '')
        aligned = levenshtein_alignment(gt, pred)
        total_gt += max(1, len(gt))
        total_correct += sum(1 for a, b in aligned if a == b and a != '')
        for a, b in aligned:
            if a and b and a != b:
                confusions[(a, b)] += 1
        per_image.append((img_name, len(gt), sum(1 for a, b in aligned if a != b)))

    acc = total_correct / total_gt if total_gt else 0.0
    return acc, confusions, per_image

best = None
best_params = None

with open(os.path.join(OUT_DIR, 'tune_report.csv'), 'w', newline='', encoding='utf-8') as report:
    writer = csv.writer(report)
    writer.writerow(['word_gap_multiplier', 'min_char_width', 'accuracy'])
    for p in grid:
        acc, confs, per_image = evaluate_with_params(p)
        writer.writerow([p['word_gap_multiplier'], p['min_char_width'], f"{acc:.4f}"])
        if best is None or acc > best:
            best = acc
            best_params = p
            best_confs = confs

print('Best params:', best_params, 'accuracy:', best)

# write best confusions
out_csv = os.path.join(OUT_DIR, 'confusions_best.csv')
with open(out_csv, 'w', newline='', encoding='utf-8') as fh:
    cw = csv.writer(fh)
    cw.writerow(['gt', 'pred', 'count'])
    for (a, b), cnt in best_confs.most_common():
        cw.writerow([a, b, cnt])

print('Wrote confusions to', out_csv)
