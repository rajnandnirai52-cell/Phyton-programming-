"""Load the saved model and classify new articles."""
import math
from pathlib import Path

import joblib
import numpy as np

from . import config
from .evaluate import feature_weights
from .preprocessing import TextPreprocessor

MIN_WORDS_FOR_RELIABLE = 15


class ModelNotFoundError(FileNotFoundError):
    pass


class FakeNewsPredictor:
    """Wraps the saved pipeline + the exact preprocessing used during training.

    Only load model files you trained yourself (joblib files can execute code on load).
    """

    def __init__(self, model_path=None):
        path = Path(model_path or config.MODEL_PATH)
        if not path.exists():
            raise ModelNotFoundError(
                f"No trained model at {path}. Run `python train.py` first.")
        artifact = joblib.load(path)
        self.pipeline = artifact["pipeline"]
        self.preprocessor = TextPreprocessor(**artifact["preprocessor_config"])
        self.model_name = artifact["model_name"]
        self.metrics = artifact.get("metrics", {})
        self.trained_on_sample_data = artifact.get("trained_on_sample_data", False)

    def _probability_fake(self, clean):
        if hasattr(self.pipeline, "predict_proba"):
            proba = self.pipeline.predict_proba([clean])[0]
            return float(proba[list(self.pipeline.classes_).index(1)])
        margin = float(self.pipeline.decision_function([clean])[0])
        return 1.0 / (1.0 + math.exp(-margin))  # margin -> pseudo-probability

    def _explain(self, clean, top_k):
        weights = feature_weights(self.pipeline.named_steps["clf"])
        if weights is None:
            return [], []
        tfidf = self.pipeline.named_steps["tfidf"]
        names = tfidf.get_feature_names_out()
        coo = tfidf.transform([clean]).tocoo()
        contrib = [(str(names[j]), float(v * weights[j])) for j, v in zip(coo.col, coo.data)]
        fake = sorted((c for c in contrib if c[1] > 0), key=lambda c: -c[1])[:top_k]
        real = sorted((c for c in contrib if c[1] < 0), key=lambda c: c[1])[:top_k]
        return [w for w, _ in fake], [w for w, _ in real]

    def predict(self, text, top_k=8):
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Please provide some article text.")
        clean = self.preprocessor.transform_one(text)
        if not clean:
            raise ValueError("The text has no usable words after preprocessing.")
        p_fake = self._probability_fake(clean)
        is_fake = p_fake >= 0.5
        fake_words, real_words = self._explain(clean, top_k)
        n_words = len(text.split())
        return {
            "label": "FAKE" if is_fake else "REAL",
            "is_fake": bool(is_fake),
            "confidence": round(p_fake if is_fake else 1 - p_fake, 4),
            "probability_fake": round(p_fake, 4),
            "words_pointing_to_fake": fake_words,
            "words_pointing_to_real": real_words,
            "warning": ("Very short text - the prediction may be unreliable."
                        if n_words < MIN_WORDS_FOR_RELIABLE else None),
            "model": self.model_name,
        }
