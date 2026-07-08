from PIL import Image
import os

from utils.ocr_engine import run_ocr


import pytest

@pytest.mark.skipif(not os.path.exists(os.path.join('data', 'eval', 'images', 'telugu_00000.png')), reason="Regression test image not found")
def test_telugu_sample_matches_expected():
    """Regression: ensure `telugu_00000.png` output stays stable.

    This records the current observed output and asserts the OCR pipeline
    produces the same result. It guards against accidental regressions
    when refactoring preprocessing/predictor logic.
    """
    img_path = os.path.join('data', 'eval', 'images', 'telugu_00000.png')
    img = Image.open(img_path)

    doc, overlay, engine = run_ocr(img, mode='auto', enhanced=True, language='Telugu')

    # Expected text captured from the current pipeline run. If you intentionally
    # improve the model and want to update this golden value, update this test.
    expected = 'గ్రుయ్రుఘో'
    assert doc.plain_text.strip() == expected
