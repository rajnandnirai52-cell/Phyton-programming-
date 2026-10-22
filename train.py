"""Command-line entry point for training.

Examples
--------
    python train.py                                   # bundled synthetic sample data
    python train.py --fast                            # smaller grids (quick)
    python train.py --fake data/Fake.csv --real data/True.csv
    python train.py --data data/news.csv --normalizer both --compare-preprocessing
"""
import argparse

from src.trainer import NORMALIZERS, run_training


def parse_args():
    p = argparse.ArgumentParser(description="Train and evaluate fake-news classifiers.")
    p.add_argument("--data", help="single CSV with a text (and/or title) column and a label column")
    p.add_argument("--fake", help="CSV of fake articles (use with --real)")
    p.add_argument("--real", help="CSV of real articles (use with --fake)")
    p.add_argument("--normalizer", choices=sorted(NORMALIZERS), default="lemma",
                   help="word normalisation: none | stem | lemma | both (default: lemma)")
    p.add_argument("--models", help="comma-separated subset, e.g. logistic_regression,naive_bayes "
                                    "(default: all five)")
    p.add_argument("--fast", action="store_true", help="use much smaller hyperparameter grids")
    p.add_argument("--cv", type=int, default=None, help="cross-validation folds (default 5)")
    p.add_argument("--sample", type=int, default=None, help="use only N random articles")
    p.add_argument("--test-size", type=float, default=None, help="test fraction (default 0.2)")
    p.add_argument("--compare-preprocessing", action="store_true",
                   help="also compare none/stem/lemma/both with a baseline model")
    p.add_argument("--output-dir", help="where to write reports (default: reports/)")
    p.add_argument("--model-path", help="where to save the best model (default: models/best_model.joblib)")
    return p.parse_args()


def main():
    a = parse_args()
    run_training(
        data=a.data, fake=a.fake, real=a.real, normalizer=a.normalizer,
        model_names=a.models.split(",") if a.models else None, fast=a.fast, cv=a.cv,
        sample=a.sample, test_size=a.test_size, compare_prep=a.compare_preprocessing,
        output_dir=a.output_dir, model_path=a.model_path)


if __name__ == "__main__":
    main()
