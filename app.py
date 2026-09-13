import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(
    page_title="NIFTY Sentiment AI",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 NIFTY SENTIMENT AI")
st.subheader("Live Market Sentiment Dashboard")

@st.cache_data(ttl=60)
def get_nifty_data():
    data = yf.download(
        "^NSEI",
        period="5d",
        interval="5m",
        progress=False,
        auto_adjust=False
    )

    if data.empty:
        return None

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    data = data.dropna()

    return data


data = get_nifty_data()

if data is None or data.empty:
    st.error("❌ NIFTY data अभी उपलब्ध नहीं है।")
    st.stop()

close = data["Close"]
high = data["High"]
low = data["Low"]
volume = data["Volume"]

# Latest price
price = float(close.iloc[-1])

# Price change
previous = float(close.iloc[-2])
change = price - previous
change_pct = (change / previous) * 100

# RSI
delta = close.diff()

gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)

avg_gain = gain.rolling(14).mean()
avg_loss = loss.rolling(14).mean()

rs = avg_gain / avg_loss
rsi = 100 - (100 / (1 + rs))

latest_rsi = float(rsi.iloc[-1])

# VWAP
typical_price = (high + low + close) / 3

vwap = (
    typical_price * volume
).cumsum() / volume.cumsum()

latest_vwap = float(vwap.iloc[-1])

# Volume
latest_volume = float(volume.iloc[-1])
average_volume = float(volume.rolling(20).mean().iloc[-1])

if latest_volume > average_volume:
    volume_status = "HIGH"
else:
    volume_status = "NORMAL"

# Simple sentiment score
score = 50

if price > latest_vwap:
    score += 15
else:
    score -= 15

if latest_rsi > 60:
    score += 20
elif latest_rsi < 40:
    score -= 20

if latest_volume > average_volume:
    score += 10

score = max(0, min(100, score))

if score >= 65:
    sentiment = "🟢 BULLISH"
elif score <= 35:
    sentiment = "🔴 BEARISH"
else:
    sentiment = "🟡 NEUTRAL"

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.metric(
        "NIFTY 50",
        f"{price:,.2f}",
        f"{change:+,.2f} ({change_pct:+.2f}%)"
    )

with col2:
    st.metric(
        "Sentiment Score",
        f"{score} / 100",
        sentiment
    )

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("RSI", f"{latest_rsi:.2f}")

with col2:
    st.metric(
        "VWAP",
        f"{latest_vwap:,.2f}"
    )

with col3:
    st.metric(
        "Volume",
        volume_status
    )

st.divider()

st.subheader("📊 Market Analysis")

if price > latest_vwap:
    st.success("📈 NIFTY VWAP के ऊपर है — bullish pressure")
else:
    st.error("📉 NIFTY VWAP के नीचे है — bearish pressure")

if latest_rsi > 60:
    st.success("🟢 RSI bullish zone में है")
elif latest_rsi < 40:
    st.error("🔴 RSI bearish zone में है")
else:
    st.info("🟡 RSI neutral zone में है")

if latest_volume > average_volume:
    st.warning("⚡ Volume average से ज्यादा है — market activity बढ़ी हुई है")
else:
    st.info("Volume सामान्य स्तर पर है")

st.divider()

st.subheader("🤖 AI Market Commentary")

if score >= 65:
    st.write(
        f"NIFTY का वर्तमान sentiment **BULLISH** है। "
        f"Sentiment Score {score}/100 है। "
        f"Price और VWAP की स्थिति तथा RSI को देखते हुए "
        f"buyers का pressure दिखाई दे रहा है।"
    )

elif score <= 35:
    st.write(
        f"NIFTY का वर्तमान sentiment **BEARISH** है। "
        f"Sentiment Score {score}/100 है। "
        f"Price/VWAP और RSI के आधार पर "
        f"sellers का pressure दिखाई दे रहा है।"
    )

else:
    st.write(
        f"NIFTY का sentiment फिलहाल **NEUTRAL** है। "
        f"Score {score}/100 है। "
        f"Market में स्पष्ट direction का इंतजार करना बेहतर है।"
    )

st.caption(
    "⚠️ यह केवल market-analysis tool है, निश्चित भविष्यवाणी या investment advice नहीं।"
)

st.divider()

if st.button("🔄 Refresh Live Data"):
    st.cache_data.clear()
    st.rerun()
