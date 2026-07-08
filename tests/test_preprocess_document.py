from PIL import Image, ImageDraw
from utils.layout_pipeline import Alignment, Block, BlockType, LayoutDocument, RecognizedLine
from utils.ocr_engine import _merge_doc_results
from utils.segment import prepare_document_image


def test_prepare_document_image_rotates_and_crops():
    base = Image.new('L', (240, 120), 255)
    draw = ImageDraw.Draw(base)
    draw.rectangle((20, 20, 180, 70), fill=0)
    draw.text((30, 25), 'HELLO', fill=0)

    rotated = base.rotate(90, expand=True, fillcolor=255)
    prepared = prepare_document_image(rotated, segmentation_params={'deskew_max_degrees': 45.0})

    assert prepared.size[0] < rotated.size[0]
    assert prepared.size[1] < rotated.size[1]
    assert prepared.size[0] > 0 and prepared.size[1] > 0


def test_merge_doc_results_preserves_text_from_both_engines():
    printed = LayoutDocument(
        blocks=[Block(type=BlockType.PARAGRAPH, lines=[RecognizedLine(text='printed', alignment=Alignment.LEFT, y=0, confidence=0.8)])],
        mean_confidence=0.8,
        char_count=7,
    )
    handwritten = LayoutDocument(
        blocks=[Block(type=BlockType.PARAGRAPH, lines=[RecognizedLine(text='handwritten', alignment=Alignment.LEFT, y=0, confidence=0.6)])],
        mean_confidence=0.6,
        char_count=11,
    )

    merged = _merge_doc_results(printed, handwritten)

    assert merged.plain_text == 'printed\n\nhandwritten'
    assert merged.char_count == 18
    assert merged.mean_confidence == 0.7
