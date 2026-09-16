import streamlit as st
import pandas as pd
from datetime import datetime
from kiteconnect import KiteConnect


st.set_page_config(
    page_title="NIFTY Live Dashboard",
    page_icon="📈",
    layout="wide"
)


st.title("📈 NIFTY LIVE TRADING DASHBOARD")
st.caption("Zerodha Kite Connect • Real Market Data")


# =====================================================
# KITE
# =====================================================

API_KEY = st.secrets.get("KITE_API_KEY")
API_SECRET = st.secrets.get("KITE_API_SECRET")

if not API_KEY or not API_SECRET:
    st.error("Kite API credentials नहीं मिले।")
    st.stop()


kite = KiteConnect(api_key=API_KEY)


# =====================================================
# LOGIN
# =====================================================

access_token = st.session_state.get("access_token")


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

            session = kite.generate_session(
                request_token,
                api_secret=API_SECRET
            )

            st.session_state["access_token"] = (
                session["access_token"]
            )

            st.query_params.clear()

            st.success("✅ Kite Login Successful")

            st.rerun()

        except Exception as e:

            st.error(
                f"Kite Login Error: {e}"
            )

    st.stop()


kite.set_access_token(access_token)


# =====================================================
# CONNECTION TEST
# =====================================================

try:

    profile = kite.profile()

    st.success(
        f"🟢 Connected: {profile.get('user_name', 'Kite User')}"
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


st.caption(
    "Last Update: "
    + datetime.now().strftime(
        "%d-%m-%Y %H:%M:%S"
    )
)


if st.button("🔄 Refresh"):

    st.rerun()


# =====================================================
# LIVE INDICES
# =====================================================

st.divider()

st.subheader("📊 Live Market")


index_symbols = [
    "NSE:NIFTY 50",
    "NSE:NIFTY BANK",
    "BSE:SENSEX",
    "NSE:NIFTY NEXT 50",
    "NSE:INDIA VIX"
]


try:

    market = kite.quote(index_symbols)

except Exception as e:

    st.error(
        f"Market Data Error: {e}"
    )

    st.stop()


def get_ltp(symbol):

    return market.get(
        symbol,
        {}
    ).get(
        "last_price",
        0
    )


def get_percent_change(symbol):

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
        f"{get_ltp('NSE:NIFTY 50'):,.2f}",
        f"{get_percent_change('NSE:NIFTY 50'):+.2f}%"
    )


with c2:

    st.metric(
        "BANK NIFTY",
        f"{get_ltp('NSE:NIFTY BANK'):,.2f}",
        f"{get_percent_change('NSE:NIFTY BANK'):+.2f}%"
    )


with c3:

    st.metric(
        "SENSEX",
        f"{get_ltp('BSE:SENSEX'):,.2f}",
        f"{get_percent_change('BSE:SENSEX'):+.2f}%"
    )


with c4:

    st.metric(
        "NIFTY NEXT 50",
        f"{get_ltp('NSE:NIFTY NEXT 50'):,.2f}",
        f"{get_percent_change('NSE:NIFTY NEXT 50'):+.2f}%"
    )


with c5:

    st.metric(
        "INDIA VIX",
        f"{get_ltp('NSE:INDIA VIX'):,.2f}",
        f"{get_percent_change('NSE:INDIA VIX'):+.2f}%"
    )


# =====================================================
# NIFTY OPTION CHAIN
# =====================================================

st.divider()

st.subheader("⛓️ NIFTY LIVE OPTION CHAIN")


nifty_price = get_ltp(
    "NSE:NIFTY 50"
)


try:

    instruments = kite.instruments("NFO")

    df = pd.DataFrame(instruments)

except Exception as e:

    st.error(
        f"NFO Error: {e}"
    )

    st.stop()


if df.empty:

    st.warning(
        "NFO instruments उपलब्ध नहीं हैं।"
    )

    st.stop()


# =====================================================
# FILTER NIFTY OPTIONS
# =====================================================

df["expiry"] = pd.to_datetime(
    df["expiry"],
    errors="coerce"
).dt.date


df["strike"] = pd.to_numeric(
    df["strike"],
    errors="coerce"
)


today = datetime.now().date()


options = df[
    (df["name"] == "NIFTY") &
    (
        df["instrument_type"]
        .isin(["CE", "PE"])
    ) &
    (
        df["expiry"] >= today
    )
].copy()


if options.empty:

    st.warning(
        "NIFTY options नहीं मिले।"
    )

    st.stop()


# =====================================================
# NEAREST EXPIRY
# =====================================================

expiry = sorted(
    options["expiry"]
    .dropna()
    .unique()
)[0]


options = options[
    options["expiry"] == expiry
].copy()


st.info(
    f"📅 Expiry: {expiry}"
)


# =====================================================
# ATM
# =====================================================

atm = round(
    nifty_price / 50
) * 50


st.write(
    f"**NIFTY:** {nifty_price:,.2f}   |   "
    f"**ATM:** {atm:,.0f}"
)


# =====================================================
# ATM ±10
# =====================================================

options = options[
    (options["strike"] >= atm - 500) &
    (options["strike"] <= atm + 500)
].copy()


# =====================================================
# QUOTES
# =====================================================

quote_keys = [
    "NFO:" + symbol
    for symbol in options["tradingsymbol"]
]


quotes = {}


for start in range(
    0,
    len(quote_keys),
    100
):

    batch = quote_keys[
        start:start + 100
    ]

    try:

        result = kite.quote(batch)

        quotes.update(result)

    except Exception as e:

        st.warning(
            f"Quote error: {e}"
        )


# =====================================================
# BUILD TABLE
# =====================================================

rows = []


for _, row in options.iterrows():

    symbol = row["tradingsymbol"]

    quote = quotes.get(
        "NFO:" + symbol,
        {}
    )

    depth = quote.get(
        "depth",
        {}
    )


    buy = depth.get(
        "buy",
        []
    )


    sell = depth.get(
        "sell",
        []
    )


    bid = None

    ask = None


    if buy:

        bid = buy[0].get(
            "price"
        )


    if sell:

        ask = sell[0].get(
            "price"
        )


    rows.append({

        "Strike": row["strike"],

        "Type": row["instrument_type"],

        "Symbol": symbol,

        "LTP": quote.get(
            "last_price"
        ),

        "OI": quote.get(
            "oi"
        ),

        "Volume": quote.get(
            "volume"
        ),

        "Bid": bid,

        "Ask": ask

    })


option_data = pd.DataFrame(
    rows
)


# =====================================================
# SUMMARY
# =====================================================

if not option_data.empty:

    ce = option_data[
        option_data["Type"] == "CE"
    ]

    pe = option_data[
        option_data["Type"] == "PE"
    ]


    ce_oi = ce["OI"].fillna(
        0
    ).sum()


    pe_oi = pe["OI"].fillna(
        0
    ).sum()


    if ce_oi > 0:

        pcr = pe_oi / ce_oi

    else:

        pcr = None


    if not pe.empty:

        support = pe.loc[
            pe["OI"].fillna(0).idxmax(),
            "Strike"
        ]

    else:

        support = None


    if not ce.empty:

        resistance = ce.loc[
            ce["OI"].fillna(0).idxmax(),
            "Strike"
        ]

    else:

        resistance = None


else:

    pcr = None
    support = None
    resistance = None


# =====================================================
# SUMMARY CARDS
# =====================================================

st.divider()

s1, s2, s3, s4 = st.columns(4)


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


# =====================================================
# CE
# =====================================================

st.divider()

st.subheader("🟢 CALL — CE")


st.dataframe(
    option_data[
        option_data["Type"] == "CE"
    ],
    use_container_width=True,
    hide_index=True
)


# =====================================================
# PE
# =====================================================

st.subheader("🔴 PUT — PE")


st.dataframe(
    option_data[
        option_data["Type"] == "PE"
    ],
    use_container_width=True,
    hide_index=True
)


# =====================================================
# AUTO REFRESH
# =====================================================

st.divider()

auto_refresh = st.checkbox(
    "⏱️ 30 सेकंड Auto Refresh"
)


if auto_refresh:

    st.markdown(
        '<meta http-equiv="refresh" content="30">',
        unsafe_allow_html=True
    )


st.divider()

st.caption(
    "Data Source: Zerodha Kite Connect"
)

st.caption(
    "Live snapshot data • No simulated data"
)

st.caption(
    "यह dashboard केवल market-data analysis के लिए है।"
)
