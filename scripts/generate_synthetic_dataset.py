"""Generate a small synthetic Hindi/Telugu dataset (images + .txt labels).

Creates `data/eval/images/` and `data/eval/labels/` with matching basenames.
"""
from PIL import Image, ImageDraw, ImageFont
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT_IMG = os.path.join(ROOT, 'data', 'eval', 'images')
OUT_GT = os.path.join(ROOT, 'data', 'eval', 'labels')

os.makedirs(OUT_IMG, exist_ok=True)
os.makedirs(OUT_GT, exist_ok=True)

samples = {
    'hindi_01': 'यह एक परीक्षण पंक्ति है।',
    'hindi_02': 'हस्तलिखित डेटा की सटीकता जाँचें।',
    'hindi_03': 'संख्या १२३ और पत्र ABC',
    'telugu_01': 'ఇది ఒక పరీక్ష పంక్తి.',
    'telugu_02': 'హస్తలిఖిత పాఠ్యాన్ని పరీక్షించండి.',
    'telugu_03': 'సంఖ్యలు ১২৩ మరియు అక్షరాలు ABC',
}

for name, text in samples.items():
    img_path = os.path.join(OUT_IMG, f"{name}.png")
    gt_path = os.path.join(OUT_GT, f"{name}.txt")

    W, H = 1200, 1600
    img = Image.new('RGB', (W, H), color='white')
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype('arial.ttf', 48)
    except Exception:
        font = ImageFont.load_default()

    y = 80
    # write the text multiple times to create some content
    for i in range(3):
        draw.text((60, y), text, fill='black', font=font)
        y += 80

    img.save(img_path)
    with open(gt_path, 'w', encoding='utf-8') as f:
        f.write(text)

print('Generated synthetic dataset in data/eval/')
