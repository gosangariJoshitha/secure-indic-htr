# Fine-tuning SecureDocAI OCR

This document outlines a minimal path to fine-tune the CRNN/CTC model
on a small, targeted dataset of handwriting samples (e.g. Hindi).

High-level steps

1. Prepare a dataset of line-level images and matching text labels.
   - Directory layout: `data/finetune/images/` and `data/finetune/labels/`.
   - Each image file (PNG/JPG) must have a `.txt` file with the same base
     name containing the transcription.
2. Reuse the notebooks in the repository (`phase2_model_training.ipynb`) as
   they show the exact preprocessing and augmentation used during initial
   training. Aim to match input size (width=128, height=64) and normalization.
3. Option A — Small dataset, quick fine-tune (CPU possible but slow):
   - Use the notebook training loop with a low learning rate (e.g. 1e-4),
     small batch size (8–16), and a few epochs (5–20).
4. Option B — Full retrain on larger dataset (GPU recommended):
   - Use the same architecture and augmentations as in `phase2_model_training.ipynb`.

Practical tips

- Normalize preprocessing in `utils/segment.py` and `utils/predictor.py` to match
  what the model expects (the notebooks define the exact pipeline).
- Use the `scripts/evaluate_ocr.py` tool to run before/after comparisons.
- If you have limited labeled data, focus on a smaller character subset
  (common Hindi glyphs) and use aggressive augmentation.

If you'd like, I can generate a runnable fine-tune script (PyTorch) that
implements the same model/optimizer/CTC pipeline used in the notebooks.
That requires confirming the exact model class name and the training
hyperparameters stored in the notebooks; I can extract them for you.
