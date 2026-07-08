"""
utils/predictor.py
==================
Loads the trained handwriting-OCR model and runs inference on a SINGLE
CHARACTER crop. This wraps the exact `CNN_BiLSTM_CTC` class defined in
phase2_model_training.ipynb — copied here verbatim, not reverse-engineered,
so the weights load with zero shape mismatches.
"""

from __future__ import annotations

import io
import time
import logging
import hashlib
import json
import functools
from pathlib import Path

import torch
import torch.nn as nn
import cv2
import numpy as np
from PIL import Image

from config import MODEL_PATH, LABEL_MAP_PATH, FL_MODEL_PATH, FORCE_CPU
from utils.constants import LABEL_TO_GLYPH, label_to_char

logger = logging.getLogger("SecureDocAI.Predictor")

# Fixed input size the model was trained on (phase1/phase2 IMG_HEIGHT/IMG_WIDTH).
IMG_HEIGHT = 64
IMG_WIDTH = 128


class CNN_BiLSTM_CTC(nn.Module):
    """
    Copied verbatim (architecture-for-architecture) from
    phase2_model_training.ipynb, Cell 6, so model_best.pth's state_dict
    loads with no missing/unexpected keys.
    """

    def __init__(self, num_classes: int):
        super().__init__()

        self.cnn = nn.Sequential(
            nn.Conv2d(1, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.GELU(),
            nn.MaxPool2d(2, 2),

            nn.Conv2d(64, 128, 3, padding=1),
            nn.BatchNorm2d(128),
            nn.GELU(),
            nn.MaxPool2d(2, 2),

            nn.Conv2d(128, 256, 3, padding=1),
            nn.BatchNorm2d(256),
            nn.GELU(),

            nn.Conv2d(256, 256, 3, padding=1),
            nn.BatchNorm2d(256),
            nn.GELU(),
            nn.MaxPool2d((2, 1), (2, 1)),

            nn.Conv2d(256, 512, 3, padding=1),
            nn.BatchNorm2d(512),
            nn.GELU(),

            nn.Conv2d(512, 512, 3, padding=1),
            nn.BatchNorm2d(512),
            nn.GELU(),
            nn.MaxPool2d((2, 1), (2, 1)),

            nn.Dropout2d(0.30),
        )

        self.bilstm = nn.LSTM(
            input_size=512 * 4,
            hidden_size=256,
            num_layers=2,
            bidirectional=True,
            batch_first=True,
            dropout=0.30,
        )

        self.layer_norm = nn.LayerNorm(512)
        self.fc = nn.Linear(512, num_classes + 1)

    def forward(self, x):
        features = self.cnn(x)                       # (B, C, H, W)
        b, c, h, w = features.size()
        features = features.permute(0, 3, 1, 2)        # (B, W, C, H)
        features = features.reshape(b, w, c * h)       # (B, W, C*H)

        lstm_out, _ = self.bilstm(features)            # (B, W, 512)
        lstm_out = self.layer_norm(lstm_out)
        output = self.fc(lstm_out)                     # (B, W, num_classes+1)
        output = output.permute(1, 0, 2)                # (T=W, B, num_classes+1)
        return output


def decode_ctc_single_char(output: torch.Tensor, num_classes: int):
    """
    Copied verbatim from phase2_model_training.ipynb. Picks the single
    highest-confidence non-blank (class, timestep) pair across the WHOLE
    output for each batch item — this model predicts exactly one character
    per call, by design.

    Args:
        output: raw model output, shape (T, B, num_classes+1)
    Returns:
        (pred_classes, confidences) each shape (B,)
    """
    probs = output.log_softmax(2).exp()              # (T, B, C+1)
    T, B, C = probs.size()

    probs_no_blank = probs.clone()
    probs_no_blank[:, :, num_classes] = 0.0           # never let blank "win"

    flat = probs_no_blank.permute(1, 0, 2).reshape(B, -1)   # (B, T*C)
    best_flat_idx = flat.argmax(dim=1)
    confidences = flat.gather(1, best_flat_idx.unsqueeze(1)).squeeze(1)
    pred_classes = best_flat_idx % C

    return pred_classes, confidences


def decode_ctc_top_k(output: torch.Tensor, num_classes: int, k: int = 5) -> list[tuple[int, float]]:
    """Decodes the top K predictions with confidences from the model output logits."""
    probs = output.log_softmax(2).exp()              # (T, B=1, C+1)
    T, B, C = probs.size()
    probs_no_blank = probs.clone()
    probs_no_blank[:, :, num_classes] = 0.0          # never let blank win
    
    flat = probs_no_blank.permute(1, 0, 2).reshape(B, -1)  # (B, T*C)
    top_vals, top_indices = torch.topk(flat, k, dim=1)
    
    results = []
    for i in range(k):
        conf = float(top_vals[0, i].item())
        pred_class = int(top_indices[0, i].item() % C)
        results.append((pred_class, conf))
    return results


def get_label_candidates(language: str | None = None) -> list[str]:
    """Return label names compatible with the selected script."""
    if not language:
        return []
    lang = (language or "").lower()
    if lang.startswith("h"):
        return [k for k in LABEL_TO_GLYPH.keys() if k.startswith("Hindi_")]
    if lang.startswith("t"):
        return [k for k in LABEL_TO_GLYPH.keys() if k.startswith("Telugu_")]
    return []


class HandwritingPredictor:
    """Wraps CNN_BiLSTM_CTC with the exact preprocessing + decode the model was trained/evaluated with.
    
    Supports model fallback: if primary model confidence < threshold, automatically tries fallback model
    and returns the best result. This is transparent to the caller.
    """

    def __init__(self, model_path: Path = MODEL_PATH, label_map_path: Path = LABEL_MAP_PATH,
                 fallback_model_path: Path | None = None, confidence_threshold: float = 0.6,
                 device: str | None = None):
        self.device = device or ("cuda" if (torch.cuda.is_available() and not FORCE_CPU) else "cpu")
        self.confidence_threshold = confidence_threshold
        self.temperature = 1.25

        with open(label_map_path, "r", encoding="utf-8") as f:
            label_data = json.load(f)
        self.idx2label = {int(k): v for k, v in label_data["idx2label"].items()}
        self.num_classes = label_data["num_classes"]

        self.model = CNN_BiLSTM_CTC(num_classes=self.num_classes)
        self._load_weights(MODEL_PATH)
        self.model.to(self.device)
        self.model.eval()
        
        # Load fallback model if provided
        self.fallback_model = None
        self.fallback_model_path = fallback_model_path
        if fallback_model_path and fallback_model_path.exists():
            self.fallback_model = CNN_BiLSTM_CTC(num_classes=self.num_classes)
            self._load_weights_into(self.fallback_model, fallback_model_path)
            self.fallback_model.to(self.device)
            self.fallback_model.eval()

        # Warmup GPU / device
        try:
            warmup_tensor = torch.zeros((1, 1, IMG_HEIGHT, IMG_WIDTH), device=self.device)
            _ = self.model(warmup_tensor)
            if self.fallback_model is not None:
                _ = self.fallback_model(warmup_tensor)
        except Exception as e:
            logger.warning(f"Device warmup failed: {e}")

        # V2 Metadata & Metrics
        self.metadata = {
            "model_version": "SecureDocAI V2 Predictor",
            "dataset": "DHCD + Telugu Syllables Dataset",
            "trained_date": "2026-06",
            "num_classes": self.num_classes,
            "language": "Hindi + Telugu (DHCD-style)",
            "input_size": f"{IMG_HEIGHT}x{IMG_WIDTH}"
        }

        self.stats = {
            "characters_predicted": 0,
            "total_confidence": 0.0,
            "total_inference_time_ms": 0.0,
            "fallback_usage_count": 0,
            "gpu_usage": "CUDA" if "cuda" in self.device else "CPU"
        }

        # Local caches
        self._prediction_cache = {}
        self.latest_top5 = []

    def _hash_pil_image(self, image: Image.Image) -> str:
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return hashlib.md5(buf.getvalue()).hexdigest()

    def _load_weights(self, model_path: Path):
        checkpoint = torch.load(model_path, map_location=self.device, weights_only=False)
        state_dict = checkpoint["model_state"] if isinstance(checkpoint, dict) and "model_state" in checkpoint else checkpoint

        result = self.model.load_state_dict(state_dict, strict=False)
        if result.missing_keys:
            print(f"[predictor] WARNING - missing keys when loading weights: {result.missing_keys}")
        if result.unexpected_keys:
            print(f"[predictor] WARNING - unexpected keys when loading weights: {result.unexpected_keys}")

    def _load_weights_into(self, model_obj: nn.Module, model_path: Path):
        """Load weights into an arbitrary model object."""
        checkpoint = torch.load(model_path, map_location=self.device, weights_only=False)
        state_dict = checkpoint["model_state"] if isinstance(checkpoint, dict) and "model_state" in checkpoint else checkpoint

        result = model_obj.load_state_dict(state_dict, strict=False)
        if result.missing_keys:
            print(f"[predictor] WARNING (fallback) - missing keys: {result.missing_keys}")
        if result.unexpected_keys:
            print(f"[predictor] WARNING (fallback) - unexpected keys: {result.unexpected_keys}")

    def _preprocess_variant(self, gray: np.ndarray, invert: bool = False,
                            dilate: bool = False, blur: bool = False) -> np.ndarray:
        work = gray.astype(np.uint8)
        if blur:
            work = cv2.GaussianBlur(work, (3, 3), 0)
        if invert:
            work = 255 - work

        _, binarized = cv2.threshold(work, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        white = np.sum(binarized > 127)
        black = np.sum(binarized <= 127)
        if white > black:
            binarized = cv2.bitwise_not(binarized)

        if dilate:
            kernel = np.ones((2, 2), np.uint8)
            binarized = cv2.dilate(binarized, kernel, iterations=1)

        kernel = np.ones((2, 2), np.uint8)
        binarized = cv2.morphologyEx(binarized, cv2.MORPH_OPEN, kernel)

        h, w = binarized.shape
        target_h, target_w = IMG_HEIGHT, IMG_WIDTH
        scale = min(target_w / max(1, w), target_h / max(1, h))
        new_w = max(12, int(round(w * scale)))
        new_h = max(12, int(round(h * scale)))
        resized = cv2.resize(binarized, (new_w, new_h), interpolation=cv2.INTER_AREA)

        canvas = np.full((target_h, target_w), 255, dtype=np.uint8)
        x0 = (target_w - new_w) // 2
        y0 = (target_h - new_h) // 2
        canvas[y0:y0 + new_h, x0:x0 + new_w] = resized

        return canvas.astype(np.float32) / 255.0

    def _preprocess_variants(self, image: Image.Image, enhanced_preprocessing: bool = False) -> list[torch.Tensor]:
        gray = np.array(image.convert("L"))
        variants = [
            self._preprocess_variant(gray, invert=False, dilate=False, blur=False),
            self._preprocess_variant(gray, invert=True, dilate=False, blur=False),
            self._preprocess_variant(gray, invert=False, dilate=True, blur=False),
            self._preprocess_variant(gray, invert=False, dilate=False, blur=True),
        ]
        
        def _make_scale_variant(scale_to: str):
            work = gray.astype(np.uint8)
            _, binarized = cv2.threshold(work, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            white = np.sum(binarized > 127)
            black = np.sum(binarized <= 127)
            if white > black:
                binarized = cv2.bitwise_not(binarized)

            kernel = np.ones((2, 2), np.uint8)
            binarized = cv2.morphologyEx(binarized, cv2.MORPH_OPEN, kernel)

            h, w = binarized.shape
            target_h, target_w = IMG_HEIGHT, IMG_WIDTH
            if scale_to == 'height':
                scale = target_h / max(1, h)
            else:
                scale = target_w / max(1, w)
            new_w = max(12, int(round(w * scale)))
            new_h = max(12, int(round(h * scale)))
            resized = cv2.resize(binarized, (new_w, new_h), interpolation=cv2.INTER_AREA)

            if new_w > target_w or new_h > target_h:
                scale2 = min(target_w / new_w, target_h / new_h)
                new_w = max(12, int(round(new_w * scale2)))
                new_h = max(12, int(round(new_h * scale2)))
                resized = cv2.resize(resized, (new_w, new_h), interpolation=cv2.INTER_AREA)

            canvas = np.full((target_h, target_w), 255, dtype=np.uint8)
            x0 = max(0, (target_w - new_w) // 2)
            y0 = max(0, (target_h - new_h) // 2)
            canvas[y0:y0 + new_h, x0:x0 + new_w] = resized
            return canvas.astype(np.float32) / 255.0

        variants.append(_make_scale_variant('height'))
        variants.append(_make_scale_variant('width'))

        # V2 Preprocessing Enhancements: CLAHE + Median Blur (Only when enhanced_preprocessing is set)
        if enhanced_preprocessing:
            try:
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                gray_clahe = clahe.apply(gray)
                gray_blur = cv2.medianBlur(gray_clahe, 3)
                variants.append(self._preprocess_variant(gray_blur, invert=False, dilate=False, blur=False))
            except Exception:
                pass

        return [torch.from_numpy(v).unsqueeze(0).unsqueeze(0).to(self.device) for v in variants]

    def _preprocess(self, image: Image.Image) -> torch.Tensor:
        return self._preprocess_variants(image, enhanced_preprocessing=False)[0]

    def _language_filtered_candidates(self, language: str | None = None) -> list[int]:
        if not language or language.lower() in ("auto", "mixed", "unknown"):
            return list(self.idx2label.keys())
        allowed = set(get_label_candidates(language=language))
        if not allowed:
            return []
        return [idx for idx, label in self.idx2label.items() if label in allowed]

    def _infer_with_model(self, tensors: list[torch.Tensor], model: nn.Module, language: str | None = None) -> tuple[str, float]:
        """Run inference with a specific model and return (char, confidence)."""
        class_scores: dict[int, float] = {}
        allowed_indices = set(self._language_filtered_candidates(language=language))
        
        # Populate Top-5 Candidates
        t_start = time.time()
        for tensor in tensors:
            output = model(tensor)  # (T, B=1, num_classes+1)
            pred_classes, confidences = decode_ctc_single_char(output, self.num_classes)
            idx = int(pred_classes[0].item())
            conf = float(confidences[0].item())
            if allowed_indices and idx not in allowed_indices:
                conf *= 0.25
            class_scores[idx] = class_scores.get(idx, 0.0) + conf

            # Decode Top-5 candidates
            top_k_candidates = decode_ctc_top_k(output, self.num_classes, k=5)
            self.latest_top5 = []
            for pred_cls, p_conf in top_k_candidates:
                label_name = self.idx2label.get(pred_cls, "")
                character = label_to_char(label_name)
                self.latest_top5.append({
                    "char": character,
                    "confidence": float(np.clip(np.power(p_conf, 1.2), 0.0, 1.0))
                })

        t_elapsed = (time.time() - t_start) * 1000.0
        self.stats["characters_predicted"] += 1
        self.stats["total_inference_time_ms"] += t_elapsed

        if not class_scores:
            return "", 0.0

        best_idx = max(class_scores, key=lambda k: class_scores[k])
        conf = class_scores[best_idx] / len(tensors)
        
        self.stats["total_confidence"] += conf

        label = self.idx2label.get(best_idx, "")
        char = label_to_char(label)
        return char, float(min(1.0, max(0.0, conf)))

    def estimate_quality(self, image: Image.Image) -> dict:
        """Estimates image quality metrics (blur, noise, contrast, brightness, stroke width, quality_score)."""
        gray = np.array(image.convert("L"))
        h, w = gray.shape
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        mean, stddev = cv2.meanStdDev(gray)
        noise_score = float(stddev[0][0])
        contrast = float(gray.max() - gray.min())
        brightness = float(gray.mean())
        _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        dist = cv2.distanceTransform(th, cv2.DIST_L2, 5)
        stroke_width = float(dist.mean()) if th.sum() > 0 else 1.0
        quality_score = min(100.0, max(0.0, (blur_score / 20.0) + (contrast / 2.5)))
        return {
            "blur": float(blur_score),
            "noise": noise_score,
            "contrast": contrast,
            "brightness": brightness,
            "stroke_width": stroke_width,
            "quality_score": float(quality_score)
        }

    def _auto_rotate_image(self, image: Image.Image) -> Image.Image:
        """Finds the rotation angle (-5, -3, 0, 3, 5) that yields the highest average confidence score."""
        angles = [-5, -3, 0, 3, 5]
        best_angle = 0
        max_conf = -1.0
        for angle in angles:
            if angle == 0:
                rotated = image
            else:
                rotated = image.rotate(angle, expand=True, fillcolor=255)
            try:
                char, conf = self._infer_with_model([self._preprocess(rotated)], self.model)
                if conf > max_conf:
                    max_conf = conf
                    best_angle = angle
            except Exception:
                pass
        if best_angle != 0:
            return image.rotate(best_angle, expand=True, fillcolor=255)
        return image

    @torch.no_grad()
    def get_character_embedding(self, image: Image.Image) -> np.ndarray:
        """Extracts the 512-dimensional CNN features/embeddings for a character image."""
        tensor = self._preprocess(image).to(self.device)
        features = self.model.cnn(tensor)
        embedding = torch.mean(features, dim=(2, 3)).squeeze().cpu().numpy()
        return embedding

    @torch.no_grad()
    def _predict_batch_with_model(self, images: list[Image.Image], model: nn.Module, language: str | None = None) -> list[tuple[str, float]]:
        if not images:
            return []
        
        tensors = []
        for img in images:
            tensors.append(self._preprocess(img).squeeze(0))
            
        batch_tensor = torch.stack(tensors).to(self.device)
        t_start = time.time()
        output = model(batch_tensor)  # (T, B, num_classes+1)
        pred_classes, confidences = decode_ctc_single_char(output, self.num_classes)
        t_elapsed = (time.time() - t_start) * 1000.0
        
        self.stats["characters_predicted"] += len(images)
        self.stats["total_inference_time_ms"] += t_elapsed
        
        allowed_indices = set(self._language_filtered_candidates(language=language))
        results = []
        for idx in range(len(images)):
            pred_idx = int(pred_classes[idx].item())
            conf = float(confidences[idx].item())
            if allowed_indices and pred_idx not in allowed_indices:
                conf *= 0.25
                
            label = self.idx2label.get(pred_idx, "")
            char = label_to_char(label)
            results.append((char, conf))
        return results

    @torch.no_grad()
    def predict_batch(self, images: list[Image.Image], language: str | None = None) -> list[tuple[str, float]]:
        """Performs batch prediction on a list of character images, running them in a single batch forward pass."""
        if not images:
            return []
            
        # 1. Run primary model
        primary_results = self._predict_batch_with_model(images, self.model, language=language)
        
        # 2. Check if we need fallback
        if self.fallback_model is None:
            calibrated_results = []
            for char, conf in primary_results:
                calibrated_conf = float(np.clip(np.power(conf, 1.2), 0.0, 1.0))
                self.stats["total_confidence"] += calibrated_conf
                calibrated_results.append((char, calibrated_conf))
            return calibrated_results
            
        final_results = list(primary_results)
        fallback_indices = []
        fallback_images = []
        for idx, (char, conf) in enumerate(primary_results):
            if conf < self.confidence_threshold:
                fallback_indices.append(idx)
                fallback_images.append(images[idx])
                
        if fallback_images:
            self.stats["fallback_usage_count"] += len(fallback_images)
            fallback_results = self._predict_batch_with_model(fallback_images, self.fallback_model, language=language)
            for sub_idx, idx in enumerate(fallback_indices):
                fb_char, fb_conf = fallback_results[sub_idx]
                if fb_conf > primary_results[idx][1]:
                    final_results[idx] = (fb_char, fb_conf)
                    
        # Apply temperature calibration only at the end
        calibrated_results = []
        for char, conf in final_results:
            calibrated_conf = float(np.clip(np.power(conf, 1.2), 0.0, 1.0))
            self.stats["total_confidence"] += calibrated_conf
            calibrated_results.append((char, calibrated_conf))
            
        return calibrated_results

    def predict_chars(self, images: list[Image.Image], language: str | None = None) -> list[tuple[str, float]]:
        """Batch inference helper, wrapper around predict_batch."""
        return self.predict_batch(images, language=language)

    def export_to_onnx(self, filepath: str | Path):
        """Prepares and exports the PyTorch CNN-BiLSTM-CTC model to ONNX format."""
        try:
            dummy_input = torch.zeros((1, 1, IMG_HEIGHT, IMG_WIDTH), device=self.device)
            torch.onnx.export(
                self.model,
                dummy_input,
                str(filepath),
                input_names=["input"],
                output_names=["output"],
                dynamic_axes={"input": {0: "batch_size"}, "output": {1: "batch_size"}},
                opset_version=11
            )
            logger.info(f"Model exported successfully to ONNX at {filepath}")
        except Exception as e:
            logger.error(f"Failed to export ONNX: {e}")

    @torch.no_grad()
    def predict_char(self, image: Image.Image, language: str | None = None,
                     auto_rotate: bool = False, enhanced_preprocessing: bool = False) -> tuple[str, float]:
        """Classifies ONE character crop. Supports automatic model fallback."""
        # Check cache
        img_hash = self._hash_pil_image(image)
        cache_key = f"{img_hash}_{language}_{auto_rotate}_{enhanced_preprocessing}"
        if cache_key in self._prediction_cache:
            return self._prediction_cache[cache_key]

        # Auto rotate rotated crops
        if auto_rotate:
            image = self._auto_rotate_image(image)

        tensors = self._preprocess_variants(image, enhanced_preprocessing=enhanced_preprocessing)
        if not tensors:
            tensors = [self._preprocess(image)]

        # Try primary model
        char_primary, conf_primary = self._infer_with_model(tensors, self.model, language=language)
        
        # If primary is low confidence and fallback available, try fallback
        final_char, final_conf = char_primary, conf_primary
        if conf_primary < self.confidence_threshold and self.fallback_model is not None:
            self.stats["fallback_usage_count"] += 1
            char_fallback, conf_fallback = self._infer_with_model(tensors, self.fallback_model, language=language)
            if conf_fallback > conf_primary:
                final_char, final_conf = char_fallback, conf_fallback
        
        # Apply temperature calibration only at the end
        calibrated_conf = float(np.clip(np.power(final_conf, 1.2), 0.0, 1.0))
        
        self._prediction_cache[cache_key] = (final_char, calibrated_conf)
        return final_char, calibrated_conf


@functools.lru_cache(maxsize=4)
def get_predictor(model_path: Path | None = None, with_fallback: bool = True) -> HandwritingPredictor:
    """Cached predictor."""
    primary = model_path or MODEL_PATH
    fallback = FL_MODEL_PATH if with_fallback else None
    
    return HandwritingPredictor(
        model_path=primary,
        fallback_model_path=fallback,
        confidence_threshold=0.6
    )
