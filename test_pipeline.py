import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from src.data_loader import load_csv, load_two_files, normalize_label  # noqa: E402
from src.evaluate import compute_metrics  # noqa: E402
from src.fallback_nlp import SimpleLemmatizer, SimpleStemmer  # noqa: E402
from src.models import get_model_specs  # noqa: E402
from src.predict import FakeNewsPredictor, ModelNotFoundError  # noqa: E402
from src.preprocessing import TextPreprocessor  # noqa: E402
from src.sample_data import generate  # noqa: E402
from src.trainer import run_training  # noqa: E402

FAKE_TEXT = ("SHOCKING: The elites do NOT want you to know the truth about the new vaccine!!! "
             "Share this before it gets deleted, they lied to you and doctors are FURIOUS.")
REAL_TEXT = ("The finance ministry said on Tuesday that unemployment fell 2.4 percent in the "
             "third quarter, according to figures released this week by officials.")


class TestPreprocessing(unittest.TestCase):
    def test_cleaning_and_stopwords(self):
        p = TextPreprocessor(lemmatization=False, stemming=False)
        out = p.transform_one("Visit http://x.com <b>QUICKLY</b>! The cats and the dogs, email a@b.com")
        self.assertEqual(out.split(), ["visit", "quickly", "cats", "dogs", "email"])

    def test_stopwords_can_be_kept(self):
        p = TextPreprocessor(remove_stopwords=False, lemmatization=False)
        self.assertIn("the", p.transform_one("the cat").split())

    def test_lemmatization_and_stemming(self):
        self.assertEqual(TextPreprocessor(lemmatization=True).transform_one("policies dogs"), "policy dog")
        stemmed = TextPreprocessor(lemmatization=False, stemming=True).transform_one("running governments")
        self.assertNotIn("running", stemmed)
        self.assertNotIn("governments", stemmed)

    def test_contractions_and_leaky_tokens(self):
        p = TextPreprocessor(lemmatization=False)
        self.assertEqual(p.transform_one("Don't say it's Trump's (Reuters) fault"), "say trump fault")
        self.assertIn("reuters", TextPreprocessor(strip_leaky_tokens=False, lemmatization=False).transform_one("Reuters says"))

    def test_config_round_trip(self):
        p = TextPreprocessor(stemming=True, lemmatization=False)
        self.assertEqual(TextPreprocessor(**p.config()).config(), p.config())

    def test_fallback_helpers(self):
        self.assertEqual(SimpleLemmatizer().lemmatize("policies"), "policy")
        self.assertEqual(SimpleLemmatizer().lemmatize("children"), "child")
        s = SimpleStemmer()
        self.assertEqual(s.stem("running"), "run")
        self.assertEqual(s.stem("cats"), s.stem("cat"))


class TestData(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_label_normalisation(self):
        for v in ("FAKE", "fake", 1, "1", "False", "unreliable"):
            self.assertEqual(normalize_label(v), 1, v)
        for v in ("REAL", "real", 0, "0", "True", "reliable"):
            self.assertEqual(normalize_label(v), 0, v)
        with self.assertRaises(ValueError):
            normalize_label("maybe")

    def test_load_csv_combines_title_and_text(self):
        path = os.path.join(self.tmp, "a.csv")
        pd.DataFrame({"Title": ["T"], "Text": ["body"], "Label": ["FAKE"]}).to_csv(path, index=False)
        df = load_csv(path)
        self.assertEqual(df.loc[0, "text"], "T. body")
        self.assertEqual(df.loc[0, "label"], 1)

    def test_two_file_layout(self):
        f, r = os.path.join(self.tmp, "Fake.csv"), os.path.join(self.tmp, "True.csv")
        pd.DataFrame({"title": ["a"], "text": ["x"]}).to_csv(f, index=False)
        pd.DataFrame({"title": ["b"], "text": ["y"]}).to_csv(r, index=False)
        df = load_two_files(f, r)
        self.assertEqual(sorted(df["label"]), [0, 1])

    def test_missing_columns(self):
        path = os.path.join(self.tmp, "bad.csv")
        pd.DataFrame({"foo": [1]}).to_csv(path, index=False)
        with self.assertRaises(ValueError):
            load_csv(path)

    def test_sample_generator(self):
        df = generate(100, seed=1)
        self.assertEqual(len(df), 100)
        self.assertEqual(set(df["label"]), {"FAKE", "REAL"})


class TestModelsAndMetrics(unittest.TestCase):
    def test_specs(self):
        self.assertEqual(len(get_model_specs()), 5)
        self.assertEqual(len(get_model_specs(["naive_bayes"])), 1)
        with self.assertRaises(ValueError):
            get_model_specs(["nope"])

    def test_metrics(self):
        m = compute_metrics([1, 1, 0, 0], [1, 0, 0, 0], [0.9, 0.4, 0.2, 0.1])
        self.assertAlmostEqual(m["accuracy"], 0.75)
        self.assertAlmostEqual(m["precision"], 1.0)
        self.assertAlmostEqual(m["recall"], 0.5)
        self.assertAlmostEqual(m["roc_auc"], 1.0)
        self.assertEqual(m["confusion_matrix"], [[2, 0], [1, 1]])


class TestEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.model_path = os.path.join(cls.tmp, "model.joblib")
        cls.out = run_training(
            model_names=["logistic_regression", "naive_bayes", "linear_svm"],
            fast=True, cv=3, sample=500, normalizer="both", compare_prep=True,
            output_dir=os.path.join(cls.tmp, "reports"), model_path=cls.model_path,
            verbose=False)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_artifacts_created(self):
        rep = Path(self.tmp, "reports")
        for name in ("model_comparison.csv", "model_comparison.png", "roc_curves.png",
                     "results.json", "preprocessing_comparison.csv",
                     "confusion_matrix_naive_bayes.png"):
            self.assertTrue((rep / name).exists(), name)
        self.assertTrue(Path(self.model_path).exists())

    def test_metrics_reasonable(self):
        table = self.out["table"]
        self.assertEqual(len(table), 3)
        self.assertTrue((table["accuracy"] > 0.8).all())
        self.assertEqual(len(self.out["preprocessing_table"]), 4)

    def test_predictor(self):
        pred = FakeNewsPredictor(self.model_path)
        self.assertEqual(pred.predict(FAKE_TEXT)["label"], "FAKE")
        res = pred.predict(REAL_TEXT)
        self.assertEqual(res["label"], "REAL")
        self.assertTrue(0.5 <= res["confidence"] <= 1.0)
        self.assertTrue(pred.trained_on_sample_data)
        with self.assertRaises(ValueError):
            pred.predict("   ")
        with self.assertRaises(ValueError):
            pred.predict("the and of")  # nothing left after stopword removal
        self.assertIsNotNone(pred.predict("Short text here")["warning"])

    def test_missing_model(self):
        with self.assertRaises(ModelNotFoundError):
            FakeNewsPredictor(os.path.join(self.tmp, "nope.joblib"))


class TestFlask(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.model_path = os.path.join(cls.tmp, "m.joblib")
        run_training(model_names=["naive_bayes"], fast=True, cv=3, sample=400,
                     output_dir=os.path.join(cls.tmp, "r"), model_path=cls.model_path,
                     verbose=False)
        cls.client = create_app(cls.model_path).test_client()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_health_and_page(self):
        self.assertEqual(self.client.get("/health").json["status"], "ok")
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_api(self):
        r = self.client.post("/api/predict", json={"text": FAKE_TEXT})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json["label"], "FAKE")
        for bad in ({"text": ""}, {"text": 5}, {"nope": 1}):
            self.assertEqual(self.client.post("/api/predict", json=bad).status_code, 400)
        self.assertEqual(self.client.post("/api/predict", json={"text": "a" * 25000}).status_code, 400)

    def test_form_escapes_html(self):
        html = self.client.post("/", data={"text": "<script>alert(1)</script> " + FAKE_TEXT}
                                ).get_data(as_text=True)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("FAKE", html)

    def test_missing_model_is_handled(self):
        c = create_app(os.path.join(self.tmp, "absent.joblib")).test_client()
        self.assertEqual(c.get("/health").json["status"], "model_missing")
        self.assertEqual(c.post("/api/predict", json={"text": FAKE_TEXT}).status_code, 503)
        self.assertEqual(c.get("/").status_code, 200)


if __name__ == "__main__":
    unittest.main()
