import streamlit as st
import pandas as pd
import time
from datetime import datetime, date, time as dt_time
from kiteconnect import KiteConnect

from Option_chan import (
    get_live_option_chain,
    calculate_pcr,
    calculate_support_resistance,
    calculate_max_pain,
    calculate_snapshot_oi_change,
    calculate_buildup,
    option_sentiment
)

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="NIFTY Professional Trading Dashboard",
    page_icon="📈",
    layout="wide"
)

# =========================================================
# STYLE
# =========================================================

st.markdown("""
<style>

.stApp {
    background-color: #0b0f14;
}

.block-container {
    padding-top: 1rem;
    padding-bottom: 2rem;
}

h1, h2, h3 {
    color: white;
}

div[data-testid="stMetric"] {
    background-color: #151b23;
    border: 1px solid #293241;
    padding: 12px;
    border-radius: 10px;
}

.signal {
    padding: 18px;
    border-radius: 12px;
    background-color: #151b23;
    border: 1px solid #293241;
    text-align: center;
    font-size: 25px;
    font-weight: bold;
}

.info-box {
    padding: 12px;
    border-radius: 10px;
    background-color: #151b23;
    border: 1px solid #293241;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# TITLE
# =========================================================

st.title("📈 NIFTY PROFESSIONAL TRADING DASHBOARD")

st.caption(
    "Zerodha Kite Connect • Live Market Data • Option Chain Analysis"
)

# =========================================================
# SECRETS
# =========================================================

API_KEY = st.secrets.get("KITE_API_KEY")
API_SECRET = st.secrets.get("KITE_API_SECRET")

if not API_KEY or not API_SECRET:

    st.error(
        "Kite API credentials Streamlit Secrets में नहीं मिले।"
    )

    st.stop()

# =========================================================
# KITE
# =========================================================

kite = KiteConnect(
    api_key=API_KEY
)

# =========================================================
# LOGIN / SESSION
# =========================================================

access_token = st.session_state.get(
    "access_token"
)

if not access_token:

    st.subheader("🔐 Kite Login")

    st.link_button(
        "🔑 Login with Kite",
        kite.login_url()
    )

    request_token = st.query_params.get(
        "request_token"
    )

    if request_token:

        try:

            session_data = kite.generate_session(
                request_token,
                api_secret=API_SECRET
            )

            access_token = session_data[
                "access_token"
            ]

            st.session_state[
                "access_token"
            ] = access_token

            st.query_params.clear()

            st.success(
                "✅ Kite Login Successful"
            )

            st.rerun()

        except Exception as e:

            st.error(
                f"Login Error: {e}"
            )

    st.stop()

# =========================================================
# SET TOKEN
# =========================================================

kite.set_access_token(
    access_token
)

# =========================================================
# PROFILE
# =========================================================

try:

    profile = kite.profile()

    user_name = profile.get(
        "user_name",
        "Kite User"
    )

except Exception:

    st.session_state.pop(
        "access_token",
        None
    )

    st.error(
        "Kite session expire हो गया है।"
    )

    st.stop()

# =========================================================
# TOP BAR
# =========================================================

top1, top2, top3 = st.columns(
    [2, 2, 1]
)

with top1:

    st.success(
        f"🟢 Connected: {user_name}"
    )

with top2:

    st.caption(
        "Last Update: "
        + datetime.now().strftime(
            "%d-%m-%Y %H:%M:%S"
        )
    )

with top3:

    refresh = st.button(
        "🔄 Refresh Now"
    )

if refresh:

    st.rerun()

# =========================================================
# MARKET DATA
# =========================================================

symbols = [

    "NSE:NIFTY 50",
    "NSE:NIFTY BANK",
    "BSE:SENSEX",
    "NSE:NIFTY NEXT 50",
    "NSE:INDIA VIX"

]

try:

    market = kite.quote(
        symbols
    )

except Exception as e:

    st.error(
        f"Market data error: {e}"
    )

    st.stop()

# =========================================================
# HELPERS
# =========================================================

def price(symbol):

    return market.get(
        symbol,
        {}
    ).get(
        "last_price",
        0
    )


def percent_change(symbol):

    data = market.get(
        symbol,
        {}
    )

    last = data.get(
        "last_price",
        0
    )

    close = data.get(
        "ohlc",
        {}
    ).get(
        "close",
        0
    )

    if close:

        return (
            (last - close)
            / close
        ) * 100

    return 0


# =========================================================
# MARKET OVERVIEW
# =========================================================

st.divider()

st.subheader(
    "📊 Market Overview"
)

c1, c2, c3, c4, c5 = st.columns(5)

with c1:

    st.metric(
        "NIFTY 50",
        f"{price('NSE:NIFTY 50'):,.2f}",
        f"{percent_change('NSE:NIFTY 50'):+.2f}%"
    )

with c2:

    st.metric(
        "BANK NIFTY",
        f"{price('NSE:NIFTY BANK'):,.2f}",
        f"{percent_change('NSE:NIFTY BANK'):+.2f}%"
    )

with c3:

    st.metric(
        "SENSEX",
        f"{price('BSE:SENSEX'):,.2f}",
        f"{percent_change('BSE:SENSEX'):+.2f}%"
    )

with c4:

    st.metric(
        "NIFTY NEXT 50",
        f"{price('NSE:NIFTY NEXT 50'):,.2f}",
        f"{percent_change('NSE:NIFTY NEXT 50'):+.2f}%"
    )

with c5:

    st.metric(
        "INDIA VIX",
        f"{price('NSE:INDIA VIX'):,.2f}",
        f"{percent_change('NSE:INDIA VIX'):+.2f}%"
    )

# =========================================================
# NIFTY PRICE
# =========================================================

nifty_price = price(
    "NSE:NIFTY 50"
)

# =========================================================
# OPTION CHAIN
# =========================================================

st.divider()

st.subheader(
    "⛓️ NIFTY OPTION CHAIN"
)

try:

    option_data = get_live_option_chain(
        nifty_price,
        strikes_each_side=10
    )

except Exception as e:

    option_data = pd.DataFrame()

    st.error(
        f"Option Chain Error: {e}"
    )

# =========================================================
# OI SNAPSHOT CHANGE
# =========================================================

if not option_data.empty:

    option_data = calculate_snapshot_oi_change(
        option_data
    )

    option_data = calculate_buildup(
        option_data
    )

# =========================================================
# PCR
# =========================================================

pcr = calculate_pcr(
    option_data
)

if pcr is None:

    pcr = 0

# =========================================================
# SUPPORT / RESISTANCE
# =========================================================

support, resistance = (
    calculate_support_resistance(
        option_data
    )
)

# =========================================================
# MAX PAIN
# =========================================================

max_pain = calculate_max_pain(
    option_data
)

# =========================================================
# SENTIMENT
# =========================================================

sentiment, sentiment_score = (
    option_sentiment(
        option_data
    )
)

# =========================================================
# OPTION SUMMARY
# =========================================================

s1, s2, s3, s4, s5, s6 = st.columns(6)

with s1:

    st.metric(
        "NIFTY",
        f"{nifty_price:,.2f}"
    )

with s2:

    st.metric(
        "PCR",
        f"{pcr:.2f}"
    )

with s3:

    st.metric(
        "Support",
        f"{support:,.0f}"
        if support
        else "-"
    )

with s4:

    st.metric(
        "Resistance",
        f"{resistance:,.0f}"
        if resistance
        else "-"
    )

with s5:

    st.metric(
        "Max Pain",
        f"{max_pain:,.0f}"
        if max_pain
        else "-"
    )

with s6:

    st.metric(
        "Sentiment",
        sentiment
    )

# =========================================================
# SENTIMENT DISPLAY
# =========================================================

st.markdown(
    f"""
    <div class="signal">
    MARKET SENTIMENT: {sentiment}
    </div>
    """,
    unsafe_allow_html=True
)

# =========================================================
# OPTION TABLE
# =========================================================

if not option_data.empty:

    display = option_data.copy()

    display = display[
        [
            "strike",
            "type",
            "ltp",
            "oi",
            "oi_change",
            "volume",
            "bid",
            "ask",
            "buildup"
        ]
    ]

    display.columns = [

        "Strike",
        "Type",
        "LTP",
        "OI",
        "OI Δ",
        "Volume",
        "Bid",
        "Ask",
        "Buildup"

    ]

    display["LTP"] = pd.to_numeric(
        display["LTP"],
        errors="coerce"
    ).round(2)

    display["OI"] = pd.to_numeric(
        display["OI"],
        errors="coerce"
    ).fillna(0).astype(int)

    display["OI Δ"] = pd.to_numeric(
        display["OI Δ"],
        errors="coerce"
    ).fillna(0).astype(int)

    display["Volume"] = pd.to_numeric(
        display["Volume"],
        errors="coerce"
    ).fillna(0).astype(int)

    display["Bid"] = pd.to_numeric(
        display["Bid"],
        errors="coerce"
    ).round(2)

    display["Ask"] = pd.to_numeric(
        display["Ask"],
        errors="coerce"
    ).round(2)

    # ---------------------------------------------
    # CALLS
    # ---------------------------------------------

    st.markdown(
        "### 🟢 CALL SIDE — CE"
    )

    calls = display[
        display["Type"] == "CE"
    ].copy()

    st.dataframe(
        calls,
        use_container_width=True,
        hide_index=True
    )

    # ---------------------------------------------
    # PUTS
    # ---------------------------------------------

    st.markdown(
        "### 🔴 PUT SIDE — PE"
    )

    puts = display[
        display["Type"] == "PE"
    ].copy()

    st.dataframe(
        puts,
        use_container_width=True,
        hide_index=True
    )

else:

    st.warning(
        "Option Chain data अभी उपलब्ध नहीं है।"
    )

# =========================================================
# BUILDUP SUMMARY
# =========================================================

st.divider()

st.subheader(
    "🧠 Option Buildup Summary"
)

if not option_data.empty:

    buildup_counts = (
        option_data[
            "buildup"
        ]
        .value_counts()
    )

    b1, b2, b3, b4 = st.columns(4)

    with b1:

        st.metric(
            "Long Buildup",
            int(
                buildup_counts.get(
                    "LONG BUILDUP",
                    0
                )
            )
        )

    with b2:

        st.metric(
            "Short Buildup",
            int(
                buildup_counts.get(
                    "SHORT BUILDUP",
                    0
                )
            )
        )

    with b3:

        st.metric(
            "Short Covering",
            int(
                buildup_counts.get(
                    "SHORT COVERING",
                    0
                )
            )
        )

    with b4:

        st.metric(
            "Long Unwinding",
            int(
                buildup_counts.get(
                    "LONG UNWINDING",
                    0
                )
            )
        )

# =========================================================
# AUTO REFRESH
# =========================================================

st.divider()

st.subheader(
    "⏱️ Live Refresh"
)

st.info(
    "Dashboard को हर 30 सेकंड में refresh करने के लिए नीचे का विकल्प ON करें।"
)

auto_refresh = st.checkbox(
    "30 सेकंड Auto Refresh",
    value=False
)

if auto_refresh:

    st.caption(
        "Auto refresh ON • Live Kite quote snapshot"
    )

    time.sleep(30)

    st.rerun()

else:

    st.caption(
        "Auto refresh OFF • ऊपर Refresh Now दबाकर manually update करें।"
    )

# =========================================================
# DISCLAIMER
# =========================================================

st.divider()

st.caption(
    "⚠️ यह dashboard केवल market-data analysis के लिए है। "
    "BUY/SELL bias कोई guaranteed result नहीं है।"
)

st.caption(
    "OI Δ = पिछले dashboard snapshot की तुलना में OI परिवर्तन।"
)

st.caption(
    "Data Source: Zerodha Kite Connect"
)

if not option_chain.empty:

    call_oi = option_chain[
        option_chain["Type"] == "CE"
    ]["OI"].fillna(0).sum()

    put_oi = option_chain[
        option_chain["Type"] == "PE"
    ]["OI"].fillna(0).sum()

    if call_oi > 0:

        pcr = put_oi / call_oi

    else:

        pcr = 0

else:

    pcr = 0

# =========================================================
# SUPPORT / RESISTANCE
# =========================================================

support = None
resistance = None

if not option_chain.empty:

    calls = option_chain[
        option_chain["Type"] == "CE"
    ].copy()

    puts = option_chain[
        option_chain["Type"] == "PE"
    ].copy()

    if not calls.empty:

        calls = calls.dropna(
            subset=["OI"]
        )

        if not calls.empty:

            resistance = calls.loc[
                calls["OI"].idxmax(),
                "Strike"
            ]

    if not puts.empty:

        puts = puts.dropna(
            subset=["OI"]
        )

        if not puts.empty:

            support = puts.loc[
                puts["OI"].idxmax(),
                "Strike"
            ]

# =========================================================
# OPTION SUMMARY
# =========================================================

o1, o2, o3, o4, o5 = st.columns(5)

with o1:

    st.metric(
        "ATM",
        f"{atm:,.0f}"
        if not option_chain.empty
        else "-"
    )

with o2:

    st.metric(
        "PCR",
        f"{pcr:.2f}"
    )

with o3:

    st.metric(
        "Support",
        f"{support:,.0f}"
        if support
        else "-"
    )

with o4:

    st.metric(
        "Resistance",
        f"{resistance:,.0f}"
        if resistance
        else "-"
    )

with o5:

    st.metric(
        "Expiry",
        str(nearest_expiry)
        if nearest_expiry
        else "-"
    )

# =========================================================
# OPTION SENTIMENT
# =========================================================

if pcr >= 1.20:

    option_bias = "BULLISH"

elif pcr <= 0.80:

    option_bias = "BEARISH"

else:

    option_bias = "NEUTRAL"

st.markdown(
    f"""
    <div class="signal-box">
    Option Sentiment: {option_bias}
    </div>
    """,
    unsafe_allow_html=True
)

# =========================================================
# OPTION TABLE
# =========================================================

if not option_chain.empty:

    display_chain = option_chain.copy()

    display_chain["LTP"] = display_chain[
        "LTP"
    ].round(2)

    display_chain["OI"] = display_chain[
        "OI"
    ].fillna(0).astype(int)

    display_chain["Volume"] = display_chain[
        "Volume"
    ].fillna(0).astype(int)

    display_chain["Bid"] = display_chain[
        "Bid"
    ].round(2)

    display_chain["Ask"] = display_chain[
        "Ask"
    ].round(2)

    st.dataframe(
        display_chain,
        use_container_width=True,
        hide_index=True
    )

else:

    st.warning(
        "Option Chain data उपलब्ध नहीं है।"
    )

# =========================================================
# TECHNICAL ANALYSIS
# =========================================================

st.divider()

st.subheader("📈 Technical Analysis")

# ---------------------------------------------------------
# FIND NIFTY INDEX TOKEN
# ---------------------------------------------------------

@st.cache_data(ttl=3600)
def get_nifty_token(api_key, token):

    client = KiteConnect(
        api_key=api_key
    )

    client.set_access_token(token)

    instruments = client.instruments(
        "NSE"
    )

    df = pd.DataFrame(
        instruments
    )

    if df.empty:
        return None

    match = df[
        df["tradingsymbol"] == "NIFTY 50"
    ]

    if match.empty:
        return None

    return int(
        match.iloc[0]["instrument_token"]
    )

# =========================================================
# HISTORICAL DATA
# =========================================================

hist_df = pd.DataFrame()

try:

    nifty_token = get_nifty_token(
        API_KEY,
        access_token
    )

    if nifty_token:

        now = datetime.now()

        market_open = datetime.combine(
            date.today(),
            time(9, 15)
        )

        if now > market_open:

            candles = kite.historical_data(
                nifty_token,
                market_open,
                now,
                "5minute"
            )

            hist_df = pd.DataFrame(
                candles
            )

except Exception as e:

    st.warning(
        f"Technical data अभी उपलब्ध नहीं: {e}"
    )

# =========================================================
# RSI
# =========================================================

def calculate_rsi(
    series,
    period=14
):

    delta = series.diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

    avg_gain = gain.rolling(
        period
    ).mean()

    avg_loss = loss.rolling(
        period
    ).mean()

    rs = (
        avg_gain /
        avg_loss.replace(
            0,
            pd.NA
        )
    )

    rsi = 100 - (
        100 / (1 + rs)
    )

    return rsi


# =========================================================
# VWAP
# =========================================================

if not hist_df.empty:

    hist_df["date"] = pd.to_datetime(
        hist_df["date"]
    )

    hist_df["close"] = pd.to_numeric(
        hist_df["close"],
        errors="coerce"
    )

    hist_df["high"] = pd.to_numeric(
        hist_df["high"],
        errors="coerce"
    )

    hist_df["low"] = pd.to_numeric(
        hist_df["low"],
        errors="coerce"
    )

    hist_df["volume"] = pd.to_numeric(
        hist_df["volume"],
        errors="coerce"
    )

    hist_df["RSI"] = calculate_rsi(
        hist_df["close"]
    )

    typical_price = (
        hist_df["high"] +
        hist_df["low"] +
        hist_df["close"]
    ) / 3

    cumulative_volume = (
        hist_df["volume"]
        .fillna(0)
        .cumsum()
    )

    cumulative_value = (
        typical_price *
        hist_df["volume"].fillna(0)
    ).cumsum()

    hist_df["VWAP"] = (
        cumulative_value /
        cumulative_volume.replace(
            0,
            pd.NA
        )
    )

    latest = hist_df.iloc[-1]

    rsi_value = latest["RSI"]

    vwap_value = latest["VWAP"]

else:

    rsi_value = None

    vwap_value = None

# =========================================================
# TECHNICAL METRICS
# =========================================================

t1, t2, t3, t4 = st.columns(4)

with t1:

    st.metric(
        "NIFTY Price",
        f"{nifty_price:,.2f}"
    )

with t2:

    st.metric(
        "RSI (14)",
        f"{rsi_value:.2f}"
        if pd.notna(rsi_value)
        else "-"
    )

with t3:

    st.metric(
        "VWAP",
        f"{vwap_value:,.2f}"
        if pd.notna(vwap_value)
        else "-"
    )

with t4:

    if (
        vwap_value is not None
        and pd.notna(vwap_value)
    ):

        if nifty_price > vwap_value:

            trend = "ABOVE VWAP"

        else:

            trend = "BELOW VWAP"

    else:

        trend = "NO DATA"

    st.metric(
        "Trend",
        trend
    )

# =========================================================
# STRATEGY SIGNAL
# =========================================================

st.divider()

st.subheader("🎯 Trading Signal")

signal = "WAIT"

signal_reason = []

if (
    rsi_value is not None
    and pd.notna(rsi_value)
    and vwap_value is not None
    and pd.notna(vwap_value)
):

    if (
        rsi_value > 60
        and nifty_price > vwap_value
    ):

        signal = "BUY BIAS"

        signal_reason.append(
            "RSI > 60"
        )

        signal_reason.append(
            "Price > VWAP"
        )

    elif (
        rsi_value < 40
        and nifty_price < vwap_value
    ):

        signal = "SELL BIAS"

        signal_reason.append(
            "RSI < 40"
        )

        signal_reason.append(
            "Price < VWAP"
        )

    else:

        signal = "WAIT / NEUTRAL"

        signal_reason.append(
            "Conditions पूरी नहीं हुईं"
        )

# =========================================================
# SIGNAL DISPLAY
# =========================================================

st.markdown(
    f"""
    <div class="signal-box">
    {signal}
    </div>
    """,
    unsafe_allow_html=True
)

if signal_reason:

    st.write(
        " • ".join(
            signal_reason
        )
    )

# =========================================================
# PRICE CHART
# =========================================================

if not hist_df.empty:

    st.divider()

    st.subheader(
        "📉 NIFTY 5-Minute Price Chart"
    )

    chart_df = hist_df[
        [
            "date",
            "close"
        ]
    ].copy()

    chart_df = chart_df.set_index(
        "date"
    )

    st.line_chart(
        chart_df,
        use_container_width=True
    )

# =========================================================
# IMPORTANT NOTE
# =========================================================

st.divider()

st.caption(
    "⚠️ यह dashboard केवल market-data analysis और educational/research use के लिए है। "
    "Signal कोई guaranteed trading result नहीं है।"
)

st.caption(
    "Data source: Zerodha Kite Connect."

