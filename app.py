import streamlit as st
import yfinance as yf
import pandas as pd

from option_chain import (
    get_nifty_option_chain,
    get_atm_option_chain,
    calculate_pcr,
    option_sentiment
)

st.set_page_config(
    page_title="NIFTY Sentiment AI",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 NIFTY SENTIMENT AI")
st.subheader("Live Market Sentiment Dashboard")


# =========================
# NIFTY PRICE DATA
# =========================

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

    return data.dropna()


data = get_nifty_data()

if data is None or data.empty:
    st.error("❌ NIFTY data उपलब्ध नहीं है।")
    st.stop()


close = data["Close"]
high = data["High"]
low = data["Low"]
volume = data["Volume"]


price = float(close.iloc[-1])

previous = float(close.iloc[-2])

change = price - previous

change_pct = (change / previous) * 100


# =========================
# RSI
# =========================

delta = close.diff()

gain = delta.clip(lower=0)

loss = -delta.clip(upper=0)

avg_gain = gain.rolling(14).mean()

avg_loss = loss.rolling(14).mean()

rs = avg_gain / avg_loss

rsi = 100 - (100 / (1 + rs))

latest_rsi = float(rsi.iloc[-1])


# =========================
# VWAP
# =========================

typical_price = (high + low + close) / 3

vwap = (
    typical_price * volume
).cumsum() / volume.cumsum()

latest_vwap = float(vwap.iloc[-1])


# =========================
# VOLUME
# =========================

latest_volume = float(volume.iloc[-1])

average_volume = float(
    volume.rolling(20).mean().iloc[-1]
)

if latest_volume > average_volume:
    volume_status = "HIGH"
else:
    volume_status = "NORMAL"


# =========================
# OPTION CHAIN
# =========================

option_data = pd.DataFrame()

option_spot = None

option_error = None

try:

    option_data, option_spot = get_nifty_option_chain()

    if not option_data.empty and option_spot:

        atm_data = get_atm_option_chain(
            option_data,
            option_spot,
            strikes_each_side=4
        )

        option_pcr = calculate_pcr(atm_data)

        option_bias, option_score = option_sentiment(
            atm_data
        )

    else:

        atm_data = pd.DataFrame()

        option_pcr = None

        option_bias = "NO DATA"

        option_score = 50

except Exception as e:

    atm_data = pd.DataFrame()

    option_pcr = None

    option_bias = "NO DATA"

    option_score = 50

    option_error = str(e)


# =========================
# PRICE SENTIMENT
# =========================

price_score = 50

if price > latest_vwap:
    price_score += 15
else:
    price_score -= 15


if latest_rsi > 60:
    price_score += 20

elif latest_rsi < 40:
    price_score -= 20


if latest_volume > average_volume:
    price_score += 10


price_score = max(
    0,
    min(100, price_score)
)


# =========================
# COMBINED SENTIMENT
# =========================

if not atm_data.empty:

    final_score = round(
        (price_score * 0.60)
        +
        (option_score * 0.40)
    )

else:

    final_score = price_score


final_score = max(
    0,
    min(100, final_score)
)


if final_score >= 65:

    sentiment = "🟢 BULLISH"

elif final_score <= 35:

    sentiment = "🔴 BEARISH"

else:

    sentiment = "🟡 NEUTRAL"


# =========================
# MAIN DASHBOARD
# =========================

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
        f"{final_score} / 100",
        sentiment
    )


st.divider()


# =========================
# INDICATORS
# =========================

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

    if option_pcr is not None:

        st.metric(
            "PCR",
            f"{option_pcr:.2f}"
        )

    else:

        st.metric(
            "PCR",
            "N/A"
        )


st.divider()


# =========================
# OPTION CHAIN
# =========================

st.subheader("📊 NIFTY OPTION CHAIN")

if not atm_data.empty:

    st.success(
        f"Option Chain Connected • Spot: {option_spot:,.2f}"
    )

    st.write(
        f"### Option Sentiment: {option_bias}"
    )

    st.write(
        f"**Option Score: {option_score}/100**"
    )

    display_data = atm_data[
        [
            "Strike",
            "CE_OI",
            "CE_Delta_OI",
            "CE_Volume",
            "PE_OI",
            "PE_Delta_OI",
            "PE_Volume"
        ]
    ].copy()

    display_data.columns = [
        "Strike",
        "CE OI",
        "CE ΔOI",
        "CE Volume",
        "PE OI",
        "PE ΔOI",
        "PE Volume"
    ]

    st.dataframe(
        display_data,
        use_container_width=True,
        hide_index=True
    )

else:

    st.warning(
        "⚠️ अभी NSE Option Chain data उपलब्ध नहीं है। "
        "NIFTY price analysis फिर भी चल रहा है।"
    )


st.divider()


# =========================
# MARKET BIAS
# =========================

st.subheader("🎯 Current Market Bias")


if final_score >= 65:

    st.success(
        f"📈 UPSIDE BIAS — {final_score}/100"
    )

elif final_score <= 35:

    st.error(
        f"📉 DOWNSIDE BIAS — {final_score}/100"
    )

else:

    st.info(
        f"➡️ NEUTRAL — {final_score}/100"
    )


# =========================
# COMMENTARY
# =========================

st.subheader("🤖 AI Market Commentary")


if final_score >= 65:

    st.write(
        "NIFTY का वर्तमान sentiment bullish है। "
        "Price, VWAP, momentum और उपलब्ध option-chain "
        "signals को मिलाकर buyers का pressure दिखाई दे रहा है।"
    )

elif final_score <= 35:

    st.write(
        "NIFTY का वर्तमान sentiment bearish है। "
        "Price, VWAP, momentum और उपलब्ध option-chain "
        "signals sellers के pressure की ओर संकेत कर रहे हैं।"
    )

else:

    st.write(
        "NIFTY का sentiment फिलहाल neutral है। "
        "Market में स्पष्ट direction नहीं है। "
        "अधिक confirmation का इंतजार करना बेहतर है।"
    )


st.divider()


st.caption(
    "⚠️ यह market-analysis tool है। "
    "यह निश्चित भविष्यवाणी या investment advice नहीं है।"
)


# =========================
# REFRESH
# =========================

if st.button("🔄 Refresh Live Data"):

    st.cache_data.clear()

    st.rerun()
