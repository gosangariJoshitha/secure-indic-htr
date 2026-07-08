from PIL import Image
from types import SimpleNamespace
import numpy as np

from utils import ocr_engine


def test_normalize_language_handles_auto_and_script_values():
    assert ocr_engine._normalize_language('Auto') is None
    assert ocr_engine._normalize_language('auto') is None
    assert ocr_engine._normalize_language('Hindi') == 'Hindi'
    assert ocr_engine._normalize_language('Telugu') == 'Telugu'
    assert ocr_engine._normalize_language('  hindi  ') == 'Hindi'
    assert ocr_engine._normalize_language('tElUgU') == 'Telugu'
    assert ocr_engine._normalize_language('unknown') is None


def test_detect_script_language_prefers_stronger_script_confidence(monkeypatch):
    sample_image = Image.new('RGB', (100, 100), 'white')
    fake_lines = [
        SimpleNamespace(is_blank=False, words=[
            SimpleNamespace(chars=[SimpleNamespace(x=0, y=0, w=10, h=10), SimpleNamespace(x=10, y=0, w=10, h=10)])
        ])
    ]

    def fake_segment_page(image, enhanced=False, language=None, segmentation_params=None):
        return fake_lines, np.array(image.convert('L'))

    class FakePredictor:
        def predict_char(self, crop, language=None):
            if language == 'Hindi':
                return 'क', 0.8
            if language == 'Telugu':
                return 'అ', 0.2
            return '', 0.0

    monkeypatch.setattr(ocr_engine, 'segment_page', fake_segment_page)
    monkeypatch.setattr(ocr_engine, 'get_predictor', lambda: FakePredictor())

    result = ocr_engine._detect_script_language(sample_image, max_chars=2)
    assert result == 'Hindi'


def test_detect_script_language_returns_none_when_no_text(monkeypatch):
    sample_image = Image.new('RGB', (50, 50), 'white')

    def fake_segment_page(image, enhanced=False, language=None, segmentation_params=None):
        return [], image.convert('L')

    monkeypatch.setattr(ocr_engine, 'segment_page', fake_segment_page)
    monkeypatch.setattr(ocr_engine, 'get_predictor', lambda: SimpleNamespace(predict_char=lambda crop, language=None: ('', 0.0)))

    assert ocr_engine._detect_script_language(sample_image) is None


def test_run_ocr_auto_sets_detected_script(monkeypatch):
    image = Image.new('RGB', (100, 100), 'white')

    def fake_prepare_document_image(img, segmentation_params=None, language=None):
        return img

    def fake_detect_script_language(img):
        return 'Telugu'

    def fake_looks_like_single_character(img):
        return False

    fake_doc = ocr_engine.LayoutDocument(
        blocks=[ocr_engine.Block(type=ocr_engine.BlockType.PARAGRAPH, lines=[ocr_engine.RecognizedLine(text='test', alignment=ocr_engine.Alignment.LEFT, y=0, confidence=1.0)])],
        page_width=100,
        page_height=100,
        mean_confidence=1.0,
        char_count=4,
    )

    def fake_handwritten_fallback(img, enhanced=False, language=None, segmentation_params=None):
        return fake_doc, None

    monkeypatch.setattr(ocr_engine, 'prepare_document_image', fake_prepare_document_image)
    monkeypatch.setattr(ocr_engine, '_detect_script_language', fake_detect_script_language)
    monkeypatch.setattr(ocr_engine, '_looks_like_single_character', fake_looks_like_single_character)
    monkeypatch.setattr(ocr_engine, '_try_handwritten_fallback', fake_handwritten_fallback)

    result_doc, _, _ = ocr_engine.run_ocr(image, mode='auto', language='Auto')
    assert getattr(result_doc, 'detected_script', None) == 'Telugu'
