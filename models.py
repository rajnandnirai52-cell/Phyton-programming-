"""Model zoo and hyperparameter grids."""
from dataclasses import dataclass
from typing import Optional

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC

from . import config

_TFIDF_GRID = {
    "tfidf__ngram_range": [(1, 1), (1, 2)],
    "tfidf__max_features": [10000, 30000],
}
_TFIDF_FAST = {"tfidf__ngram_range": [(1, 2)], "tfidf__max_features": [20000]}


@dataclass
class ModelSpec:
    name: str
    label: str
    estimator: object
    param_grid: dict
    fast_grid: dict
    n_iter: Optional[int] = None  # if set and grid is larger, use randomized search


def get_model_specs(names=None):
    rs = config.RANDOM_STATE
    specs = [
        ModelSpec(
            "logistic_regression", "Logistic Regression",
            LogisticRegression(max_iter=1000, random_state=rs),
            {**_TFIDF_GRID, "clf__C": [0.1, 1, 10], "clf__class_weight": [None, "balanced"]},
            {**_TFIDF_FAST, "clf__C": [1, 10]}),
        ModelSpec(
            "naive_bayes", "Multinomial Naive Bayes",
            MultinomialNB(),
            {**_TFIDF_GRID, "clf__alpha": [0.05, 0.1, 0.5, 1.0]},
            {**_TFIDF_FAST, "clf__alpha": [0.1, 1.0]}),
        ModelSpec(
            "linear_svm", "Linear SVM",
            LinearSVC(random_state=rs),
            {**_TFIDF_GRID, "clf__C": [0.1, 1, 10]},
            {**_TFIDF_FAST, "clf__C": [0.5, 1]}),
        ModelSpec(
            "sgd_classifier", "SGD Classifier (modified Huber)",
            SGDClassifier(loss="modified_huber", max_iter=1000, random_state=rs),
            {**_TFIDF_GRID, "clf__alpha": [1e-5, 1e-4, 1e-3]},
            {**_TFIDF_FAST, "clf__alpha": [1e-4, 1e-3]}),
        ModelSpec(
            "random_forest", "Random Forest",
            RandomForestClassifier(random_state=rs, n_jobs=1),
            {**_TFIDF_GRID, "clf__n_estimators": [100, 300],
             "clf__max_depth": [None, 30], "clf__min_samples_split": [2, 5]},
            {**_TFIDF_FAST, "clf__n_estimators": [100]},
            n_iter=8),
    ]
    if names:
        wanted = {n.strip() for n in names}
        unknown = wanted - {s.name for s in specs}
        if unknown:
            raise ValueError(f"Unknown model(s): {sorted(unknown)}. "
                             f"Available: {[s.name for s in specs]}")
        specs = [s for s in specs if s.name in wanted]
    return specs
