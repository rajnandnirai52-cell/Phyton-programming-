"""Load news datasets from CSV and normalise them to columns: text, label (1=FAKE, 0=REAL)."""
import pandas as pd

from . import config

_POSITIVE = {"fake", "false", "unreliable", "hoax", "misinformation", "1", "1.0", "true_fake"}
_NEGATIVE = {"real", "true", "reliable", "genuine", "factual", "0", "0.0"}
_TEXT_COLS = ("text", "content", "article", "body", "news")
_TITLE_COLS = ("title", "headline")
_LABEL_COLS = ("label", "class", "target", "category")


def normalize_label(value):
    """Map many label spellings (FAKE/REAL, 0/1, true/false, ...) to 1=fake / 0=real."""
    s = str(value).strip().lower()
    if s in _POSITIVE:
        return 1
    if s in _NEGATIVE:
        return 0
    raise ValueError(
        f"Unrecognised label {value!r}. Use FAKE/REAL (or 1=fake, 0=real).")


def _first_present(columns, candidates):
    for c in candidates:
        if c in columns:
            return c
    return None


def _combine_text(df):
    """Build one 'text' column from title + body (whichever exist)."""
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    text_col = _first_present(df.columns, _TEXT_COLS)
    title_col = _first_present(df.columns, _TITLE_COLS)
    if text_col is None and title_col is None:
        raise ValueError(
            f"No text column found. Expected one of {_TEXT_COLS + _TITLE_COLS}; "
            f"got {list(df.columns)}")
    parts = []
    if title_col:
        parts.append(df[title_col].fillna("").astype(str))
    if text_col:
        parts.append(df[text_col].fillna("").astype(str))
    combined = parts[0] if len(parts) == 1 else parts[0] + ". " + parts[1]
    out = pd.DataFrame({"text": combined})
    return out, df


def load_csv(path):
    """Load one CSV that already has a label column."""
    out, df = _combine_text(pd.read_csv(path))
    label_col = _first_present(df.columns, _LABEL_COLS)
    if label_col is None:
        raise ValueError(f"No label column found. Expected one of {_LABEL_COLS}.")
    out["label"] = df[label_col].map(normalize_label)
    return out


def load_two_files(fake_path, real_path):
    """Kaggle-style layout: one CSV of fake articles and one of real articles."""
    fake, _ = _combine_text(pd.read_csv(fake_path))
    real, _ = _combine_text(pd.read_csv(real_path))
    fake["label"], real["label"] = 1, 0
    return pd.concat([fake, real], ignore_index=True)


def clean_frame(df):
    """Drop empty/duplicate rows and shuffle deterministically."""
    df = df.dropna(subset=["text", "label"]).copy()
    df["text"] = df["text"].astype(str).str.strip()
    df = df[df["text"].str.len() > 0].drop_duplicates(subset="text")
    df["label"] = df["label"].astype(int)
    return df.sample(frac=1, random_state=config.RANDOM_STATE).reset_index(drop=True)


def load_dataset(data=None, fake=None, real=None):
    """Return a cleaned DataFrame. Falls back to the bundled synthetic sample data."""
    if fake or real:
        if not (fake and real):
            raise ValueError("Provide both --fake and --real CSV files.")
        df = load_two_files(fake, real)
        source = "custom"
    elif data:
        df = load_csv(data)
        source = "custom"
    else:
        if not config.SAMPLE_DATA_PATH.exists():
            from .sample_data import generate
            config.DATA_DIR.mkdir(parents=True, exist_ok=True)
            generate().to_csv(config.SAMPLE_DATA_PATH, index=False)
        df = load_csv(config.SAMPLE_DATA_PATH)
        source = "sample"
    df = clean_frame(df)
    if df["label"].nunique() < 2:
        raise ValueError("Dataset must contain both FAKE and REAL examples.")
    df.attrs["source"] = source
    return df
