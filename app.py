import streamlit as st
import pandas as pd
from datetime import datetime

from kiteconnect import KiteConnect

from Option_chan import (
    get_live_option_chain,
    calculate_pcr,
    calculate_support_resistance,
    calculate_max_pain,
    calculate_snapshot_oi_change,
    calculate_buildup,
    option_sentiment,
)


# =========================================================
# PAGE
# =========================================================

st.set_page_config(
    page_title="NIFTY Professional Dashboard",
    page_icon="📈",
    layout="wide",
)


# =========================================================
# STYLE
# =========================================================

st.markdown(
    """
    <style>

    .stApp {
        background-color: #0b0f14;
    }

    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
    }

    div[data-testid="stMetric"] {
        background-color: #151b23;
        border: 1px solid #293241;
        border-radius: 10px;
        padding: 10px;
    }

    .signal-box {
        padding: 18px;
        border-radius: 12px;
        background-color: #151b23;
        border: 1px solid #293241;
        text-align: center;
        font-size: 24px;
        font-weight: bold;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


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
# KITE CLIENT
# =========================================================

kite = KiteConnect(
    api_key=API_KEY
)


# =========================================================
# LOGIN
# =========================================================

access_token = st.session_state.get(
    "access_token"
)


if not access_token:

    st.subheader("🔐 Kite Login")

    st.link_button(
        "🔑 Login with Kite",
        kite.login_url(),
    )

    request_token = st.query_params.get(
        "request_token"
    )

    if request_token:

        try:

            session_data = kite.generate_session(
                request_token,
                api_secret=API_SECRET,
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
                f"Kite Login Error: {e}"
            )

    st.stop()


# =========================================================
# SET ACCESS TOKEN
# =========================================================

kite.set_access_token(
    access_token
)


# =========================================================
# PROFILE TEST
# =========================================================

try:

    profile = kite.profile()

    user_name = profile.get(
        "user_name",
        "Kite User",
    )

except Exception as e:

    st.session_state.pop(
        "access_token",
        None,
    )

    st.error(
        f"Kite session error: {e}"
    )

    st.stop()


# =========================================================
# TOP BAR
# =========================================================

c1, c2, c3 = st.columns(
    [2, 2, 1]
)

with c1:

    st.success(
        f"🟢 Connected: {user_name}"
    )

with c2:

    st.caption(
        "Last Update: "
        + datetime.now().strftime(
            "%d-%m-%Y %H:%M:%S"
        )
    )

with c3:

    if st.button(
        "🔄 Refresh Now",
        use_container_width=True,
    ):

        st.rerun()


# =========================================================
# MARKET QUOTES
# =========================================================

market_symbols = [
    "NSE:NIFTY 50",
    "NSE:NIFTY BANK",
    "BSE:SENSEX",
    "NSE:NIFTY NEXT 50",
    "NSE:INDIA VIX",
]


try:

    market = kite.quote(
        market_symbols
    )

except Exception as e:

    st.error(
        f"Market data error: {e}"
    )

    st.stop()


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def get_price(symbol):

    return market.get(
        symbol,
        {}
    ).get(
        "last_price",
        0,
    )


def get_change(symbol):

    data = market.get(
        symbol,
        {}
    )

    last_price = data.get(
        "last_price",
        0,
    )

    close_price = data.get(
        "ohlc",
        {}
    ).get(
        "close",
        0,
    )

    if close_price:

        return (
            (last_price - close_price)
            / close_price
        ) * 100

    return 0


# =========================================================
# MARKET OVERVIEW
# =========================================================

st.divider()

st.subheader(
    "📊 Market Overview"
)


m1, m2, m3, m4, m5 = st.columns(5)


with m1:

    st.metric(
        "NIFTY 50",
        f"{get_price('NSE:NIFTY 50'):,.2f}",
        f"{get_change('NSE:NIFTY 50'):+.2f}%",
    )


with m2:

    st.metric(
        "BANK NIFTY",
        f"{get_price('NSE:NIFTY BANK'):,.2f}",
        f"{get_change('NSE:NIFTY BANK'):+.2f}%",
    )


with m3:

    st.metric(
        "SENSEX",
        f"{get_price('BSE:SENSEX'):,.2f}",
        f"{get_change('BSE:SENSEX'):+.2f}%",
    )


with m4:

    st.metric(
        "NIFTY NEXT 50",
        f"{get_price('NSE:NIFTY NEXT 50'):,.2f}",
        f"{get_change('NSE:NIFTY NEXT 50'):+.2f}%",
    )


with m5:

    st.metric(
        "INDIA VIX",
        f"{get_price('NSE:INDIA VIX'):,.2f}",
        f"{get_change('NSE:INDIA VIX'):+.2f}%",
    )


# =========================================================
# NIFTY SPOT
# =========================================================

nifty_price = get_price(
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
        strikes_each_side=10,
    )

except Exception as e:

    option_data = pd.DataFrame()

    st.error(
        f"Option Chain Error: {e}"
    )


# =========================================================
# SNAPSHOT OI CHANGE
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
        f"{nifty_price:,.2f}",
    )


with s2:

    st.metric(
        "PCR",
        f"{pcr:.2f}",
    )


with s3:

    st.metric(
        "Support",
        f"{support:,.0f}"
        if support is not None
        else "-",
    )


with s4:

    st.metric(
        "Resistance",
        f"{resistance:,.0f}"
        if resistance is not None
        else "-",
    )


with s5:

    st.metric(
        "Max Pain",
        f"{max_pain:,.0f}"
        if max_pain is not None
        else "-",
    )


with s6:

    st.metric(
        "Sentiment",
        sentiment,
    )


# =========================================================
# SENTIMENT BOX
# =========================================================

st.markdown(
    f"""
    <div class="signal-box">
        MARKET SENTIMENT: {sentiment}
    </div>
    """,
    unsafe_allow_html=True,
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
            "buildup",
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
        "Buildup",
    ]

    display["LTP"] = pd.to_numeric(
        display["LTP"],
        errors="coerce",
    ).round(2)

    display["OI"] = pd.to_numeric(
        display["OI"],
        errors="coerce",
    ).fillna(0).astype(int)

    display["OI Δ"] = pd.to_numeric(
        display["OI Δ"],
        errors="coerce",
    ).fillna(0).astype(int)

    display["Volume"] = pd.to_numeric(
        display["Volume"],
        errors="coerce",
    ).fillna(0).astype(int)

    display["Bid"] = pd.to_numeric(
        display["Bid"],
        errors="coerce",
    ).round(2)

    display["Ask"] = pd.to_numeric(
        display["Ask"],
        errors="coerce",
    ).round(2)


    st.markdown(
        "### 🟢 CALL SIDE — CE"
    )

    calls = display[
        display["Type"] == "CE"
    ]

    st.dataframe(
        calls,
        use_container_width=True,
        hide_index=True,
    )


    st.markdown(
        "### 🔴 PUT SIDE — PE"
    )

    puts = display[
        display["Type"] == "PE"
    ]

    st.dataframe(
        puts,
        use_container_width=True,
        hide_index=True,
    )

else:

    st.warning(
        "Option Chain data उपलब्ध नहीं है।"
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
        option_data["buildup"]
        .value_counts()
    )

    b1, b2, b3, b4 = st.columns(4)


    with b1:

        st.metric(
            "Long Buildup",
            int(
                buildup_counts.get(
                    "LONG BUILDUP",
                    0,
                )
            ),
        )


    with b2:

        st.metric(
            "Short Buildup",
            int(
                buildup_counts.get(
                    "SHORT BUILDUP",
                    0,
                )
            ),
        )


    with b3:

        st.metric(
            "Short Covering",
            int(
                buildup_counts.get(
                    "SHORT COVERING",
                    0,
                )
            ),
        )


    with b4:

        st.metric(
            "Long Unwinding",
            int(
                buildup_counts.get(
                    "LONG UNWINDING",
                    0,
                )
            ),
        )


# =========================================================
# REFRESH CONTROL
# =========================================================

st.divider()

st.subheader(
    "⏱️ Dashboard Refresh"
)

auto_refresh = st.checkbox(
    "30 सेकंड Auto Refresh",
    value=False,
)

if auto_refresh:

    st.info(
        "Auto Refresh ON — page हर 30 सेकंड में update होगी।"
    )

else:

    st.caption(
        "Auto Refresh OFF — Refresh Now button से update करें।"
    )


# =========================================================
# AUTO REFRESH USING META REFRESH
# =========================================================

if auto_refresh:

    st.markdown(
        """
        <meta http-equiv="refresh" content="30">
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "⚠️ यह dashboard केवल market-data analysis के लिए है। "
    "BUY/SELL bias guaranteed result नहीं है।"
)

st.caption(
    "OI Δ = पिछले dashboard snapshot की तुलना में OI परिवर्तन।"
)

st.caption(
    "Data Source: Zerodha Kite Connect"
)
