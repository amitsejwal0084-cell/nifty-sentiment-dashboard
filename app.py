import streamlit as st

st.set_page_config(
    page_title="NIFTY Sentiment AI",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 NIFTY SENTIMENT AI")
st.subheader("Market Sentiment Dashboard")

st.success("✅ Python Backend Successfully Connected")

st.metric(
    "NIFTY 50",
    "25,000",
    "+125 (+0.50%)"
)

st.metric(
    "Sentiment Score",
    "78 / 100",
    "Bullish"
)

st.info(
    "अभी यह Demo Data है। अगले चरण में Live Market Data जोड़ा जाएगा।"
)
