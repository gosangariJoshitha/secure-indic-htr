from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Iterable

from PIL import Image, UnidentifiedImageError


HINDI_CLASS_MAP = {
    "character_1_ka": "क",
    "character_2_kha": "ख",
    "character_3_ga": "ग",
    "character_4_gha": "घ",
    "character_5_kna": "ङ",
    "character_6_cha": "च",
    "character_7_chha": "छ",
    "character_8_ja": "ज",
    "character_9_jha": "झ",
    "character_10_yna": "ञ",
    "character_11_taamatar": "ट",
    "character_12_thaa": "ठ",
    "character_13_daa": "ड",
    "character_14_dhaa": "ढ",
    "character_15_adna": "ण",
    "character_16_tabala": "त",
    "character_17_tha": "थ",
    "character_18_da": "द",
    "character_19_dha": "ध",
    "character_20_na": "न",
    "character_21_pa": "प",
    "character_22_pha": "फ",
    "character_23_ba": "ब",
    "character_24_bha": "भ",
    "character_25_ma": "म",
    "character_26_yaw": "य",
    "character_27_ra": "र",
    "character_28_la": "ल",
    "character_29_waw": "व",
    "character_30_motosaw": "श",
    "character_31_petchiryakha": "ष",
    "character_32_patalosaw": "स",
    "character_33_ha": "ह",
    "character_34_chhya": "क्ष",
    "character_35_tra": "त्र",
    "character_36_gya": "ज्ञ",
}


TELUGU_CLASS_MAP = {
    "Telugu_a": "అ",
    "Telugu_aa": "ఆ",
    "Telugu_i": "ఇ",
    "Telugu_ii": "ఈ",
    "Telugu_u": "ఉ",
    "Telugu_uu": "ఊ",
    "Telugu_e": "ఎ",
    "Telugu_ee": "ఏ",
    "Telugu_ai": "ఐ",
    "Telugu_o": "ఒ",
    "Telugu_oo": "ఓ",
    "Telugu_ou": "ఔ",
    "Telugu_ka": "క",
    "Telugu_kha": "ఖ",
    "Telugu_ga": "గ",
    "Telugu_gha": "ఘ",
    "Telugu_cha": "చ",
    "Telugu_chha": "ఛ",
    "Telugu_ja": "జ",
    "Telugu_jha": "ఝ",
    "Telugu_ta": "త",
    "Telugu_ttha": "ట",
    "Telugu_da": "ద",
    "Telugu_dda": "డ",
    "Telugu_na": "న",
    "Telugu_pa": "ప",
    "Telugu_pha": "ఫ",
    "Telugu_ba": "బ",
    "Telugu_bha": "భ",
    "Telugu_ma": "మ",
    "Telugu_ya": "య",
    "Telugu_ra": "ర",
    "Telugu_la": "ల",
    "Telugu_lla": "ళ",
    "Telugu_va": "వ",
    "Telugu_sha": "శ",
    "Telugu_sa": "స",
    "Telugu_ha": "హ",
    "Telugu_nna": "ణ",
    "Telugu_ksa": "క్ష",
    "Telugu_rra": "ఱ",
    "Telugu_jna": "జ్ఞ",
}


def iter_image_files(root: Path) -> Iterable[Path]:
    for p in root.rglob('*'):
        if p.is_file() and p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}:
            yield p


def convert_dataset(src_root: Path, out_images_dir: Path, out_labels_dir: Path, language: str, limit: int | None = None) -> int:
    out_images_dir.mkdir(parents=True, exist_ok=True)
    out_labels_dir.mkdir(parents=True, exist_ok=True)

    if language == 'hindi':
        class_map = HINDI_CLASS_MAP
    elif language == 'telugu':
        class_map = TELUGU_CLASS_MAP
    else:
        raise ValueError(f'Unsupported language: {language}')

    count = 0
    image_dirs = []
    for d in sorted(src_root.rglob('*')):
        if d.is_dir() and any(p.is_file() and p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'} for p in d.iterdir()):
            image_dirs.append(d)

    for class_folder in image_dirs:
        label = class_map.get(class_folder.name)
        if label is None:
            if language == 'hindi':
                token = class_folder.name.replace('character_', '')
            else:
                token = class_folder.name.replace('Telugu_', '')
            label = token if token else class_folder.name

        for image_path in sorted(iter_image_files(class_folder)):
            try:
                with Image.open(image_path) as im:
                    im = im.convert('L')
                    if im.size[0] < 8 or im.size[1] < 8:
                        continue
                    stem = f"{language}_{count:05d}"
                    out_image_path = out_images_dir / f"{stem}.png"
                    out_label_path = out_labels_dir / f"{stem}.txt"
                    im.save(out_image_path)
                    out_label_path.write_text(label, encoding='utf-8')
                    count += 1
                    if limit is not None and count >= limit:
                        return count
            except (UnidentifiedImageError, OSError):
                continue
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--src', default='data/eval/hindi_raw')
    parser.add_argument('--out-images', default='data/eval/images')
    parser.add_argument('--out-labels', default='data/eval/labels')
    parser.add_argument('--language', choices=['hindi', 'telugu'], required=True)
    parser.add_argument('--limit', type=int, default=None)
    args = parser.parse_args()

    src = Path(args.src)
    out_images = Path(args.out_images)
    out_labels = Path(args.out_labels)
    count = convert_dataset(src, out_images, out_labels, args.language, limit=args.limit)
    print(f'Converted {count} images for {args.language}')
    print(f'Images -> {out_images}')
    print(f'Labels -> {out_labels}')


if __name__ == '__main__':
    main()
