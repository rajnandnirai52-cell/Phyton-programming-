"""Flask deployment.

Run:   python app.py            (then open http://127.0.0.1:5000)
API:   POST /api/predict  {"text": "..."}  ->  JSON prediction
"""
from flask import Flask, jsonify, render_template, request

from src.predict import FakeNewsPredictor, ModelNotFoundError

MAX_CHARS = 20_000


def create_app(model_path=None):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 1_000_000  # reject huge request bodies (1 MB)
    state = {"predictor": None, "error": None}

    def get_predictor():
        """Load the model lazily so the app can start (and show a helpful message) without one."""
        if state["predictor"] is None:
            try:
                state["predictor"] = FakeNewsPredictor(model_path)
                state["error"] = None
            except ModelNotFoundError as exc:
                state["error"] = str(exc)
        return state["predictor"]

    @app.route("/", methods=["GET", "POST"])
    def index():
        predictor = get_predictor()
        ctx = {"text": "", "result": None, "error": state["error"],
               "predictor": predictor, "max_chars": MAX_CHARS}
        if request.method == "POST" and predictor:
            text = request.form.get("text", "")
            ctx["text"] = text
            if len(text) > MAX_CHARS:
                ctx["error"] = f"Text is too long (max {MAX_CHARS:,} characters)."
            else:
                try:
                    ctx["result"] = predictor.predict(text)
                except ValueError as exc:
                    ctx["error"] = str(exc)
        return render_template("index.html", **ctx)

    @app.post("/api/predict")
    def api_predict():
        predictor = get_predictor()
        if predictor is None:
            return jsonify(error=state["error"]), 503
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or not isinstance(payload.get("text"), str):
            return jsonify(error='Send JSON like {"text": "article text"}.'), 400
        if len(payload["text"]) > MAX_CHARS:
            return jsonify(error=f"Text too long (max {MAX_CHARS} characters)."), 400
        try:
            return jsonify(predictor.predict(payload["text"]))
        except ValueError as exc:
            return jsonify(error=str(exc)), 400

    @app.get("/health")
    def health():
        predictor = get_predictor()
        return jsonify(status="ok" if predictor else "model_missing",
                       model=predictor.model_name if predictor else None)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
