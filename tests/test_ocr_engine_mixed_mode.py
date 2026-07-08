from PIL import Image

from utils import ocr_engine
from utils.layout_pipeline import Alignment, Block, BlockType, LayoutDocument, RecognizedLine


def test_run_ocr_mixed_mode_falls_back_to_handwritten(monkeypatch):
    image = Image.new('RGB', (120, 80), 'white')

    def fake_run_tesseract(*args, **kwargs):
        raise RuntimeError('tesseract unavailable')

    fallback_doc = LayoutDocument(
        blocks=[Block(type=BlockType.PARAGRAPH, lines=[RecognizedLine(text='hola', alignment=Alignment.LEFT, y=0, indent_level=0, confidence=0.95)])],
        page_width=120,
        page_height=80,
        mean_confidence=0.95,
        char_count=4,
    )

    def fake_handwritten_fallback(*args, **kwargs):
        return fallback_doc, None

    monkeypatch.setattr(ocr_engine, '_run_tesseract', fake_run_tesseract)
    monkeypatch.setattr(ocr_engine, '_try_handwritten_fallback', fake_handwritten_fallback)

    result_doc, _, engine = ocr_engine.run_ocr(image, mode='mixed')

    assert engine == 'handwritten'
    assert result_doc.plain_text == 'hola'
