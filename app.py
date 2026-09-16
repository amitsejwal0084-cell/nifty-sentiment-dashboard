import streamlit as st
import pandas as pd
from datetime import datetime
from kiteconnect import KiteConnect


# =====================================================
# PAGE
# =====================================================

st.set_page_config(
    page_title="NIFTY Professional Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("📈 NIFTY PROFESSIONAL TRADING DASHBOARD")

st.caption(
    "Zerodha Kite Connect • Real Market Data"
)


# =====================================================
# KITE SETTINGS
# =====================================================

API_KEY = st.secrets.get("KITE_API_KEY")
API_SECRET = st.secrets.get("KITE_API_SECRET")

if not API_KEY or not API_SECRET:

    st.error(
        "KITE_API_KEY / KITE_API_SECRET Streamlit Secrets में नहीं मिले।"
    )

    st.stop()


kite = KiteConnect(
    api_key=API_KEY
)


# =====================================================
# LOGIN
# =====================================================

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


# =====================================================
# CONNECTION
# =====================================================

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


# =====================================================
# MARKET DATA
# =====================================================

st.divider()

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


def get_price(symbol):

    return market.get(
        symbol,
        {}
    ).get(
        "last_price",
        0
    )


def get_change(symbol):

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
        f"{get_price('NSE:NIFTY 50'):,.2f}",
        f"{get_change('NSE:NIFTY 50'):+.2f}%"
    )


with c2:

    st.metric(
        "BANK NIFTY",
        f"{get_price('NSE:NIFTY BANK'):,.2f}",
        f"{get_change('NSE:NIFTY BANK'):+.2f}%"
    )


with c3:

    st.metric(
        "SENSEX",
        f"{get_price('BSE:SENSEX'):,.2f}",
        f"{get_change('BSE:SENSEX'):+.2f}%"
    )


with c4:

    st.metric(
        "NIFTY NEXT 50",
        f"{get_price('NSE:NIFTY NEXT 50'):,.2f}",
        f"{get_change('NSE:NIFTY NEXT 50'):+.2f}%"
    )


with c5:

    st.metric(
        "INDIA VIX",
        f"{get_price('NSE:INDIA VIX'):,.2f}",
        f"{get_change('NSE:INDIA VIX'):+.2f}%"
    )


# =====================================================
# NIFTY SPOT
# =====================================================

nifty_price = get_price(
    "NSE:NIFTY 50"
)


# =====================================================
# NFO INSTRUMENTS
# =====================================================

st.divider()

st.subheader(
    "⛓️ NIFTY LIVE OPTION CHAIN"
)


try:

    instruments = kite.instruments(
        "NFO"
    )

    instruments_df = pd.DataFrame(
        instruments
    )

except Exception as e:

    st.error(
        f"NFO Instrument Error: {e}"
    )

    st.stop()


if instruments_df.empty:

    st.warning(
        "NFO instrument data उपलब्ध नहीं है।"
    )

    st.stop()


# =====================================================
# PREPARE INSTRUMENT DATA
# =====================================================

instruments_df["expiry"] = pd.to_datetime(
    instruments_df["expiry"],
    errors="coerce"
).dt.date


instruments_df["strike"] = pd.to_numeric(
    instruments_df["strike"],
    errors="coerce"
)


today = datetime.now().date()


options = instruments_df[
    (instruments_df["name"] == "NIFTY") &
    (
        instruments_df["instrument_type"]
        .isin(["CE", "PE"])
    ) &
    (
        instruments_df["expiry"] >= today
    )
].copy()


if options.empty:

    st.warning(
        "NIFTY option contracts नहीं मिले।"
    )

    st.stop()


# =====================================================
# NEAREST EXPIRY
# =====================================================

nearest_expiry = sorted(
    options["expiry"]
    .dropna()
    .unique()
)[0]


options = options[
    options["expiry"] == nearest_expiry
].copy()


st.info(
    f"📅 Nearest Expiry: {nearest_expiry}"
)


# =====================================================
# ATM
# =====================================================

atm = round(
    nifty_price / 50
) * 50


st.write(
    f"**NIFTY Spot:** {nifty_price:,.2f}  |  "
    f"**ATM:** {atm:,.0f}"
)


# =====================================================
# ATM ±10 STRIKES
# =====================================================

strike_step = 50

low_strike = (
    atm - (10 * strike_step)
)

high_strike = (
    atm + (10 * strike_step)
)


options = options[
    (options["strike"] >= low_strike) &
    (options["strike"] <= high_strike)
].copy()


# =====================================================
# QUOTES
# =====================================================

quote_symbols = [
    "NFO:" + symbol
    for symbol in options[
        "tradingsymbol"
    ]
]


quotes = {}


for start in range(
    0,
    len(quote_symbols),
    100
):

    batch = quote_symbols[
        start:start + 100
    ]

    try:

        response = kite.quote(
            batch
        )

        if response:

            quotes.update(
                response
            )

    except Exception as e:

        st.warning(
            f"Quote batch error: {e}"
        )


# =====================================================
# BUILD OPTION DATA
# =====================================================

rows = []


for _, row in options.iterrows():

    symbol = row[
        "tradingsymbol"
    ]

    key = (
        "NFO:"
        + symbol
    )

    quote = quotes.get(
        key,
        {}
    )


    depth = quote.get(
        "depth",
        {}
    )


    buy_depth = depth.get(
        "buy",
        []
    )


    sell_depth = depth.get(
        "sell",
        []
    )


    bid = None

    ask = None


    if buy_depth:

        bid = buy_depth[0].get(
            "price"
        )


    if sell_depth:

        ask = sell_depth[0].get(
            "price"
        )


    rows.append({

        "Strike": row[
            "strike"
        ],

        "Type": row[
            "instrument_type"
        ],

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
# SORT
# =====================================================

if not option_data.empty:

    option_data = option_data.sort_values(
        ["Strike", "Type"]
    ).reset_index(
        drop=True
    )


# =====================================================
# PCR
# =====================================================

if not option_data.empty:

    ce_oi = option_data[
        option_data["Type"] == "CE"
    ]["OI"].fillna(0).sum()


    pe_oi = option_data[
        option_data["Type"] == "PE"
    ]["OI"].fillna(0).sum()


    if ce_oi > 0:

        pcr = pe_oi / ce_oi

    else:

        pcr = None

else:

    pcr = None


# =====================================================
# SUPPORT
# =====================================================

puts = option_data[
    option_data["Type"] == "PE"
].copy()


if not puts.empty:

    support = puts.loc[
        puts["OI"].fillna(0).idxmax(),
        "Strike"
    ]

else:

    support = None


# =====================================================
# RESISTANCE
# =====================================================

calls = option_data[
    option_data["Type"] == "CE"
].copy()


if not calls.empty:

    resistance = calls.loc[
        calls["OI"].fillna(0).idxmax(),
        "Strike"
    ]

else:

    resistance = None


# =====================================================
# MAX PAIN
# =====================================================

max_pain = None


strikes = sorted(
    option_data[
        "Strike"
    ].dropna().unique()
)


if strikes:

    pain = {}


    for test_strike in strikes:

        call_pain = (
            (
                test_strike
                - calls["Strike"]
            ).clip(lower=0)
            * calls["OI"].fillna(0)
        ).sum()


        put_pain = (
            (
                puts["Strike"]
                - test_strike
            ).clip(lower=0)
            * puts["OI"].fillna(0)
        ).sum()


        pain[test_strike] = (
            call_pain
            + put_pain
        )


    if pain:

        max_pain = min(
            pain,
            key=pain.get
        )


# =====================================================
# SUMMARY
# =====================================================

st.divider()

st.subheader(
    "📌 Option Summary"
)


s1, s2, s3, s4, s5 = st.columns(5)


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


# =====================================================
# CE TABLE
# =====================================================

st.divider()

st.subheader(
    "🟢 CALL OPTIONS — CE"
)


ce_display = option_data[
    option_data["Type"] == "CE"
].copy()


st.dataframe(
    ce_display,
    use_container_width=True,
    hide_index=True
)


# =====================================================
# PE TABLE
# =====================================================

st.subheader(
    "🔴 PUT OPTIONS — PE"
)


pe_display = option_data[
    option_data["Type"] == "PE"
].copy()


st.dataframe(
    pe_display,
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
        """
        <meta http-equiv="refresh" content="30">
        """,
        unsafe_allow_html=True
    )


# =====================================================
# FOOTER
# =====================================================

st.divider()

st.caption(
    "🟢 Data Source: Zerodha Kite Connect"
)

st.caption(
    "Option data is a live market snapshot. "
    "Tick-by-tick WebSocket streaming will be added separately."
)

st.caption(
    "यह dashboard केवल market-data analysis के लिए है।"
    )warning(
        "Option Chain Data उपलब्ध नहीं है।"
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
        """
        <meta http-equiv="refresh" content="30">
        """,
        unsafe_allow_html=True
    )


# =====================================================
# FOOTER
# =====================================================

st.divider()

st.caption(
    "🟢 Live data source: Zerodha Kite Connect"
)

st.caption(
    "यह dashboard केवल market-data analysis के लिए है।"
)
