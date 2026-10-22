# Fake News Detection (Python, scikit-learn, NLTK, Flask/Streamlit)

Classifies news articles as **FAKE** or **REAL** using TF-IDF features and five tuned
machine-learning models, then serves the best one through a Flask web app (or Streamlit).

## Quick start

    pip install -r requirements.txt
    python train.py --fast                # ~1 min, small grids
    python app.py                         # open http://127.0.0.1:5000

`python train.py` (no `--fast`) runs the full hyperparameter search (a few minutes).
Alternative UI: `streamlit run streamlit_app.py`. Tests: `python -m unittest discover -s tests`.

## IMPORTANT: use a real dataset

The project ships with a **synthetic** sample dataset (`data/sample_news.csv`, generated from
templates by `src/sample_data.py`) so everything runs immediately. Scores on it are **not
meaningful** for real-world news, and the web app shows a warning banner while the model was
trained on it. For real results, download a labelled dataset and train on it:

    # Kaggle-style "Fake and Real News": Fake.csv + True.csv (columns title, text, ...)
    python train.py --fake data/Fake.csv --real data/True.csv

    # or one CSV with a text/title column and a label column (FAKE/REAL or 1/0)
    python train.py --data data/news.csv

Labels are accepted as FAKE/REAL, fake/real, true/false, reliable/unreliable or 1 (fake) / 0 (real).
On the very large Kaggle file, add `--fast` or `--sample 10000` to keep training quick.

**Dataset caveat:** on Kaggle's Fake/True.csv, real articles start with a "(Reuters)" tag,
which lets models score ~99% by spotting the publisher rather than truthfulness. This project
strips those tags (`strip_leaky_tokens`), but such datasets are still far easier than real-world
misinformation; expect lower accuracy on articles from other sources.

## How each requirement is met

| Requirement | Implementation |
|---|---|
| **Text preprocessing** | `src/preprocessing.py`: lowercase, strip HTML/URLs/emails/handles, tokenise, **stopword removal**, **lemmatization**, **stemming** (switch with `--normalizer none|stem|lemma|both`) |
| **TF-IDF features** | `src/features.py`: `TfidfVectorizer` (uni/bi-grams, sublinear tf, min/max df) inside a `Pipeline`, so it is re-fit in every CV fold (no leakage) |
| **Multiple ML models** | `src/models.py`: Logistic Regression, Multinomial Naive Bayes, Linear SVM, SGD (modified Huber), Random Forest |
| **Hyperparameter tuning** | `GridSearchCV` (5-fold stratified, scored on F1); Random Forest uses `RandomizedSearchCV`. TF-IDF settings (n-grams, vocabulary size) are tuned together with each model's own parameters |
| **Standard metrics** | Accuracy, precision, recall, F1, ROC-AUC, confusion matrices, classification reports, ROC curves, model-comparison chart |
| **Deployment** | `app.py` (Flask: web page + JSON API + `/health`) and `streamlit_app.py` |

## What training produces

- `models/best_model.joblib` - the best pipeline plus the exact preprocessing settings
- `reports/model_comparison.csv` / `.png` - all models side by side
- `reports/confusion_matrix_<model>.png`, `reports/roc_curves.png`
- `reports/top_features.csv` / `top_features_<model>.png` - words that push toward FAKE or REAL
- `reports/results.json` - best parameters and full classification reports
- `reports/preprocessing_comparison.csv` (with `--compare-preprocessing`) - none vs stem vs lemma vs both

**Method notes:** the train/test split happens *before* preprocessing and vectorising; the test set
is used only for final reporting. The best model is chosen by **cross-validation F1**, never by test score.
FAKE is the positive class, so precision/recall/F1 describe how well fake articles are caught.

## Web API

    curl -X POST http://127.0.0.1:5000/api/predict \
         -H "Content-Type: application/json" \
         -d '{"text": "SHOCKING truth they do not want you to know ..."}'

Response: `label`, `confidence`, `probability_fake`, `words_pointing_to_fake`,
`words_pointing_to_real`, `warning` (for very short text), `model`.
Models without native probabilities (Linear SVM) report a sigmoid of the decision margin.

## NLTK notes

On first run the code tries to download NLTK's `stopwords` and `wordnet` data. If NLTK or the
data is unavailable (e.g. offline), each step automatically falls back to a built-in
approximation, so the project still runs. `python -c "from src.preprocessing import backend_info; print(backend_info())"`
shows which implementation is active. To download manually: `python -m nltk.downloader stopwords wordnet omw-1.4`.

## Project layout

    train.py                CLI: train / tune / evaluate / save
    app.py                  Flask app          templates/index.html
    streamlit_app.py        Streamlit app
    generate_sample_data.py regenerate the synthetic demo data
    src/
      preprocessing.py  fallback_nlp.py   data_loader.py   sample_data.py
      features.py       models.py         evaluate.py      trainer.py     predict.py
    tests/test_pipeline.py  21 unit/integration tests
    data/  models/  reports/

## Limitations

The model learns *writing style and vocabulary* from its training data. It cannot check facts,
does not know about events after its training data, and will be wrong on styles it has not seen.
Use it as a learning project or a first-pass signal, never as a fact-checker. Only load
`.joblib` model files you trained yourself.
