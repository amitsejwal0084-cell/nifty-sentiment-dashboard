import streamlit as st
import pandas as pd
from kiteconnect import KiteConnect


def get_kite_client():

    api_key = st.secrets.get("KITE_API_KEY")
    access_token = st.session_state.get("access_token")

    if not api_key:
        raise Exception("KITE_API_KEY नहीं मिला।")

    if not access_token:
        raise Exception("Kite access token नहीं मिला।")

    kite = KiteConnect(
        api_key=api_key
    )

    kite.set_access_token(
        access_token
    )

    return kite


def get_live_option_chain(
    spot_price,
    strikes_each_side=10
):

    kite = get_kite_client()

    instruments = kite.instruments("NFO")

    df = pd.DataFrame(instruments)

    if df.empty:
        return pd.DataFrame()

    df["expiry"] = pd.to_datetime(
        df["expiry"],
        errors="coerce"
    ).dt.date

    df["strike"] = pd.to_numeric(
        df["strike"],
        errors="coerce"
    )

    today = pd.Timestamp.now().date()

    options = df[
        (df["name"] == "NIFTY") &
        (df["instrument_type"].isin(["CE", "PE"])) &
        (df["expiry"] >= today)
    ].copy()

    if options.empty:
        return pd.DataFrame()

    expiry = sorted(
        options["expiry"].dropna().unique()
    )[0]

    options = options[
        options["expiry"] == expiry
    ].copy()

    atm = round(
        float(spot_price) / 50
    ) * 50

    low = atm - (
        strikes_each_side * 50
    )

    high = atm + (
        strikes_each_side * 50
    )

    options = options[
        (options["strike"] >= low) &
        (options["strike"] <= high)
    ].copy()

    symbols = [
        "NFO:" + symbol
        for symbol in options["tradingsymbol"]
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

        response = kite.quote(batch)

        if response:
            quotes.update(response)

    rows = []

    for _, row in options.iterrows():

        symbol = row["tradingsymbol"]

        q = quotes.get(
            "NFO:" + symbol,
            {}
        )

        rows.append(
            {
                "strike": row["strike"],
                "type": row["instrument_type"],
                "symbol": symbol,
                "ltp": q.get("last_price"),
                "oi": q.get("oi"),
                "volume": q.get("volume"),
            }
        )

    return pd.DataFrame(rows)


def calculate_pcr(option_data):

    if option_data.empty:
        return None

    ce_oi = option_data[
        option_data["type"] == "CE"
    ]["oi"].fillna(0).sum()

    pe_oi = option_data[
        option_data["type"] == "PE"
    ]["oi"].fillna(0).sum()

    if ce_oi == 0:
        return None

    return round(
        pe_oi / ce_oi,
        2
    )


def calculate_support_resistance(
    option_data
):

    if option_data.empty:
        return None, None

    calls = option_data[
        option_data["type"] == "CE"
    ]

    puts = option_data[
        option_data["type"] == "PE"
    ]

    resistance = None
    support = None

    if not calls.empty:

        valid = calls.dropna(
            subset=["oi"]
        )

        if not valid.empty:

            resistance = valid.loc[
                valid["oi"].idxmax(),
                "strike"
            ]

    if not puts.empty:

        valid = puts.dropna(
            subset=["oi"]
        )

        if not valid.empty:

            support = valid.loc[
                valid["oi"].idxmax(),
                "strike"
            ]

    return support, resistance


def calculate_max_pain(
    option_data
):

    if option_data.empty:
        return None

    strikes = sorted(
        option_data["strike"]
        .dropna()
        .unique()
    )

    if not strikes:
        return None

    calls = option_data[
        option_data["type"] == "CE"
    ]

    puts = option_data[
        option_data["type"] == "PE"
    ]

    pain = {}

    for test_strike in strikes:

        call_pain = (
            (
                test_strike -
                calls["strike"]
            ).clip(lower=0)
            * calls["oi"].fillna(0)
        ).sum()

        put_pain = (
            (
                puts["strike"] -
                test_strike
            ).clip(lower=0)
            * puts["oi"].fillna(0)
        ).sum()

        pain[test_strike] = (
            call_pain + put_pain
        )

    return min(
        pain,
        key=pain.get
    )


def calculate_snapshot_oi_change(
    current_data
):

    if current_data.empty:
        return current_data

    previous = st.session_state.get(
        "previous_option_oi",
        {}
    )

    data = current_data.copy()

    data["oi_change"] = data.apply(
        lambda row:
        row["oi"] -
        previous.get(
            row["symbol"],
            row["oi"]
        ),
        axis=1
    )

    st.session_state[
        "previous_option_oi"
    ] = dict(
        zip(
            data["symbol"],
            data["oi"].fillna(0)
        )
    )

    return data


def calculate_buildup(
    option_data
):

    if option_data.empty:
        return option_data

    data = option_data.copy()

    data["buildup"] = "NEUTRAL"

    data.loc[
        data["oi_change"] > 0,
        "buildup"
    ] = "OI BUILDUP"

    data.loc[
        data["oi_change"] < 0,
        "buildup"
    ] = "OI UNWINDING"

    return data


def option_sentiment(
    option_data
):

    pcr = calculate_pcr(
        option_data
    )

    if pcr is None:
        return "NO DATA", 50

    if pcr >= 1.20:
        return "BULLISH", 70

    if pcr <= 0.80:
        return "BEARISH", 30

    return "NEUTRAL", 50
