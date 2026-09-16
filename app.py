import streamlit as st
import pandas as pd
from datetime import datetime
from kiteconnect import KiteConnect


# =====================================================
# PAGE
# =====================================================

st.set_page_config(
    page_title="NIFTY Trading Dashboard",
    page_icon="📈",
    layout="wide"
)


st.title("📈 NIFTY PROFESSIONAL TRADING DASHBOARD")

st.caption(
    "Zerodha Kite Connect • Live Market Data"
)


# =====================================================
# KITE CREDENTIALS
# =====================================================

API_KEY = st.secrets.get("KITE_API_KEY")
API_SECRET = st.secrets.get("KITE_API_SECRET")


if not API_KEY or not API_SECRET:

    st.error(
        "KITE_API_KEY या KITE_API_SECRET नहीं मिला।"
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
# CONNECTION TEST
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


st.divider()


# =====================================================
# LIVE MARKET DATA
# =====================================================

st.subheader("📊 Live Market")


symbols = [
    "NSE:NIFTY 50",
    "NSE:NIFTY BANK",
    "BSE:SENSEX",
    "NSE:NIFTY NEXT 50",
    "NSE:INDIA VIX"
]


try:

    market = kite.quote(symbols)

except Exception as e:

    st.error(
        f"Market Data Error: {e}"
    )

    st.stop()


def get_price(symbol):

    data = market.get(
        symbol,
        {}
    )

    return data.get(
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
# NIFTY PRICE
# =====================================================

nifty_price = get_price(
    "NSE:NIFTY 50"
)


st.divider()


# =====================================================
# OPTION CHAIN
# =====================================================

st.subheader(
    "⛓️ NIFTY OPTION CHAIN"
)


try:

    instruments = kite.instruments(
        "NFO"
    )

    instrument_df = pd.DataFrame(
        instruments
    )

except Exception as e:

    instrument_df = pd.DataFrame()

    st.error(
        f"NFO Instrument Error: {e}"
    )


if not instrument_df.empty:

    instrument_df["expiry"] = pd.to_datetime(
        instrument_df["expiry"],
        errors="coerce"
    ).dt.date

    instrument_df["strike"] = pd.to_numeric(
        instrument_df["strike"],
        errors="coerce"
    )

    today = datetime.now().date()


    options = instrument_df[
        (instrument_df["name"] == "NIFTY") &
        (
            instrument_df["instrument_type"]
            .isin(["CE", "PE"])
        ) &
        (
            instrument_df["expiry"] >= today
        )
    ].copy()


    if not options.empty:

        expiry = sorted(
            options["expiry"]
            .dropna()
            .unique()
        )[0]


        options = options[
            options["expiry"] == expiry
        ].copy()


        atm = round(
            nifty_price / 50
        ) * 50


        low = atm - 500
        high = atm + 500


        options = options[
            (options["strike"] >= low) &
            (options["strike"] <= high)
        ].copy()


        symbols = [
            "NFO:" + symbol
            for symbol in options[
                "tradingsymbol"
            ]
        ]


        quotes = {}


        for start in range(
            0,
            len(symbols),
            100
        ):

            batch = symbols[
                start:start + 100
            ]

            try:

                response = kite.quote(
                    batch
                )

                quotes.update(
                    response
                )

            except Exception:
                pass


        rows = []


        for _, row in options.iterrows():

            trading_symbol = row[
                "tradingsymbol"
            ]

            quote = quotes.get(
                "NFO:" + trading_symbol,
                {}
            )


            rows.append({

                "Strike": row["strike"],

                "Type": row[
                    "instrument_type"
                ],

                "Symbol": trading_symbol,

                "LTP": quote.get(
                    "last_price"
                ),

                "OI": quote.get(
                    "oi"
                ),

                "Volume": quote.get(
                    "volume"
                )

            })


        option_data = pd.DataFrame(
            rows
        )


    else:

        option_data = pd.DataFrame()


else:

    option_data = pd.DataFrame()


# =====================================================
# OPTION SUMMARY
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


    if not ce.empty:

        resistance = ce.loc[
            ce["OI"].fillna(0).idxmax(),
            "Strike"
        ]

    else:

        resistance = None


    if not pe.empty:

        support = pe.loc[
            pe["OI"].fillna(0).idxmax(),
            "Strike"
        ]

    else:

        support = None


    strikes = sorted(
        option_data[
            "Strike"
        ].dropna().unique()
    )


    max_pain = None


    if strikes:

        pain = {}


        for test_strike in strikes:

            call_pain = (
                (
                    test_strike
                    - ce["Strike"]
                ).clip(lower=0)
                * ce["OI"].fillna(0)
            ).sum()


            put_pain = (
                (
                    pe["Strike"]
                    - test_strike
                ).clip(lower=0)
                * pe["OI"].fillna(0)
            ).sum()


            pain[test_strike] = (
                call_pain + put_pain
            )


        max_pain = min(
            pain,
            key=pain.get
        )


else:

    pcr = None
    support = None
    resistance = None
    max_pain = None


# =====================================================
# SUMMARY CARDS
# =====================================================

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
# OPTION TABLE
# =====================================================

st.divider()

st.subheader(
    "📋 Live Option Chain"
)


if not option_data.empty:

    st.dataframe(
        option_data,
        use_container_width=True,
        hide_index=True
    )

else:

    st.warning(
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
