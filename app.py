import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from kiteconnect import KiteConnect


# =========================================================
# PAGE
# =========================================================

st.set_page_config(
    page_title="NIFTY Live Trading Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("📈 NIFTY LIVE TRADING DASHBOARD")
st.caption("Zerodha Kite Connect • Real Market Data")


# =========================================================
# KITE
# =========================================================

API_KEY = st.secrets.get("KITE_API_KEY")
API_SECRET = st.secrets.get("KITE_API_SECRET")

if not API_KEY or not API_SECRET:
    st.error("Kite API credentials नहीं मिले।")
    st.stop()

kite = KiteConnect(api_key=API_KEY)


# =========================================================
# LOGIN
# =========================================================

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
            st.error(f"Kite Login Error: {e}")

    st.stop()


kite.set_access_token(access_token)


# =========================================================
# CONNECTION
# =========================================================

try:

    profile = kite.profile()

    st.success(
        f"🟢 Connected: {profile.get('user_name', 'Kite User')}"
    )

except Exception as e:

    st.session_state.pop("access_token", None)

    st.error(f"Kite Session Error: {e}")
    st.stop()


st.caption(
    "Last Update: "
    + datetime.now().strftime("%d-%m-%Y %H:%M:%S")
)


if st.button("🔄 Refresh"):

    st.rerun()


# =========================================================
# LIVE INDEX DATA
# =========================================================

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

    st.error(f"Market Data Error: {e}")
    st.stop()


def get_ltp(symbol):

    return market.get(
        symbol,
        {}
    ).get(
        "last_price",
        0
    )


def get_change(symbol):

    data = market.get(symbol, {})

    last = data.get("last_price", 0)

    close = data.get(
        "ohlc",
        {}
    ).get(
        "close",
        0
    )

    if close:

        return ((last - close) / close) * 100

    return 0


c1, c2, c3, c4, c5 = st.columns(5)


with c1:
    st.metric(
        "NIFTY 50",
        f"{get_ltp('NSE:NIFTY 50'):,.2f}",
        f"{get_change('NSE:NIFTY 50'):+.2f}%"
    )


with c2:
    st.metric(
        "BANK NIFTY",
        f"{get_ltp('NSE:NIFTY BANK'):,.2f}",
        f"{get_change('NSE:NIFTY BANK'):+.2f}%"
    )


with c3:
    st.metric(
        "SENSEX",
        f"{get_ltp('BSE:SENSEX'):,.2f}",
        f"{get_change('BSE:SENSEX'):+.2f}%"
    )


with c4:
    st.metric(
        "NIFTY NEXT 50",
        f"{get_ltp('NSE:NIFTY NEXT 50'):,.2f}",
        f"{get_change('NSE:NIFTY NEXT 50'):+.2f}%"
    )


with c5:
    st.metric(
        "INDIA VIX",
        f"{get_ltp('NSE:INDIA VIX'):,.2f}",
        f"{get_change('NSE:INDIA VIX'):+.2f}%"
    )


# =========================================================
# HISTORICAL DATA FUNCTIONS
# =========================================================

def get_historical_data(
    instrument_token,
    interval="5minute",
    days=5
):

    to_date = datetime.now()
    from_date = to_date - timedelta(days=days)

    try:

        data = kite.historical_data(
            instrument_token,
            from_date,
            to_date,
            interval
        )

        return pd.DataFrame(data)

    except Exception as e:

        return pd.DataFrame()


def calculate_rsi(series, period=14):

    delta = series.diff()

    gain = delta.clip(lower=0)

    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    rs = avg_gain / avg_loss.replace(
        0,
        np.nan
    )

    rsi = 100 - (
        100 / (1 + rs)
    )

    return rsi


def calculate_vwap(df):

    if df.empty:
        return pd.Series(dtype=float)

    typical_price = (
        df["high"]
        + df["low"]
        + df["close"]
    ) / 3

    volume = pd.to_numeric(
        df["volume"],
        errors="coerce"
    ).fillna(0)

    cumulative_pv = (
        typical_price * volume
    ).cumsum()

    cumulative_volume = volume.cumsum()

    vwap = (
        cumulative_pv
        / cumulative_volume.replace(
            0,
            np.nan
        )
    )

    return vwap


# =========================================================
# FIND NIFTY INSTRUMENT TOKEN
# =========================================================

try:

    nse_instruments = kite.instruments("NSE")

    nse_df = pd.DataFrame(
        nse_instruments
    )

except Exception as e:

    nse_df = pd.DataFrame()

    st.warning(
        f"NSE instruments error: {e}"
    )


nifty_token = None


if not nse_df.empty:

    nifty_rows = nse_df[
        (
            nse_df["tradingsymbol"]
            == "NIFTY 50"
        )
        &
        (
            nse_df["exchange"]
            == "NSE"
        )
    ]

    if not nifty_rows.empty:

        nifty_token = int(
            nifty_rows.iloc[0][
                "instrument_token"
            ]
        )


# =========================================================
# TECHNICAL ANALYSIS
# =========================================================

st.divider()

st.subheader(
    "📈 NIFTY Technical Analysis"
)


technical_df = pd.DataFrame()


if nifty_token is not None:

    technical_df = get_historical_data(
        nifty_token,
        interval="5minute",
        days=5
    )


if not technical_df.empty:

    technical_df["date"] = pd.to_datetime(
        technical_df["date"]
    )

    technical_df["close"] = pd.to_numeric(
        technical_df["close"],
        errors="coerce"
    )

    technical_df["volume"] = pd.to_numeric(
        technical_df["volume"],
        errors="coerce"
    )

    technical_df["RSI"] = calculate_rsi(
        technical_df["close"],
        14
    )

    technical_df["VWAP"] = calculate_vwap(
        technical_df
    )

    latest = technical_df.iloc[-1]

    current_price = float(
        latest["close"]
    )

    current_rsi = latest["RSI"]

    current_vwap = latest["VWAP"]

    # -----------------------------------------------------
    # VOLUME BREAKOUT
    # -----------------------------------------------------

    volume_average = (
        technical_df["volume"]
        .rolling(20)
        .mean()
    )

    latest_volume = latest["volume"]

    latest_average_volume = (
        volume_average.iloc[-1]
    )

    volume_breakout = False
    volume_breakdown = False

    if pd.notna(latest_average_volume):

        if latest_volume > (
            latest_average_volume * 1.5
        ):

            if current_price > (
                technical_df["close"]
                .iloc[-2]
            ):

                volume_breakout = True

            elif current_price < (
                technical_df["close"]
                .iloc[-2]
            ):

                volume_breakdown = True


    # -----------------------------------------------------
    # SENTIMENT
    # -----------------------------------------------------

    bullish_points = 0
    bearish_points = 0


    # RSI
    if pd.notna(current_rsi):

        if current_rsi > 60:

            bullish_points += 1

        elif current_rsi < 40:

            bearish_points += 1


    # VWAP
    if pd.notna(current_vwap):

        if current_price > current_vwap:

            bullish_points += 1

        elif current_price < current_vwap:

            bearish_points += 1


    # Volume
    if volume_breakout:

        bullish_points += 1

    if volume_breakdown:

        bearish_points += 1


    if bullish_points >= 2:

        sentiment = "🟢 BULLISH"

    elif bearish_points >= 2:

        sentiment = "🔴 BEARISH"

    else:

        sentiment = "🟡 NEUTRAL"


    # -----------------------------------------------------
    # DISPLAY
    # -----------------------------------------------------

    t1, t2, t3, t4, t5 = st.columns(5)


    with t1:

        st.metric(
            "Price",
            f"{current_price:,.2f}"
        )


    with t2:

        if pd.notna(current_rsi):

            st.metric(
                "RSI (14)",
                f"{current_rsi:.2f}"
            )

        else:

            st.metric(
                "RSI (14)",
                "—"
            )


    with t3:

        if pd.notna(current_vwap):

            st.metric(
                "VWAP",
                f"{current_vwap:,.2f}"
            )

        else:

            st.metric(
                "VWAP",
                "—"
            )


    with t4:

        if volume_breakout:

            st.metric(
                "Volume",
                "BREAKOUT"
            )

        elif volume_breakdown:

            st.metric(
                "Volume",
                "BREAKDOWN"
            )

        else:

            st.metric(
                "Volume",
                "Normal"
            )


    with t5:

        st.metric(
            "Sentiment",
            sentiment
        )


    # -----------------------------------------------------
    # STRATEGY STATUS
    # -----------------------------------------------------

    st.divider()

    st.subheader(
        "🎯 Market Setup"
    )


    buy_condition = (
        pd.notna(current_rsi)
        and pd.notna(current_vwap)
        and current_rsi > 60
        and current_price > current_vwap
        and volume_breakout
    )


    sell_condition = (
        pd.notna(current_rsi)
        and pd.notna(current_vwap)
        and current_rsi < 40
        and current_price < current_vwap
        and volume_breakdown
    )


    if buy_condition:

        st.success(
            "🟢 BUY SETUP — RSI > 60 + Price > VWAP + Volume Breakout"
        )

    elif sell_condition:

        st.error(
            "🔴 SELL SETUP — RSI < 40 + Price < VWAP + Volume Breakdown"
        )

    else:

        st.info(
            "⚪ NO TRADE SETUP — सभी conditions पूरी नहीं हैं"
        )


    st.caption(
        "यह केवल market-data analysis है; कोई automatic order execute नहीं होता।"
    )


    # =========================================================
    # संगम — मल्टी-इंडिकेटर कॉन्फ्लुएंस पैनल
    # =========================================================

    st.divider()
    st.subheader("🔱 संगम — मल्टी-इंडिकेटर कॉन्फ्लुएंस सिग्नल")

    def calculate_ema(series, period):
        return series.ewm(span=period, adjust=False).mean()

    def calculate_macd(series):
        ema12 = series.ewm(span=12, adjust=False).mean()
        ema26 = series.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        return macd_line, signal_line

    def calculate_bollinger(series, period=20, mult=2):
        mid = series.rolling(period).mean()
        sd = series.rolling(period).std()
        return mid, mid + mult * sd, mid - mult * sd

    def calculate_supertrend(df, period=10, mult=3):
        high, low, close = df["high"], df["low"], df["close"]
        prev_close = close.shift(1)
        tr = pd.concat(
            [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
            axis=1
        ).max(axis=1)
        atr = tr.ewm(alpha=1 / period, adjust=False).mean()
        hl2 = (high + low) / 2
        basic_upper = hl2 + mult * atr
        basic_lower = hl2 - mult * atr
        final_upper = basic_upper.copy()
        final_lower = basic_lower.copy()
        for i in range(1, len(df)):
            if basic_upper.iloc[i] < final_upper.iloc[i - 1] or close.iloc[i - 1] > final_upper.iloc[i - 1]:
                final_upper.iloc[i] = basic_upper.iloc[i]
            else:
                final_upper.iloc[i] = final_upper.iloc[i - 1]
            if basic_lower.iloc[i] > final_lower.iloc[i - 1] or close.iloc[i - 1] < final_lower.iloc[i - 1]:
                final_lower.iloc[i] = basic_lower.iloc[i]
            else:
                final_lower.iloc[i] = final_lower.iloc[i - 1]
        trend = pd.Series(index=df.index, dtype=int)
        trend.iloc[0] = 1 if close.iloc[0] > final_upper.iloc[0] else -1
        for i in range(1, len(df)):
            if trend.iloc[i - 1] == 1:
                trend.iloc[i] = -1 if close.iloc[i] < final_lower.iloc[i] else 1
            else:
                trend.iloc[i] = 1 if close.iloc[i] > final_upper.iloc[i] else -1
        return trend

    if nifty_token is None:
        st.warning("NIFTY instrument token नहीं मिला — संगम पैनल नहीं दिखाया जा सकता।")
    else:
        # स्विंग-स्टाइल indicators (EMA50, Supertrend) के लिए daily candles चाहिए,
        # इसलिए ऊपर के 5-मिनट वाले technical_df से अलग, रोज़ाना डेटा अलग से लाया जा रहा है
        daily_df = get_historical_data(nifty_token, interval="day", days=200)

        if daily_df.empty or len(daily_df) < 55:
            st.warning("संगम पैनल के लिए कम से कम ~60 दिनों का daily candle डेटा चाहिए, जो अभी उपलब्ध नहीं है।")
        else:
            daily_df["close"] = pd.to_numeric(daily_df["close"], errors="coerce")
            daily_df["high"] = pd.to_numeric(daily_df["high"], errors="coerce")
            daily_df["low"] = pd.to_numeric(daily_df["low"], errors="coerce")
            daily_df["volume"] = pd.to_numeric(daily_df["volume"], errors="coerce")

            close = daily_df["close"]
            ema20 = calculate_ema(close, 20)
            ema50 = calculate_ema(close, 50)
            rsi14 = calculate_rsi(close, 14)  # आपके app.py में पहले से मौजूद फंक्शन दोबारा इस्तेमाल हो रहा है
            macd_line, signal_line = calculate_macd(close)
            bb_mid, bb_upper, bb_lower = calculate_bollinger(close, 20, 2)
            st_trend = calculate_supertrend(daily_df, 10, 3)

            last_close = close.iloc[-1]
            indicators = []

            # EMA क्रॉसओवर
            vote = 0
            if last_close > ema20.iloc[-1] > ema50.iloc[-1]:
                vote = 1
            elif last_close < ema20.iloc[-1] < ema50.iloc[-1]:
                vote = -1
            indicators.append(("EMA 20/50", f"₹{ema20.iloc[-1]:,.1f} / ₹{ema50.iloc[-1]:,.1f}", vote))

            # RSI
            vote = 0
            r = rsi14.iloc[-1]
            if pd.notna(r):
                if r < 30:
                    vote = 1
                elif r > 70:
                    vote = -1
            indicators.append(("RSI (14)", f"{r:.1f}" if pd.notna(r) else "—", vote))

            # MACD
            vote = 0
            m, s = macd_line.iloc[-1], signal_line.iloc[-1]
            if pd.notna(m) and pd.notna(s):
                vote = 1 if m > s else (-1 if m < s else 0)
            indicators.append(("MACD", f"{m:.2f} vs {s:.2f}" if pd.notna(m) else "—", vote))

            # Bollinger
            vote = 0
            if pd.notna(bb_upper.iloc[-1]):
                if last_close <= bb_lower.iloc[-1]:
                    vote = 1
                elif last_close >= bb_upper.iloc[-1]:
                    vote = -1
            indicators.append(("Bollinger Bands", f"₹{bb_lower.iloc[-1]:,.1f} – ₹{bb_upper.iloc[-1]:,.1f}" if pd.notna(bb_upper.iloc[-1]) else "—", vote))

            # Supertrend
            t = st_trend.iloc[-1]
            vote = 1 if t == 1 else -1
            indicators.append(("Supertrend", "तेजी रुझान" if t == 1 else "मंदी रुझान", vote))

            # वॉल्यूम पुष्टि
            vote = 0
            vol_note = "—"
            avg_vol20 = daily_df["volume"].rolling(20).mean().iloc[-1]
            last_vol = daily_df["volume"].iloc[-1]
            price_chg5 = close.iloc[-1] - close.iloc[-6]
            if pd.notna(avg_vol20) and avg_vol20 > 0:
                ratio = last_vol / avg_vol20 * 100
                vol_note = f"{ratio:.0f}% औसत वॉल्यूम"
                if last_vol > avg_vol20 * 1.2:
                    vote = 1 if price_chg5 > 0 else (-1 if price_chg5 < 0 else 0)
            indicators.append(("वॉल्यूम पुष्टि", vol_note, vote))

            score = sum(v for _, _, v in indicators)
            confidence = abs(score) / 6 * 100

            cols = st.columns(6)
            for col, (name, value_str, vote) in zip(cols, indicators):
                with col:
                    badge = "🟢 तेजी" if vote > 0 else ("🔴 मंदी" if vote < 0 else "⚪ न्यूट्रल")
                    st.metric(name, value_str, badge)

            st.progress(min(100, int(confidence)))

            if score >= 2:
                st.success(f"🟢 बुलिश बायस — स्कोर {score:+d}/6 · {confidence:.0f}% इंडिकेटर सहमत")
            elif score <= -2:
                st.error(f"🔴 बेयरिश बायस — स्कोर {score:+d}/6 · {confidence:.0f}% इंडिकेटर सहमत")
            else:
                st.info(f"⚪ न्यूट्रल / मिश्रित संकेत — स्कोर {score:+d}/6 · {confidence:.0f}% इंडिकेटर सहमत")

            st.caption(
                "⚠️ यह किसी भी अन्य इंडिकेटर सिस्टम की तरह 100% सटीक नहीं है — यह सिर्फ छह लोकप्रिय "
                "indicators की आपसी सहमति (confluence) दिखाता है, गारंटीशुदा सिग्नल नहीं। "
                "निवेश सलाह नहीं है; अपने जोखिम पर ट्रेड करें।"
            )


else:

    st.warning(
        "⚠️ Historical candle data उपलब्ध नहीं है। "
        "RSI/VWAP/Volume analysis के लिए Kite historical-data access आवश्यक है। "
        "Fake value नहीं दिखाई जा रही है।"
    )


# =========================================================
# OPTION CHAIN
# =========================================================

st.divider()

st.subheader(
    "⛓️ NIFTY LIVE OPTION CHAIN"
)


nifty_price = get_ltp(
    "NSE:NIFTY 50"
)


# =========================================================
# NFO
# =========================================================

try:

    instruments = kite.instruments("NFO")

    df = pd.DataFrame(
        instruments
    )

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
    (df["name"] == "NIFTY")
    &
    (
        df["instrument_type"]
        .isin(["CE", "PE"])
    )
    &
    (
        df["expiry"] >= today
    )
].copy()


if options.empty:

    st.warning(
        "NIFTY options नहीं मिले।"
    )

    st.stop()


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


atm = round(
    nifty_price / 50
) * 50


st.write(
    f"**NIFTY:** {nifty_price:,.2f} | "
    f"**ATM:** {atm:,.0f}"
)


options = options[
    (options["strike"] >= atm - 500)
    &
    (options["strike"] <= atm + 500)
].copy()


# =========================================================
# QUOTES
# =========================================================

quote_keys = [
    "NFO:" + symbol
    for symbol in options[
        "tradingsymbol"
    ]
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

        result = kite.quote(
            batch
        )

        quotes.update(
            result
        )

    except Exception as e:

        st.warning(
            f"Quote error: {e}"
        )


# =========================================================
# BUILD OPTION DATA
# =========================================================

rows = []


for _, row in options.iterrows():

    symbol = row[
        "tradingsymbol"
    ]

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


if option_data.empty:

    st.warning(
        "Option quote data उपलब्ध नहीं है।"
    )

    st.stop()


# =========================================================
# NUMERIC
# =========================================================

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


option_data = option_data.sort_values(
    [
        "Strike",
        "Type"
    ]
).reset_index(
    drop=True
)


# =========================================================
# OI SNAPSHOT
# =========================================================

if "previous_option_snapshot" not in st.session_state:

    st.session_state[
        "previous_option_snapshot"
    ] = {}


previous_snapshot = st.session_state[
    "previous_option_snapshot"
]


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


# =========================================================
# SAVE SNAPSHOT
# =========================================================

new_snapshot = {}


for _, row in option_data.iterrows():

    new_snapshot[
        row["Symbol"]
    ] = {

        "OI": row["OI"],

        "LTP": row["LTP"]
    }


st.session_state[
    "previous_option_snapshot"
] = new_snapshot


# =========================================================
# PCR
# =========================================================

ce_oi = option_data[
    option_data["Type"] == "CE"
]["OI"].fillna(0).sum()


pe_oi = option_data[
    option_data["Type"] == "PE"
]["OI"].fillna(0).sum()


pcr = (
    pe_oi / ce_oi
    if ce_oi > 0
    else None
)


# =========================================================
# SUPPORT / RESISTANCE
# =========================================================

puts = option_data[
    option_data["Type"] == "PE"
].copy()


calls = option_data[
    option_data["Type"] == "CE"
].copy()


support = None
resistance = None


if not puts.empty:

    support = puts.loc[
        puts["OI"].fillna(0).idxmax(),
        "Strike"
    ]


if not calls.empty:

    resistance = calls.loc[
        calls["OI"].fillna(0).idxmax(),
        "Strike"
    ]


# =========================================================
# MAX PAIN
# =========================================================

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


# =========================================================
# OPTION SUMMARY
# =========================================================

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


# =========================================================
# OI SUMMARY
# =========================================================

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

    st.metric(
        "Total CE OI Change",
        (
            f"{total_ce_oi_change:,.0f}"
            if pd.notna(
                total_ce_oi_change
            )
            else "—"
        )
    )


with b2:

    st.metric(
        "Total PE OI Change",
        (
            f"{total_pe_oi_change:,.0f}"
            if pd.notna(
                total_pe_oi_change
            )
            else "—"
        )
    )


with b3:

    st.metric(
        "Data",
        "LIVE"
    )


# =========================================================
# CE
# =========================================================

st.divider()

st.subheader(
    "🟢 CALL OPTIONS — CE"
)


ce_display = option_data[
    option_data["Type"] == "CE"
].copy()


st.dataframe(
    ce_display[
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
    ],
    use_container_width=True,
    hide_index=True
)


# =========================================================
# PE
# =========================================================

st.subheader(
    "🔴 PUT OPTIONS — PE"
)


pe_display = option_data[
    option_data["Type"] == "PE"
].copy()


st.dataframe(
    pe_display[
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
    ],
    use_container_width=True,
    hide_index=True
)


# =========================================================
# AUTO REFRESH
# =========================================================

st.divider()

auto_refresh = st.checkbox(
    "⏱️ 30 सेकंड Auto Refresh"
)


if auto_refresh:

    st.markdown(
        '<meta http-equiv="refresh" content="30">',
        unsafe_allow_html=True
    )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "Data Source: Zerodha Kite Connect"
)

st.caption(
    "Live snapshot data • No simulated data"
)

st.caption(
    "RSI/VWAP are calculated from Kite candle data."
)

st.caption(
    "यह dashboard केवल market-data analysis के लिए है।"
)
