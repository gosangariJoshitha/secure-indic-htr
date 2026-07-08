
"""scripts/evaluate_ocr.py
Light evaluation harness for the OCR pipeline.

Usage:
    python scripts/evaluate_ocr.py --images-dir path/to/images --gt-dir path/to/ground_truth

Ground truth files must be plain text files with the same base name
as the image and a `.txt` extension (e.g. `scan01.jpg` + `scan01.txt`).

The script runs the app's `run_layout_pipeline` on each image and
computes character-level edit distance, percent-accuracy, and a basic
substitution confusion table saved as `confusions.csv` in the output dir.
"""
from __future__ import annotations

import argparse
import os
import csv
import sys
from collections import Counter
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from utils.layout_pipeline import run_layout_pipeline
from utils.predictor import get_predictor


def levenshtein_alignment(s: str, t: str):
    n, m = len(s), len(t)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if s[i - 1] == t[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)

    i, j = n, m
    aligned = []
    while i > 0 or j > 0:
        if i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + (0 if s[i - 1] == t[j - 1] else 1):
            aligned.append((s[i - 1], t[j - 1]))
            i -= 1
            j -= 1
        elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            aligned.append((s[i - 1], ""))
            i -= 1
        else:
            aligned.append(("", t[j - 1]))
            j -= 1
    aligned.reverse()
    return aligned


def evaluate(images_dir: str, gt_dir: str, enhanced: bool = False, language: str | None = None):
    images = [p for p in os.listdir(images_dir) if p.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff'))]
    images.sort()
    total_gt_chars = 0
    total_correct_chars = 0
    confusions = Counter()
    predictor = get_predictor()

    for img_name in images:
        base = os.path.splitext(img_name)[0]
        img_path = os.path.join(images_dir, img_name)
        gt_path = os.path.join(gt_dir, base + '.txt')
        if not os.path.exists(gt_path):
            print(f"Skipping {img_name}: no ground-truth file found ({gt_path})")
            continue

        with Image.open(img_path) as im:
            pred_char, conf = predictor.predict_char(im, language=language)

        with open(gt_path, 'r', encoding='utf-8') as fh:
            gt = fh.read().replace('\r', '').strip()

        if gt:
            total_gt_chars += 1
            total_correct_chars += int(pred_char == gt)
            if pred_char != gt:
                confusions[(gt, pred_char)] += 1

    overall_accuracy = (total_correct_chars / total_gt_chars) if total_gt_chars else 0.0
    print(f"Images evaluated: {total_gt_chars}")
    print(f"Total GT chars: {total_gt_chars}")
    print(f"Total correct chars: {total_correct_chars}")
    print(f"Char-level accuracy: {overall_accuracy*100:.2f}%")

    out_csv = os.path.join(images_dir, 'confusions.csv')
    with open(out_csv, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.writer(fh)
        writer.writerow(['gt_char', 'pred_char', 'count'])
        for (a, b), cnt in confusions.most_common():
            writer.writerow([a, b, cnt])

    print(f"Saved confusions to: {out_csv}")


def main():
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    p = argparse.ArgumentParser()
    p.add_argument('--images-dir', required=True)
    p.add_argument('--gt-dir', required=True)
    p.add_argument('--enhanced', action='store_true')
    p.add_argument('--language', default=None)
    args = p.parse_args()

    evaluate(args.images_dir, args.gt_dir, enhanced=args.enhanced, language=args.language)


if __name__ == '__main__':
    main()
