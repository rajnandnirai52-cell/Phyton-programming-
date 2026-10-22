"""Central configuration (paths and defaults)."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
REPORTS_DIR = BASE_DIR / "reports"

SAMPLE_DATA_PATH = DATA_DIR / "sample_news.csv"
MODEL_PATH = MODELS_DIR / "best_model.joblib"

RANDOM_STATE = 42
TEST_SIZE = 0.2
CV_FOLDS = 5
N_JOBS = -1

# Class convention used everywhere: 1 = FAKE (the "positive" class we detect), 0 = REAL.
LABEL_MAP = {0: "REAL", 1: "FAKE"}
