import streamlit as st
import pandas as pd
from kiteconnect import KiteConnect


def get_kite():
    api_key = st.secrets["KITE_API_KEY"]
    access_token = st.secrets["KITE_ACCESS_TOKEN"]

    kite = KiteConnect(api_key=api_key)
    kite.set_access_token(access_token)

    return kite


def get_nifty_option_chain():
    kite = get_kite()

    instruments = kite.instruments("NFO")

    df = pd.DataFrame(instruments)

    if df.empty:
        return pd.DataFrame(), None

    df = df[
        (df["name"] == "NIFTY") &
        (df["segment"] == "NFO-OPT")
    ].copy()

    if df.empty:
        return pd.DataFrame(), None

    df["expiry"] = pd.to_datetime(df["expiry"])

    today = pd.Timestamp.today().normalize()

    future = df[df["expiry"] >= today]

    if future.empty:
        return pd.DataFrame(), None

    expiry = future["expiry"].min()

    df = df[df["expiry"] == expiry].copy()

    # NIFTY spot
    quote = kite.ltp(["NSE:NIFTY 50"])

    spot = float(
        quote["NSE:NIFTY 50"]["last_price"]
    )

    # ATM
    atm = round(spot / 50) * 50

    df["distance"] = abs(
        df["strike"] - atm
    )

    strikes = (
        df[["strike", "distance"]]
        .drop_duplicates()
        .sort_values("distance")
        .head(9)["strike"]
        .tolist()
    )

    df = df[df["strike"].isin(strikes)]

    symbols = [
        f"NFO:{x}"
        for x in df["tradingsymbol"]
    ]

    quotes = kite.quote(symbols)

    rows = []

    for _, row in df.iterrows():

        symbol = f"NFO:{row['tradingsymbol']}"

        q = quotes.get(symbol, {})

        rows.append({
            "strike_price": row["strike"],
            "option_type": row["instrument_type"],
            "trading_symbol": row["tradingsymbol"],
            "ltp": q.get("last_price"),
            "open_interest": q.get("oi", 0),
            "volume": q.get("volume", 0),
        })

    option_df = pd.DataFrame(rows)

    return option_df, spot


def get_atm_option_chain(
    option_data,
    option_spot,
    strikes_each_side=4
):

    if option_data.empty or option_spot is None:
        return pd.DataFrame()

    atm = round(
        float(option_spot) / 50
    ) * 50

    low = atm - strikes_each_side * 50
    high = atm + strikes_each_side * 50

    df = option_data.copy()

    return df[
        (df["strike_price"] >= low) &
        (df["strike_price"] <= high)
    ].copy()


def calculate_pcr(atm_data):

    if atm_data.empty:
        return None

    calls = atm_data[
        atm_data["option_type"] == "CE"
    ]["open_interest"].sum()

    puts = atm_data[
        atm_data["option_type"] == "PE"
    ]["open_interest"].sum()

    if calls == 0:
        return None

    return round(
        float(puts / calls),
        2
    )


def option_sentiment(atm_data):

    pcr = calculate_pcr(atm_data)

    if pcr is None:
        return "NO DATA", 50

    if pcr >= 1.20:
        return "BULLISH", 70

    if pcr <= 0.80:
        return "BEARISH", 30

    return "NEUTRAL", 50


def calculate_support_resistance(atm_data):

    if atm_data.empty:
        return None, None

    calls = atm_data[
        atm_data["option_type"] == "CE"
    ]

    puts = atm_data[
        atm_data["option_type"] == "PE"
    ]

    resistance = None
    support = None

    if not calls.empty:
        resistance = calls.loc[
            calls["open_interest"].idxmax(),
            "strike_price"
        ]

    if not puts.empty:
        support = puts.loc[
            puts["open_interest"].idxmax(),
            "strike_price"
        ]

    return support, resistance
