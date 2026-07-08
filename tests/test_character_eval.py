from pathlib import Path
from PIL import Image

from scripts.evaluate_ocr import evaluate


def test_character_eval_runs_on_sample(tmp_path):
    images_dir = tmp_path / 'images'
    gt_dir = tmp_path / 'labels'
    images_dir.mkdir()
    gt_dir.mkdir()

    img = Image.new('L', (32, 32), 255)
    img.save(images_dir / 'sample.png')
    (gt_dir / 'sample.txt').write_text('अ', encoding='utf-8')

    evaluate(str(images_dir), str(gt_dir))

    assert (images_dir / 'confusions.csv').exists()
