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


# -----------------------------
# NIFTY DATA
# -----------------------------

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
        return pd.DataFrame()

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    data = data.dropna()

    return data


# -----------------------------
# RSI
# -----------------------------

def calculate_rsi(series, period=14):

    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss.replace(0, pd.NA)

    rsi = 100 - (100 / (1 + rs))

    return rsi


# -----------------------------
# ANALYSIS
# -----------------------------

data = get_nifty_data()


if data.empty:

    st.error(
        "❌ NIFTY market data अभी उपलब्ध नहीं है। "
        "थोड़ी देर बाद Refresh करें।"
    )

    st.stop()


close = pd.to_numeric(
    data["Close"],
    errors="coerce"
)

high = pd.to_numeric(
    data["High"],
    errors="coerce"
)

low = pd.to_numeric(
    data["Low"],
    errors="coerce"
)

volume = pd.to_numeric(
    data["Volume"],
    errors="coerce"
)


data["RSI"] = calculate_rsi(close)


# -----------------------------
# VWAP
# -----------------------------

typical_price = (
    high + low + close
) / 3

cumulative_volume = volume.cumsum()

data["VWAP"] = (
    (typical_price * volume).cumsum()
    / cumulative_volume.replace(0, pd.NA)
)


# -----------------------------
# CURRENT VALUES
# -----------------------------

latest_price = float(close.iloc[-1])

previous_price = float(close.iloc[-2])

change = latest_price - previous_price

change_pct = (
    change / previous_price
) * 100


latest_rsi = data["RSI"].iloc[-1]

latest_vwap = data["VWAP"].iloc[-1]


if pd.isna(latest_rsi):
    latest_rsi = 50


if pd.isna(latest_vwap):
    latest_vwap = latest_price


# -----------------------------
# VOLUME ANALYSIS
# -----------------------------

avg_volume = volume.tail(20).mean()

latest_volume = volume.iloc[-1]


if latest_volume > avg_volume * 1.5:

    volume_status = "HIGH VOLUME"
    volume_score = 10

elif latest_volume > avg_volume:

    volume_status = "ABOVE AVERAGE"
    volume_score = 5

else:

    volume_status = "NORMAL"
    volume_score = 0


# -----------------------------
# TREND
# -----------------------------

ema20 = close.ewm(
    span=20,
    adjust=False
).mean()

ema50 = close.ewm(
    span=50,
    adjust=False
).mean()


latest_ema20 = float(ema20.iloc[-1])
latest_ema50 = float(ema50.iloc[-1])


# -----------------------------
# SENTIMENT SCORE
# -----------------------------

score = 50


# Price vs VWAP
if latest_price > latest_vwap:

    score += 15

else:

    score -= 15


# RSI
if latest_rsi > 60:

    score += 20

elif latest_rsi < 40:

    score -= 20


# EMA trend
if latest_ema20 > latest_ema50:

    score += 10

elif latest_ema20 < latest_ema50:

    score -= 10


# Volume
if latest_price > latest_vwap:

    score += volume_score

else:

    score -= volume_score


# Keep score between 0 and 100
score = max(
    0,
    min(100, round(score))
)


# -----------------------------
# MARKET BIAS
# -----------------------------

if score >= 65:

    bias = "BULLISH"
    bias_text = "UPSIDE BIAS"

elif score <= 35:

    bias = "BEARISH"
    bias_text = "DOWNSIDE BIAS"

else:

    bias = "NEUTRAL"
    bias_text = "SIDEWAYS / NEUTRAL"


# -----------------------------
# SUPPORT / RESISTANCE
# -----------------------------

recent_high = float(
    high.tail(50).max()
)

recent_low = float(
    low.tail(50).min()
)


support = round(
    recent_low / 50
) * 50


resistance = round(
    recent_high / 50
) * 50


# -----------------------------
# DASHBOARD
# -----------------------------

st.divider()

col1, col2 = st.columns(2)

with col1:

    st.metric(
        "NIFTY 50",
        f"{latest_price:,.2f}",
        f"{change:+.2f} ({change_pct:+.2f}%)"
    )


with col2:

    st.metric(
        "Sentiment Score",
        f"{score} / 100",
        bias
    )


st.divider()


# -----------------------------
# MARKET BIAS
# -----------------------------

st.subheader(
    f"🎯 Current Market Bias: {bias_text}"
)


if bias == "BULLISH":

    st.success(
        "🟢 Market में bullish conditions दिखाई दे रही हैं।"
    )

elif bias == "BEARISH":

    st.error(
        "🔴 Market में bearish conditions दिखाई दे रही हैं।"
    )

else:

    st.warning(
        "🟡 Market अभी neutral/sideways conditions में है।"
    )


# -----------------------------
# INDICATORS
# -----------------------------

st.subheader("📊 Market Indicators")


c1, c2, c3, c4 = st.columns(4)


with c1:

    st.metric(
        "RSI",
        f"{latest_rsi:.2f}"
    )


with c2:

    st.metric(
        "VWAP",
        f"{latest_vwap:,.2f}"
    )


with c3:

    st.metric(
        "Volume",
        volume_status
    )


with c4:

    trend = (
        "UPTREND"
        if latest_ema20 > latest_ema50
        else "DOWNTREND"
    )

    st.metric(
        "Trend",
        trend
    )


# -----------------------------
# SUPPORT / RESISTANCE
# -----------------------------

st.subheader("📍 Support & Resistance")


s1, s2 = st.columns(2)


with s1:

    st.metric(
        "Support",
        f"{support:,.0f}"
    )


with s2:

    st.metric(
        "Resistance",
        f"{resistance:,.0f}"
    )


# -----------------------------
# AI COMMENTARY
# -----------------------------

st.subheader("🧠 Market Commentary")


if bias == "BULLISH":

    commentary = (
        f"NIFTY price VWAP के ऊपर है और RSI "
        f"{latest_rsi:.1f} है। Short-term momentum "
        "bullish दिखाई दे रहा है। Volume और trend "
        "को confirmation के लिए monitor करें।"
    )

elif bias == "BEARISH":

    commentary = (
        f"NIFTY price VWAP के नीचे है और RSI "
        f"{latest_rsi:.1f} है। Short-term momentum "
        "weak दिखाई दे रहा है। Support levels पर "
        "price reaction को monitor करें।"
    )

else:

    commentary = (
        f"NIFTY का current sentiment neutral है। "
        f"RSI {latest_rsi:.1f} है और price/VWAP "
        "relationship को अगली direction के लिए monitor करें।"
    )


st.info(commentary)


# -----------------------------
# WARNING
# -----------------------------

st.caption(
    "⚠️ यह dashboard market indicators के आधार पर "
    "sentiment estimate करता है। यह guaranteed prediction "
    "या investment advice नहीं है।"
)


# -----------------------------
# AUTO REFRESH
# -----------------------------

st.caption(
    "🔄 Data लगभग हर 60 seconds में refresh होता है।"
)
