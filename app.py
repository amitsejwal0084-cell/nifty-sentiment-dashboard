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


st.set_page_config(
    page_title="NIFTY Trading Dashboard",
    page_icon="📈",
    layout="wide"
)


st.title("📈 NIFTY PROFESSIONAL TRADING DASHBOARD")

st.caption(
    "Zerodha Kite Connect • Live Market Data"
)


API_KEY = st.secrets.get("KITE_API_KEY")
API_SECRET = st.secrets.get("KITE_API_SECRET")


if not API_KEY or not API_SECRET:

    st.error(
        "Kite API Key या API Secret Streamlit Secrets में नहीं मिला।"
    )

    st.stop()


kite = KiteConnect(
    api_key=API_KEY
)


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
                f"Kite Login Error: {e}"
            )

    st.stop()


kite.set_access_token(
    access_token
)


try:

    profile = kite.profile()

    user_name = profile.get(
        "user_name",
        "Kite User"
    )

except Exception as e:

    st.session_state.pop(
        "access_token",
        None
    )

    st.error(
        f"Kite Session Error: {e}"
    )

    st.stop()


st.success(
    f"🟢 Connected: {user_name}"
)


st.caption(
    "Last Update: "
    + datetime.now().strftime(
        "%d-%m-%Y %H:%M:%S"
    )
)


if st.button("🔄 Refresh Now"):

    st.rerun()


st.divider()


# ==============================
# LIVE MARKET
# ==============================

st.subheader("📊 Live Market")


market_symbols = [
    "NSE:NIFTY 50",
    "NSE:NIFTY BANK",
    "BSE:SENSEX",
    "NSE:NIFTY NEXT 50",
    "NSE:INDIA VIX"
]


try:

    market = kite.quote(
        market_symbols
    )

except Exception as e:

    st.error(
        f"Market Data Error: {e}"
    )

    st.stop()


def price(symbol):

    return market.get(
        symbol,
        {}
    ).get(
        "last_price",
        0
    )


def change(symbol):

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


c1, c2, c3, c4, c5 = st.columns(5)


with c1:

    st.metric(
        "NIFTY 50",
        f"{price('NSE:NIFTY 50'):,.2f}",
        f"{change('NSE:NIFTY 50'):+.2f}%"
    )


with c2:

    st.metric(
        "BANK NIFTY",
        f"{price('NSE:NIFTY BANK'):,.2f}",
        f"{change('NSE:NIFTY BANK'):+.2f}%"
    )


with c3:

    st.metric(
        "SENSEX",
        f"{price('BSE:SENSEX'):,.2f}",
        f"{change('BSE:SENSEX'):+.2f}%"
    )


with c4:

    st.metric(
        "NIFTY NEXT 50",
        f"{price('NSE:NIFTY NEXT 50'):,.2f}",
        f"{change('NSE:NIFTY NEXT 50'):+.2f}%"
    )


with c5:

    st.metric(
        "INDIA VIX",
        f"{price('NSE:INDIA VIX'):,.2f}",
        f"{change('NSE:INDIA VIX'):+.2f}%"
    )


# ==============================
# NIFTY
# ==============================

nifty_price = price(
    "NSE:NIFTY 50"
)


st.divider()


# ==============================
# OPTION CHAIN
# ==============================

st.subheader(
    "⛓️ NIFTY OPTION CHAIN"
)


try:

    option_data = get_live_option_chain(
        nifty_price,
        10
    )

except Exception as e:

    option_data = pd.DataFrame()

    st.error(
        f"Option Chain Error: {e}"
    )


if not option_data.empty:

    option_data = calculate_snapshot_oi_change(
        option_data
    )

    option_data = calculate_buildup(
        option_data
    )


pcr = calculate_pcr(
    option_data
)


support, resistance = (
    calculate_support_resistance(
        option_data
    )
)


max_pain = calculate_max_pain(
    option_data
)


sentiment, score = option_sentiment(
    option_data
)


# ==============================
# SUMMARY
# ==============================

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
        if pcr is not None
        else "-"
    )


with s3:

    st.metric(
        "Support",
        f"{support:,.0f}"
        if support is not None
        else "-"
    )


with s4:

    st.metric(
        "Resistance",
        f"{resistance:,.0f}"
        if resistance is not None
        else "-"
    )


with s5:

    st.metric(
        "Max Pain",
        f"{max_pain:,.0f}"
        if max_pain is not None
        else "-"
    )


with s6:

    st.metric(
        "Sentiment",
        sentiment
    )


st.divider()


# ==============================
# OPTION TABLE
# ==============================

if option_data.empty:

    st.info(
        "Option Chain अभी उपलब्ध नहीं है।"
    )

else:

    st.subheader(
        "📋 Option Chain Data"
    )

    st.dataframe(
        option_data,
        use_container_width=True,
        hide_index=True
    )


st.divider()


st.subheader(
    "⏱️ Dashboard Refresh"
)


auto_refresh = st.checkbox(
    "30 सेकंड Auto Refresh"
)


if auto_refresh:

    st.markdown(
        """
        <meta http-equiv="refresh" content="30">
        """,
        unsafe_allow_html=True
    )


st.caption(
    "Data Source: Zerodha Kite Connect"
)

st.caption(
    "यह dashboard केवल market-data analysis के लिए है।"
)
