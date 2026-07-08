"""scripts/convert_dataset_to_eval.py
Convert a raw character-folder dataset into the evaluation layout used by
`scripts/evaluate_ocr.py` (one image per file, matching `.txt` GT file).

Usage:
    python scripts/convert_dataset_to_eval.py --src data/eval/hindi_raw --lang Hindi
    python scripts/convert_dataset_to_eval.py --src data/eval/telugu_raw --lang Telugu
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from utils.constants import LABEL_TO_GLYPH


def find_label_for_parent(parent: str, language: str) -> str | None:
    parent = parent.strip()
    if language.lower().startswith('tel'):
        candidate = f"Telugu_{parent}"
        if candidate in LABEL_TO_GLYPH:
            return candidate
        # try suffix match
        for k in LABEL_TO_GLYPH:
            if k.startswith('Telugu_') and k.endswith('_' + parent):
                return k
        # last resort: maybe the parent is already a full label
        if parent in LABEL_TO_GLYPH:
            return parent
        return None

    if language.lower().startswith('hin'):
        # try exact matches first
        for k in LABEL_TO_GLYPH:
            if k.startswith('Hindi_') and k.endswith('_' + parent):
                return k
        # try parent as full label
        for k in LABEL_TO_GLYPH:
            if k.startswith('Hindi_') and k == parent:
                return k
        # heuristic: parent might be like '1_ka' or 'ka'
        for k in LABEL_TO_GLYPH:
            if k.startswith('Hindi_') and parent in k:
                return k
        return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--src', required=True)
    p.add_argument('--lang', required=True)
    p.add_argument('--out-images', default='data/eval/images')
    p.add_argument('--out-labels', default='data/eval/labels')
    args = p.parse_args()

    src = Path(args.src)
    out_images = Path(args.out_images)
    out_labels = Path(args.out_labels)
    out_images.mkdir(parents=True, exist_ok=True)
    out_labels.mkdir(parents=True, exist_ok=True)

    exts = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff')
    count = 0
    skipped = 0

    for img in sorted(src.rglob('*')):
        if not img.is_file():
            continue
        if img.suffix.lower() not in exts:
            continue
        parent = img.parent.name
        label_key = find_label_for_parent(parent, args.lang)
        if label_key is None:
            print(f"Skipping {img} — could not map parent '{parent}' to a label")
            skipped += 1
            continue

        glyph = LABEL_TO_GLYPH.get(label_key)
        if glyph is None:
            print(f"Skipping {img} — label '{label_key}' not in LABEL_TO_GLYPH")
            skipped += 1
            continue

        count += 1
        out_name = f"{args.lang.lower()}_{parent}_{count:05d}{img.suffix.lower()}"
        dst = out_images / out_name
        shutil.copyfile(img, dst)

        label_file = out_labels / (dst.stem + '.txt')
        label_file.write_text(glyph, encoding='utf-8')

    print(f"Copied {count} files to {out_images}; skipped {skipped} files")


if __name__ == '__main__':
    main()
