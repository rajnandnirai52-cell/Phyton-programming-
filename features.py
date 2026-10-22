"""TF-IDF feature extraction + pipeline construction."""
from sklearn.base import clone
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline


def build_tfidf(**overrides):
    """TF-IDF vectoriser. Defaults are the starting point; the grid search tunes some of them."""
    params = dict(
        ngram_range=(1, 2),
        max_features=20000,
        min_df=2,          # ignore words that appear in fewer than 2 documents
        max_df=0.95,       # ignore words present in >95% of documents
        sublinear_tf=True,  # use 1 + log(tf) to dampen very frequent terms
    )
    params.update(overrides)
    return TfidfVectorizer(**params)


def build_pipeline(estimator):
    """TF-IDF -> classifier, so vectorisation is re-fit inside every CV fold (no leakage)."""
    return Pipeline([("tfidf", build_tfidf()), ("clf", clone(estimator))])
