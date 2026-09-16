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
        raise Exception(
            "KITE_API_KEY Streamlit Secrets में नहीं मिला।"
        )

    if not access_token:
        raise Exception(
            "Kite access token नहीं मिला। पहले Kite Login करें।"
        )

    kite = KiteConnect(
        api_key=api_key
    )

    kite.set_access_token(
        access_token
    )

    return kite


# =========================================================
# NFO INSTRUMENTS
# =========================================================

@st.cache_data(ttl=3600)
def load_nfo_instruments(
    api_key,
    access_token
):

    kite = KiteConnect(
        api_key=api_key
    )

    kite.set_access_token(
        access_token
    )

    instruments = kite.instruments(
        "NFO"
    )

    df = pd.DataFrame(
        instruments
    )

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
# NIFTY EXPIRY
# =========================================================

def get_nearest_nifty_expiry():

    api_key = st.secrets.get(
        "KITE_API_KEY"
    )

    access_token = st.session_state.get(
        "access_token"
    )

    df = load_nfo_instruments(
        api_key,
        access_token
    )

    if df.empty:
        return None

    today = date.today()

    nifty = df[
        (df["name"] == "NIFTY") &
        (
            df["instrument_type"]
            .isin(["CE", "PE"])
        ) &
        (df["expiry"] >= today)
    ].copy()

    if nifty.empty:
        return None

    return sorted(
        nifty["expiry"].dropna().unique()
    )[0]


# =========================================================
# NIFTY OPTIONS
# =========================================================

def get_nifty_option_contracts():

    api_key = st.secrets.get(
        "KITE_API_KEY"
    )

    access_token = st.session_state.get(
        "access_token"
    )

    df = load_nfo_instruments(
        api_key,
        access_token
    )

    if df.empty:
        return pd.DataFrame()

    expiry = get_nearest_nifty_expiry()

    if expiry is None:
        return pd.DataFrame()

    options = df[
        (df["name"] == "NIFTY") &
        (df["expiry"] == expiry) &
        (
            df["instrument_type"]
            .isin(["CE", "PE"])
        )
    ].copy()

    return options


# =========================================================
# ATM OPTION CONTRACTS
# =========================================================

def get_atm_option_contracts(
    spot_price,
    strikes_each_side=10
):

    contracts = get_nifty_option_contracts()

    if (
        contracts.empty
        or spot_price is None
    ):
        return pd.DataFrame()

    strike_interval = 50

    atm = round(
        float(spot_price)
        / strike_interval
    ) * strike_interval

    low = (
        atm -
        strikes_each_side
        * strike_interval
    )

    high = (
        atm +
        strikes_each_side
        * strike_interval
    )

    result = contracts[
        (contracts["strike"] >= low) &
        (contracts["strike"] <= high)
    ].copy()

    result = result.sort_values(
        [
            "strike",
            "instrument_type"
        ]
    )

    return result


# =========================================================
# LIVE OPTION CHAIN
# =========================================================

def get_live_option_chain(
    spot_price,
    strikes_each_side=10
):

    kite = get_kite_client()

    contracts = get_atm_option_contracts(
        spot_price,
        strikes_each_side
    )

    if contracts.empty:
        return pd.DataFrame()

    instrument_keys = [
        f"NFO:{symbol}"
        for symbol in contracts[
            "tradingsymbol"
        ]
    ]

    quotes = {}

    batch_size = 100

    for i in range(
        0,
        len(instrument_keys),
        batch_size
    ):

        batch = instrument_keys[
            i:i + batch_size
        ]

        response = kite.quote(
            batch
        )

        if response:
            quotes.update(
                response
            )

    rows = []

    for _, contract in contracts.iterrows():

        symbol = contract[
            "tradingsymbol"
        ]

        key = f"NFO:{symbol}"

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

        bid = (
            buy_depth[0]["price"]
            if buy_depth
            else None
        )

        ask = (
            sell_depth[0]["price"]
            if sell_depth
            else None
        )

        rows.append({

            "strike": contract[
                "strike"
            ],

            "type": contract[
                "instrument_type"
            ],

            "symbol": symbol,

            "token": contract[
                "instrument_token"
            ],

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

            "bid": bid,

            "ask": ask,

            "last_quantity": quote.get(
                "last_quantity"
            ),

            "average_price": quote.get(
                "average_price"
            )

        })

    result = pd.DataFrame(
        rows
    )

    if result.empty:
        return result

    numeric_columns = [

        "strike",
        "ltp",
        "volume",
        "oi",
        "oi_day_high",
        "oi_day_low",
        "bid",
        "ask",
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

def calculate_pcr(
    option_data
):

    if option_data.empty:
        return None

    calls = option_data[
        option_data["type"] == "CE"
    ]

    puts = option_data[
        option_data["type"] == "PE"
    ]

    call_oi = (
        calls["oi"]
        .fillna(0)
        .sum()
    )

    put_oi = (
        puts["oi"]
        .fillna(0)
        .sum()
    )

    if call_oi <= 0:
        return None

    return round(
        float(
            put_oi / call_oi
        ),
        2
    )


# =========================================================
# SUPPORT / RESISTANCE
# =========================================================

def calculate_support_resistance(
    option_data
):

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
# OI CHANGE FROM PREVIOUS SNAPSHOT
# =========================================================

def calculate_snapshot_oi_change(
    current_data
):

    if current_data.empty:
        return current_data

    previous = st.session_state.get(
        "previous_option_oi"
    )

    current = current_data.copy()

    if previous is None:

        current["oi_change"] = 0

    else:

        current["oi_change"] = (
            current.apply(
                lambda row:
                row["oi"]
                - previous.get(
                    row["symbol"],
                    row["oi"]
                ),
                axis=1
            )
        )

    st.session_state[
        "previous_option_oi"
    ] = dict(
        zip(
            current["symbol"],
            current["oi"].fillna(0)
        )
    )

    return current


# =========================================================
# CALL / PUT OI BUILDUP
# =========================================================

def calculate_buildup(
    option_data
):

    if option_data.empty:
        return option_data

    data = option_data.copy()

    def buildup(row):

        oi_change = row.get(
            "oi_change",
            0
        )

        ltp = row.get(
            "ltp",
            0
        )

        average_price = row.get(
            "average_price",
            0
        )

        if pd.isna(oi_change):
            return "NO DATA"

        if pd.isna(ltp):
            return "NO DATA"

        if pd.isna(average_price):
            average_price = ltp

        price_up = (
            ltp > average_price
        )

        price_down = (
            ltp < average_price
        )

        if (
            oi_change > 0
            and price_up
        ):
            return "LONG BUILDUP"

        if (
            oi_change > 0
            and price_down
        ):
            return "SHORT BUILDUP"

        if (
            oi_change < 0
            and price_up
        ):
            return "SHORT COVERING"

        if (
            oi_change < 0
            and price_down
        ):
            return "LONG UNWINDING"

        return "NEUTRAL"

    data["buildup"] = data.apply(
        buildup,
        axis=1
    )

    return data


# =========================================================
# MAX PAIN
# =========================================================

def calculate_max_pain(
    option_data
):

    if option_data.empty:
        return None

    data = option_data.copy()

    data["oi"] = pd.to_numeric(
        data["oi"],
        errors="coerce"
    ).fillna(0)

    strikes = sorted(
        data["strike"]
        .dropna()
        .unique()
    )

    if not strikes:
        return None

    calls = data[
        data["type"] == "CE"
    ]

    puts = data[
        data["type"] == "PE"
    ]

    pain_values = {}

    for test_strike in strikes:

        call_pain = (
            (
                test_strike
                - calls["strike"]
            ).clip(lower=0)
            * calls["oi"]
        ).sum()

        put_pain = (
            (
                puts["strike"]
                - test_strike
            ).clip(lower=0)
            * puts["oi"]
        ).sum()

        pain_values[
            test_strike
        ] = call_pain + put_pain

    if not pain_values:
        return None

    return min(
        pain_values,
        key=pain_values.get
    )


# =========================================================
# OPTION SENTIMENT
# =========================================================

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
