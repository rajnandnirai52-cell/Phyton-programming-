"""Regenerate the synthetic demo dataset: python generate_sample_data.py [n_rows]"""
import sys

from src import config
from src.sample_data import generate

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1200
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    df = generate(n)
    df.to_csv(config.SAMPLE_DATA_PATH, index=False)
    print(f"Wrote {len(df)} rows to {config.SAMPLE_DATA_PATH}")
    print(df["label"].value_counts().to_string())
