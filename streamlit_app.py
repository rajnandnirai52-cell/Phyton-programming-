"""Streamlit deployment (alternative to the Flask app).

Run:  streamlit run streamlit_app.py
"""
import streamlit as st

from src.predict import FakeNewsPredictor, ModelNotFoundError

st.set_page_config(page_title="Fake News Detector", page_icon="📰")
st.title("📰 Fake News Detector")
st.caption("TF-IDF features + a tuned scikit-learn classifier.")


@st.cache_resource
def load_predictor():
    return FakeNewsPredictor()


try:
    predictor = load_predictor()
except ModelNotFoundError as exc:
    st.error(str(exc))
    st.stop()

if predictor.trained_on_sample_data:
    st.warning("This model was trained on synthetic sample data - for demonstration only. "
               "Train on a real dataset for meaningful results.")

text = st.text_area("Article text", height=220,
                    placeholder="Paste the headline and body of a news article...")

if st.button("Analyse", type="primary"):
    try:
        res = predictor.predict(text)
    except ValueError as exc:
        st.error(str(exc))
    else:
        (st.error if res["is_fake"] else st.success)(f"Prediction: **{res['label']}**")
        st.progress(res["probability_fake"], text=f"Probability fake: {res['probability_fake']:.1%}")
        st.write(f"Confidence: {res['confidence']:.1%}  |  Model: {res['model']}")
        if res["warning"]:
            st.info(res["warning"])
        c1, c2 = st.columns(2)
        c1.markdown("**Words pushing toward FAKE**")
        c1.write(", ".join(res["words_pointing_to_fake"]) or "-")
        c2.markdown("**Words pushing toward REAL**")
        c2.write(", ".join(res["words_pointing_to_real"]) or "-")

st.caption("Educational project - judges writing style, does not verify facts.")
