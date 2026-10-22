"""Evaluation metrics and plots."""
import matplotlib

matplotlib.use("Agg")  # headless-safe backend
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,  # noqa: E402
                             precision_score, recall_score, roc_auc_score,
                             roc_curve)

from .config import LABEL_MAP  # noqa: E402


def get_scores(pipeline, X):
    """Continuous score for the FAKE class (probability if available, else margin)."""
    if hasattr(pipeline, "predict_proba"):
        return pipeline.predict_proba(X)[:, list(pipeline.classes_).index(1)]
    return pipeline.decision_function(X)


def compute_metrics(y_true, y_pred, y_score):
    """Standard binary-classification metrics; FAKE (1) is the positive class."""
    y_true = np.asarray(y_true)
    both = len(set(y_true.tolist())) == 2
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_score)) if both else float("nan"),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist(),
    }


def feature_weights(clf):
    """Per-feature weight toward FAKE (positive) vs REAL (negative), if the model exposes it."""
    if hasattr(clf, "coef_"):
        return np.asarray(clf.coef_).ravel()
    if hasattr(clf, "feature_log_prob_"):
        return clf.feature_log_prob_[1] - clf.feature_log_prob_[0]
    return None


def top_features(pipeline, k=15):
    """Return (top_fake_words, top_real_words) as lists of (word, weight), or None."""
    weights = feature_weights(pipeline.named_steps["clf"])
    if weights is None:
        return None
    names = np.asarray(pipeline.named_steps["tfidf"].get_feature_names_out())
    order = np.argsort(weights)
    fake = [(names[i], float(weights[i])) for i in order[::-1][:k]]
    real = [(names[i], float(weights[i])) for i in order[:k]]
    return fake, real


# ---------------------------------------------------------------- plots
def plot_confusion_matrix(cm, path, title):
    cm = np.asarray(cm)
    fig, ax = plt.subplots(figsize=(4.5, 4))
    ax.imshow(cm, cmap="Blues")
    ax.set_xticks([0, 1], [LABEL_MAP[0], LABEL_MAP[1]])
    ax.set_yticks([0, 1], [LABEL_MAP[0], LABEL_MAP[1]])
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title(title)
    for (i, j), v in np.ndenumerate(cm):
        ax.text(j, i, str(v), ha="center", va="center",
                color="white" if v > cm.max() / 2 else "black", fontsize=13)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_roc_curves(curves, path):
    """curves: {label: (y_true, y_score)}"""
    fig, ax = plt.subplots(figsize=(6, 5))
    for label, (y_true, y_score) in curves.items():
        fpr, tpr, _ = roc_curve(y_true, y_score)
        ax.plot(fpr, tpr, label=f"{label} (AUC={roc_auc_score(y_true, y_score):.3f})")
    ax.plot([0, 1], [0, 1], "k--", alpha=0.4)
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title("ROC curves (test set)")
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_model_comparison(results, path):
    """results: list of dicts with 'label' and metric keys."""
    metrics = ["accuracy", "precision", "recall", "f1"]
    x = np.arange(len(results))
    width = 0.2
    fig, ax = plt.subplots(figsize=(9, 5))
    for i, m in enumerate(metrics):
        ax.bar(x + i * width, [r[m] for r in results], width, label=m)
    ax.set_xticks(x + 1.5 * width, [r["label"] for r in results], rotation=15, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_title("Model comparison (test set)")
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_top_features(fake, real, path, title):
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    for ax, data, name, color in ((axes[0], fake, "Words pointing to FAKE", "#c0392b"),
                                  (axes[1], real, "Words pointing to REAL", "#2471a3")):
        words = [w for w, _ in data][::-1]
        vals = [abs(v) for _, v in data][::-1]
        ax.barh(words, vals, color=color)
        ax.set_title(name)
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
