from types import SimpleNamespace

from utils.helpers import get_latest_ocr_context, store_latest_ocr_context


def test_store_and_retrieve_latest_ocr_context():
    state = {}
    doc = SimpleNamespace(mean_confidence=0.91, char_count=17)

    payload = store_latest_ocr_context(
        state,
        doc=doc,
        elapsed=2.4,
        overlay=None,
        engine_used="mixed",
        edited_text="hello world",
        filename="scan.png",
        language="Hindi",
    )

    assert payload["edited_text"] == "hello world"
    assert state["latest_ocr_context"]["engine_used"] == "mixed"
    assert get_latest_ocr_context(state)["doc"].char_count == 17
    assert get_latest_ocr_context(state)["metrics"]["confidence"] == 0.91
