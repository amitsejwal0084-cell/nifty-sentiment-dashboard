import streamlit as st
import pandas as pd
from datetime import datetime, date, time
from kiteconnect import KiteConnect

# =========================================================
# PAGE
# =========================================================

st.set_page_config(
    page_title="NIFTY Professional Trading Dashboard",
    page_icon="📈",
    layout="wide"
)

# =========================================================
# CUSTOM STYLE
# =========================================================

st.markdown("""
<style>

.main {
    background-color: #0b0f14;
}

.block-container {
    padding-top: 1rem;
    padding-bottom: 2rem;
}

h1, h2, h3 {
    color: white;
}

.metric-card {
    background: #151b23;
    border: 1px solid #293241;
    border-radius: 12px;
    padding: 15px;
    margin-bottom: 10px;
}

.signal-box {
    padding: 18px;
    border-radius: 12px;
    background: #151b23;
    border: 1px solid #293241;
    text-align: center;
    font-size: 24px;
    font-weight: bold;
}

.small-text {
    color: #9ca3af;
    font-size: 13px;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# TITLE
# =========================================================

st.title("📈 NIFTY PROFESSIONAL TRADING DASHBOARD")

st.caption(
    "Kite Connect • Live Market Data • Option Chain • Technical Analysis"
)

# =========================================================
# KITE CREDENTIALS
# =========================================================

API_KEY = st.secrets.get("KITE_API_KEY")
API_SECRET = st.secrets.get("KITE_API_SECRET")

if not API_KEY or not API_SECRET:

    st.error(
        "❌ KITE_API_KEY या KITE_API_SECRET Streamlit Secrets में नहीं मिला।"
    )

    st.stop()

kite = KiteConnect(api_key=API_KEY)

# =========================================================
# LOGIN
# =========================================================

access_token = st.session_state.get("access_token")

if not access_token:

    st.subheader("🔐 Kite Connection")

    login_url = kite.login_url()

    st.link_button(
        "🔑 Login with Kite",
        login_url
    )

    st.info(
        "Kite Login करें। Login के बाद आपको वापस Dashboard पर भेजा जाएगा।"
    )

    request_token = st.query_params.get("request_token")

    if request_token:

        try:

            session_data = kite.generate_session(
                request_token,
                api_secret=API_SECRET
            )

            access_token = session_data["access_token"]

            st.session_state["access_token"] = access_token

            st.query_params.clear()

            st.success(
                "✅ Kite authentication successful!"
            )

            st.rerun()

        except Exception as e:

            st.error(
                f"Kite authentication failed: {e}"
            )

    st.stop()

# =========================================================
# SET ACCESS TOKEN
# =========================================================

kite.set_access_token(access_token)

# =========================================================
# CONNECTION TEST
# =========================================================

try:

    profile = kite.profile()

    user_name = profile.get(
        "user_name",
        "Kite User"
    )

except Exception as e:

    st.error(
        f"❌ Kite connection error: {e}"
    )

    st.session_state.pop(
        "access_token",
        None
    )

    st.stop()

# =========================================================
# TOP STATUS
# =========================================================

c1, c2, c3 = st.columns([2, 2, 1])

with c1:

    st.success(
        f"🟢 Connected: {user_name}"
    )

with c2:

    st.caption(
        f"Last update: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
    )

with c3:

    if st.button("🔄 Refresh"):

        st.rerun()

# =========================================================
# MARKET QUOTES
# =========================================================

MARKET_SYMBOLS = [

    "NSE:NIFTY 50",
    "NSE:NIFTY BANK",
    "NSE:INDIA VIX",
    "BSE:SENSEX",
    "NSE:NIFTY NEXT 50"

]

try:

    market = kite.quote(MARKET_SYMBOLS)

except Exception as e:

    st.error(
        f"❌ Market data error: {e}"
    )

    st.stop()

# =========================================================
# HELPER
# =========================================================

def get_quote(symbol):

    return market.get(symbol, {})


def get_price(symbol):

    data = get_quote(symbol)

    return data.get(
        "last_price",
        0
    )


def get_change(symbol):

    data = get_quote(symbol)

    last_price = data.get(
        "last_price",
        0
    )

    previous_close = data.get(
        "ohlc",
        {}
    ).get(
        "close",
        0
    )

    if previous_close:

        change = (
            (last_price - previous_close)
            / previous_close
        ) * 100

        return change

    return 0


# =========================================================
# MARKET OVERVIEW
# =========================================================

st.divider()

st.subheader("📊 Market Overview")

m1, m2, m3, m4, m5 = st.columns(5)

markets = [

    ("NIFTY 50", "NSE:NIFTY 50", m1),

    ("BANK NIFTY", "NSE:NIFTY BANK", m2),

    ("SENSEX", "BSE:SENSEX", m3),

    ("NIFTY NEXT 50", "NSE:NIFTY NEXT 50", m4),

    ("INDIA VIX", "NSE:INDIA VIX", m5)

]

for name, symbol, column in markets:

    price = get_price(symbol)

    change = get_change(symbol)

    with column:

        st.metric(
            name,
            f"{price:,.2f}",
            f"{change:+.2f}%"
        )

# =========================================================
# NIFTY SPOT
# =========================================================

nifty_price = get_price(
    "NSE:NIFTY 50"
)

nifty_change = get_change(
    "NSE:NIFTY 50"
)

# =========================================================
# OPTION CHAIN
# =========================================================

st.divider()

st.subheader("⛓️ NIFTY Option Chain")

# ---------------------------------------------------------
# LOAD NFO INSTRUMENTS
# ---------------------------------------------------------

@st.cache_data(ttl=3600)
def load_nfo(api_key, token):

    client = KiteConnect(
        api_key=api_key
    )

    client.set_access_token(token)

    data = client.instruments("NFO")

    df = pd.DataFrame(data)

    if df.empty:
        return df

    df["expiry"] = pd.to_datetime(
        df["expiry"],
        errors="coerce"
    ).dt.date

    df["strike"] = pd.to_numeric(
        df["strike"],
        errors="coerce"
    )

    return df


try:

    nfo = load_nfo(
        API_KEY,
        access_token
    )

except Exception as e:

    st.error(
        f"NFO instruments error: {e}"
    )

    nfo = pd.DataFrame()

# =========================================================
# NEAREST EXPIRY
# =========================================================

option_data = pd.DataFrame()

nearest_expiry = None

if not nfo.empty:

    today = date.today()

    nifty_options = nfo[
        (nfo["name"] == "NIFTY") &
        (nfo["instrument_type"].isin(["CE", "PE"])) &
        (nfo["expiry"] >= today)
    ].copy()

    if not nifty_options.empty:

        nearest_expiry = sorted(
            nifty_options["expiry"].dropna().unique()
        )[0]

        option_data = nifty_options[
            nifty_options["expiry"] == nearest_expiry
        ].copy()

# =========================================================
# ATM
# =========================================================

if not option_data.empty:

    strike_step = 50

    atm = round(
        nifty_price / strike_step
    ) * strike_step

    strikes_each_side = 5

    low_strike = (
        atm -
        strikes_each_side * strike_step
    )

    high_strike = (
        atm +
        strikes_each_side * strike_step
    )

    chain = option_data[
        (option_data["strike"] >= low_strike) &
        (option_data["strike"] <= high_strike)
    ].copy()

else:

    chain = pd.DataFrame()

# =========================================================
# OPTION QUOTES
# =========================================================

if not chain.empty:

    symbols = [

        f"NFO:{symbol}"

        for symbol in chain["tradingsymbol"]
    ]

    quotes = {}

    try:

        for start in range(
            0,
            len(symbols),
            100
        ):

            batch = symbols[
                start:start + 100
            ]

            result = kite.quote(
                batch
            )

            if result:

                quotes.update(
                    result
                )

    except Exception as e:

        st.error(
            f"Option quote error: {e}"
        )

    rows = []

    for _, row in chain.iterrows():

        symbol = row["tradingsymbol"]

        key = f"NFO:{symbol}"

        q = quotes.get(
            key,
            {}
        )

        depth = q.get(
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

        bid = (
            buy[0].get("price")
            if buy else None
        )

        ask = (
            sell[0].get("price")
            if sell else None
        )

        rows.append({

            "Strike": row["strike"],

            "Type": row["instrument_type"],

            "Symbol": symbol,

            "LTP": q.get(
                "last_price"
            ),

            "OI": q.get(
                "oi"
            ),

            "Volume": q.get(
                "volume"
            ),

            "Bid": bid,

            "Ask": ask

        })

    option_chain = pd.DataFrame(
        rows
    )

else:

    option_chain = pd.DataFrame()

# =========================================================
# PCR
# =========================================================

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
)
