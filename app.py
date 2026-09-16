import streamlit as st
import pandas as pd
from datetime import datetime
from kiteconnect import KiteConnect


# =====================================================
# PAGE
# =====================================================

st.set_page_config(
    page_title="NIFTY Live Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("📈 NIFTY LIVE TRADING DASHBOARD")
st.caption("Zerodha Kite Connect • Real Market Data")


# =====================================================
# KITE CREDENTIALS
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

    request_token = st.query_params.get("request_token")

    if request_token:

        try:

            session_data = kite.generate_session(
                request_token,
                api_secret=API_SECRET
            )

            st.session_state["access_token"] = (
                session_data["access_token"]
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


# =====================================================
# TIME
# =====================================================

st.caption(
    "Last Update: "
    + datetime.now().strftime(
        "%d-%m-%Y %H:%M:%S"
    )
)


# =====================================================
# MANUAL REFRESH
# =====================================================

if st.button("🔄 Refresh"):

    st.rerun()


# =====================================================
# LIVE MARKET
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


# =====================================================
# NFO INSTRUMENTS
# =====================================================

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
# CLEAN DATA
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


# =====================================================
# FILTER NIFTY OPTIONS
# =====================================================

options = df[
    (df["name"] == "NIFTY") &
    (
        df["instrument_type"].isin(
            ["CE", "PE"]
        )
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
# ATM ±10 STRIKES
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
# BUILD OPTION TABLE
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


if option_data.empty:

    st.warning(
        "Option quote data उपलब्ध नहीं है।"
    )

    st.stop()


# =====================================================
# NUMERIC COLUMNS
# =====================================================

for column in [
    "Strike",
    "LTP",
    "OI",
    "Volume",
    "Bid",
    "Ask"
]:

    option_data[column] = pd.to_numeric(
        option_data[column],
        errors="coerce"
    )


# =====================================================
# SORT
# =====================================================

option_data = option_data.sort_values(
    ["Strike", "Type"]
).reset_index(
    drop=True
)


# =====================================================
# OI SNAPSHOT STORAGE
# =====================================================

if "previous_option_snapshot" not in st.session_state:

    st.session_state[
        "previous_option_snapshot"
    ] = {}


previous_snapshot = st.session_state[
    "previous_option_snapshot"
]


# =====================================================
# CALCULATE OI CHANGE + PRICE CHANGE
# =====================================================

oi_changes = []
oi_change_percentages = []
price_changes = []
buildups = []


for _, row in option_data.iterrows():

    symbol = row["Symbol"]

    current_oi = row["OI"]

    current_ltp = row["LTP"]


    previous = previous_snapshot.get(
        symbol
    )


    if previous is None:

        oi_change = None
        oi_change_percent = None
        price_change = None
        buildup = "Waiting..."


    else:

        previous_oi = previous.get(
            "OI"
        )

        previous_ltp = previous.get(
            "LTP"
        )


        # -----------------------------
        # OI CHANGE
        # -----------------------------

        if (
            pd.notna(current_oi)
            and pd.notna(previous_oi)
        ):

            oi_change = (
                current_oi
                - previous_oi
            )


            if previous_oi != 0:

                oi_change_percent = (
                    oi_change
                    / previous_oi
                ) * 100

            else:

                oi_change_percent = None

        else:

            oi_change = None
            oi_change_percent = None


        # -----------------------------
        # PRICE CHANGE
        # -----------------------------

        if (
            pd.notna(current_ltp)
            and pd.notna(previous_ltp)
        ):

            price_change = (
                current_ltp
                - previous_ltp
            )

        else:

            price_change = None


        # -----------------------------
        # BUILDUP
        # -----------------------------

        if (
            oi_change is None
            or price_change is None
        ):

            buildup = "N/A"

        elif (
            oi_change > 0
            and price_change > 0
        ):

            buildup = "Long Buildup"

        elif (
            oi_change > 0
            and price_change < 0
        ):

            buildup = "Short Buildup"

        elif (
            oi_change < 0
            and price_change > 0
        ):

            buildup = "Short Covering"

        elif (
            oi_change < 0
            and price_change < 0
        ):

            buildup = "Long Unwinding"

        else:

            buildup = "Neutral"


    oi_changes.append(
        oi_change
    )

    oi_change_percentages.append(
        oi_change_percent
    )

    price_changes.append(
        price_change
    )

    buildups.append(
        buildup
    )


# =====================================================
# ADD COLUMNS
# =====================================================

option_data["OI Change"] = (
    oi_changes
)


option_data["OI Change %"] = (
    oi_change_percentages
)


option_data["Price Change"] = (
    price_changes
)


option_data["Buildup"] = (
    buildups
)


# =====================================================
# SAVE CURRENT SNAPSHOT
# =====================================================

new_snapshot = {}


for _, row in option_data.iterrows():

    symbol = row["Symbol"]

    new_snapshot[symbol] = {

        "OI": row["OI"],

        "LTP": row["LTP"]

    }


st.session_state[
    "previous_option_snapshot"
] = new_snapshot


# =====================================================
# PCR
# =====================================================

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
# OI CHANGE SUMMARY
# =====================================================

st.divider()

st.subheader(
    "📈 OI Change & Buildup"
)


total_ce_oi_change = option_data[
    option_data["Type"] == "CE"
]["OI Change"].sum(
    min_count=1
)


total_pe_oi_change = option_data[
    option_data["Type"] == "PE"
]["OI Change"].sum(
    min_count=1
)


b1, b2, b3 = st.columns(3)


with b1:

    if pd.notna(total_ce_oi_change):

        st.metric(
            "Total CE OI Change",
            f"{total_ce_oi_change:,.0f}"
        )

    else:

        st.metric(
            "Total CE OI Change",
            "—"
        )


with b2:

    if pd.notna(total_pe_oi_change):

        st.metric(
            "Total PE OI Change",
            f"{total_pe_oi_change:,.0f}"
        )

    else:

        st.metric(
            "Total PE OI Change",
            "—"
        )


with b3:

    st.metric(
        "Snapshot",
        "Live"
    )


st.caption(
    "OI Change पहली snapshot पर — रहेगा। अगली refresh पर बदलाव calculate होगा।"
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


ce_display = ce_display[
    [
        "Strike",
        "Symbol",
        "LTP",
        "OI",
        "OI Change",
        "OI Change %",
        "Price Change",
        "Volume",
        "Bid",
        "Ask",
        "Buildup"
    ]
]


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


pe_display = pe_display[
    [
        "Strike",
        "Symbol",
        "LTP",
        "OI",
        "OI Change",
        "OI Change %",
        "Price Change",
        "Volume",
        "Bid",
        "Ask",
        "Buildup"
    ]
]


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
        '<meta http-equiv="refresh" content="30">',
        unsafe_allow_html=True
    )


# =====================================================
# FOOTER
# =====================================================

st.divider()

st.caption(
    "Data Source: Zerodha Kite Connect"
)

st.caption(
    "Live snapshot data • No simulated data"
)

st.caption(
    "OI Change = current snapshot OI − previous successful snapshot OI"
)

st.caption(
    "Buildup classification is based on price change + OI change and is for analysis only."
)
