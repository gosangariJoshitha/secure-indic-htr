from utils.predictor import get_label_candidates


def test_hindi_candidates_are_hindi_only():
    labels = get_label_candidates(language="Hindi")
    assert labels
    assert all(label.startswith("Hindi_") for label in labels)
    assert not any(label.startswith("Telugu_") for label in labels)


def test_telugu_candidates_are_telugu_only():
    labels = get_label_candidates(language="Telugu")
    assert labels
    assert all(label.startswith("Telugu_") for label in labels)
    assert not any(label.startswith("Hindi_") for label in labels)
