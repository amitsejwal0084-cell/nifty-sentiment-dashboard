import streamlit as st
import pandas as pd
from datetime import date
from kiteconnect import KiteConnect


# =========================================================
# KITE CLIENT
# =========================================================

def get_kite_client():
    api_key = st.secrets.get("KITE_API_KEY")
    access_token = st.session_state.get("access_token")

    if not api_key:
        raise Exception("KITE_API_KEY Streamlit Secrets में नहीं मिला।")

    if not access_token:
        raise Exception(
            "Kite access token नहीं मिला। पहले Kite Login करें।"
        )

    kite = KiteConnect(api_key=api_key)
    kite.set_access_token(access_token)

    return kite


# =========================================================
# NFO INSTRUMENTS
# =========================================================

@st.cache_data(ttl=3600)
def load_nfo_instruments():

    api_key = st.secrets.get("KITE_API_KEY")
    access_token = st.session_state.get("access_token")

    if not api_key or not access_token:
        return pd.DataFrame()

    kite = KiteConnect(api_key=api_key)
    kite.set_access_token(access_token)

    instruments = kite.instruments("NFO")

    df = pd.DataFrame(instruments)

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


# =========================================================
# FIND NEAREST NIFTY EXPIRY
# =========================================================

def get_nearest_nifty_expiry():

    df = load_nfo_instruments()

    if df.empty:
        return None

    today = date.today()

    nifty = df[
        (df["name"] == "NIFTY") &
        (df["instrument_type"].isin(["CE", "PE"])) &
        (df["expiry"] >= today)
    ].copy()

    if nifty.empty:
        return None

    return sorted(
        nifty["expiry"].dropna().unique()
    )[0]


# =========================================================
# GET NIFTY OPTION CONTRACTS
# =========================================================

def get_nifty_option_contracts():

    df = load_nfo_instruments()

    if df.empty:
        return pd.DataFrame()

    expiry = get_nearest_nifty_expiry()

    if expiry is None:
        return pd.DataFrame()

    options = df[
        (df["name"] == "NIFTY") &
        (df["expiry"] == expiry) &
        (df["instrument_type"].isin(["CE", "PE"]))
    ].copy()

    return options


# =========================================================
# GET ATM ± STRIKES
# =========================================================

def get_atm_option_contracts(
    spot_price,
    strikes_each_side=5
):

    contracts = get_nifty_option_contracts()

    if contracts.empty or spot_price is None:
        return pd.DataFrame()

    strike_interval = 50

    atm = round(
        float(spot_price) / strike_interval
    ) * strike_interval

    low = (
        atm -
        strikes_each_side * strike_interval
    )

    high = (
        atm +
        strikes_each_side * strike_interval
    )

    result = contracts[
        (contracts["strike"] >= low) &
        (contracts["strike"] <= high)
    ].copy()

    result = result.sort_values(
        ["strike", "instrument_type"]
    )

    return result


# =========================================================
# LIVE OPTION QUOTES
# =========================================================

def get_live_option_chain(
    spot_price,
    strikes_each_side=5
):

    kite = get_kite_client()

    contracts = get_atm_option_contracts(
        spot_price,
        strikes_each_side
    )

    if contracts.empty:
        return pd.DataFrame()

    tokens = contracts[
        "instrument_token"
    ].astype(int).tolist()

    instrument_keys = [
        f"NFO:{symbol}"
        for symbol in contracts["tradingsymbol"]
    ]

    quotes = {}

    # Kite quote requests are kept in manageable batches
    batch_size = 100

    for i in range(
        0,
        len(instrument_keys),
        batch_size
    ):

        batch = instrument_keys[
            i:i + batch_size
        ]

        response = kite.quote(batch)

        if response:
            quotes.update(response)

    rows = []

    for _, contract in contracts.iterrows():

        symbol = contract["tradingsymbol"]

        key = f"NFO:{symbol}"

        quote = quotes.get(key, {})

        rows.append(
            {
                "strike": contract["strike"],
                "type": contract["instrument_type"],
                "symbol": symbol,
                "token": contract["instrument_token"],
                "ltp": quote.get(
                    "last_price"
                ),
                "volume": quote.get(
                    "volume"
                ),
                "oi": quote.get(
                    "oi"
                ),
                "oi_day_high": quote.get(
                    "oi_day_high"
                ),
                "oi_day_low": quote.get(
                    "oi_day_low"
                ),
                "last_quantity": quote.get(
                    "last_quantity"
                ),
                "average_price": quote.get(
                    "average_price"
                ),
            }
        )

    result = pd.DataFrame(rows)

    if result.empty:
        return result

    numeric_columns = [
        "strike",
        "ltp",
        "volume",
        "oi",
        "oi_day_high",
        "oi_day_low",
        "last_quantity",
        "average_price"
    ]

    for column in numeric_columns:

        result[column] = pd.to_numeric(
            result[column],
            errors="coerce"
        )

    return result


# =========================================================
# PCR
# =========================================================

def calculate_pcr(option_data):

    if option_data.empty:
        return None

    calls = option_data[
        option_data["type"] == "CE"
    ]

    puts = option_data[
        option_data["type"] == "PE"
    ]

    call_oi = calls["oi"].fillna(0).sum()
    put_oi = puts["oi"].fillna(0).sum()

    if call_oi <= 0:
        return None

    return round(
        float(put_oi / call_oi),
        2
    )


# =========================================================
# MAX CALL / PUT OI
# =========================================================

def calculate_support_resistance(option_data):

    if option_data.empty:
        return None, None

    calls = option_data[
        option_data["type"] == "CE"
    ].copy()

    puts = option_data[
        option_data["type"] == "PE"
    ].copy()

    resistance = None
    support = None

    if not calls.empty:

        calls = calls.dropna(
            subset=["oi"]
        )

        if not calls.empty:

            resistance = calls.loc[
                calls["oi"].idxmax(),
                "strike"
            ]

    if not puts.empty:

        puts = puts.dropna(
            subset=["oi"]
        )

        if not puts.empty:

            support = puts.loc[
                puts["oi"].idxmax(),
                "strike"
            ]

    return support, resistance


# =========================================================
# OPTION SENTIMENT
# =========================================================

def option_sentiment(option_data):

    pcr = calculate_pcr(option_data)

    if pcr is None:
        return "NO DATA", 50

    if pcr >= 1.20:
        return "BULLISH", 70

    if pcr <= 0.80:
        return "BEARISH", 30

    return "NEUTRAL", 50
