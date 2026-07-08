"""
test_model_load.py
===================
Run this BEFORE `streamlit run app.py` to confirm the model loads cleanly.

    python test_model_load.py

If you see "Missing keys" or "Unexpected keys" in the output, copy that
output back so the CNN_BiLSTM_CTC architecture in utils/predictor.py can
be corrected to match your exact training notebook (phase2_model_training.ipynb).
"""

from PIL import Image
import numpy as np

from utils.predictor import get_predictor, IMG_HEIGHT, IMG_WIDTH

print("Loading model...")
predictor = get_predictor()
print(f"Model loaded on device: {predictor.device}")
print(f"Number of classes: {predictor.num_classes}")

# Build a blank grayscale dummy image at the exact training input size
# (64x128, single channel) just to confirm the forward pass runs end-to-end.
dummy = Image.fromarray(np.full((IMG_HEIGHT, IMG_WIDTH), 255, dtype=np.uint8))
char, confidence = predictor.predict_char(dummy)

print(f"Dummy prediction character: {char!r}")
print(f"Dummy prediction confidence: {confidence:.4f}")
print()
print("If you got this far with no errors, the model loads and runs correctly.")
print()
print("Next: run a real segmentation+recognition pass with:")
print("    from PIL import Image")
print("    from utils.layout_pipeline import run_layout_pipeline")
print("    doc = run_layout_pipeline(Image.open('your_scan.jpg'))")
print("    print(doc.plain_text)")
